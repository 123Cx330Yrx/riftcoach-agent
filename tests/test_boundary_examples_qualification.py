"""Strict same-version qualification cannot borrow successful diagnostic tails."""
import hashlib
import json
from contextlib import nullcontext
from types import SimpleNamespace as NS
import pytest
from app.evaluation import boundary_examples_qualification as q
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import run_boundary_examples_qualification as runner, qualify_role_observations as audit
from tests.test_role_observation_qualification import make_run, change, seal
from scripts.review_independence_contract import MODE_V2, freeze_v2_identity


def test_preparation_preserves_original15_and_exact_tested_requests():
    from scripts.review_boundary_examples import request_for
    from scripts.run_boundary_examples_tail import Workflow
    from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
    plan, requests = runner.prepare()
    assert plan == json.loads(runner.PREPARATION.read_bytes())
    sources = {f['key']:s for f,s in q.frozen_cases()[0]}
    assert len(plan['cases']) == 15
    assert plan['identity']['contract']['version'] == '1.5.5'
    assert plan['batch_budget']['max_calls'] == 35
    assert plan['role_call_reservations'] == {'glm-5.3-flash':10,'glm-5.3':25}
    assert plan['batch_budget']['estimated_uncached_cny'] == '37.167104'
    assert plan['host_review_submission_mode'] == 'independent-drafts-v1'
    assert not plan['execution_authorized'] and not plan['allow_reassessment']
    assert plan['inherited_completed_cases'] == plan['offline_initial_injections'] == 0
    for row in plan['cases']:
        tested = request_for(Workflow.build_inputs(sources[row['key']]))
        assert requests[row['key']] == validate_request(tested,transport_id=REVIEW_MODEL_TRANSPORT_ID)
        assert row['request_sha256'] == hashlib.sha256(requests[row['key']]).hexdigest()


def test_adopt_host_timing_creates_explicit_new_plan_without_mutating_base():
    base = dict(batch_budget=dict(max_seconds=10200), cases=[])
    adopted = runner.adopt_host_timing(base, max_host_seconds=86400)
    assert 'host_review_timing' not in base
    assert adopted['host_review_timing'] == dict(
        mode='separate-development-host-clock-v1', adopted=True,
        max_host_seconds=86400, process_restart_allowed=False,
        timing_contract='wall_equals_active_plus_host_v1')


def test_fresh_preparation_records_identity_and_native_reader_source():
    from app.evaluation.golden_review_experiment import digest
    plan, _ = runner.prepare_fresh(keys=['claim-scope:4'])
    for path in ('scripts/review_independence_contract.py', 'scripts/codex_review_event_source.py'):
        assert plan['source_sha256'][path] == digest((runner.ROOT/path).read_text(encoding='utf-8'))


@pytest.mark.parametrize('timed', [False, True])
def test_execute_prepared_wires_event_source_and_clock_to_all_gates(tmp_path, monkeypatch, timed):
    plan = freeze_v2_identity(dict(experiment='offline-host-timed',
        identity={}, cases=[], batch_budget=dict(max_seconds=900), host_review_submission_mode=MODE_V2),
        root_thread_id='offline-root', primary_id='offline-primary', independent_id='offline-reviewer')
    if timed:
        plan = runner.adopt_host_timing(plan)
    source = NS(fetch=lambda **_kwargs: pytest.fail('Unexpected host fetch in wiring test'))
    preparation = tmp_path/'preparation.json'
    preparation.write_text(json.dumps(plan), encoding='utf-8')
    captured = {}
    monkeypatch.setattr(runner, 'verify_public_ci', lambda _run: 'a' * 40)
    monkeypatch.setattr(runner, 'load_role_settings', lambda _path: ({}, {}))
    monkeypatch.setattr(runner, 'RunScopedRoleReceiptedProviderFactory', lambda **_kwargs: object())
    monkeypatch.setattr(runner, 'route_environment', lambda _name: nullcontext())
    monkeypatch.setattr(runner, 'require_unchanged_checkout', lambda _head: None)
    seen = []
    def adjudicate(path, remaining, *, event_source):
        seen.append(('adjudicate', event_source))
        return {'accepted': True}
    def handoff(path, decision, plan, *, directory, event_source):
        seen.append(('handoff', event_source))
        return decision
    monkeypatch.setattr(runner, 'adjudicate_file', adjudicate)
    monkeypatch.setattr(runner, 'validate_handoff', handoff)
    def fake_observe(_factory, _directory, _plan, **kwargs):
        captured.update(kwargs)
        stage = _directory/'claim-scope-4/initial.json'
        stage.parent.mkdir()
        stage.write_text('{"key":"claim-scope:4","stage":"initial"}')
        assert kwargs['adjudicate'](stage, 300) == {'accepted': True}
        kwargs['before_send']()
        return {'tasks_observed': True}
    monkeypatch.setattr(runner, 'observe', fake_observe)
    args = NS(execute=True, env_file=tmp_path/'env', ci_run='123', plan_sha=runner.canonical_sha(plan))
    result = runner.execute_prepared(args, plan, {}, directory=tmp_path/'run',
        preparation=preparation, host_timing=plan.get('host_review_timing'), event_source=source)
    assert result == {'tasks_observed': True}
    assert (captured['clock'].__class__.__name__ == 'DevelopmentHostClock') is timed
    assert seen == [('adjudicate', source), ('handoff', source)]
    assert captured['before_case'] is not None and captured['before_send'] is not None
    assert captured['adjudicate'] is not None


