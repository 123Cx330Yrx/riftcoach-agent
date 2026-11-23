"""Real file/Trace/receipt -> production terminal writer -> Candidate accept -> DB."""
from copy import deepcopy
from datetime import timedelta
from types import MappingProxyType
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.conversations.turns import TerminalAssistantTurn
from app.memory.models import CandidateKind, CandidateMutationDisposition, DecisionActorKind
from app.evidence.summary_bridge import summary_projection_digest
from app.memory.training_materializers import TrainingPlanMaterializer, TrainingProgressMaterializer
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.memory_records import MemoryCandidateRecord
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter, TerminalTurnWriterError
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from app.persistence.training_writer import PostgresTrainingTargetWriter
from tests.memory_candidate_postgres_support import BASE, migrated_memory_repository, seed_conversation
from tests.test_run_query_service import REPORT, _create_terminal_run
from tests.test_terminal_turn_writer_postgres import _turn
from tests.test_training_match_measurement import measured_summary
from tests.test_training_repository_postgres import _activate_payload, _identity_and_candidate, _seed_terminal_review


def registry():
    writer = PostgresTrainingTargetWriter(clock=lambda: BASE)
    return MappingProxyType({CandidateKind.TRAINING_PLAN: TrainingPlanMaterializer(writer),
                             CandidateKind.TRAINING_PROGRESS: TrainingProgressMaterializer(writer)})


def accept(repository, candidate_id, actor=DecisionActorKind.USER):
    return repository.accept_candidate(owner_id="memory-owner", candidate_id=candidate_id,
        actor_id="memory-owner", actor_kind=actor, now=BASE + timedelta(minutes=5), materializers=registry())


def activate(repository, factory, conversation, number=700, expected=None):
    payload = _activate_payload(expected_version=expected)
    payload["value"]["metrics"] = [
        {"metric_key": "match.deaths_before_15", "direction": "decrease", "unit": "count"},
        {"metric_key": "match.vision_score", "direction": "increase", "unit": "score"},
    ]
    candidate = _identity_and_candidate(repository, factory, number=number, payload=payload,
        kind=CandidateKind.TRAINING_PLAN, conversation_id=conversation)
    result = accept(repository, candidate.candidate_id)
    assert result.disposition is CandidateMutationDisposition.ACCEPTED
    return result.candidate.materialized_target_id


def prepare(factory, root, *, number, subject, relationship, conversation, summary=None, digest_override=None):
    summary = measured_summary() if summary is None else summary
    store, receipt = _create_terminal_run(root, run_id=f"training-run-{number}", player_summary=summary)
    manifest = store.read_manifest()
    final = next(row for row in manifest.artifacts if row["kind"] == "final_report")
    source = next(row for row in manifest.artifacts if row["kind"] == "player_summary")
    task_id, run_id = _seed_terminal_review(factory, number=number, subject_id=subject,
        relationship_id=relationship, conversation_id=conversation, artifact_sha=final["sha256"],
        publication_mode="evidence_bound_v1", summary_digest=digest_override or summary_projection_digest(summary),
        message_projection_status="pending", created_at=BASE + timedelta(minutes=3))
    turn = _turn(task_id=task_id, run_id=run_id, subject=subject, relationship=relationship,
                 conversation=conversation, artifact_sha=final["sha256"])
    turn = TerminalAssistantTurn.model_validate({**turn.model_dump(mode="python"),
                                                "assistant_content": REPORT, "assistant_content_sha256": None})
    return turn, store


def counts(factory):
    with factory() as session:
        return tuple(session.scalar(sa.select(sa.func.count()).select_from(model))
                     for model in (ConversationMessageRecord, MemoryCandidateRecord, TrainingProgressRecord))


def another_conversation(factory, conversation):
    new_id = uuid4()
    with factory.begin() as session:
        previous = session.get(ConversationRecord, conversation)
        attributes = {key: getattr(previous, key) for key in (
            "schema_version", "owner_id", "relationship_id", "player_subject_id", "relationship_role",
            "status", "created_at", "updated_at")}
        session.add(ConversationRecord(conversation_id=new_id, idempotency_key=str(new_id),
            request_fingerprint="a" * 64, next_message_sequence=1, **attributes))
    return new_id


