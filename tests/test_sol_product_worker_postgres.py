"""Opt-in product release through real SQL/API/Worker; scripted external IO."""
import json
from uuid import UUID

import pytest

from app.product import sol_contract as product
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, resume, setup_worker


@pytest.mark.parametrize('mode,restart', [('pass', False), ('repair', True)])
def test_product_worker_publishes_owner_report_with_cumulative_accounting(continued_api, tmp_path, monkeypatch, mode, restart):
    owner, other, repo, _ = continued_api
    task, run = create(owner)
    make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo, mode=mode,
        contract=product, profile=product.WORKER_PROFILE)
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
    if restart:
        journal = tmp_path / run / '.continuation/journal'
        application = json.loads((journal / 'application.json').read_bytes())
        fresh = [json.loads(p.read_bytes()) for p in journal.glob('*-fresh.json')]
        assert len(fresh) == 2
        assert {v['report_sha256'] for v in fresh} == {application['report_sha256']}


def test_evidence_bound_product_uses_atomic_snapshot_and_owner_queries(continued_api, tmp_path, monkeypatch):
    from app.tasks.service import ReviewTaskService
    from app.tasks.models import CreateReviewTaskCommand, TaskPublicationMode
    from app.product.recent_review import RecentReviewProductRequest
    owner, other, repo, _ = continued_api
    result = ReviewTaskService(repository=repo).create(CreateReviewTaskCommand(
        owner_id='owner-1', idempotency_key='product-evidence',
        request=RecentReviewProductRequest(riot_id='DemoPlayer#TEST', routing_region='asia', focus='overall'),
        publication_mode=TaskPublicationMode.EVIDENCE_BOUND_V1))
    task, run = result.task.task_id, result.task.run_id
    make, _, _, _ = setup_worker(tmp_path, monkeypatch, repo,
        contract=product, profile=product.WORKER_PROFILE)
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


@pytest.mark.parametrize('initial_product', [False, True])
def test_existing_task_never_changes_contract_on_worker_switch(continued_api, tmp_path, monkeypatch, initial_product):
    from app.evaluation import sol_review_contract as old
    from app.tasks.continuation import WORKER_SOL_PROFILE
    owner, _, repo, _ = continued_api
    task, _ = create(owner)
    contracts = [(old, WORKER_SOL_PROFILE), (product, product.WORKER_PROFILE)]
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
def test_product_timeout_recovery_or_cancel_keeps_unknown_cost(continued_api, tmp_path, monkeypatch, cancel):
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