@pytest.mark.parametrize('fault,error', [
    ('legacy', 'mode_not_v2'), ('missing_source', 'trusted_event_fetch_required'),
    ('missing_registry', 'principal_registry_missing'), ('same_author', 'principal_roles_not_independent'),
    ('invalid_source', 'trusted_event_fetch_required'),
])
def test_execution_rejects_missing_review_dependency_before_any_io(tmp_path, monkeypatch, fault, error):
    plan = freeze_v2_identity(dict(host_review_submission_mode=MODE_V2),
        root_thread_id='offline-root', primary_id='offline-primary', independent_id='offline-reviewer')
    source = NS(fetch=lambda **_kwargs: pytest.fail('Unexpected event fetch'))
    if fault == 'legacy':
        plan['host_review_submission_mode'] = 'independent-drafts-v1'
    elif fault == 'missing_source':
        source = None
    elif fault == 'invalid_source':
        source = object()
    elif fault == 'missing_registry':
        del plan['review_principals']
    else:
        plan['review_principals']['independent']['principal_id'] = 'offline-primary'
    preparation = tmp_path/'preparation.json'
    preparation.write_text(json.dumps(plan), encoding='utf-8')
    for name in ('verify_public_ci', 'load_role_settings', 'RunScopedRoleReceiptedProviderFactory', 'observe'):
        monkeypatch.setattr(runner, name, lambda *a, **kw: pytest.fail('IO before review admission'))
    args = NS(execute=True, env_file=tmp_path/'env', ci_run='123', plan_sha=runner.canonical_sha(plan))
    with pytest.raises(ValueError, match=error):
        runner.execute_prepared(args, plan, {}, directory=tmp_path/'run', preparation=preparation,
            event_source=source)
    assert not (tmp_path/'run').exists()


def test_closed_preview_rejects_changed_seal(tmp_path, monkeypatch):
    changed = tmp_path/'changed.json'
    changed.write_bytes(runner.CLOSED_RESULT.read_bytes()+b' ')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', changed)
    with pytest.raises(ValueError, match='closed_evidence_changed'):
        runner.prepare()


def test_closed_preview_rebuilds_requests_and_rejects_drift(monkeypatch):
    original = runner.prepare_fresh
    def changed(**kwargs):
        plan, requests = original(**kwargs)
        plan['cases'][0]['request_sha256'] = '0'*64
        return plan, requests
    monkeypatch.setattr(runner, 'prepare_fresh', changed)
    with pytest.raises(ValueError, match='closed_preparation_changed'):
        runner.prepare()


