"""Server measurement candidates, atomic with the durable terminal projection."""
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from uuid import UUID

from sqlalchemy.orm import Session

from app.conversations.turns import TerminalAssistantTurn
from app.memory.models import (
    CandidateCreateDisposition, CandidateKind, MemoryOperation, PendingMemoryCandidate,
    ProvenanceKind, TargetScope, MemoryConversationIdentity,
)
from app.memory.training_measurement import METRICS, PRODUCER_ID, PRODUCER_VERSION, match_measurements, measurement_key
from app.persistence.training_query_repository import PostgresTrainingQueryRepository
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.task_record import ReviewTaskRecord
from app.product.run_query import RunQueryService
from app.evidence.summary_bridge import summary_projection_digest


def produce_training_progress(
    session: Session, *, task: ReviewTaskRecord, turn: TerminalAssistantTurn,
    message_id: UUID, identity: MemoryConversationIdentity,
    repository: PostgresMemoryCandidateRepository, runs_root: Path | None,
) -> tuple[UUID, ...]:
    plan = PostgresTrainingQueryRepository.active_plan_for_measurement(
        session, identity=identity, task_created_at=task.created_at,
    )
    if plan is None or not any(
        item["metric_key"] in METRICS and item["unit"] == METRICS[item["metric_key"]][1]
        for item in plan.payload["metrics"]
    ):
        return ()
    # Legacy tasks have no durable subject-bound Summary digest. Do not backfill them.
    if task.publication_mode != "evidence_bound_v1" or task.summary_digest is None:
        return ()
    if runs_root is None:
        raise ValueError("training_measurement_source_unconfigured")
    summary, summary_sha, report_sha = RunQueryService(runs_root).read_training_measurement_source(task.run_id)
    if (summary_projection_digest(summary) != task.summary_digest
            or report_sha != turn.artifact_reference.sha256
            or report_sha != turn.assistant_content_sha256):
        raise ValueError("training_measurement_source_mismatch")
    candidates = []
    for key, value, measurement in match_measurements(
        summary, metrics=plan.payload["metrics"], plan_created_at=plan.created_at,
        task_created_at=task.created_at, summary_sha256=summary_sha,
    ):
        stable_key = measurement_key(
            owner_id=identity.owner_id, relationship_id=identity.relationship_id,
            plan_id=plan.plan_id, metric_key=key, match_id=measurement.match_id,
        )
        pending = PendingMemoryCandidate(
            candidate_id=uuid5(NAMESPACE_URL, stable_key), owner_id=identity.owner_id,
            conversation_id=identity.conversation_id, idempotency_key=stable_key,
            source_message_id=message_id, source_task_id=task.task_id, source_run_id=task.run_id,
            source_artifact_sha256=report_sha, target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.TRAINING_PROGRESS, memory_key=key,
            operation=MemoryOperation.APPEND, provenance_kind=ProvenanceKind.DETERMINISTIC_RUN_FACT,
            producer_id=PRODUCER_ID, producer_version=PRODUCER_VERSION,
            proposal_payload={"value": {
                "plan_id": str(plan.plan_id), "metric_key": key, "metric_value": value,
                "observed_at": measurement.observed_at.isoformat(), "supersedes_progress_id": None,
            }, "measurement": measurement.model_dump(mode="json")},
            created_at=turn.created_at, expires_at=turn.created_at + timedelta(days=30),
        )
        result = repository.create_measurement_in_session(session, pending=pending, identity=identity)
        if result.disposition is CandidateCreateDisposition.CREATED:
            candidates.append(result.candidate.candidate_id)
        elif result.disposition is not CandidateCreateDisposition.MEASUREMENT_ALREADY_OFFERED:
            raise ValueError("training_measurement_candidate_persistence_failed")
    return tuple(candidates)
