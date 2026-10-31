"""Product contract on actual Runtime/session; all model IO is scripted."""
import json
from pathlib import Path

import pytest

from app.evaluation import sol_review_contract as prior
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused
from app.product import sol_contract as product
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.product.sol_workflow import ProductWorkflow, ProductBudget
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.observed_provider import ObservedLLMProvider
from tests.test_sol_natural_candidate import application, offline
from tests.test_natural_duty_candidate import run
from tests.test_native_editor_product_budget import SummaryBuilder
from tests.test_runtime_execution_factory_combined import _NoopObserver


def session_at(root, *, manual=False, pins=None, clock=None, max_new_models=None):
    return CandidateSession(root / 'session', binding=dict(worker_profile=product.WORKER_PROFILE,
        task_id='product-test', candidate_contract=product.VERSION),
        transport_root=root / 'transport' / 'candidate', journal_root=root / 'journal',
        contract_module=product, worker_product=True, manual_retry=manual,
        guard_sha=None if pins is None else pins['guard_sha256'],
        checkpoint_sha=None if pins is None else pins['checkpoint_sha256'],
        max_new_models=max_new_models, before_new_model=lambda: None,
        **({} if clock is None else {'clock': clock}))


def current_pins(root):
    from app.evaluation.sol_natural_session import digest
    return {'guard_sha256': digest((root/'session/guard.json').read_bytes()),
            'checkpoint_sha256': digest(sorted((root/'session/checkpoints').glob('*.json'))[-1].read_bytes())}


def make_app(root, session, *, mode='repair', statuses=(), extra_round=False):
    factory, attempts = application(root, mode=mode, statuses=statuses, candidate=product, factory_only=True)
    original = factory.make
    def make(name):
        provider = original(name)
        provider.generator.extra_round = extra_round
        return provider
    factory.make = make
    app = build_natural_duty_candidate(summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=root/'runs'/str(len(list((root/'session/checkpoints').glob('*.json')))),
        candidate=product, execution_session=session)
    flows = []
    original_flow = app._runtime._execution_factory._review_workflow_factory
    def capture(runtime, budget):
        flow = original_flow(runtime, budget); flows.append(flow); return flow
    app._runtime._execution_factory._review_workflow_factory = capture
    return app, factory, flows, attempts


@pytest.mark.parametrize('mode,extra,count', [('pass', False, 4), ('repair', False, 6), ('repair', True, 7), ('identical', False, 6)])
def test_product_publishes_complete_pair_and_exact_applied_report(tmp_path, mode, extra, count):
    with session_at(tmp_path) as session:
        app, factory, flows, attempts = make_app(tmp_path, session, mode=mode, extra_round=extra)
        result = run(app)
        assert result.publication_status.value == 'published', result
        flow = flows[0]
        assert isinstance(flow, ProductWorkflow)
        assert flow.send.provider.calls == count
        assert len(attempts) == (2 if mode == 'pass' else 4)
        if mode != 'pass':
            application_record = json.loads((tmp_path/'journal/application.json').read_bytes())
            fresh = [json.loads(path.read_bytes()) for path in (tmp_path/'journal').glob('*-fresh.json')]
            assert len(fresh) == 2
            assert {row['report_sha256'] for row in fresh} == {application_record['report_sha256']}
        if mode == 'identical':
            record = json.loads((tmp_path/'journal/identical-patch-deduplication.json').read_bytes())
            assert {row['duty'] for item in record['resolutions'] for row in item['issue_coverage']} == {'facts', 'completion'}
        session.close({'completed': True})


@pytest.mark.parametrize('mode,reason', [('bad_anchor', 'product_patch_repair_required'),
    ('fresh_reject', 'product_fresh_repair_required'), ('overlap', 'session_awaiting_patch_coordination')])
def test_unsafe_or_rejected_repairs_pause_without_rebuying(tmp_path, mode, reason):
    for number in range(2):
        with session_at(tmp_path, pins=None if number == 0 else current_pins(tmp_path)) as session:
            app, _, flows, attempts = make_app(tmp_path, session, mode=mode)
            with pytest.raises(SessionPaused, match=reason):
                run(app)
            if number:
                assert attempts == []
            assert not (tmp_path/'journal/outcome.json').exists()
            assert not (tmp_path/'session/terminal.json').exists()