def test_remaining_preparation_accounts_for_failed_call_without_reusing_it():
    old, old_requests = runner.prepare()
    plan, requests = runner.prepare_remaining()
    assert plan == json.loads(runner.REMAINING_PREPARATION.read_bytes())
    assert len(plan['cases']) == 14
    assert [r['key'] for r in plan['cases']] == old['original15_keys'][1:]
    assert plan['identity'] == old['identity']
    assert plan['original15_keys'] == old['original15_keys']
    assert plan['batch_budget'] == dict(max_calls=34, max_tokens=3290112,
        max_seconds=10200, estimated_uncached_cny='35.737600', hard_billing_cap=False)
    assert plan['role_call_reservations'] == {'glm-5.3-flash':10,'glm-5.3':24}
    assert plan['prior_closed_batch']['reserved_calls'] == 2
    assert plan['prior_closed_batch']['known_tokens'] == 29682
    assert plan['prior_closed_batch']['unknown_usage_calls'] == 0
    assert plan['explicit_new_execution_keys'] == ['claim-scope:4']
    assert not plan['execution_authorized'] and not plan['allow_reassessment']
    assert plan['offline_initial_injections'] == 0
    assert requests == {key:raw for key,raw in old_requests.items() if key != 'claim-scope:1'}


@pytest.mark.parametrize('remaining', [False, True])
def test_closed_preview_keeps_historical_identity_but_checks_actual_bytes(monkeypatch, remaining):
    prepare = runner.prepare_remaining if remaining else runner.prepare
    expected, _ = prepare()
    original = runner.prepare_fresh

    def changed_identity(**kwargs):
        plan, requests = original(**kwargs)
        plan['identity']['manifest_sha256'] = 'a' * 64
        plan['original15_plan_sha256'] = 'b' * 64
        return plan, requests

    monkeypatch.setattr(runner, 'prepare_fresh', changed_identity)
    assert prepare()[0] == expected
    assert runner.prepare_fresh()[0]['identity'] != expected['identity']

    def changed_request(**kwargs):
        plan, requests = changed_identity(**kwargs)
        requests[next(iter(requests))] += b' '
        return plan, requests

    monkeypatch.setattr(runner, 'prepare_fresh', changed_request)
    with pytest.raises(ValueError, match='closed_preparation_changed'):
        prepare()


def test_closed_batch_cannot_restart_or_create_new_calls():
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))


def test_remaining_closed_export_blocks_before_ci_or_credentials(tmp_path, monkeypatch):
    closed = tmp_path/'closed.json'
    closed.write_text('{}')
    monkeypatch.setattr(runner, 'REMAINING_DIRECTORY', tmp_path/'absent')
    monkeypatch.setattr(runner, 'REMAINING_CLOSED_RESULT', closed)
    monkeypatch.setattr(runner, 'prepare_remaining', lambda: pytest.fail('Preparation after closure'))
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True, remaining=True))


@pytest.mark.parametrize('keys', [set(), {'claim-scope:4'}, {'claim-scope:1','claim-scope:4'}])
def test_remaining_wrong_prior_qualification_cannot_execute(tmp_path, monkeypatch, keys):
    monkeypatch.setattr(runner, 'REMAINING_DIRECTORY', tmp_path/'absent')
    monkeypatch.setattr(runner, 'REMAINING_CLOSED_RESULT', tmp_path/'absent-export.json')
    monkeypatch.setattr(audit, 'inspect_runs', lambda *a,**k: (None,None,None,None,keys))
    monkeypatch.setattr(runner, 'execute_prepared', lambda *a,**k: pytest.fail('Unexpected execution'))
    with pytest.raises(ValueError, match='remaining_qualification_changed'):
        runner.run(NS(execute=True, remaining=True))


def test_remaining_handoff_uses_new_full_requests_and_frozen_preparation(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'REMAINING_DIRECTORY', tmp_path/'new-run')
    monkeypatch.setattr(runner, 'REMAINING_CLOSED_RESULT', tmp_path/'absent-export.json')
    expected, requests = runner.prepare_remaining()
    def inspect(runs, **kwargs):
        assert runs == [runner.RUN_DIRECTORY]
        assert kwargs['closed_exports'] == [(runner.CLOSED_RESULT,runner.CLOSED_SHA)]
        return None,None,None,None,{'claim-scope:1'}
    monkeypatch.setattr(audit, 'inspect_runs', inspect)
    def execute(args, plan, actual_requests, **kwargs):
        assert plan == expected and actual_requests == requests
        assert kwargs == dict(directory=tmp_path/'new-run',preparation=runner.REMAINING_PREPARATION)
        return {'provider_requests':0}
    monkeypatch.setattr(runner, 'execute_prepared', execute)
    assert runner.run(NS(execute=True,remaining=True)) == {'provider_requests':0}