def test_production_writer_offers_measured_zero_then_only_user_accept_materializes(tmp_path):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=701)
        plan_id = activate(repository, factory, conversation)
        turn, _ = prepare(factory, tmp_path, number=701, subject=subject, relationship=relationship, conversation=conversation)
        writer = PostgresTerminalTurnWriter(factory, runs_root=tmp_path)
        result = writer.write(turn)
        assert len(result.candidate_ids) == 4
        assert counts(factory) == (1, 5, 0)
        assert writer.write(turn).candidate_ids == tuple(sorted(result.candidate_ids))
        candidate = repository.get_candidate(owner_id="memory-owner", candidate_id=result.candidate_ids[0])
        assert candidate.proposal_payload["value"]["metric_value"] == 0
        assert candidate.proposal_payload["value"]["observed_at"] == (BASE + timedelta(minutes=1)).isoformat()
        assert candidate.source_run_id == turn.binding.run_id
        assert candidate.proposal_payload["measurement"]["match_id"] == "PRIVATE_MATCH_1"
        assert candidate.proposal_payload["measurement"]["summary_sha256"] != candidate.proposal_payload["measurement"]["summary_projection_sha256"]
        assert accept(repository, candidate.candidate_id, DecisionActorKind.SYSTEM).disposition is CandidateMutationDisposition.TERMINAL_CONFLICT
        assert accept(repository, candidate.candidate_id).disposition is CandidateMutationDisposition.ACCEPTED
        assert accept(repository, candidate.candidate_id).disposition is CandidateMutationDisposition.REPLAYED
        with factory() as session:
            event = session.scalar(sa.select(TrainingProgressRecord))
            assert event.plan_id == plan_id and event.metric_value == 0
            assert event.observed_at == BASE + timedelta(minutes=1)


def test_cross_run_conversation_changed_value_rejected_and_hidden_do_not_reoffer(tmp_path):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=711)
        activate(repository, factory, conversation)
        writer = PostgresTerminalTurnWriter(factory, runs_root=tmp_path)
        turn, _ = prepare(factory, tmp_path, number=711, subject=subject, relationship=relationship, conversation=conversation)
        first = writer.write(turn)
        repository.reject_candidate(owner_id="memory-owner", candidate_id=first.candidate_ids[0],
            actor_id="memory-owner", reason_code="user_rejected", now=BASE + timedelta(minutes=5))
        with factory.begin() as session:
            session.get(MemoryCandidateRecord, first.candidate_ids[1]).hidden_at = BASE + timedelta(minutes=5)
        other_conversation = another_conversation(factory, conversation)
        summary = measured_summary()
        summary["matches"][0]["deaths_before_15"] = 9
        second, _ = prepare(factory, tmp_path, number=712, subject=subject, relationship=relationship,
                             conversation=other_conversation, summary=summary)
        assert writer.write(second).candidate_ids == ()
        assert counts(factory) == (2, 5, 0)
        with factory() as session:
            original = session.get(MemoryCandidateRecord, first.candidate_ids[0])
            assert original.source_run_id == turn.binding.run_id
            assert original.proposal_payload["value"]["metric_value"] == 0


def test_mid_projection_failure_rolls_back_and_pending_replay_recovers(tmp_path, monkeypatch):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=721)
        activate(repository, factory, conversation)
        turn, _ = prepare(factory, tmp_path, number=721, subject=subject, relationship=relationship, conversation=conversation)
        writer = PostgresTerminalTurnWriter(factory, runs_root=tmp_path)
        original = writer._candidate_repository.create_measurement_in_session
        called = 0
        def interrupt(*args, **kwargs):
            nonlocal called
            called += 1
            if called == 2:
                raise ValueError("synthetic interruption")
            return original(*args, **kwargs)
        monkeypatch.setattr(writer._candidate_repository, "create_measurement_in_session", interrupt)
        with pytest.raises(TerminalTurnWriterError):
            writer.write(turn)
        assert counts(factory) == (0, 1, 0)
        with factory() as session:
            assert session.get(ReviewTaskRecord, turn.source_task_id).message_projection_status == "pending"
        monkeypatch.setattr(writer._candidate_repository, "create_measurement_in_session", original)
        assert len(writer.replay_pending_batch()[0].candidate_ids) == 4
        assert counts(factory) == (1, 5, 0)
        assert writer.replay_pending_batch() == ()