def test_contract_reuses_complete_business_requests_but_has_independent_budget():
    from app.evaluation import role_qualification
    from scripts import review_duty_composition as duty
    cases, _ = role_qualification.frozen_cases()
    assert len(cases) == 15
    for _, source in cases:
        inputs = duty.TimedDocumentWorkflow.build_inputs(source)
        for name in duty.DUTIES:
            assert product.request_bytes(product.make_request(inputs, name)) == prior.request_bytes(prior.make_request(inputs, name))
    d = product.CONTRACT.descriptor()
    assert (d['max_calls'], d['total_tokens'], d['execution_timeout_s'], d['transport_retries']) == (8, 401920, 900, 2)
    assert product.CONTRACT.snapshot() != prior.CONTRACT.snapshot()
    assert prior.CONTRACT.descriptor()['max_calls'] == 10


def isolated_budget(root, session, statuses=()):
    factory, attempts = application(root, candidate=product, statuses=statuses, factory_only=True)
    provider = ObservedLLMProvider(delegate=factory('candidate'), observer=_NoopObserver(),
        request_identity=product.request_identity)
    return ProductBudget(provider, session=session, coach_contract=product.CONTRACT), attempts


@pytest.mark.parametrize('limit', ['calls', 'tokens', 'generation_slots', 'active_time'])
def test_budget_stops_before_transport_and_preserves_cumulative_clock(tmp_path, limit):
    from tests.test_natural_duty_transport import generation
    now = [0.0]
    with session_at(tmp_path, clock=lambda: now[0]) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        if limit == 'calls':
            budget.calls = 8
        elif limit == 'tokens':
            budget.tokens, budget.reserved_tokens = 300000, 100000
        elif limit == 'generation_slots':
            budget.calls = 4
        else:
            now[0] = 900.0
        before = budget.calls
        with pytest.raises(SessionPaused, match='product_budget_exhausted'):
            budget.chat(generation())
        assert budget.calls == before and attempts == []
        assert not list((tmp_path/'transport').rglob('http-request.json'))
    if limit == 'active_time':
        now[0] += 100000  # Human waiting does not consume or reset the task clock.
        with session_at(tmp_path, clock=lambda: now[0], pins=current_pins(tmp_path)) as resumed:
            assert resumed.active_seconds == 900
            budget, attempts = isolated_budget(tmp_path, resumed)
            with pytest.raises(SessionPaused, match='product_budget_exhausted'):
                budget.chat(generation())
            assert attempts == []


def test_only_two_explicit_same_item_retries_and_ordinary_resume_never_sends(tmp_path):
    from scripts import review_duty_composition as duty
    from tests.test_natural_duty_candidate import Responses
    request = product.make_request(duty.TimedDocumentWorkflow.build_inputs(Responses().req), 'facts')
    requests = []
    unknown = 0
    for ordinal, manual in enumerate([False, False, True, True, True]):
        with session_at(tmp_path, manual=manual, pins=None if ordinal == 0 else current_pins(tmp_path)) as session:
            budget, attempts = isolated_budget(tmp_path, session, statuses=(524,))
            reason = 'session_retry_budget_extension_required' if ordinal == 4 else 'session_timeout_awaiting_manual_retry'
            with pytest.raises(SessionPaused, match=reason):
                budget.chat(request)
            requests.append(attempts)
            assert budget.reserved_tokens >= unknown
            unknown = budget.reserved_tokens
    assert requests == [[524], [], [524], [524], []]
    assert budget.calls == 3 and budget.router._retries == 2 and unknown > 0


@pytest.mark.parametrize('calls,known,unknown,active', [(7, 0, 0, 0), (4, 200000, 50000, 0), (4, 0, 0, 900)])
def test_revision_requires_room_for_both_fresh_reviews(tmp_path, calls, known, unknown, active):
    now = [0.0]
    with session_at(tmp_path, clock=lambda: now[0]) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        budget.calls, budget.tokens, budget.reserved_tokens = calls, known, unknown
        from types import SimpleNamespace
        flow = object.__new__(ProductWorkflow)
        flow.send, flow.session, flow.contract_module = SimpleNamespace(provider=budget), session, product
        now[0] = active
        with pytest.raises(SessionPaused, match='product_fresh_budget_required'):
            flow._fresh_room()
        assert not (tmp_path/'journal/application.json').exists() and attempts == []


def test_product_requires_its_own_durable_profile(tmp_path):
    with pytest.raises(ValueError, match='product.*session'):
        application(tmp_path, candidate=product)
    with pytest.raises(ValueError, match='product'):
        CandidateSession(tmp_path/'wrong', binding=dict(worker_profile='sol-dual-development-v1', task_id='x'),
            transport_root=tmp_path/'transport', journal_root=tmp_path/'journal',
            contract_module=product, worker_product=True)
