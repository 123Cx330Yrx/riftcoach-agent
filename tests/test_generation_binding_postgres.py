"""Creation pins and real Worker continuation using scripted external services."""
import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

from app.product import player_wording_worker as wording, sol_chat_contract as chat
from app.product.generation_binding import capture
from app.tasks.service import ReviewTaskService
from app.persistence.task_record import ReviewTaskRecord
from tests.test_task_service import command
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, setup_worker, resume


@pytest.fixture
def pinned_api(continued_api):
    try:
        yield continued_api
    finally:
        # This fixture owns only the disposable CI database. Production downgrade
        # deliberately refuses to discard bindings (covered separately below).
        with continued_api[2]._session_factory() as s, s.begin():
            s.execute(sa.update(ReviewTaskRecord).values(generation_binding=None))


def create_pinned(repo, profile=wording.WORKER_PROFILE, key='binding'):
    view = ReviewTaskService(repository=repo, generation_profile=profile).create(command(key=key)).task
    return repo.get_by_task_id(owner_id='owner-1', task_id=view.task_id)


def test_creation_replay_and_private_pin(pinned_api):
    owner, other, repo, _ = pinned_api
    first = create_pinned(repo)
    replay = create_pinned(repo, chat.WORKER_PROFILE)
    assert replay.task_id == first.task_id
    assert replay.generation_binding == first.generation_binding == capture(wording.WORKER_PROFILE)
    assert 'generation_binding' not in first.model_dump(mode='json')
    assert 'generation_binding' not in owner.get(f'/tasks/{first.task_id}').text
    assert other.get(f'/tasks/{first.task_id}').status_code == 404
    assert repo.get_by_task_id(owner_id='owner-2', task_id=first.task_id) is None
    legacy = create_pinned(repo, None, key='legacy')
    assert legacy.generation_binding is None


@pytest.mark.parametrize('case,reason', [
    ('missing', 'generation_binding_required'),
    ('profile', 'generation_profile_mismatch'),
    ('changed', 'generation_binding_changed'),
    ('claim_race', 'generation_binding_changed'),
])
def test_rejected_before_sources_or_model(pinned_api, tmp_path, monkeypatch, case, reason):
    owner, _, repo, _ = pinned_api
    profile = None if case == 'missing' else chat.WORKER_PROFILE if case == 'profile' else wording.WORKER_PROFILE
    task = create_pinned(repo, profile)
    def alter():
        with repo._session_factory() as s, s.begin():
            row = s.get(ReviewTaskRecord, task.task_id)
            pin = deepcopy(row.generation_binding)
            pin['components_sha256'] = '0' * 64
            row.generation_binding = pin
    if case == 'changed':
        alter()
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo,
        contract=wording, profile=wording.WORKER_PROFILE)
    worker, route = make()
    if case == 'claim_race':
        original = route.candidate.execute
        def execute(claimed):
            alter()
            return original(claimed)
        route.candidate.execute = execute
    assert worker.run_once().status.value == 'paused'
    stored = repo.get_by_task_id(owner_id='owner-1', task_id=task.task_id)
    assert stored.status.value == 'recovery_required' and stored.recovery_reason == reason
    assert summary.reads == 0 and not factories and not requests
    assert worker.run_once().status.value == 'idle'


@pytest.mark.parametrize('mode', ['pass', 'repair'])
def test_wording_worker_resume_preserves_generation_and_review_contract(pinned_api, tmp_path, monkeypatch, mode):
    from app.product.player_wording_contract import WORDING
    from app.product.player_language import PLAYER_LANGUAGE_POLICY
    owner, _, repo, _ = pinned_api
    task = create_pinned(repo)
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo,
        mode=mode, contract=wording, profile=wording.WORKER_PROFILE)
    worker, route = make()
    route.candidate.max_new_models = 3
    assert worker.run_once().status.value == 'paused'
    state = owner.get(f'/tasks/{task.task_id}/continuation').json()
    assert resume(owner, str(task.task_id), state['checkpoint_sha256'], 'continue').status_code == 200
    worker, _ = make()
    assert worker.run_once().status.value == 'succeeded'
    assert summary.reads == 1
    assert requests == ([[200], [200]] if mode == 'pass' else [[200], [200, 200, 200]])
    generated = [r for f in factories for p in f.providers.values() for r in p.generator.requests]
    assert generated
    for request in generated:
        assert any(WORDING in m.content for m in request.messages if m.content)
    contexts = list((tmp_path/task.run_id/'.continuation/transport'/task.run_id/'review').glob('call-*/validation-context.json'))
    assert len(contexts) == (2 if mode == 'pass' else 4)
    for path in contexts:
        value = json.loads(path.read_bytes())
        inputs = chat.restore_context(value)
        old = chat.make_request(inputs, value['duty'], value['stage'])
        new = wording.make_request(inputs, value['duty'], value['stage'])
        assert chat.request_bytes(old) == wording.request_bytes(new)
        assert PLAYER_LANGUAGE_POLICY in new.messages[0].content
    stored = repo.get_by_task_id(owner_id='owner-1', task_id=task.task_id)
    assert stored.report_available and stored.generation_binding == task.generation_binding


def test_downgrade_refuses_to_erase_creation_pin(pinned_api):
    import os
    from alembic import command as migration_command
    from alembic.config import Config
    repo = pinned_api[2]
    create_pinned(repo)
    config = Config('alembic.ini')
    config.set_main_option('sqlalchemy.url', os.environ['RIFTCOACH_TEST_DATABASE_URL'])
    with pytest.raises(sa.exc.DBAPIError, match='cannot discard'):
        migration_command.downgrade(config, '0015_task_continuation')
    with repo._session_factory() as s:
        assert s.scalar(sa.text('SELECT version_num FROM alembic_version')) == '0016_task_generation_binding'
        assert s.scalar(sa.select(ReviewTaskRecord.generation_binding)) is not None
