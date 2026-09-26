from __future__ import annotations

from uuid import UUID
import os

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.memory.composition import build_typed_memory_materializers
from app.memory.service import MemoryCandidateService
from app.memory.typed_service import TypedMemoryQueryService
from app.persistence.typed_memory_query_repository import PostgresTypedMemoryQueryRepository
from app.memory.models import RelationshipRole
from tests.memory_candidate_postgres_support import migrated_memory_repository, seed_conversation
from tests.test_memory_candidate_api import UnusedPlayerLinkService, UnusedTaskService, UnusedRunQuery, ReadyProbe
from scripts.run_local_observation_api import create_local_observation_app


def _client(*, owner: str, candidate_service, query_service) -> TestClient:
    return TestClient(create_app(
        task_service=UnusedTaskService(),
        player_link_service=UnusedPlayerLinkService(),
        query_service=UnusedRunQuery(),
        actor_provider=StaticActorContextProvider(owner_id=owner, profile="test"),
        readiness_probe=ReadyProbe(),
        memory_candidate_service=candidate_service,
        typed_memory_query_service=query_service,
    ))


def test_user_observation_round_trip_and_scope() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        _subject, relationship_id, observed_conversation = seed_conversation(
            factory, number=701, owner_id="observation-owner", role=RelationshipRole.OBSERVED
        )
        _self_subject, _self_relationship, self_conversation = seed_conversation(
            factory, number=702, owner_id="observation-owner"
        )
        candidate_service = MemoryCandidateService(
            repository=repository, materializers=build_typed_memory_materializers()
        )
        query_service = TypedMemoryQueryService(PostgresTypedMemoryQueryRepository(factory))
        owner = _client(owner="observation-owner", candidate_service=candidate_service, query_service=query_service)
        other = _client(owner="other-owner", candidate_service=candidate_service, query_service=query_service)
        payload = {
            "text": "ShowMaker中路观摩记录",
            "archive_reference": {
                "kind": "user_attached_archive",
                "source_run_id": "golden_20260910_compact_1cd694d",
                "bundle_digest": "a" * 64,
                "report_sha256": "b" * 64,
                "observed_at": "2026-09-10T12:15:25+00:00",
            },
        }
        created = owner.post(
            f"/conversations/{observed_conversation}/memory-candidates",
            headers={"Idempotency-Key": "observation-note-701"},
            json={"target_scope": "owner_player", "candidate_kind": "review_memory", "memory_key": "observation_note", "operation": "append", "proposal_payload": {"value": payload}},
        )
        assert created.status_code == 201, created.text
        candidate_id = created.json()["candidate_id"]
        stored = repository.get_candidate(owner_id="observation-owner", candidate_id=UUID(candidate_id))
        assert stored is not None and stored.source_task_id is None and stored.source_run_id is None
        assert created.json()["requires_confirmation"] is True
        accepted = owner.post(f"/memory-candidates/{candidate_id}/accept")
        assert accepted.status_code == 200, accepted.text
        replay = owner.post(f"/memory-candidates/{candidate_id}/accept")
        assert replay.status_code == 200
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM review_memories")) == 1

        reviews = owner.get(f"/memory/players/{relationship_id}/reviews")
        assert reviews.status_code == 200
        assert reviews.json()["records"][0]["payload"] == payload
        fresh_query = TypedMemoryQueryService(PostgresTypedMemoryQueryRepository(factory))
        fresh_page = fresh_query.reviews(owner_id="observation-owner", relationship_id=relationship_id, include_history=False, limit=10)
        assert fresh_page.records[0].payload == payload
        assert other.get(f"/memory/players/{relationship_id}/reviews").status_code == 404
        assert other.post(f"/memory-candidates/{candidate_id}/accept").status_code == 404

        self_response = owner.post(
            f"/conversations/{self_conversation}/memory-candidates",
            headers={"Idempotency-Key": "self-observation-702"},
            json={"target_scope": "owner_player", "candidate_kind": "review_memory", "memory_key": "observation_note", "operation": "append", "proposal_payload": {"value": payload}},
        )
        assert self_response.status_code == 422
        training_response = owner.post(
            f"/conversations/{observed_conversation}/memory-candidates",
            headers={"Idempotency-Key": "training-observation-701"},
            json={"target_scope": "owner_player", "candidate_kind": "training_plan", "memory_key": "observation_note", "operation": "append", "proposal_payload": {"value": payload}},
        )
        assert training_response.status_code == 422


def test_local_composed_session_note_survives_app_restart(tmp_path) -> None:
    with migrated_memory_repository() as (_repository, factory, _engine):
        _, relationship_id, _ = seed_conversation(
            factory, number=703, owner_id="local-observation-owner", role=RelationshipRole.OBSERVED,
        )
        environment = {
            "DATABASE_URL": os.environ["RIFTCOACH_TEST_DATABASE_URL"],
            "RIFTCOACH_API_PROFILE": "local",
            "RIFTCOACH_LOCAL_OWNER_ID": "local-observation-owner",
            "RIFTCOACH_RUNS_ROOT": str(tmp_path),
        }
        with TestClient(create_local_observation_app(environment)) as client:
            assert client.get("/health/ready").status_code == 200
            assert client.get(f"/memory/players/{relationship_id}/reviews").status_code == 401
            issued = client.post("/auth/session")
            assert issued.status_code == 200
            csrf = {"X-CSRF-Token": issued.json()["csrf_token"]}
            body = {"player_profile_id": str(relationship_id)}
            assert client.post("/conversations", json=body).status_code == 403
            created = client.post("/conversations", json=body, headers={
                **csrf, "Idempotency-Key": "local-observation-session-conversation",
            })
            assert created.status_code == 201, created.text
            conversation_id = created.json()["conversation_id"]
            candidate = client.post(f"/conversations/{conversation_id}/memory-candidates", json={
                "target_scope": "owner_player", "candidate_kind": "review_memory",
                "memory_key": "observation_note", "operation": "append",
                "proposal_payload": {"value": {"text": "Local session persistence fixture"}},
            }, headers={**csrf, "Idempotency-Key": "local-session-note"})
            assert candidate.status_code == 201, candidate.text
            candidate_id = candidate.json()["candidate_id"]
            endpoint = f"/memory-candidates/{candidate_id}/accept"
            assert client.post(endpoint).status_code == 403
            assert client.post(endpoint, headers=csrf).status_code == 200
            assert client.post(endpoint, headers=csrf).status_code == 200
        # Fresh composition and session store; records are queried from PostgreSQL.
        with TestClient(create_local_observation_app(environment)) as restarted:
            assert restarted.get(f"/memory/players/{relationship_id}/reviews").status_code == 401
            assert restarted.post("/auth/session").status_code == 200
            readback = restarted.get(f"/memory/players/{relationship_id}/reviews")
            assert readback.status_code == 200
            records = readback.json()["records"]
            assert len(records) == 1
            assert records[0]["payload"] == {"text": "Local session persistence fixture"}
        with TestClient(create_local_observation_app({
            **environment, "RIFTCOACH_LOCAL_OWNER_ID": "other-local-owner",
        })) as other:
            assert other.post("/auth/session").status_code == 200
            assert other.get(f"/memory/players/{relationship_id}/reviews").status_code == 404
