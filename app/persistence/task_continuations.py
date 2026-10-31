"""Lease-fenced pins and explicit owner continuation of a paused candidate."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID
import re

import sqlalchemy as sa

from app.persistence.task_record import ReviewTaskRecord
from app.tasks.continuation import ContinuationError, ResumeContinuation
from app.tasks.models import TaskStatus
from app.tasks.reliable_runtime import TaskLifecycleEventKind


class PostgresTaskContinuations:
    def __init__(self, repository):
        self.repository = repository

    def _row(self, session, task_id, owner_id, *, lock=False):
        query = sa.select(ReviewTaskRecord).where(
            ReviewTaskRecord.task_id == task_id, ReviewTaskRecord.owner_id == owner_id)
        record = session.scalar(query.with_for_update() if lock else query)
        if record is None:
            raise ContinuationError("task_not_found")
        return record

    def load(self, *, owner_id, task_id):
        with self.repository._session_factory() as session:
            record = self._row(session, task_id, owner_id)
            value = deepcopy(record.continuation_reference)
            if value is not None:
                value["pause_reason"] = record.recovery_reason
            return value

    @staticmethod
    def _live(record, task, *, allow_cancel=False):
        from app.persistence.task_repository import _record_has_live_lease
        if task.lease is None or not _record_has_live_lease(record,
                worker_id=task.worker_id, lease_generation=task.lease.generation,
                lease_token=task.lease.private_token, now=datetime.now(timezone.utc)):
            raise ContinuationError("continuation_lease_lost")
        if record.cancel_requested_at is not None and not allow_cancel:
            raise ContinuationError("continuation_cancel_requested")

    def begin(self, task, binding):
        with self.repository._session_factory() as session, session.begin():
            record = self._row(session, task.task_id, task.owner_id, lock=True)
            self._live(record, task)
            value = deepcopy(record.continuation_reference)
            if value is None:
                from app.tasks.continuation import contract_for_worker_profile
                contract_for_worker_profile(binding["worker_profile"])
                value = dict(profile=binding["worker_profile"], binding=binding,
                             guard_sha256=None, checkpoint_sha256=None,
                             checkpoint=None, phase="prepared", manual_retry=False,
                             resumes={}, accounting=None)
            if value["profile"] != binding["worker_profile"] or value["binding"] != binding:
                raise ContinuationError("continuation_binding_changed")
            result = deepcopy(value)
            # A grant belongs to one claim. An interrupted uncommitted attempt
            # cannot acquire another grant merely by restarting the Worker.
            value["manual_retry"] = False
            record.continuation_reference = value
            return result

    def pin(self, task, checkpoint, accounting):
        with self.repository._session_factory() as session, session.begin():
            record = self._row(session, task.task_id, task.owner_id, lock=True)
            # Keep the just-observed cost after cancellation; the next dispatch
            # still checks the live cancellation fence independently.
            self._live(record, task, allow_cancel=True)
            value = deepcopy(record.continuation_reference)
            if value is None:
                raise ContinuationError("continuation_missing")
            if value["guard_sha256"] not in (None, checkpoint["guard_sha256"]):
                raise ContinuationError("continuation_guard_changed")
            value.update(checkpoint)
            value["accounting"] = accounting
            record.continuation_reference = value

    def pause(self, task, reason):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", reason):
            reason = "continuation_integrity_required"
        with self.repository._session_factory() as session, session.begin():
            record = self._row(session, task.task_id, task.owner_id, lock=True)
            self._live(record, task)
            if record.continuation_reference is None:
                raise ContinuationError("continuation_missing")
            now = max(record.updated_at, datetime.now(timezone.utc))
            record.status = TaskStatus.RECOVERY_REQUIRED.value
            record.recovery_required_at = record.updated_at = now
            record.recovery_reason = reason
            record.lease_token = record.lease_expires_at = None
            self.repository._append_event(session, record=record,
                event_kind=TaskLifecycleEventKind.RECOVERY_REQUIRED,
                operation_identity=f"continuation-paused-{task.lease_generation}",
                occurred_at=now, reason=reason)
            return True

    def resume(self, *, owner_id, task_id, request_id, command):
        if not isinstance(task_id, UUID) or not isinstance(command, ResumeContinuation):
            raise ContinuationError("continuation_conflict")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", request_id):
            raise ContinuationError("continuation_conflict")
        with self.repository._session_factory() as session, session.begin():
            record = self._row(session, task_id, owner_id, lock=True)
            value = deepcopy(record.continuation_reference)
            if value is None:
                raise ContinuationError("continuation_conflict")
            request = command.model_dump(mode="json")
            previous = value["resumes"].get(request_id)
            if previous is not None:
                if previous != request:
                    raise ContinuationError("continuation_conflict")
                return dict(task_id=str(task_id), run_id=record.run_id,
                            status=record.status, replayed=True)
            if (record.status != TaskStatus.RECOVERY_REQUIRED.value
                    or record.cancel_requested_at is not None
                    or value["checkpoint_sha256"] != command.checkpoint_sha256
                    or len(value["resumes"]) >= 100):
                raise ContinuationError("continuation_conflict")
            # Explicit retry only applies to a receipt-classified recoverable
            # failure. Unknown/pending intent is never resend permission.
            if command.manual_retry and record.recovery_reason not in {
                    "session_timeout_awaiting_manual_retry", "session_format_awaiting_manual_retry"}:
                raise ContinuationError("continuation_conflict")
            value["resumes"][request_id] = request
            value["manual_retry"] = command.manual_retry
            record.continuation_reference = value
            previous_worker = record.worker_id
            record.status = TaskStatus.QUEUED.value
            record.worker_id = record.claimed_at = record.heartbeat_at = None
            record.recovery_required_at = record.recovery_reason = None
            record.updated_at = max(record.updated_at, datetime.now(timezone.utc))
            self.repository._append_event(session, record=record,
                event_kind=TaskLifecycleEventKind.CONTINUATION_RESUMED,
                operation_identity=f"resume-{len(value['resumes'])}",
                occurred_at=record.updated_at, worker_id_override=previous_worker,
                reason="manual_retry" if command.manual_retry else "continue_checkpoint")
            return dict(task_id=str(task_id), run_id=record.run_id,
                        status=record.status, replayed=False)

    def recover_local_failure(self, *, owner_id, task_id, proof_path, proof_sha256, runs_root):
        """Administrative, receipt-checked transition; never a generic failed retry.

        The new directory must be prepared before this transaction. The old
        failed event is append-only and its terminal fields are retained here.
        Recovery only enables ordinary owner resume; it dispatches no request.
        """
        from app.product.local_failure_recovery import verify_local_failure_recovery
        from app.evaluation.sol_natural_session import SessionBlocked
        if not isinstance(task_id, UUID) or not re.fullmatch(r"[0-9a-f]{64}", proof_sha256):
            raise ContinuationError("continuation_conflict")
        with self.repository._session_factory() as session, session.begin():
            record = self._row(session, task_id, owner_id, lock=True)
            value = deepcopy(record.continuation_reference)
            if value is None:
                raise ContinuationError("continuation_conflict")
            previous = value.get("local_failure_recovery")
            if previous is not None:
                if previous["proof_sha256"] != proof_sha256 or previous["runs_root"] != str(runs_root):
                    raise ContinuationError("continuation_conflict")
                return dict(task_id=str(task_id), run_id=record.run_id, status=record.status, replayed=True)
            if (record.status != TaskStatus.FAILED.value or record.terminal_reason != "worker_execution_failed"
                    or record.cancel_requested_at is not None or record.report_available
                    or record.publication_reference is not None or record.publication_status is not None):
                raise ContinuationError("continuation_conflict")
            try:
                proof = verify_local_failure_recovery(proof_path, proof_sha256, runs_root=runs_root)
            except (OSError, ValueError, KeyError, SessionBlocked):
                raise ContinuationError("local_failure_recovery_invalid") from None
            parent = proof["parent_reference"]
            if (proof["binding"] != value["binding"] or proof["binding"]["task_id"] != str(task_id)
                    or proof["binding"]["owner_id"] != owner_id
                    or proof["binding"]["run_id"] != record.run_id
                    or any(parent[key] != value[key] for key in
                           ("guard_sha256", "checkpoint_sha256", "profile", "accounting"))):
                raise ContinuationError("continuation_conflict")
            value["local_failure_recovery"] = dict(proof_sha256=proof_sha256,
                runs_root=str(runs_root), parent_checkpoint_sha256=value["checkpoint_sha256"],
                failed_at=record.finished_at.isoformat(), terminal_reason=record.terminal_reason,
                runtime_terminal_reason="harness_execution_failed",
                lease_generation=record.lease_generation)
            value.update(proof["child_checkpoint"])
            value["manual_retry"] = False
            record.continuation_reference = value
            record.status = TaskStatus.RECOVERY_REQUIRED.value
            record.finished_at = record.terminal_reason = None
            record.recovery_reason = "local_artifact_failure_recovered"
            record.updated_at = record.recovery_required_at = max(record.updated_at, datetime.now(timezone.utc))
            self.repository._append_event(session, record=record,
                event_kind=TaskLifecycleEventKind.RECOVERY_REQUIRED,
                operation_identity="local-recovery-" + proof_sha256,
                occurred_at=record.updated_at, reason=record.recovery_reason)
            return dict(task_id=str(task_id), run_id=record.run_id, status=record.status, replayed=False)
