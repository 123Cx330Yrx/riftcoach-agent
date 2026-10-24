"""Dynamic actual Runtime/worker checks; scripted HTTP is not model acceptance."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json

import pytest

from app.evaluation import sol_natural_contract as old, sol_necessity_contract as new
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, tree
from app.runtime.sol_natural_provider import SolNaturalProvider
from app.runtime.store import RuntimeTraceStore
from scripts import review_necessity_candidate as fixed
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_process import run_once, read_json
from scripts.reviewer_responses_transport import Profile
from tests.test_natural_duty_candidate import Responses, run
from tests.test_sol_natural_candidate import application, offline
from tests.test_sol_natural_session import session, app_for, crash_after_model, NoSearch


@pytest.mark.parametrize('duty', ['facts', 'completion'])
@pytest.mark.parametrize('stage', ['initial', 'fresh'])
def test_dynamic_full_source_policy_and_old_receiver_isolation(duty, stage):
    # This input differs from all fixed a/b/c; dynamic restoration must work.
    inputs = build_inputs(Responses().req)
    request = new.make_request(inputs, duty, stage)
    baseline = old.make_request(inputs, duty, stage)
    context = request.metadata[new.CONTEXT]
    assert new.restore_context(context) == inputs
    new.validate_business(visible(json_value(request)), context)
    assert new.role_for_request(request) == 'review'
    assert request.messages[1:] == baseline.messages[1:]
    if duty == 'facts':
        assert request.messages[0].content == baseline.messages[0].content + fixed.NECESSITY_POLICY
    else:
        assert request.messages == baseline.messages
    with pytest.raises(ValueError):
        old.role_for_request(request)
    with pytest.raises(ValueError):
        new.role_for_request(baseline)
    with pytest.raises(ValueError):
        old.validate_business(visible(json_value(request)), context)
    with pytest.raises(ValueError):
        new.validate_business(visible(json_value(baseline)), baseline.metadata[old.CONTEXT])


@pytest.mark.parametrize('fault', ['report', 'sources', 'policy', 'version', 'group', 'mode'])
def test_changed_material_or_contract_rejected_before_claim(tmp_path, fault):
    request = new.make_request(build_inputs(Responses().req), 'facts')
    business, context = visible(json_value(request)), deepcopy(request.metadata[new.CONTEXT])
    profile, mode = new.REVIEW_PROFILE, new.RESPONSE_MODE
    if fault == 'report':
        context['report'] += ' different report'
    elif fault == 'sources':
        context['pack_json'] = '{}'
    elif fault == 'policy':
        business['messages'][0]['content'] = 'different policy'
    elif fault == 'version':
        context['version'] = old.VERSION
    elif fault == 'group':
        profile = Profile(group='GPT-pro', route='proxy-12000')
    else:
        mode = 'natural-sol-v1'
    with pytest.raises((ValueError, KeyError)):
        run_once(business, validation_context=context, profile=profile,
            response_mode=mode, api_key='OFFLINE_SENTINEL', directory=tmp_path/'call')
    assert not (tmp_path/'call').exists()


@pytest.mark.parametrize('mode,expected,calls', [
    ('repair', 'candidate_repaired_pass_unqualified', 6),
    ('pass', 'candidate_initial_pass_unqualified', 4),
    ('fresh_reject', 'fresh_facts_rejected', 5),
])
def test_real_application_worker_application_and_same_report_fresh(tmp_path, mode, expected, calls):
    app, factory, flows, attempts = application(tmp_path, candidate=new, mode=mode)
    result = run(app)
    flow, router = flows[0], factory.providers['candidate']
    assert flow.outcome == expected and flow.send.provider.calls == calls
    assert len(attempts) == calls-2
    assert result.publication_status.value == 'rejected'
    trace = RuntimeTraceStore(tmp_path/'reports', 'candidate').read_trace(result.trace_reference)
    assert trace.identity.coach_contract == new.CONTRACT.snapshot()
    price = new.CONTRACT.pricing_profiles[new.REVIEW_PROVIDER, new.REVIEW_MODEL]
    assert (price.input_cost_per_million, price.output_cost_per_million) == (Decimal('.5'), Decimal('2.5'))
    root = router.reviewer.directory
    contexts = [read_json(p) for p in sorted(root.glob('call-*/validation-context.json'))]
    for path in root.glob('call-*/profile.json'):
        profile = read_json(path)
        assert profile['group'] == 'GPT-企业专线' and profile['response_mode'] == new.RESPONSE_MODE
    if mode == 'repair':
        fresh = [v for v in contexts if v['stage'] == 'fresh']
        assert len(fresh) == 2 and {v['duty'] for v in fresh} == {'facts', 'completion'}
        assert fresh[0]['report'] == fresh[1]['report'] == flow.assembly.report
        assert all(v['report'] != flow.assembly.report for v in contexts if v['stage'] == 'initial')
        assert len(list(flow.journal_root.glob('application.json'))) == 1
        assert all(read_json(p)['usage_state'] == 'known' for p in root.glob('call-*/receipt.json'))
    elif mode == 'pass':
        assert not (flow.journal_root/'application.json').exists()


@pytest.mark.parametrize('fault', ['wrong_model', 'reasoning_conflict', 'non_tool'])
def test_complete_protocol_or_identity_rejection_is_not_timeout_retry(tmp_path, fault):
    app, factory, flows, attempts = application(tmp_path, candidate=new, mode=fault)
    run(app)
    assert attempts == [200]
    assert flows[0].outcome == 'candidate_execution_failed'
    assert flows[0].send.provider.calls == 3
    assert not (flows[0].journal_root/'application.json').exists()


def test_timeout_retains_unknown_and_only_retries_same_current_stage(tmp_path):
    app, factory, flows, attempts = application(tmp_path, candidate=new, statuses=(524,))
    run(app)
    assert attempts == [524, 200, 200, 200, 200]
    assert flows[0].outcome == 'candidate_repaired_pass_unqualified'
    assert flows[0].send.provider.reserved_tokens > 0
    requests = sorted(factory.providers['candidate'].reviewer.directory.glob('call-*/request.json'))
    assert read_json(requests[0]) == read_json(requests[1])
    assert len(factory.providers['candidate'].generator.requests) == 2


def test_receipt_reconciliation_resume_and_closed_readonly_replay(tmp_path):
    first = session(tmp_path, candidate=new)
    crash_after_model(first, 3)
    with pytest.raises(SessionPaused), first:
        app, factory, attempts = app_for(tmp_path, first, 1, candidate=new)
        run(app)
    assert attempts == [200]
    original = tree(first.transport_root)
    recovered = session(tmp_path, first, candidate=new, reconcile=True)
    with recovered:
        value = recovered.reconcile_completed()
        assert value['provider_requests'] == 0 and value['reconciled_ordinal'] == 3
    assert tree(first.transport_root) == original
    resumed = session(tmp_path, recovered, candidate=new)
    with resumed:
        app, factory, attempts = app_for(tmp_path, resumed, 2, candidate=new, knowledge=NoSearch())
        result = run(app)
        assert attempts == [200, 200, 200]
        assert factory.providers['candidate'].candidate_budget.calls == 6
        assert result.publication_status.value == 'rejected'
        resumed.close(dict(outcome=read_json(resumed.journal_root/'outcome.json')['outcome']))
    before = tree(resumed.root), tree(resumed.transport_root), tree(resumed.journal_root)
    replay = session(tmp_path, resumed, candidate=new, read_only=True)
    with replay:
        app, factory, attempts = app_for(tmp_path, replay, 3, candidate=new, knowledge=NoSearch())
        run(app)
        assert attempts == [] and factory.providers['candidate'].generator.requests == []
    assert before == (tree(replay.root), tree(replay.transport_root), tree(replay.journal_root))


def test_old_candidate_cannot_silently_consume_new_router(tmp_path):
    app, factory, flows, attempts = application(tmp_path, candidate=new)
    with pytest.raises(ValueError, match='sol_reviewer_contract_binding'):
        SolNaturalProvider(factory.descriptor.generator, factory.descriptor.reviewer)
    with pytest.raises(ValueError, match='session_candidate_contract_binding'):
        CandidateSession(tmp_path/'session', binding={'candidate_contract':new.VERSION},
            transport_root=tmp_path/'transport', journal_root=tmp_path/'journal')


def test_actual_first_send_capture_has_no_key_io_or_quality_claim():
    from scripts.prepare_sol_necessity_natural import prepare
    result = prepare()
    assert result['contract'] == new.CONTRACT.snapshot().model_dump(mode='json')
    assert result['profile']['group'] == 'GPT-企业专线'
    assert result['logical_generation_calls'] + result['logical_review_calls'] == 6
    assert all(result[k] is False for k in ('key_read', 'paid_launcher_ready', 'execution_authorized',
        'semantic_approval', 'qualified', 'production_admitted', 'publication_allowed'))
    assert result['provider_requests'] == 0
