"""Ordinary conversation API/SQL/Worker with pinned archive and scripted models."""
from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.composition import create_composed_app
from app.memory.models import RelationshipRole
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.player_records import PlayerAliasRecord, PlayerSubjectRecord
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter
from app.product import sol_chat_contract as contract
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tasks.reliable_runtime import TaskLeasePolicy
from app.workers.composition import load_worker_composition_settings
from app.workers.review_worker import ReviewWorker
from scripts.archived_product_inputs import (ArchivedProductInputs, ExistingProductSecrets,
    compose_archived_executor)
from tests.memory_candidate_postgres_support import seed_conversation
from tests.test_archived_product_inputs import archived
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_sol_worker_continuation_postgres import continued_api
from tests.test_sol_natural_candidate import application


def test_pinned_archive_consumed_through_observed_conversation_worker(continued_api, archived, tmp_path, monkeypatch):
    inputs = ArchivedProductInputs(archived[0], **archived[1])
    repository = continued_api[2]
    factory = repository._session_factory
    subject, _, conversation = seed_conversation(factory, number=902,
        owner_id='owner-1', role=RelationshipRole.OBSERVED)
    args = inputs.arguments
    now = datetime.now(timezone.utc)
    with factory.begin() as session:
        session.get(PlayerSubjectRecord, subject).puuid = args['puuid']
        session.add(PlayerAliasRecord(player_alias_id=uuid4(), player_subject_id=subject,
            routing_region='asia', game_name=args['game_name'], tag_line=args['tag_line'],
            normalized_riot_id_hash='a'*64, first_seen_at=now, last_seen_at=now))
    root = tmp_path/'runs'
    env = dict(DATABASE_URL=os.environ['RIFTCOACH_TEST_DATABASE_URL'],
        RIFTCOACH_API_PROFILE='test', RIFTCOACH_LOCAL_OWNER_ID='owner-1',
        RIFTCOACH_RUNS_ROOT=str(root), RIFTCOACH_TASK_PUBLICATION_MODE='evidence_bound_v1',
        RIFTCOACH_WORKER_EXECUTION_PROFILE=contract.WORKER_PROFILE,
        LLM_MODEL='glm-5.3-flash', LLM_BASE_URL='https://open.bigmodel.cn/api/paas/v4/',
        LLM_PROVIDER='zhipu', LLM_DEFAULT_PROVIDER='zhipu')
    secrets = ExistingProductSecrets(flash_reader=lambda: 'OFFLINE_FLASH', reviewer_reader=lambda: 'OFFLINE_SOL')

    def scripted(**kwargs):
        assert kwargs['contract_module'] is contract
        value, _ = application(kwargs['transport_root'].parent, mode='pass', candidate=contract, factory_only=True)
        return value

    monkeypatch.setattr('app.runtime.sol_natural_provider.SolNaturalProviderFactory', scripted)
    route = compose_archived_executor(load_worker_composition_settings(env, secret_source=secrets),
        repository=repository, inputs=inputs,
        knowledge=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        memory_repository=PostgresMemoryContextRepository(factory))
    worker = ReviewWorker(repository=repository, executor=route, worker_id='archived-product-test',
        terminal_turn_writer=PostgresTerminalTurnWriter(factory, runs_root=root),
        continuation_store=route.store,
        lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=60))
    app = create_composed_app(environment=env,
        actor_provider=StaticActorContextProvider(owner_id='owner-1', profile='test'))
    with TestClient(app) as owner:
        response = owner.post(f'/conversations/{conversation}/reviews/recent',
            headers={'Idempotency-Key': 'archived-product'}, json=dict(count=5, queue=420, focus='overall'))
        assert response.status_code == 202, response.text
        task, run = response.json()['task_id'], response.json()['run_id']
        assert worker.run_once().status.value == 'succeeded', owner.get(f'/tasks/{task}/continuation').json().get('reason')
        assert owner.get(f'/runs/{run}/report').status_code == 200
        assert owner.get(f'/runs/{run}/evidence').status_code == 200
        accounting = owner.get(f'/runs/{run}/usage').json()['session_accounting']
        assert accounting['requests_reserved'] == 4 and accounting['unknown_token_reservation'] == 0
        assert inputs.reads == 1 and secrets.read_names == ['llm-api', 'sol-review-api']
        assert worker.run_once().status.value == 'idle'
