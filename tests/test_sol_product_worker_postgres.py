"""Opt-in product release through real SQL/API/Worker; scripted external IO."""
import json
from copy import deepcopy
from uuid import UUID

import pytest

from app.product import sol_contract as responses_product, sol_chat_contract as chat_product
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, resume, setup_worker


def _name_input(summary):
    from app.product.player_language import render_name_hints
    shared = summary.summary
    before = deepcopy(shared)
    summary.summary = deepcopy(shared)
    summary.summary['request'].update(data_dragon_version='16.21.1', data_dragon_language='zh_CN')
    expected = render_name_hints(summary.summary)
    assert '青钢影' in expected
    return shared, before, expected


def _assert_language_consumers(root, factories, product, expected, count):
    from app.product.player_language import PLAYER_LANGUAGE_POLICY
    for factory in factories:
        for provider in factory.providers.values():
            for request in provider.generator.requests:
                sections = [s for m in request.messages if m.content and m.content.lstrip().startswith('{')
                            for s in json.loads(m.content).get('sections', [])]
                assert any(PLAYER_LANGUAGE_POLICY in s['content'] and s['trust'] == 'internal_policy' for s in sections)
                assert any(expected in s['content'] and s['trust'] != 'internal_policy' for s in sections)
    contexts = [json.loads(p.read_bytes()) for p in root.glob('call-*/validation-context.json')]
    assert len(contexts) == count
    for context in contexts:
        inputs = product.restore_context(context)
        request = product.make_request(inputs, context['duty'], context['stage'])
        product.request_bytes(request)
        assert PLAYER_LANGUAGE_POLICY in request.messages[0].content
        assert expected in json.loads(inputs.data_json)['deterministic_source_facts']


@pytest.mark.parametrize('mode,restart', [('pass', False), ('repair', True)])
@pytest.mark.parametrize('product', [responses_product, chat_product], ids=['responses', 'chat'])
def test_product_worker_publishes_owner_report_with_cumulative_accounting(continued_api, tmp_path, monkeypatch, mode, restart, product):
    owner, other, repo, _ = continued_api
    task, run = create(owner)
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo, mode=mode,
        contract=product, profile=product.WORKER_PROFILE)
    shared, before, expected = _name_input(summary)
    worker, route = make()
    if restart:
        route.candidate.max_new_models = 3
        assert worker.run_once().status.value == 'paused'
        paused = owner.get(f'/tasks/{task}/continuation').json()
        assert paused['profile'] == product.WORKER_PROFILE
        assert resume(owner, task, paused['checkpoint_sha256'], 'product-continue').status_code == 200
        worker, _ = make()
    result = worker.run_once()
    assert result.status.value == 'succeeded', result
    assert worker.run_once().status.value == 'idle'
    stored = repo.get_by_task_id(owner_id='owner-1', task_id=UUID(task))
    assert stored.report_available and stored.publication_status.value == 'published'
    report = owner.get(f'/runs/{run}/report')
    assert report.status_code == 200, report.text
    assert other.get(f'/runs/{run}/report').status_code == 404
    usage = owner.get(f'/runs/{run}/usage')
    assert usage.status_code == 200, usage.text
    total = usage.json()['session_accounting']
    count = 6 if restart else 4
    assert (total['requests_reserved'], total['known_tokens'], total['unknown_token_reservation']) == (count, count * 20, 0)
    assert summary.reads == 1
    assert requests == ([[200], [200, 200, 200]] if restart else [[200, 200]])
    _assert_language_consumers(tmp_path/run/'.continuation/transport'/run/'review',
        factories, product, expected, 4 if restart else 2)
    assert shared == before
    if restart:
        journal = tmp_path / run / '.continuation/journal'
        application = json.loads((journal / 'application.json').read_bytes())
        fresh = [json.loads(p.read_bytes()) for p in journal.glob('*-fresh.json')]
        assert len(fresh) == 2
        assert {v['report_sha256'] for v in fresh} == {application['report_sha256']}


