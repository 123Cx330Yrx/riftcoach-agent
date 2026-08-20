from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import sqlalchemy as sa

from app.memory.composition import build_typed_memory_materializers
from app.memory.models import (
    CandidateKind,
    CandidateMutationDisposition,
    DecisionActorKind,
    MemoryOperation,
    ProvenanceKind,
    TargetScope,
)
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.training_query_repository import PostgresTrainingQueryRepository
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


ARTIFACT_SHA = "a" * 64


def _identity_and_candidate(repository, factory, *, number, payload, kind, conversation_id, **kwargs):
    identity = repository.get_conversation_identity(
        owner_id="memory-owner",
        conversation_id=conversation_id,
    )
    assert identity is not None
    pending = pending_candidate(
        number,
        conversation_id=conversation_id,
        payload=payload,
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=kind,
        memory_key=("active_plan" if kind is CandidateKind.TRAINING_PLAN else "deaths_before_15"),
        operation=(MemoryOperation.SET if kind is CandidateKind.TRAINING_PLAN else MemoryOperation.APPEND),
        provenance_kind=(
            ProvenanceKind.USER_STRUCTURED_INPUT
            if kind is CandidateKind.TRAINING_PLAN
            else ProvenanceKind.DETERMINISTIC_RUN_FACT
        ),
        **kwargs,
    )
    created = repository.create_or_replay_candidate(
        pending,
        identity=identity,
        requires_confirmation=kind is CandidateKind.TRAINING_PLAN,
        gate_policy_version="memory-gate-v1",
    )
    assert created.candidate is not None
    return created.candidate


def _activate_payload(*, expected_version=None):
    return {
        "value": {
            "action": "activate",
            "title": "Reduce early deaths",
            "objective": "Review positioning before minute 15",
            "metrics": [
                {
                    "metric_key": "deaths_before_15",
                    "direction": "decrease",
                    "unit": "count",
                    "stable_tolerance": 0.0,
                }
            ],
        },
        "expected_version": expected_version,
    }


def _accept(repository, candidate_id):
    return repository.accept_candidate(
        owner_id="memory-owner",
        candidate_id=candidate_id,
        actor_id="memory-owner",
        actor_kind=DecisionActorKind.USER,
        now=BASE + timedelta(days=1),
        materializers=build_typed_memory_materializers(),
    )


def _seed_terminal_review(
    factory,
    *,
    number: int,
    conversation_id: UUID,
    relationship_id: UUID,
    subject_id: UUID,
    artifact_sha: str = ARTIFACT_SHA,
    status: str = "succeeded",
):
    task_id = UUID(f"85000000-0000-4000-8000-{number:012d}")
    run_id = f"training-run-{number}"
    with factory.begin() as session:
        session.add(
            ReviewTaskRecord(
                task_id=task_id,
                run_id=run_id,
                task_kind="recent_review",
                schema_version="2.0",
                owner_id="memory-owner",
                idempotency_key=f"training-task-{number}",
                request_fingerprint=f"{number:064x}",
                request_payload={"count": 3, "queue": "ranked_solo"},
                conversation_id=conversation_id,
                relationship_id=relationship_id,
                player_subject_id=subject_id,
                relationship_role="self",
                status=status,
                worker_id="training-worker",
                created_at=BASE,
                updated_at=BASE + timedelta(minutes=2),
                claimed_at=BASE + timedelta(minutes=1),
                finished_at=BASE + timedelta(minutes=2),
                terminal_reason="completed" if status == "succeeded" else "failed",
                publication_status="published" if status == "succeeded" else None,
                report_available=status == "succeeded",
                trace_reference={"run_id": run_id},
                receipt_reference={"run_id": run_id},
                artifact_reference=(
                    {
                        "kind": "final_report",
                        "schema_version": "1.0",
                        "relative_path": "output/final_report.md",
                        "sha256": artifact_sha,
                        "producer": "review-harness",
                    }
                    if status == "succeeded"
                    else None
                ),
            )
        )
    return task_id, run_id


def test_plan_activate_replace_and_complete_are_candidate_atomic():
    with migrated_memory_repository() as (repository, factory, _engine):
        _subject, relationship, conversation = seed_conversation(factory)
        first = _identity_and_candidate(
            repository,
            factory,
            number=101,
            payload=_activate_payload(),
            kind=CandidateKind.TRAINING_PLAN,
            conversation_id=conversation,
        )
        assert _accept(repository, first.candidate_id).disposition is CandidateMutationDisposition.ACCEPTED

        second = _identity_and_candidate(
            repository,
            factory,
            number=102,
            payload=_activate_payload(expected_version=1),
            kind=CandidateKind.TRAINING_PLAN,
            conversation_id=conversation,
        )
        second_result = _accept(repository, second.candidate_id)
        assert second_result.disposition is CandidateMutationDisposition.ACCEPTED

        with factory() as session:
            plans = list(
                session.scalars(
                    sa.select(TrainingPlanRecord).order_by(TrainingPlanRecord.version)
                )
            )
        assert [(row.version, row.status) for row in plans] == [(1, "superseded"), (2, "active")]
        assert plans[0].status_candidate_id == second.candidate_id
        assert plans[1].supersedes_plan_id == plans[0].plan_id

        terminal = _identity_and_candidate(
            repository,
            factory,
            number=103,
            payload={
                "value": {"action": "complete", "plan_id": str(plans[1].plan_id)},
                "expected_version": 2,
            },
            kind=CandidateKind.TRAINING_PLAN,
            conversation_id=conversation,
        )
        assert _accept(repository, terminal.candidate_id).disposition is CandidateMutationDisposition.ACCEPTED
        with factory() as session:
            latest = session.get(TrainingPlanRecord, plans[1].plan_id)
            assert latest is not None and latest.status == "completed"
            assert latest.status_candidate_id == terminal.candidate_id


