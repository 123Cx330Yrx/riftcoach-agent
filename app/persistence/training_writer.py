from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa

from app.memory.models import MemoryCandidate, compute_payload_sha256
from app.memory.ports import MaterializationSession
from app.memory.training_models import (
    ParsedTrainingPlanWrite,
    ParsedTrainingProgressWrite,
    TrainingContractError,
    TrainingPlanAction,
)
from app.memory.training_ports import TrainingTargetWriter
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from app.persistence.typed_memory_writer import MemoryTargetVersionConflict


IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


class TrainingArtifactInvalid(TrainingContractError):
    def __init__(self) -> None:
        super().__init__("training_artifact_invalid")


class PostgresTrainingTargetWriter(TrainingTargetWriter):
    """Writes Plan/Progress using the Candidate Repository-owned transaction."""

    def __init__(
        self,
        *,
        plan_id_factory: IdFactory = uuid4,
        progress_id_factory: IdFactory = uuid4,
        clock: Clock | None = None,
    ) -> None:
        if not callable(plan_id_factory) or not callable(progress_id_factory):
            raise TypeError("training id factories must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._plan_id_factory = plan_id_factory
        self._progress_id_factory = progress_id_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def write_plan(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTrainingPlanWrite,
    ) -> UUID:
        _validate_session(session)
        if not isinstance(candidate, MemoryCandidate) or not isinstance(
            parsed, ParsedTrainingPlanWrite
        ):
            raise TypeError("training plan writer received invalid contracts")
        now = _as_utc(self._clock())
        _lock_scope(session, candidate.owner_id, candidate.relationship_id)
        _require_active_self_relationship(session, candidate)

        if parsed.action is TrainingPlanAction.ACTIVATE:
            current = session.scalar(
                sa.select(TrainingPlanRecord)
                .where(
                    TrainingPlanRecord.owner_id == candidate.owner_id,
                    TrainingPlanRecord.relationship_id == candidate.relationship_id,
                    TrainingPlanRecord.status == "active",
                )
                .with_for_update()
            )
            if current is None:
                if parsed.expected_version is not None:
                    raise MemoryTargetVersionConflict()
                version = 1
                supersedes = None
            else:
                if parsed.expected_version != current.version:
                    raise MemoryTargetVersionConflict()
                current.status = "superseded"
                current.status_candidate_id = candidate.candidate_id
                current.updated_at = now
                version = current.version + 1
                supersedes = current.plan_id
            plan_id = self._plan_id_factory()
            if not isinstance(plan_id, UUID):
                raise TypeError("plan_id_factory must return UUID")
            record = TrainingPlanRecord(
                plan_id=plan_id,
                schema_version="1.0",
                source_candidate_id=candidate.candidate_id,
                status_candidate_id=None,
                owner_id=candidate.owner_id,
                source_conversation_id=candidate.conversation_id,
                relationship_id=candidate.relationship_id,
                player_subject_id=candidate.player_subject_id,
                relationship_role=candidate.relationship_role.value,
                version=version,
                status="active",
                payload=parsed.normalized_payload,
                payload_sha256=compute_payload_sha256(parsed.normalized_payload),
                supersedes_plan_id=supersedes,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            return plan_id

        current = session.scalar(
            sa.select(TrainingPlanRecord)
            .where(
                TrainingPlanRecord.plan_id == parsed.plan_id,
                TrainingPlanRecord.owner_id == candidate.owner_id,
                TrainingPlanRecord.relationship_id == candidate.relationship_id,
                TrainingPlanRecord.player_subject_id == candidate.player_subject_id,
                TrainingPlanRecord.relationship_role == "self",
                TrainingPlanRecord.status == "active",
            )
            .with_for_update()
        )
        if current is None:
            raise TrainingContractError("training_plan_not_found")
        if parsed.expected_version != current.version:
            raise MemoryTargetVersionConflict()
        current.status = (
            "completed"
            if parsed.action is TrainingPlanAction.COMPLETE
            else "abandoned"
        )
        current.status_candidate_id = candidate.candidate_id
        current.updated_at = now
        session.flush()
        return current.plan_id

    def write_progress(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTrainingProgressWrite,
    ) -> UUID:
        _validate_session(session)
        if not isinstance(candidate, MemoryCandidate) or not isinstance(
            parsed, ParsedTrainingProgressWrite
        ):
            raise TypeError("training progress writer received invalid contracts")
        now = _as_utc(self._clock())
        plan = session.scalar(
            sa.select(TrainingPlanRecord)
            .where(
                TrainingPlanRecord.plan_id == parsed.plan_id,
                TrainingPlanRecord.owner_id == candidate.owner_id,
                TrainingPlanRecord.relationship_id == candidate.relationship_id,
                TrainingPlanRecord.player_subject_id == candidate.player_subject_id,
                TrainingPlanRecord.relationship_role == "self",
                TrainingPlanRecord.status == "active",
            )
            .with_for_update()
        )
        if plan is None or not _plan_allows_metric(plan.payload, parsed.metric_key):
            raise TrainingContractError("training_plan_metric_invalid")
        _require_complete_artifact(session, candidate)

        corrected = None
        if parsed.supersedes_progress_id is not None:
            corrected = session.scalar(
                sa.select(TrainingProgressRecord)
                .where(
                    TrainingProgressRecord.progress_id
                    == parsed.supersedes_progress_id,
                    TrainingProgressRecord.owner_id == candidate.owner_id,
                    TrainingProgressRecord.plan_id == parsed.plan_id,
                    TrainingProgressRecord.metric_key == parsed.metric_key,
                    TrainingProgressRecord.status == "active",
                )
                .with_for_update()
            )
            if corrected is None:
                raise TrainingContractError("training_progress_correction_invalid")

        progress_id = self._progress_id_factory()
        if not isinstance(progress_id, UUID):
            raise TypeError("progress_id_factory must return UUID")
        record = TrainingProgressRecord(
            progress_id=progress_id,
            schema_version="1.0",
            plan_id=parsed.plan_id,
            source_candidate_id=candidate.candidate_id,
            owner_id=candidate.owner_id,
            source_conversation_id=candidate.conversation_id,
            relationship_id=candidate.relationship_id,
            player_subject_id=candidate.player_subject_id,
            relationship_role=candidate.relationship_role.value,
            metric_key=parsed.metric_key,
            metric_value=parsed.metric_value,
            observed_at=parsed.observed_at,
            source_task_id=candidate.source_task_id,
            source_run_id=candidate.source_run_id,
            source_artifact_sha256=candidate.source_artifact_sha256,
            status="active",
            supersedes_progress_id=parsed.supersedes_progress_id,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        if corrected is not None:
            corrected.status = "superseded"
            corrected.updated_at = now
            session.flush()
        return progress_id


def _validate_session(session: MaterializationSession) -> None:
    for method in ("add", "flush", "execute", "scalar"):
        if not callable(getattr(session, method, None)):
            raise TypeError(f"materialization session must expose {method}()")


def _lock_scope(
    session: MaterializationSession,
    owner_id: str,
    relationship_id: UUID,
) -> None:
    digest = hashlib.sha256(
        f"training-plan\0{owner_id}\0{relationship_id}".encode("utf-8")
    ).digest()
    lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
    session.execute(
        sa.text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": lock_id},
    )


def _require_active_self_relationship(
    session: MaterializationSession,
    candidate: MemoryCandidate,
) -> None:
    relationship = session.scalar(
        sa.select(OwnerPlayerRelationshipRecord).where(
            OwnerPlayerRelationshipRecord.owner_id == candidate.owner_id,
            OwnerPlayerRelationshipRecord.relationship_id == candidate.relationship_id,
            OwnerPlayerRelationshipRecord.player_subject_id == candidate.player_subject_id,
            OwnerPlayerRelationshipRecord.relationship_role == "self",
            OwnerPlayerRelationshipRecord.status == "active",
        )
    )
    if relationship is None:
        raise TrainingContractError("training_scope_not_found")


def _require_complete_artifact(
    session: MaterializationSession,
    candidate: MemoryCandidate,
) -> None:
    task = session.scalar(
        sa.select(ReviewTaskRecord).where(
            ReviewTaskRecord.task_id == candidate.source_task_id,
            ReviewTaskRecord.run_id == candidate.source_run_id,
            ReviewTaskRecord.owner_id == candidate.owner_id,
            ReviewTaskRecord.conversation_id == candidate.conversation_id,
            ReviewTaskRecord.relationship_id == candidate.relationship_id,
            ReviewTaskRecord.player_subject_id == candidate.player_subject_id,
            ReviewTaskRecord.relationship_role == "self",
        )
    )
    artifact = None if task is None else task.artifact_reference
    if (
        task is None
        or task.status != "succeeded"
        or task.publication_status not in {"published", "degraded"}
        or not task.report_available
        or not isinstance(artifact, dict)
        or artifact.get("kind") != "final_report"
        or artifact.get("sha256") != candidate.source_artifact_sha256
    ):
        raise TrainingArtifactInvalid()


def _plan_allows_metric(payload: object, metric_key: str) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("metrics"), list):
        return False
    return any(
        isinstance(item, dict) and item.get("metric_key") == metric_key
        for item in payload["metrics"]
    )


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TypeError("clock must return timezone-aware datetime")
    return value.astimezone(timezone.utc)


__all__ = [
    "PostgresTrainingTargetWriter",
    "TrainingArtifactInvalid",
]