def test_chat_format_pause_keeps_known_cost_and_original_generation(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, _, _, failed = setup_worker(tmp_path, monkeypatch, repo, mode='bad_json',
        contract=chat_product, profile=chat_product.WORKER_PROFILE)
    worker, _ = make()
    assert worker.run_once().status.value == 'paused'
    state = owner.get(f'/tasks/{task}/continuation').json()
    assert state['reason'] == 'session_format_awaiting_manual_retry'
    assert state['session_accounting']['known_tokens'] == 60
    assert state['session_accounting']['unknown_token_reservation'] == 0
    assert owner.get(f'/runs/{run}/report').status_code == 409
    assert failed == [[200]]
    root = tmp_path / run / '.continuation/transport'
    before = {p: p.read_bytes() for p in root.rglob('*.json')}
    make, summary, _, calls = setup_worker(tmp_path, monkeypatch, repo,
        contract=chat_product, profile=chat_product.WORKER_PROFILE)
    assert resume(owner, task, state['checkpoint_sha256'], 'format-ordinary').status_code == 200
    worker, _ = make()
    assert worker.run_once().status.value == 'paused'
    assert calls == [[]]
    state = owner.get(f'/tasks/{task}/continuation').json()
    assert resume(owner, task, state['checkpoint_sha256'], 'format-manual', True).status_code == 200
    worker, _ = make()
    assert worker.run_once().status.value == 'succeeded'
    assert owner.get(f'/runs/{run}/report').status_code == 200
    total = owner.get(f'/runs/{run}/usage').json()['session_accounting']
    assert (total['requests_reserved'], total['known_tokens'], total['unknown_token_reservation'], total['retries']) == (5, 100, 0, 1)
    assert calls == [[], [200, 200]] and summary.reads == 0
    assert before and all(p.read_bytes() == value for p, value in before.items())


@pytest.mark.parametrize('mode,restart', [('pass', False), ('repair', True)])
@pytest.mark.parametrize('product', [responses_product, chat_product], ids=['responses', 'chat'])
def test_evidence_bound_product_uses_atomic_snapshot_and_owner_queries(continued_api, tmp_path, monkeypatch, product, mode, restart):
    from app.tasks.service import ReviewTaskService
    from app.tasks.models import CreateReviewTaskCommand, TaskPublicationMode
    from app.product.recent_review import RecentReviewProductRequest
    owner, other, repo, _ = continued_api
    result = ReviewTaskService(repository=repo).create(CreateReviewTaskCommand(
        owner_id='owner-1', idempotency_key='product-evidence',
        request=RecentReviewProductRequest(riot_id='DemoPlayer#TEST', routing_region='asia', focus='overall'),
        publication_mode=TaskPublicationMode.EVIDENCE_BOUND_V1))
    task, run = result.task.task_id, result.task.run_id
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo, mode=mode,
        contract=product, profile=product.WORKER_PROFILE)
    shared, before, expected = _name_input(summary)
    worker, route = make()
    if restart:
        route.candidate.max_new_models = 3
        assert worker.run_once().status.value == 'paused'
        paused = owner.get(f'/tasks/{task}/continuation').json()
        assert resume(owner, task, paused['checkpoint_sha256'], 'evidence-continue').status_code == 200
        worker, _ = make()
    result = worker.run_once()
    assert result.status.value == 'succeeded', result
    stored = repo.get_by_task_id(owner_id='owner-1', task_id=task)
    assert stored.publication_mode == TaskPublicationMode.EVIDENCE_BOUND_V1
    assert stored.publication_reference is not None and stored.summary_digest is not None
    evidence = owner.get(f'/runs/{run}/evidence')
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()['run_id'] == run and evidence.json()['revision'] == 1
    assert other.get(f'/runs/{run}/evidence').status_code == 404
    assert owner.get(f'/runs/{run}/report').status_code == (200 if stored.report_available else 409)
    assert other.get(f'/runs/{run}/report').status_code == 404
    assert stored.report_available and worker.run_once().status.value == 'idle'
    assert summary.reads == 1
    assert requests == ([[200], [200, 200, 200]] if restart else [[200, 200]])
    total = owner.get(f'/runs/{run}/usage').json()['session_accounting']
    count = 6 if restart else 4
    assert (total['requests_reserved'], total['known_tokens'], total['unknown_token_reservation']) == (count, count * 20, 0)
    from app.product.source_scope import SOURCE_SCOPE_POLICY, SCOPE_MARKER
    # The task above explicitly selects Evidence publication. Legacy tasks
    # intentionally have no source projection and are covered separately.
    generation = [r for factory in factories for provider in factory.providers.values()
                  for r in provider.generator.requests]
    assert len(generation) == 2
    for request in generation:
        sections = [s for m in request.messages if m.content and m.content.lstrip().startswith('{')
                    for s in json.loads(m.content).get('sections', [])]
        assert any(SOURCE_SCOPE_POLICY in s['content'] and s['trust'] == 'internal_policy' for s in sections)
        assert any(SCOPE_MARKER in s['content'] for s in sections)
    review_root = tmp_path / run / '.continuation/transport' / run / 'review'
    _assert_language_consumers(review_root, factories, product, expected, 4 if restart else 2)
    assert shared == before
    contexts = [json.loads(p.read_bytes()) for p in review_root.glob('call-*/validation-context.json')]
    assert len(contexts) == (4 if restart else 2)
    for context in contexts:
        supplied = json.loads(context['data_json'])['deterministic_source_facts']
        assert SCOPE_MARKER in supplied
    if restart:
        journal = tmp_path / run / '.continuation/journal'
        application = json.loads((journal / 'application.json').read_bytes())
        fresh = [json.loads(p.read_bytes()) for p in journal.glob('*-fresh.json')]
        assert len(fresh) == 2
        assert {v['report_sha256'] for v in fresh} == {application['report_sha256']}


