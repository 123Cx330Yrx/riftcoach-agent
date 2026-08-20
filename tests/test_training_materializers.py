from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.memory.models import (
    CandidateKind,
    CandidateStatus,
    MemoryCandidate,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.memory.training_materializers import (
    TrainingMaterializerError,
    TrainingPlanMaterializer,
    TrainingProgressMaterializer,
)


NOW = datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc)
TARGET_ID = UUID("30000000-0000-0000-0000-000000000001")
PLAN_ID = UUID("30000000-0000-0000-0000-000000000002")


class FakeSession:
    def add(self, instance: object) -> None:
        raise AssertionError("writer owns persistence calls")

    def flush(self) -> None:
        raise AssertionError("writer owns persistence calls")

    def execute(self, statement: object, params: object | None = None):
        raise AssertionError("writer owns persistence calls")

    def scalar(self, statement: object):
        raise AssertionError("writer owns persistence calls")


class RecordingWriter:
    def __init__(self, result=TARGET_ID) -> None:
        self.result = result
        self.calls = []

    def write_plan(self, session, *, candidate, parsed):
        self.calls.append(("plan", session, candidate, parsed))
        return self.result

    def write_progress(self, session, *, candidate, parsed):
        self.calls.append(("progress", session, candidate, parsed))
        return self.result


def _candidate(*, kind: CandidateKind) -> MemoryCandidate:
    plan = kind is CandidateKind.TRAINING_PLAN
    return MemoryCandidate(
        candidate_id=UUID("31000000-0000-0000-0000-000000000001"),
        owner_id="training-owner",
        conversation_id=UUID("31000000-0000-0000-0000-000000000002"),
        relationship_id=UUID("31000000-0000-0000-0000-000000000003"),
        player_subject_id=UUID("31000000-0000-0000-0000-000000000004"),
        relationship_role=RelationshipRole.SELF,
        idempotency_key=f"training-{kind.value}",
        request_fingerprint="1" * 64,
        source_message_id=None,
        source_task_id=(None if plan else UUID("31000000-0000-0000-0000-000000000005")),
        source_run_id=(None if plan else "training-run-1"),
        source_artifact_sha256=(None if plan else "a" * 64),
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=kind,
        memory_key=("active_plan" if plan else "deaths_before_15"),
        operation=(MemoryOperation.SET if plan else MemoryOperation.APPEND),
        proposal_payload=(
            {
                "value": {
                    "action": "activate",
                    "title": "Reduce early deaths",
                    "objective": "Review positioning",
                    "metrics": [
                        {
                            "metric_key": "deaths_before_15",
                            "direction": "decrease",
                            "unit": "count",
                        }
                    ],
                }
            }
            if plan
            else {
                "value": {
                    "plan_id": str(PLAN_ID),
                    "metric_key": "deaths_before_15",
                    "metric_value": 1.0,
                    "observed_at": "2026-08-21T12:00:00Z",
                    "supersedes_progress_id": None,
                }
            }
        ),
        proposal_payload_sha256="2" * 64,
        provenance_kind=(
            ProvenanceKind.USER_STRUCTURED_INPUT
            if plan
            else ProvenanceKind.DETERMINISTIC_RUN_FACT
        ),
        producer_id="training-test",
        producer_version="1.0.0",
        proposal_confidence=None,
        gate_policy_version="memory-gate-v1",
        requires_confirmation=plan,
        status=CandidateStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


@pytest.mark.parametrize(
    ("materializer_type", "kind", "method", "version"),
    [
        (TrainingPlanMaterializer, CandidateKind.TRAINING_PLAN, "plan", "training-plan-v1"),
        (
            TrainingProgressMaterializer,
            CandidateKind.TRAINING_PROGRESS,
            "progress",
            "training-progress-v1",
        ),
    ],
)
def test_training_materializer_parses_and_returns_reference(
    materializer_type,
    kind,
    method,
    version,
):
    session = FakeSession()
    writer = RecordingWriter()
    candidate = _candidate(kind=kind)

    reference = materializer_type(writer).materialize(session, candidate)

    assert reference.target_kind == kind.value
    assert reference.target_id == TARGET_ID
    assert reference.materializer_version == version
    assert writer.calls[0][0] == method
    assert writer.calls[0][1] is session
    assert writer.calls[0][2] is candidate
    assert not hasattr(session, "commit")
    assert not hasattr(session, "rollback")


def test_training_materializer_rejects_wrong_kind_without_writer_call():
    writer = RecordingWriter()
    with pytest.raises(TrainingMaterializerError, match="training_materializer_kind_mismatch"):
        TrainingPlanMaterializer(writer).materialize(
            FakeSession(),
            _candidate(kind=CandidateKind.TRAINING_PROGRESS),
        )
    assert writer.calls == []


def test_training_materializer_rejects_non_uuid_target():
    writer = RecordingWriter(result="not-a-uuid")
    with pytest.raises(TrainingMaterializerError, match="training_materializer_target_id_invalid"):
        TrainingProgressMaterializer(writer).materialize(
            FakeSession(),
            _candidate(kind=CandidateKind.TRAINING_PROGRESS),
        )


def test_training_materializer_rejects_candidate_key_mismatch():
    writer = RecordingWriter()
    plan = _candidate(kind=CandidateKind.TRAINING_PLAN).model_copy(
        update={"memory_key": "other_plan"}
    )
    with pytest.raises(TrainingMaterializerError, match="training_plan_provenance_invalid"):
        TrainingPlanMaterializer(writer).materialize(FakeSession(), plan)
    progress = _candidate(kind=CandidateKind.TRAINING_PROGRESS).model_copy(
        update={"memory_key": "vision_score"}
    )
    with pytest.raises(TrainingMaterializerError, match="training_progress_metric_key_mismatch"):
        TrainingProgressMaterializer(writer).materialize(FakeSession(), progress)
    assert writer.calls == []


def test_training_materializer_constructor_requires_both_writer_methods():
    with pytest.raises(TypeError, match="write_plan"):
        TrainingPlanMaterializer(object())
    with pytest.raises(TypeError, match="write_progress"):
        TrainingProgressMaterializer(object())


def test_writer_failure_propagates_to_outer_candidate_transaction():
    class FailingWriter(RecordingWriter):
        def write_plan(self, session, *, candidate, parsed):
            del session, candidate, parsed
            raise RuntimeError("training writer failed")

    with pytest.raises(RuntimeError, match="training writer failed"):
        TrainingPlanMaterializer(FailingWriter()).materialize(
            FakeSession(),
            _candidate(kind=CandidateKind.TRAINING_PLAN),
        )
