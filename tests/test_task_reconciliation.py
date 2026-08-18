from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from app.product.recent_review_service import RecentReviewApplicationResult
from app.product.recent_review import RecentReviewRuntimeRequestCompiler
from app.product.recent_review_service import RecentReviewApplicationService
from app.product.run_receipts import FileRunReceiptStore
from app.product.run_receipts import RunReceiptReference
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.runtime import RuntimeExecutionFactory
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.runtime.signals import RuntimePublicationStatus
from app.runtime.models import RuntimeStatus
from app.skills.recent_form_review import RecentFormReviewOutput
from app.tasks.models import (
    ReviewTask,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.recent_review_executor import (
    RecentReviewTaskExecutionError,
    RecentReviewTaskExecutor,
)
from app.tasks.reconciliation import (
    ManualRecoveryStatus,
    ManualReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
    ReconciliationStatus,
    ReviewTaskReconciler,
    TaskReconciliationError,
    TaskTerminalEvidenceError,
)
from tests.test_run_query_service import _create_terminal_run
from tests.test_agent_draft_preparer import demo_summary
from tests.test_agent_runtime import FactoryProbe, RuntimeProvider


NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)


def running_task(
    *,
    run_id: str = "review_reconcile_demo",
    number: int = 1,
    payload: dict | None = None,
) -> ReviewTask:
    created = NOW + timedelta(seconds=number)
    return ReviewTask(
        task_id=UUID(f"50000000-0000-4000-8000-{number:012d}"),
        run_id=run_id,
        task_kind="recent_review",
        schema_version="1.0",
        owner_id="owner-1",
        idempotency_key=f"request-{number}",
        request_fingerprint="0" * 64,
        request_payload=payload
        or {
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        status=TaskStatus.RUNNING,
        worker_id="worker-1",
        created_at=created,
        updated_at=created + timedelta(seconds=1),
        claimed_at=created + timedelta(seconds=1),
        finished_at=None,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )


def terminal(
    *,
    run_id: str,
    publication: TaskPublicationStatus = TaskPublicationStatus.PUBLISHED,
    report_available: bool = True,
) -> TaskTerminal:
    return TaskTerminal(
        run_id=run_id,
        terminal_reason=(
            "quality_gate_passed"
            if publication is TaskPublicationStatus.PUBLISHED
            else "deterministic_fallback"
            if publication is TaskPublicationStatus.DEGRADED
            else "quality_gate_rejected"
        ),
        publication_status=publication,
        report_available=report_available,
        trace_reference=RuntimeTraceReference(
            run_id=run_id,
            sha256="a" * 64,
        ),
        receipt_reference=RunReceiptReference(
            run_id=run_id,
            sha256="b" * 64,
        ),
        artifact_reference=(
            RuntimeArtifactReference(
                kind="final_report",
                schema_version="1.0",
                relative_path="output/final_report.md",
                sha256="c" * 64,
                producer="review_harness.publisher",
            )
            if report_available
            else None
        ),
    )


def application_result(
    *,
    run_id: str,
    publication: RuntimePublicationStatus = RuntimePublicationStatus.PUBLISHED,
) -> RecentReviewApplicationResult:
    return RecentReviewApplicationResult(
        run_id=run_id,
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=publication,
        terminal_reason=(
            "quality_gate_passed"
            if publication is RuntimePublicationStatus.PUBLISHED
            else "deterministic_fallback"
            if publication is RuntimePublicationStatus.DEGRADED
            else "quality_gate_rejected"
        ),
        output=RecentFormReviewOutput(
            run_id=run_id,
            status=publication.value,
            report=None
            if publication is RuntimePublicationStatus.REJECTED
            else "# report",
            evaluation_score=91
            if publication is RuntimePublicationStatus.PUBLISHED
            else None,
        ),
        trace_reference=RuntimeTraceReference(
            run_id=run_id,
            sha256="a" * 64,
        ),
    )


class FakeApplication:
    def __init__(self, result: RecentReviewApplicationResult):
        self.result = result
        self.calls: list[tuple[object, str]] = []

    def review(self, request, *, run_id: str):
        self.calls.append((request, run_id))
        return self.result


class FakeVerifier:
    def __init__(self, result: TaskTerminal | Exception):
        self.result = result
        self.calls: list[ReviewTask] = []

    def terminal_for(self, task: ReviewTask) -> TaskTerminal:
        self.calls.append(task)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRepository:
    def __init__(self, *, succeed_result: bool = True, fail_result: bool = True):
        self.succeed_result = succeed_result
        self.fail_result = fail_result
        self.succeed_calls: list[tuple[UUID, str, TaskTerminal]] = []
        self.fail_calls: list[tuple[UUID, str, str]] = []

    def succeed(self, *, task_id, worker_id, terminal):
        self.succeed_calls.append((task_id, worker_id, terminal))
        return self.succeed_result

    def fail(self, *, task_id, worker_id, reason):
        self.fail_calls.append((task_id, worker_id, reason))
        return self.fail_result


def _fingerprint_for(task: ReviewTask) -> str:
    from app.tasks.fingerprint import compute_task_request_fingerprint

    return compute_task_request_fingerprint(
        task_kind=task.task_kind,
        schema_version=task.schema_version,
        request_payload=task.request_payload,
    )


def test_executor_passes_sql_run_id_and_returns_verified_terminal():
    task = running_task()
    task = task.model_copy(update={"request_fingerprint": _fingerprint_for(task)})
    result = application_result(run_id=task.run_id)
    verifier = FakeVerifier(terminal(run_id=task.run_id))
    app = FakeApplication(result)

    output = RecentReviewTaskExecutor(
        application_service=app,
        evidence_verifier=verifier,
    ).execute(task)

    assert output.run_id == task.run_id
    assert app.calls[0][1] == task.run_id
    assert verifier.calls == [task]


def test_executor_rejects_fingerprint_mismatch_before_application():
    task = running_task()
    app = FakeApplication(application_result(run_id=task.run_id))
    verifier = FakeVerifier(terminal(run_id=task.run_id))

    with pytest.raises(RecentReviewTaskExecutionError) as caught:
        RecentReviewTaskExecutor(
            application_service=app,
            evidence_verifier=verifier,
        ).execute(task)

    assert caught.value.code == "task_fingerprint_mismatch"
    assert app.calls == []
    assert verifier.calls == []


@pytest.mark.parametrize(
    "publication",
    (
        RuntimePublicationStatus.PUBLISHED,
        RuntimePublicationStatus.DEGRADED,
        RuntimePublicationStatus.REJECTED,
    ),
)
def test_executor_accepts_all_legal_harness_publication_terminals(publication):
    task = running_task()
    task = task.model_copy(update={"request_fingerprint": _fingerprint_for(task)})
    task_terminal = terminal(
        run_id=task.run_id,
        publication=TaskPublicationStatus(publication.value),
        report_available=publication is not RuntimePublicationStatus.REJECTED,
    )
    output = RecentReviewTaskExecutor(
        application_service=FakeApplication(
            application_result(run_id=task.run_id, publication=publication)
        ),
        evidence_verifier=FakeVerifier(task_terminal),
    ).execute(task)

    assert output.publication_status.value == publication.value


def test_executor_rejects_application_and_receipt_terminal_mismatch():
    task = running_task()
    task = task.model_copy(update={"request_fingerprint": _fingerprint_for(task)})

    with pytest.raises(RecentReviewTaskExecutionError) as caught:
        RecentReviewTaskExecutor(
            application_service=FakeApplication(
                application_result(run_id=task.run_id)
            ),
            evidence_verifier=FakeVerifier(
                terminal(
                    run_id=task.run_id,
                    publication=TaskPublicationStatus.DEGRADED,
                    report_available=True,
                )
            ),
        ).execute(task)

    assert caught.value.code == "terminal_identity_mismatch"


@pytest.mark.parametrize(
    "publication",
    (
        RuntimePublicationStatus.PUBLISHED,
        RuntimePublicationStatus.DEGRADED,
        RuntimePublicationStatus.REJECTED,
    ),
)
def test_concrete_verifier_builds_all_legal_terminals_from_complete_evidence(
    tmp_path,
    publication,
):
    _, receipt = _create_terminal_run(
        tmp_path,
        run_id=f"reconcile_verified_{publication.value}",
        publication=publication,
    )
    task = running_task(run_id=receipt.run_id)

    output = RecentReviewTerminalEvidenceVerifier(tmp_path).terminal_for(task)

    assert output.run_id == receipt.run_id
    assert output.receipt_reference.sha256
    assert output.trace_reference == receipt.trace_reference
    assert output.publication_status.value == publication.value
    if publication is RuntimePublicationStatus.REJECTED:
        assert output.report_available is False
        assert output.artifact_reference is None
    else:
        assert output.report_available is True
        assert output.artifact_reference is not None
        assert output.artifact_reference.kind == "final_report"


def test_concrete_verifier_rejects_receipt_bytes_changed_during_verification(
    tmp_path,
):
    _, receipt = _create_terminal_run(tmp_path, run_id="reconcile_receipt_race")
    task = running_task(run_id=receipt.run_id)

    class MutatingQuery:
        def __init__(self):
            from app.product.run_query import RunQueryService

            self._delegate = RunQueryService(tmp_path)

        def get_run(self, run_id: str):
            view = self._delegate.get_run(run_id)
            path = tmp_path / run_id / "api_run_receipt.json"
            path.write_bytes(path.read_bytes() + b" ")
            return view

    verifier = RecentReviewTerminalEvidenceVerifier(
        tmp_path,
        query_service=MutatingQuery(),
    )

    with pytest.raises(TaskTerminalEvidenceError) as caught:
        verifier.terminal_for(task)

    assert caught.value.code == "terminal_evidence_invalid"


def test_reconciler_only_projects_a_complete_receipt_and_never_reruns():
    task = running_task()
    repository = FakeRepository()
    verifier = FakeVerifier(terminal(run_id=task.run_id))

    result = ReviewTaskReconciler(
        repository=repository,
        verifier=verifier,
    ).reconcile(task)

    assert result.status is ReconciliationStatus.RECONCILED
    assert result.reason == "reconciled"
    assert len(repository.succeed_calls) == 1


def test_reconciler_projects_recovery_required_when_receipt_is_missing():
    task = running_task()
    repository = FakeRepository()
    verifier = FakeVerifier(TaskTerminalEvidenceError("receipt_missing"))

    result = ReviewTaskReconciler(
        repository=repository,
        verifier=verifier,
    ).reconcile(task)

    assert result.status is ReconciliationStatus.RECOVERY_REQUIRED
    assert result.reason == "receipt_missing"
    assert repository.succeed_calls == []


def test_reconciler_maps_unexpected_evidence_failure_to_a_body_free_error():
    task = running_task()
    repository = FakeRepository()
    verifier = FakeVerifier(RuntimeError("C:\\private database-secret"))

    with pytest.raises(TaskReconciliationError) as caught:
        ReviewTaskReconciler(
            repository=repository,
            verifier=verifier,
        ).reconcile(task)

    assert caught.value.code == "terminal_evidence_read_failed"
    assert "private" not in str(caught.value)
    assert repository.succeed_calls == []


def test_reconciler_does_not_overwrite_a_lost_owner():
    task = running_task()
    repository = FakeRepository(succeed_result=False)

    result = ReviewTaskReconciler(
        repository=repository,
        verifier=FakeVerifier(terminal(run_id=task.run_id)),
    ).reconcile(task)

    assert result.status is ReconciliationStatus.OWNERSHIP_LOST
    assert result.reason == "task_ownership_lost"


def test_reconciler_rejects_evidence_for_a_different_run_before_sql_cas():
    task = running_task()
    repository = FakeRepository()

    result = ReviewTaskReconciler(
        repository=repository,
        verifier=FakeVerifier(terminal(run_id="review_other_run")),
    ).reconcile(task)

    assert result.status is ReconciliationStatus.RECOVERY_REQUIRED
    assert result.reason == "terminal_evidence_invalid"
    assert repository.succeed_calls == []


def test_manual_recovery_requires_exact_worker_confirmation_and_uses_cas():
    task = running_task()
    repository = FakeRepository()
    recovery = ManualReviewTaskRecovery(repository)

    with pytest.raises(ValueError, match="confirmation"):
        recovery.recover(
            task_id=task.task_id,
            worker_id="worker-1",
            confirmation_worker_id="worker-2",
        )
    assert repository.fail_calls == []

    result = recovery.recover(
        task_id=task.task_id,
        worker_id="worker-1",
        confirmation_worker_id="worker-1",
    )
    assert result.status is ManualRecoveryStatus.RECOVERED
    assert repository.fail_calls == [
        (task.task_id, "worker-1", "worker_confirmed_dead")
    ]


class FixtureSummaryBuilder:
    def build(self, **kwargs) -> dict:
        assert kwargs == {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "count": 10,
            "queue": 420,
        }
        return demo_summary()


def test_executor_runs_the_existing_offline_application_runtime_and_harness(
    tmp_path,
):
    task = running_task(run_id="review_executor_vertical")
    task = task.model_copy(update={"request_fingerprint": _fingerprint_for(task)})
    provider = RuntimeProvider()
    probe = FactoryProbe()
    composition = RuntimeCompositionRoot.from_directories(
        skills_root="skills",
        prompt_programs_root="prompt_programs",
    )
    runtime = composition.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        execution_factory=RuntimeExecutionFactory(
            knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
                Path("data/rag_docs")
            ),
            evaluator_factory=probe.evaluator_factory,
            reviser_factory=probe.reviser_factory,
        ),
    )
    application = RecentReviewApplicationService(
        summary_builder=FixtureSummaryBuilder(),
        compiler=RecentReviewRuntimeRequestCompiler(
            composition.skill_catalog,
            run_id_factory=lambda: (_ for _ in ()).throw(
                AssertionError("SQL run_id must bypass generation")
            ),
        ),
        runtime=runtime,
        receipt_writer=FileRunReceiptStore(tmp_path),
    )

    output = RecentReviewTaskExecutor(
        application_service=application,
        evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
    ).execute(task)

    assert output.run_id == task.run_id
    assert output.publication_status is TaskPublicationStatus.PUBLISHED
    assert output.receipt_reference.sha256
    assert len(provider.requests) == 3
