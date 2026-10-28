"""Shared live-path binding with offline HTTP; never model quality evidence."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from app.evaluation import sol_review_contract as candidate, sol_completion_contract as diagnostic
from app.evaluation import sol_necessity_contract as previous
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.sol_natural_session import SessionPaused, tree
from app.runtime.store import RuntimeTraceStore
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_process import run_once, read_json
from scripts.reviewer_responses_transport import Profile
from tests.test_natural_duty_candidate import Responses, run
from tests.test_sol_natural_candidate import application, offline
from tests.test_sol_natural_session import session, app_for, NoSearch


@pytest.mark.parametrize('duty', ['facts', 'completion'])
@pytest.mark.parametrize('stage', ['initial', 'fresh'])
def test_full_business_matches_reviewed_diagnostic_without_inheritance(duty, stage, monkeypatch):
    # Arbitrary dynamic input, with no access to the fixed diagnostic material.
    monkeypatch.setattr(diagnostic, 'materials', lambda: pytest.fail('fixed diagnostic material read'))
    inputs = build_inputs(Responses().req)
    request = candidate.make_request(inputs, duty, stage)
    reference = diagnostic.make_request(inputs, duty, stage)
    assert replace(request, metadata=reference.metadata) == reference
    assert candidate.restore_context(request.metadata[candidate.CONTEXT]) == inputs
    candidate.validate_business(visible(json_value(request)), request.metadata[candidate.CONTEXT])
    for old in (previous, diagnostic):
        with pytest.raises((ValueError, KeyError)):
            old.role_for_request(request)
        with pytest.raises((ValueError, KeyError)):
            candidate.role_for_request(old.make_request(inputs, duty, stage))
    assert candidate.request_sha(request)


@pytest.mark.parametrize('fault', ['report', 'sources', 'policy', 'version', 'group', 'mode', 'control_case'])
def test_invalid_binding_stops_before_claim(tmp_path, fault):
    request = candidate.make_request(build_inputs(Responses().req), 'completion')
    business, context = visible(json_value(request)), deepcopy(request.metadata[candidate.CONTEXT])
    profile, mode = candidate.REVIEW_PROFILE, candidate.RESPONSE_MODE
    if fault == 'report': context['report'] += ' altered'
    elif fault == 'sources': context['pack_json'] = '{}'
    elif fault == 'policy': business['messages'][0]['content'] = 'different policy'
    elif fault == 'version': context['version'] = previous.VERSION
    elif fault == 'group': profile = Profile(group='GPT-pro', route='proxy-12000')
    elif fault == 'mode': mode = diagnostic.RESPONSE_MODE
    else: context['control_case'] = 'b'
    with pytest.raises((ValueError, KeyError)):
        run_once(business, validation_context=context, profile=profile, response_mode=mode,
            api_key='OFFLINE_SENTINEL', directory=tmp_path/'call')
    assert not (tmp_path/'call').exists()


@pytest.mark.parametrize('mode,outcome,calls', [
    ('repair', 'candidate_repaired_pass_unqualified', 6),
    ('mixed_tool', 'candidate_repaired_pass_unqualified', 6),
    ('pass', 'candidate_initial_pass_unqualified', 4),
    ('fresh_reject', 'fresh_facts_rejected', 5),
])
def test_actual_runtime_worker_single_application_and_same_report(tmp_path, mode, outcome, calls):
    app, factory, flows, attempts = application(tmp_path, candidate=candidate, mode=mode)
    result = run(app)
    flow, router = flows[0], factory.providers['candidate']
    assert flow.outcome == outcome and flow.send.provider.calls == calls
    assert len(attempts) == calls-2 and result.publication_status.value == 'rejected'
    trace = RuntimeTraceStore(tmp_path/'reports', 'candidate').read_trace(result.trace_reference)
    assert trace.identity.coach_contract == candidate.CONTRACT.snapshot()
    assert trace.usage.provider_calls_attempted == calls
    contexts = [read_json(p) for p in sorted(router.reviewer.directory.glob('call-*/validation-context.json'))]
    assert {c['version'] for c in contexts} == {candidate.VERSION}
    for path in router.reviewer.directory.glob('call-*/profile.json'):
        profile = read_json(path)
        assert profile['response_mode'] == candidate.RESPONSE_MODE and profile['group'] == 'GPT-企业专线'
    if mode in ('repair', 'mixed_tool'):
        fresh = [c for c in contexts if c['stage'] == 'fresh']
        assert len(fresh) == 2 and {c['duty'] for c in fresh} == {'facts', 'completion'}
        assert fresh[0]['report'] == fresh[1]['report'] == flow.assembly.report
        assert all(c['report'] != flow.assembly.report for c in contexts if c['stage'] == 'initial')
        assert len(list(flow.journal_root.glob('application.json'))) == 1
    elif mode == 'pass':
        assert not (flow.journal_root/'application.json').exists()


@pytest.mark.parametrize('failure', ['timeout', 'format'])
def test_current_stage_manual_recovery_preserves_prefix_and_readonly_replay(tmp_path, failure):
    prefix = session(tmp_path, candidate=candidate, max_new_models=3)
    with pytest.raises(SessionPaused), prefix:
        app, factory, calls = app_for(tmp_path, prefix, 1, candidate=candidate)
        run(app)
    assert calls == [200]
    prefix_transport = tree(prefix.transport_root)
    first = session(tmp_path, prefix, candidate=candidate)
    reason = 'timeout_awaiting_manual_retry' if failure == 'timeout' else 'format_awaiting_manual_retry'
    with pytest.raises(SessionPaused, match=reason), first:
        app, factory, calls = app_for(tmp_path, first, 2, candidate=candidate, knowledge=NoSearch(),
            statuses=(524,) if failure == 'timeout' else (), mode='bad_json' if failure == 'format' else 'repair')
        run(app)
    assert calls == ([524] if failure == 'timeout' else [200])
    assert not first.status()['closed'] and not (first.journal_root/'outcome.json').exists()
    budget = factory.providers['candidate'].candidate_budget
    unknown, known = budget.reserved_tokens, budget.tokens
    assert (unknown > 0) is (failure == 'timeout')
    retained = tree(first.transport_root)
    resumed = session(tmp_path, first, candidate=candidate)
    with pytest.raises(SessionPaused, match=reason), resumed:
        app, factory, calls = app_for(tmp_path, resumed, 3, candidate=candidate, knowledge=NoSearch())
        run(app)
    assert calls == [] and retained == tree(resumed.transport_root)
    final = session(tmp_path, resumed, candidate=candidate, manual_retry=True)
    with final:
        app, factory, calls = app_for(tmp_path, final, 4, candidate=candidate, knowledge=NoSearch())
        run(app)
        budget = factory.providers['candidate'].candidate_budget
        assert calls == [200]*3 and budget.calls == 7
        assert budget.reserved_tokens == unknown and budget.tokens > known
        assert factory.providers['candidate'].generator.requests == []
        assert read_json(final.journal_root/'outcome.json')['outcome'] == 'candidate_repaired_pass_unqualified'
        final.close(dict(outcome='candidate_repaired_pass_unqualified'))
    assert all(tree(final.transport_root)[p] == pin for p, pin in retained.items())
    assert all(tree(final.transport_root)[p] == pin for p, pin in prefix_transport.items())
    completion = sorted(final.transport_root.glob('review/call-*/request.json'))[1:3]
    assert read_json(completion[0]) == read_json(completion[1])
    assert len(list(final.journal_root.glob('application.json'))) == 1
    before = tree(final.root), tree(final.transport_root), tree(final.journal_root)
    replay = session(tmp_path, final, candidate=candidate, read_only=True)
    with replay:
        app, factory, calls = app_for(tmp_path, replay, 5, candidate=candidate, knowledge=NoSearch())
        run(app)
        assert calls == [] and factory.providers['candidate'].generator.requests == []
    assert before == (tree(final.root), tree(final.transport_root), tree(final.journal_root))


@pytest.mark.parametrize('mode', ['wrong_model', 'reasoning_conflict', 'two_tools', 'bad_anchor'])
def test_hard_errors_are_not_format_or_timeout_recovery(tmp_path, mode):
    current = session(tmp_path, candidate=candidate)
    with current:
        app, factory, calls = app_for(tmp_path, current, 1, candidate=candidate, mode=mode)
        run(app)
        assert not current.status()['format_waiting'] and not current.status()['timeout_waiting']
        assert read_json(current.journal_root/'outcome.json')['outcome'] == 'candidate_execution_failed'
        assert len(calls) == (2 if mode == 'bad_anchor' else 1)


def test_inventory_preserves_original15_and_uses_runtime_contract():
    from scripts.audit_sol_review_qualification import audit
    from scripts import audit_natural_duty_qualification as legacy
    value, original = audit(), legacy.audit()
    assert value == json.loads((candidate.ROOT/'data/evaluation/results/sol_review_qualification_inventory_natural_coordination_20261028.json').read_text(encoding='utf-8'))
    assert value['contract'] == candidate.CONTRACT.snapshot().model_dump(mode='json')
    assert value['label_counts'] == dict(accept=5, reject=10)
    assert value['initial_request_count'] == 30
    assert value['fixed_report_review_slots_if_all_cases_match_labels'] == 50
    assert value['aliases'] == original['aliases'] and value['coverage_sha256'] == original['coverage_sha256']
    for row, old in zip(value['cases'], original['cases'], strict=True):
        for key in ('key', 'expected_initial', 'dataset_sha256', 'input_sha256', 'report_sha256'):
            assert row[key] == old[key]
        assert row['fresh_request_sha256'] is None and not row['completed']
        assert all(r['input_ceiling'] <= 64000 for r in row['initial_requests'].values())
    assert not any(value[k] for k in ('provider_calls', 'key_reads', 'qualified', 'execution_ready',
        'execution_authorized', 'publication_allowed', 'semantic_approval', 'labels_sent_to_model'))


def test_actual_user_entry_first_send_capture_without_key_or_provider_io():
    from scripts.prepare_sol_necessity_natural import prepare
    result = prepare('dual-policy-runtime-offline-20261025', candidate=candidate)
    assert result['contract'] == candidate.CONTRACT.snapshot().model_dump(mode='json')
    assert result['limits'] == dict(max_calls=10, total_tokens=739840, execution_timeout_s=3600, transport_retries=4)
    assert result['logical_generation_calls'] + result['logical_review_calls'] == 6
    assert not any(result[k] for k in ('provider_requests', 'key_read', 'execution_authorized',
        'semantic_approval', 'qualified', 'production_admitted', 'publication_allowed'))
