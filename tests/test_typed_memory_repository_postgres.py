from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import sqlalchemy as sa

from app.memory.models import (
    CandidateKind,
    CandidateMutationDisposition,
    CandidateStatus,
    DecisionActorKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.memory.typed_materializers import (
    OwnerPreferenceMaterializer,
    PlayerProfileMaterializer,
    ReviewMemoryMaterializer,
)
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.typed_memory_query_repository import PostgresTypedMemoryQueryRepository
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)
from app.persistence.typed_memory_writer import PostgresTypedMemoryTargetWriter
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


def registry():
    writer = PostgresTypedMemoryTargetWriter(clock=lambda: BASE + timedelta(days=1))
    return {
        CandidateKind.OWNER_PREFERENCE: OwnerPreferenceMaterializer(writer),
        CandidateKind.PLAYER_PROFILE: PlayerProfileMaterializer(writer),
        CandidateKind.REVIEW_MEMORY: ReviewMemoryMaterializer(writer),
    }


def create(
    repository,
    factory,
    *,
    number: int,
    payload: dict[str, object],
    kind: CandidateKind = CandidateKind.OWNER_PREFERENCE,
    scope: TargetScope = TargetScope.OWNER_GLOBAL,
    key: str = "report_language",
    operation: MemoryOperation = MemoryOperation.SET,
    role: RelationshipRole = RelationshipRole.SELF,
    provenance_kind: ProvenanceKind = ProvenanceKind.USER_STRUCTURED_INPUT,
):
    _subject, _relationship, conversation_id = seed_conversation(
        factory,
        number=number,
        role=role,
    )
    identity = repository.get_conversation_identity(
        owner_id="memory-owner",
        conversation_id=conversation_id,
    )
    assert identity is not None
    result = repository.create_or_replay_candidate(
        pending_candidate(
            number,
            conversation_id=conversation_id,
            payload=payload,
            target_scope=scope,
            candidate_kind=kind,
            memory_key=key,
            operation=operation,
            provenance_kind=provenance_kind,
        ),
        identity=identity,
        requires_confirmation=False,
        gate_policy_version="memory-gate-v1",
    )
    assert result.candidate is not None
    return result.candidate


def accept(repository, item, materializers):
    return repository.accept_candidate(
        owner_id="memory-owner",
        candidate_id=item.candidate_id,
        actor_id="memory-owner",
        actor_kind=DecisionActorKind.USER,
        now=BASE + timedelta(days=2),
        materializers=materializers,
    )


def test_three_materializers_commit_real_typed_targets_with_candidate_terminal() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        preference = create(repository, factory, number=1, payload={"value": "zh-CN"})
        profile = create(
            repository,
            factory,
            number=2,
            payload={"value": "TOP"},
            kind=CandidateKind.PLAYER_PROFILE,
            scope=TargetScope.OWNER_PLAYER,
            key="main_role",
        )
        review = create(
            repository,
            factory,
            number=3,
            payload={
                "value": {
                    "metric": "deaths_before_15",
                    "direction": "down",
                    "value": 1.0,
                }
            },
            kind=CandidateKind.REVIEW_MEMORY,
            scope=TargetScope.OWNER_PLAYER,
            key="public_trend",
            operation=MemoryOperation.APPEND,
            role=RelationshipRole.OBSERVED,
            provenance_kind=ProvenanceKind.DETERMINISTIC_RUN_FACT,
        )
        materializers = registry()
        results = [
            accept(repository, preference, materializers),
            accept(repository, profile, materializers),
            accept(repository, review, materializers),
        ]
        assert {result.disposition for result in results} == {
            CandidateMutationDisposition.ACCEPTED
        }
        with engine.connect() as connection:
            assert connection.scalar(sa.select(sa.func.count()).select_from(MemoryPreferenceRecord)) == 1
            assert connection.scalar(sa.select(sa.func.count()).select_from(PlayerProfileRecord)) == 1
            assert connection.scalar(sa.select(sa.func.count()).select_from(ReviewMemoryRecord)) == 1


def test_preference_update_supersedes_history_and_requires_expected_version() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        first = create(repository, factory, number=1, payload={"value": "zh-CN"})
        assert accept(repository, first, registry()).disposition is CandidateMutationDisposition.ACCEPTED

        stale = create(repository, factory, number=2, payload={"value": "en-US"})
        stale_result = accept(repository, stale, registry())
        assert stale_result.disposition is CandidateMutationDisposition.VERSION_CONFLICT
        stored_stale = repository.get_candidate(
            owner_id="memory-owner",
            candidate_id=stale.candidate_id,
        )
        assert stored_stale is not None and stored_stale.status is CandidateStatus.PENDING

        second = create(
            repository,
            factory,
            number=3,
            payload={"value": "en-US", "expected_version": 1},
        )
        assert accept(repository, second, registry()).disposition is CandidateMutationDisposition.ACCEPTED
        with engine.connect() as connection:
            rows = connection.execute(
                sa.select(
                    MemoryPreferenceRecord.version,
                    MemoryPreferenceRecord.status,
                    MemoryPreferenceRecord.payload,
                ).order_by(MemoryPreferenceRecord.version)
            ).all()
        assert rows == [(1, "superseded", {"value": "zh-CN"}), (2, "active", {"value": "en-US"})]


