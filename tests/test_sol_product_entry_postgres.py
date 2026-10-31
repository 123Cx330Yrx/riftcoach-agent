"""Normal composed HTTP entry with real SQL/Memory/Evidence; external IO scripted."""
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.composition import create_composed_app
from app.memory.models import RelationshipRole
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.player_records import PlayerAliasRecord
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter
from app.product import sol_contract as product
from app.tasks.models import TaskPublicationMode
from tests.memory_candidate_postgres_support import seed_conversation
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, setup_worker, resume


@pytest.mark.parametrize('conversation_bound', [False, True])
def test_composed_api_binds_evidence_and_observed_conversation(
    continued_api, tmp_path, monkeypatch, conversation_bound,
):
    _, _, repo, _ = continued_api
    factory = repo._session_factory
    subject, relationship, conversation = seed_conversation(factory, number=901,
        owner_id='owner-1', role=RelationshipRole.OBSERVED)
    with factory.begin() as session:
        session.add(PlayerAliasRecord(player_alias_id=uuid4(), player_subject_id=subject,
            routing_region='asia', game_name='DemoPlayer', tag_line='TEST',
            normalized_riot_id_hash='a' * 64,
            first_seen_at=datetime.now(timezone.utc), last_seen_at=datetime.now(timezone.utc)))
    env = dict(DATABASE_URL=os.environ['RIFTCOACH_TEST_DATABASE_URL'],
        RIFTCOACH_API_PROFILE='test', RIFTCOACH_LOCAL_OWNER_ID='owner-1',
        RIFTCOACH_RUNS_ROOT=str(tmp_path), RIFTCOACH_TASK_PUBLICATION_MODE='evidence_bound_v1')
    def client(owner):
        return TestClient(create_composed_app(environment=env,
            actor_provider=StaticActorContextProvider(owner_id=owner, profile='test')))
    with client('owner-1') as owner, client('owner-2') as other:
        path = f'/conversations/{conversation}/reviews/recent' if conversation_bound else '/reviews/recent'
        payload = dict(count=5, queue=420, focus='overall')
        if not conversation_bound:
            payload.update(riot_id='DemoPlayer#TEST', routing_region='asia')
        # Publication mode is server-selected, never a client bypass.
        assert owner.post(path, headers={'Idempotency-Key': 'forged-mode'},
            json={**payload, 'publication_mode': 'legacy'}).status_code == 422
        response = owner.post(path, headers={'Idempotency-Key': 'normal-product-entry'}, json=payload)
        assert response.status_code == 202, response.text
        task, run = UUID(response.json()['task_id']), response.json()['run_id']
        stored = repo.get_by_task_id(owner_id='owner-1', task_id=task)
        assert stored.publication_mode is TaskPublicationMode.EVIDENCE_BOUND_V1
        if conversation_bound:
            assert stored.conversation_binding.relationship_role.value == 'observed'
            assert other.post(path, headers={'Idempotency-Key': 'foreign'}, json=payload).status_code == 404
        make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo,
            contract=product, profile=product.WORKER_PROFILE,
            memory_repository=PostgresMemoryContextRepository(factory),
            terminal_turn_writer=PostgresTerminalTurnWriter(factory, runs_root=tmp_path))
        worker, route = make()
        if conversation_bound:
            route.candidate.max_new_models = 3
            assert worker.run_once().status.value == 'paused'
            state = owner.get(f'/tasks/{task}/continuation').json()
            assert resume(owner, task, state['checkpoint_sha256'], 'entry-continue').status_code == 200
            worker, _ = make()
        result = worker.run_once()
        assert result.status.value == 'succeeded', owner.get(f'/tasks/{task}/continuation').json().get('reason')
        assert worker.run_once().status.value == 'idle'
        assert summary.reads == 1
        assert owner.get(f'/runs/{run}/report').status_code == 200
        assert owner.get(f'/runs/{run}/evidence').status_code == 200
        assert other.get(f'/runs/{run}/evidence').status_code == 404
        assert other.get(f'/runs/{run}/report').status_code == 404
        total = owner.get(f'/runs/{run}/usage').json()['session_accounting']
        assert total['requests_reserved'] == 4 and total['known_tokens'] == 80
        if conversation_bound:
            assert summary.calls[0][0] == 'build_by_puuid'
            assert summary.calls[0][1]['puuid'] == 'PUUID_MEMORY_901'
            reports = sorted((tmp_path / run / '.continuation/segments').glob('*/' + run + '/inputs/deterministic_report.md'))
            assert len(reports) == 2 and reports[0].read_bytes() == reports[1].read_bytes()
            response = owner.get(f'/conversations/{conversation}/messages')
            assert response.status_code == 200, response.text
            messages = response.json()['items']
            assert len([m for m in messages if m['role'] == 'assistant']) == 1
            with factory() as session:
                assert session.scalar(sa.text('SELECT count(*) FROM training_progress_events')) == 0
            assert requests == [[200], [200]]
        else:
            assert requests == [[200, 200]]