@pytest.mark.parametrize("damage", ["summary_bytes", "task_digest", "duplicate_match", "message_content"])
def test_source_damage_leaves_no_partial_message_or_candidates(tmp_path, damage):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=731)
        activate(repository, factory, conversation)
        summary = measured_summary()
        if damage == "duplicate_match":
            summary["matches"].append(deepcopy(summary["matches"][0]))
        turn, store = prepare(factory, tmp_path, number=731, subject=subject,
                              relationship=relationship, conversation=conversation, summary=summary,
                              digest_override="b" * 64 if damage == "task_digest" else None)
        if damage == "summary_bytes":
            (store.run_directory / "inputs/player_summary.json").write_text("{}", encoding="utf-8")
        if damage == "message_content":
            turn = TerminalAssistantTurn.model_validate({**turn.model_dump(mode="python"),
                "assistant_content": "# Another report", "assistant_content_sha256": None})
        with pytest.raises(TerminalTurnWriterError):
            PostgresTerminalTurnWriter(factory, runs_root=tmp_path).write(turn)
        assert counts(factory) == (0, 1, 0)


def test_plan_replacement_invalidates_pending_accept_and_completed_run_never_backfills(tmp_path):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=741)
        activate(repository, factory, conversation)
        turn, _ = prepare(factory, tmp_path, number=741, subject=subject, relationship=relationship, conversation=conversation)
        writer = PostgresTerminalTurnWriter(factory, runs_root=tmp_path)
        result = writer.write(turn)
        activate(repository, factory, conversation, number=742, expected=1)
        assert accept(repository, result.candidate_ids[0]).disposition is CandidateMutationDisposition.TARGET_INVALID
        assert set(writer.write(turn).candidate_ids) == set(result.candidate_ids)
        assert counts(factory) == (1, 6, 0)


def test_projection_can_return_more_than_eight_server_measurements(tmp_path):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=751)
        activate(repository, factory, conversation)
        summary = measured_summary()
        for index in range(3):
            row = deepcopy(summary["matches"][0])
            row["match_id"] = f"EXTRA_MATCH_{index}"
            summary["matches"].append(row)
        turn, _ = prepare(factory, tmp_path, number=751, subject=subject,
                          relationship=relationship, conversation=conversation, summary=summary)
        assert len(PostgresTerminalTurnWriter(factory, runs_root=tmp_path).write(turn).candidate_ids) == 10


def test_concurrent_runs_offer_once_and_different_self_relationship_is_independent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=761)
        activate(repository, factory, conversation)
        other_conversation = another_conversation(factory, conversation)
        turns = [prepare(factory, tmp_path, number=number, subject=subject,
                         relationship=relationship, conversation=source_conversation)[0]
                 for number, source_conversation in ((761, conversation), (762, other_conversation))]
        writer = PostgresTerminalTurnWriter(factory, runs_root=tmp_path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(writer.write, turns))
        assert sum(len(result.candidate_ids) for result in results) == 4
        assert counts(factory) == (2, 5, 0)
        other_subject, other_relationship, other_conversation = seed_conversation(factory, number=763)
        activate(repository, factory, other_conversation, number=763)
        other_turn, _ = prepare(factory, tmp_path, number=763, subject=other_subject,
                                relationship=other_relationship, conversation=other_conversation)
        assert len(writer.write(other_turn).candidate_ids) == 4
        assert counts(factory) == (3, 10, 0)


def test_foreign_relationship_cannot_accept_measurement_and_legacy_task_cannot_produce(tmp_path):
    with migrated_memory_repository() as (repository, factory, _):
        subject, relationship, conversation = seed_conversation(factory, number=771)
        activate(repository, factory, conversation)
        # A legacy task is intentionally not upgraded merely because files exist.
        task_id, run_id = _seed_terminal_review(factory, number=771, subject_id=subject,
            relationship_id=relationship, conversation_id=conversation, message_projection_status="pending")
        turn = _turn(task_id=task_id, run_id=run_id, subject=subject, relationship=relationship, conversation=conversation)
        assert PostgresTerminalTurnWriter(factory, runs_root=tmp_path).write(turn).candidate_ids == ()
        assert counts(factory) == (1, 1, 0)
        fresh, _ = prepare(factory, tmp_path, number=772, subject=subject, relationship=relationship, conversation=conversation)
        result = PostgresTerminalTurnWriter(factory, runs_root=tmp_path).write(fresh)
        denied = repository.accept_candidate(owner_id="another-owner", candidate_id=result.candidate_ids[0],
            actor_id="another-owner", actor_kind=DecisionActorKind.USER, now=BASE + timedelta(minutes=5), materializers=registry())
        assert denied.disposition is CandidateMutationDisposition.NOT_FOUND