def test_concurrent_same_expected_version_yields_one_active_and_one_pending_conflict() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        first = create(repository, factory, number=1, payload={"value": "zh-CN"})
        assert accept(repository, first, registry()).disposition is CandidateMutationDisposition.ACCEPTED
        candidate_a = create(
            repository,
            factory,
            number=2,
            payload={"value": "en-US", "expected_version": 1},
        )
        candidate_b = create(
            repository,
            factory,
            number=3,
            payload={"value": "zh-CN", "expected_version": 1},
        )
        start = Barrier(2)

        def run(item):
            start.wait(timeout=5)
            local = PostgresMemoryCandidateRepository(factory)
            return accept(local, item, registry())

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(run, (candidate_a, candidate_b)))
        assert {result.disposition for result in results} == {
            CandidateMutationDisposition.ACCEPTED,
            CandidateMutationDisposition.VERSION_CONFLICT,
        }
        with engine.connect() as connection:
            active_count = connection.scalar(
                sa.select(sa.func.count()).select_from(MemoryPreferenceRecord).where(
                    MemoryPreferenceRecord.status == "active"
                )
            )
            total_count = connection.scalar(
                sa.select(sa.func.count()).select_from(MemoryPreferenceRecord)
            )
        assert active_count == 1
        assert total_count == 2


def test_invalid_typed_payload_is_safe_and_rolls_back_candidate() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        item = create(repository, factory, number=1, payload={"value": "unsupported"})
        result = accept(repository, item, registry())
        assert result.disposition is CandidateMutationDisposition.TARGET_INVALID
        stored = repository.get_candidate(
            owner_id="memory-owner",
            candidate_id=item.candidate_id,
        )
        with engine.connect() as connection:
            count = connection.scalar(sa.select(sa.func.count()).select_from(MemoryPreferenceRecord))
        assert stored is not None and stored.status is CandidateStatus.PENDING
        assert count == 0


def test_owner_scoped_query_returns_active_and_bounded_history() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        first = create(repository, factory, number=1, payload={"value": "zh-CN"})
        assert accept(repository, first, registry()).disposition is CandidateMutationDisposition.ACCEPTED
        second = create(
            repository,
            factory,
            number=2,
            payload={"value": "en-US", "expected_version": 1},
        )
        assert accept(repository, second, registry()).disposition is CandidateMutationDisposition.ACCEPTED

        query = PostgresTypedMemoryQueryRepository(factory)
        active = query.list_preferences(
            owner_id="memory-owner",
            include_history=False,
            limit=50,
        )
        history = query.list_preferences(
            owner_id="memory-owner",
            include_history=True,
            limit=50,
        )
        other_owner = query.list_preferences(
            owner_id="other-owner",
            include_history=True,
            limit=50,
        )
        assert [(item.version, item.status.value) for item in active] == [(2, "active")]
        assert [(item.version, item.status.value) for item in history] == [
            (2, "active"),
            (1, "superseded"),
        ]
        assert other_owner == ()


def test_profile_query_hides_cross_owner_and_observed_relationships() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        profile = create(
            repository,
            factory,
            number=1,
            payload={"value": "TOP"},
            kind=CandidateKind.PLAYER_PROFILE,
            scope=TargetScope.OWNER_PLAYER,
            key="main_role",
        )
        assert accept(repository, profile, registry()).disposition is CandidateMutationDisposition.ACCEPTED
        _subject, observed_relationship, _conversation = seed_conversation(
            factory,
            number=2,
            role=RelationshipRole.OBSERVED,
        )
        query = PostgresTypedMemoryQueryRepository(factory)
        own = query.list_profile(
            owner_id="memory-owner",
            relationship_id=profile.relationship_id,
            include_history=False,
            limit=50,
        )
        cross_owner = query.list_profile(
            owner_id="other-owner",
            relationship_id=profile.relationship_id,
            include_history=False,
            limit=50,
        )
        observed = query.list_profile(
            owner_id="memory-owner",
            relationship_id=observed_relationship,
            include_history=False,
            limit=50,
        )
        assert own is not None and len(own) == 1
        assert own[0].relationship_id == profile.relationship_id
        assert cross_owner is None
        assert observed is None