def test_remaining_stale_plan_is_rejected_before_ci(tmp_path, monkeypatch):
    plan, requests = runner.prepare_remaining()
    monkeypatch.setattr(runner, 'verify_public_ci', lambda *a: pytest.fail('CI before binding check'))
    with pytest.raises(ValueError, match='preparation_required'):
        runner.execute_prepared(NS(execute=True,env_file='unused',ci_run='123',plan_sha='0'*64),
            plan,requests,directory=tmp_path/'new-run',preparation=runner.REMAINING_PREPARATION)
    assert not (tmp_path/'new-run').exists()


def test_remaining_closed_preview_preserves_seal(tmp_path, monkeypatch):
    altered = tmp_path/'altered.json'
    altered.write_bytes(runner.REMAINING_CLOSED_RESULT.read_bytes()+b' ')
    monkeypatch.setattr(runner, 'REMAINING_CLOSED_RESULT', altered)
    with pytest.raises(ValueError, match='remaining_closed_evidence_changed'):
        runner.prepare_remaining()


def test_remaining_closed_preview_rejects_budget_drift(monkeypatch):
    original = runner.prepare_fresh
    def changed(**kwargs):
        plan, requests = original(**kwargs)
        if kwargs.get('experiment') == runner.REMAINING_EXPERIMENT:
            plan['batch_budget']['max_seconds'] += 1
        return plan, requests
    monkeypatch.setattr(runner, 'prepare_fresh', changed)
    with pytest.raises(ValueError, match='remaining_closed_preparation_changed'):
        runner.prepare_remaining()


def test_full15_actual_executor_drafts_and_strict_gate(make_run,tmp_path):
    from tests.test_review_independence_integration import OfflineHostEvents
    from scripts.review_independence_contract import using_host_event_source
    source = OfflineHostEvents()
    plan,_ = q.prepare_qualification()
    run,sealed = make_run(tuple(r['key'] for r in plan['cases']),profile=q.PROFILE,host_drafts=True,host_event_source=source)
    with using_host_event_source(source):
        result = audit.qualify([run],evidence_root=tmp_path,output_directory=tmp_path/'audit',closed_exports=[sealed],profile=q.PROFILE)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert not result['production_admitted'] and not result['actual_product_task_qualified']
    change(run/'claim-scope-4/independent-final-review.json',lambda d:d.update(accepted=False))
    with pytest.raises(ValueError,match='sealed_file_hash'): q.validate_qualification(result,evidence_root=tmp_path)


def test_saved_handoff_in_separate_process(make_run,tmp_path):
    run,sealed = make_run(('claim-scope:4',),profile=q.PROFILE,host_process=True)
    result = audit.inspect_runs([run],evidence_root=tmp_path,closed_exports=[sealed],profile=q.PROFILE)
    assert result[4] == {'claim-scope:4'}  # Read-only legacy replay; not new admission.


@pytest.mark.parametrize('from_profile,to_profile',[('correction-scope','boundary-examples'),('boundary-examples','correction-scope')])
def test_qualifications_do_not_cross_policy_versions(make_run,tmp_path,from_profile,to_profile):
    run,sealed = make_run(('claim-scope:1',),profile=from_profile)
    with pytest.raises(ValueError,match='plan_identity_mismatch'):
        audit.qualify([run],evidence_root=tmp_path,output_directory=tmp_path/'audit',closed_exports=[sealed],profile=to_profile)


def test_rejected_independent_stage_stops_before_edit(make_run):
    def sabotage(path):
        change(path.with_name('independent-'+path.stem+'-review.json'),lambda d:d.update(accepted=False,defects=[{'kind':'wrong_correction','detail':'Offline rejection'}]))
    run,result=make_run(('claim-scope:4',),profile=q.PROFILE,inspect_fault=sabotage)
    assert not result['tasks_observed']
    assert result['cases'][0]['accounting']['reserved_calls']==1
    assert not (run/'claim-scope-4/revision.json').exists()


def test_closed_or_unfrozen_prevents_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'run')
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'closed')
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('CI accessed'))
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('credentials accessed'))
    with pytest.raises(ValueError,match='preparation_required'): runner.run(NS(execute=True,env_file=None,ci_run=None,plan_sha=None))
    (tmp_path/'run').mkdir()
    with pytest.raises(ValueError,match='closed_or_exists'): runner.run(NS(execute=True))