@pytest.mark.parametrize('initial_product', [False, True])
@pytest.mark.parametrize('product', [responses_product, chat_product], ids=['responses', 'chat'])
def test_existing_task_never_changes_contract_on_worker_switch(continued_api, tmp_path, monkeypatch, initial_product, product):
    from app.evaluation import sol_review_contract as old
    from app.tasks.continuation import WORKER_SOL_PROFILE
    owner, _, repo, _ = continued_api
    task, _ = create(owner)
    prior = responses_product if product is chat_product else old
    contracts = [(prior, prior.WORKER_PROFILE if product is chat_product else WORKER_SOL_PROFILE), (product, product.WORKER_PROFILE)]
    first_contract, first_profile = contracts[int(initial_product)]
    make, _, _, first_calls = setup_worker(tmp_path, monkeypatch, repo,
        contract=first_contract, profile=first_profile)
    worker, route = make()
    route.candidate.max_new_models = 0
    assert worker.run_once().status.value == 'paused'
    pin = owner.get(f'/tasks/{task}/continuation').json()['checkpoint_sha256']
    assert resume(owner, task, pin, 'profile-switch').status_code == 200
    next_contract, next_profile = contracts[int(not initial_product)]
    make, _, _, next_calls = setup_worker(tmp_path, monkeypatch, repo,
        contract=next_contract, profile=next_profile)
    worker, _ = make()
    assert worker.run_once().status.value == 'paused'
    state = owner.get(f'/tasks/{task}/continuation').json()
    assert state['profile'] == first_profile and state['reason'] == 'continuation_binding_changed'
    assert first_calls == [[]] and next_calls == []


@pytest.mark.parametrize('cancel', [False, True])
@pytest.mark.parametrize('product', [responses_product, chat_product], ids=['responses', 'chat'])
def test_product_timeout_recovery_or_cancel_keeps_unknown_cost(continued_api, tmp_path, monkeypatch, cancel, product):
    owner, other, repo, _ = continued_api
    task, run = create(owner)
    make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo, statuses=(524,),
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make()
    assert worker.run_once().status.value == 'paused'
    state = owner.get(f'/tasks/{task}/continuation').json()
    unknown = state['session_accounting']['unknown_token_reservation']
    assert unknown > 0
    if cancel:
        assert owner.post(f'/tasks/{task}/cancel', headers={'Idempotency-Key': 'cancel-product'}).status_code == 200
        assert resume(owner, task, state['checkpoint_sha256'], 'late', True).status_code == 409
    else:
        assert resume(owner, task, state['checkpoint_sha256'], 'ordinary').status_code == 200
        worker, _ = make()
        assert worker.run_once().status.value == 'paused'
        state = owner.get(f'/tasks/{task}/continuation').json()
        assert resume(other, task, state['checkpoint_sha256'], 'foreign', True).status_code == 404
        assert resume(owner, task, state['checkpoint_sha256'], 'manual', True).status_code == 200
        worker, _ = make()
        assert worker.run_once().status.value == 'succeeded'
        assert owner.get(f'/runs/{run}/report').status_code == 200
    total = owner.get(f'/runs/{run}/usage').json()['session_accounting']
    assert total['unknown_token_reservation'] == unknown
    assert total['requests_reserved'] == (3 if cancel else 5)
    assert total['retries'] == (0 if cancel else 1)
    assert requests == ([[524]] if cancel else [[524], [], [200, 200]])
    assert summary.reads == 1