def test_plan_stale_version_keeps_candidate_pending():
    with migrated_memory_repository() as (repository, factory, _engine):
        _subject, _relationship, conversation = seed_conversation(factory)
        first = _identity_and_candidate(
            repository, factory, number=111, payload=_activate_payload(),
            kind=CandidateKind.TRAINING_PLAN, conversation_id=conversation,
        )
        _accept(repository, first.candidate_id)
        stale = _identity_and_candidate(
            repository, factory, number=112, payload=_activate_payload(expected_version=9),
            kind=CandidateKind.TRAINING_PLAN, conversation_id=conversation,
        )
        assert _accept(repository, stale.candidate_id).disposition is CandidateMutationDisposition.VERSION_CONFLICT
        assert repository.get_candidate(owner_id="memory-owner", candidate_id=stale.candidate_id).status.value == "pending"


def test_progress_requires_complete_artifact_and_correction_supersedes_event():
    with migrated_memory_repository() as (repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory)
        plan_candidate = _identity_and_candidate(
            repository, factory, number=121, payload=_activate_payload(),
            kind=CandidateKind.TRAINING_PLAN, conversation_id=conversation,
        )
        plan_result = _accept(repository, plan_candidate.candidate_id)
        assert plan_result.candidate is not None
        plan_id = plan_result.candidate.materialized_target_id
        assert plan_id is not None

        task1, run1 = _seed_terminal_review(
            factory, number=1, conversation_id=conversation,
            relationship_id=relationship, subject_id=subject,
        )
        progress1 = _identity_and_candidate(
            repository, factory, number=122,
            payload={"value": {"plan_id": str(plan_id), "metric_key": "deaths_before_15", "metric_value": 2.0, "observed_at": "2026-08-21T12:00:00Z", "supersedes_progress_id": None}},
            kind=CandidateKind.TRAINING_PROGRESS, conversation_id=conversation,
            source_task_id=task1, source_run_id=run1, source_artifact_sha256=ARTIFACT_SHA,
        )
        result1 = _accept(repository, progress1.candidate_id)
        assert result1.disposition is CandidateMutationDisposition.ACCEPTED
        assert result1.candidate is not None
        progress_id = result1.candidate.materialized_target_id

        task2, run2 = _seed_terminal_review(
            factory, number=2, conversation_id=conversation,
            relationship_id=relationship, subject_id=subject,
        )
        progress2 = _identity_and_candidate(
            repository, factory, number=123,
            payload={"value": {"plan_id": str(plan_id), "metric_key": "deaths_before_15", "metric_value": 1.0, "observed_at": "2026-08-22T12:00:00Z", "supersedes_progress_id": str(progress_id)}},
            kind=CandidateKind.TRAINING_PROGRESS, conversation_id=conversation,
            source_task_id=task2, source_run_id=run2, source_artifact_sha256=ARTIFACT_SHA,
        )
        result2 = _accept(repository, progress2.candidate_id)
        assert result2.disposition is CandidateMutationDisposition.ACCEPTED
        with factory() as session:
            rows = list(session.scalars(sa.select(TrainingProgressRecord).order_by(TrainingProgressRecord.created_at)))
        assert [(row.metric_value, row.status) for row in rows] == [(2.0, "superseded"), (1.0, "active")]
        assert rows[1].supersedes_progress_id == rows[0].progress_id
        page = PostgresTrainingQueryRepository(factory).list_progress(
            owner_id="memory-owner",
            relationship_id=relationship,
            metric_key="deaths_before_15",
            include_history=True,
            limit=50,
        )
        assert page is not None
        assert [(item.metric_value, item.status.value) for item in page.events] == [
            (1.0, "active"),
            (2.0, "superseded"),
        ]
        assert page.trends[0].comparison.trend.value == "insufficient_data"


def test_progress_rejects_failed_task_and_unknown_metric_without_partial_event():
    with migrated_memory_repository() as (repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory)
        plan_candidate = _identity_and_candidate(
            repository, factory, number=131, payload=_activate_payload(),
            kind=CandidateKind.TRAINING_PLAN, conversation_id=conversation,
        )
        plan = _accept(repository, plan_candidate.candidate_id).candidate
        assert plan is not None and plan.materialized_target_id is not None
        task, run = _seed_terminal_review(
            factory, number=3, conversation_id=conversation,
            relationship_id=relationship, subject_id=subject, status="failed",
        )
        progress = _identity_and_candidate(
            repository, factory, number=132,
            payload={"value": {"plan_id": str(plan.materialized_target_id), "metric_key": "deaths_before_15", "metric_value": 1.0, "observed_at": "2026-08-21T12:00:00Z", "supersedes_progress_id": None}},
            kind=CandidateKind.TRAINING_PROGRESS, conversation_id=conversation,
            source_task_id=task, source_run_id=run, source_artifact_sha256=ARTIFACT_SHA,
        )
        assert _accept(repository, progress.candidate_id).disposition is CandidateMutationDisposition.TARGET_INVALID
        with factory() as session:
            assert session.scalar(sa.select(sa.func.count()).select_from(TrainingProgressRecord)) == 0
