"""Real executor/receipt/audit paths with network and host fixtures, not live quality."""
import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from app.evaluation import review_bound_qualification as q
from app.evaluation import boundary_examples_qualification as previous
from scripts import run_review_bound_qualification as entry
from scripts import run_boundary_examples_v2 as shared
from scripts import qualify_role_observations as audit
from tests.test_role_observation_qualification import make_run, change, seal


def test_sealed_live_edit_and_fresh_replay_under_current_protocol():
    """Historical initial is injected: replay evidence, not a fresh qualified case."""
    from app.evaluation.golden_integrated_runtime import Exchange
    from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE, validate_request, CAPACITY_TRANSPORT_ID
    from app.evaluation.source_patch_editor import report_inputs
    from tests.test_coarse_revision_editor import cases
    import hashlib
    saved = json.loads((q.old.ROOT/'data/evaluation/results/golden_review_bound_edit_result_20261001.json').read_bytes())
    public = saved['public_json_contents']
    _, inputs, accepted, _ = cases()['claim-scope:4']
    journal = public['necessary-edit/stage.json']['journal']
    accepted = type(accepted).model_validate(journal['review_source_context']['accepted_review'], strict=True)
    prepared = q.editor.edit_request(inputs, accepted)
    issued = REQUEST.validate_json(json.dumps(public['necessary-edit/request.json']), strict=True)
    response = RESPONSE.validate_json(json.dumps(public['necessary-edit/response.json']), strict=True)
    exchange = Exchange(issued, response, hashlib.sha256(validate_request(
        issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    assembly = q.editor.inspect_exchange(prepared, exchange, inputs, accepted)
    assert json.loads(json.dumps(assembly.journal)) == journal
    final_request = q.editor.Current.make_request(report_inputs(inputs, assembly.report))
    issued_final = REQUEST.validate_json(json.dumps(public['conditional-fresh/request.json']), strict=True)
    metadata = dict(issued_final.metadata)
    metadata.pop('coach_budget_contract', None)
    assert replace(issued_final, timeout_s=final_request.timeout_s, metadata=metadata) == final_request
    assert public['conditional-fresh/response.json']['tool_calls'][0]['arguments']['score'] == 93
    assert not saved['original15_qualified'] and not saved['production_admitted']


def test_same_fifteen_sources_and_initial_requests_new_revision_identity():
    plan, requests = q.prepare_qualification()
    old, old_requests = previous.prepare_qualification()
    assert requests == old_requests and plan['cases'] == old['cases']
    assert plan['identity'] != old['identity']
    assert plan['identity']['contract'] == old['identity']['contract']
    prepared, _ = entry.prepare(root_thread_id='root', independent_thread_id='child')
    assert prepared['batch_budget']['max_calls'] == 35
    assert prepared['role_call_reservations'] == {'glm-5.3-flash': 10, 'glm-5.3': 25}
    assert prepared['offline_initial_injections'] == prepared['inherited_completed_cases'] == 0
    assert not prepared['production_admitted'] and not prepared['execution_authorized']


def test_full15_executor_dual_host_and_strict_replay_preserve_edit_evidence(make_run, tmp_path):
    from tests.test_review_independence_integration import OfflineHostEvents
    from scripts.review_independence_contract import using_host_event_source, FINAL_POLICY
    class FinalEvents(OfflineHostEvents):
        def attach(self, review, bound):
            result = super().attach(review, bound)
            event = result['independent_source_event']
            event['host_review_evidence_policy'] = FINAL_POLICY
            self.events[event['event_id']] = deepcopy(event)
            return result
    source = FinalEvents()
    plan, _ = q.prepare_qualification()
    run, sealed = make_run(tuple(r['key'] for r in plan['cases']), profile=q.PROFILE,
        host_drafts=True, host_event_source=source, host_review_evidence_policy=FINAL_POLICY)
    stage = json.loads((run/'claim-scope-4/revision.json').read_bytes())
    assert stage['journal']['version'] == q.editor.VERSION
    assert stage['journal']['review_source_context']['proves_edit_support'] is False
    assert json.loads((run/'claim-scope-4/revision-journal.json').read_bytes()) == stage['journal']
    with using_host_event_source(source):
        result = audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'audit',
            closed_exports=[sealed], profile=q.PROFILE)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert not result['actual_product_task_qualified'] and not result['production_admitted']
    change(run/'claim-scope-4/revision.json', lambda d: d.update(journal=None))
    resealed = seal(run, tmp_path, tmp_path/'tampered-seal.json')
    with using_host_event_source(source), pytest.raises(ValueError):
        audit.inspect_runs([run], evidence_root=tmp_path, closed_exports=[resealed], profile=q.PROFILE)


@pytest.mark.parametrize('source_profile,target_profile', [
    ('review-bound', 'boundary-examples'), ('boundary-examples', 'review-bound')])
def test_old_and_new_qualifications_cannot_be_borrowed(make_run, tmp_path, source_profile, target_profile):
    run, sealed = make_run(('claim-scope:1',), profile=source_profile)
    with pytest.raises(ValueError, match='plan_identity_mismatch'):
        audit.inspect_runs([run], evidence_root=tmp_path, closed_exports=[sealed], profile=target_profile)


def test_new_entry_offline_preview_and_stale_execution_have_no_external_io(tmp_path, monkeypatch):
    from scripts.review_independence_contract import FINAL_POLICY
    args = NS(root_thread_id='root', independent_thread_id='child', experiment='review-bound-offline',
        max_host_seconds=86400, host_review_evidence_policy=FINAL_POLICY, execute=False,
        output=tmp_path/'plan.json', preparation=None, plan_sha=None, ci_run=None,
        env_file=None, codex_executable=None)
    monkeypatch.setattr(shared, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(shared, 'CodexReadOnlyClient', lambda *_: pytest.fail('Unexpected host IO'))
    result = entry.run(args)
    assert result['provider_requests'] == 0 and result['cases'] == 15
    args.execute = True
    args.preparation = args.output
    args.plan_sha = '0'*64
    with pytest.raises(ValueError, match='frozen_preparation_required'):
        entry.run(args)
    assert not (tmp_path/'runs').exists()


def test_independent_rejection_stops_before_revision(make_run):
    def reject(path):
        change(path.with_name('independent-'+path.stem+'-review.json'),
            lambda d: d.update(accepted=False, defects=[{'kind':'wrong_correction','detail':'Offline rejection'}]))
    run, result = make_run(('claim-scope:4',), profile=q.PROFILE, inspect_fault=reject)
    assert not result['tasks_observed']
    assert not (run/'claim-scope-4/revision.json').exists()


def test_execute_entry_routes_new_backend_after_native_identity_check(tmp_path, monkeypatch):
    from scripts.review_independence_contract import FINAL_POLICY
    args = NS(root_thread_id='root', independent_thread_id='child', experiment='review-bound-routing',
        max_host_seconds=86400, host_review_evidence_policy=FINAL_POLICY, execute=True,
        output=None, preparation=tmp_path/'plan.json', plan_sha=None, ci_run='offline-ci',
        env_file=tmp_path/'not-read.env', codex_executable=tmp_path/'not-run.exe')
    plan, requests = entry.prepare(root_thread_id='root', independent_thread_id='child',
        experiment=args.experiment)
    args.preparation.write_text(json.dumps(plan), encoding='utf-8')
    args.plan_sha = shared.runner.canonical_sha(plan)
    seen = []
    class Client:
        def __init__(self, executable):
            assert executable == args.codex_executable
        def __enter__(self):
            seen.append('open')
            return self
        def __exit__(self, *_):
            seen.append('closed')
        def request(self, method, params):
            assert method == 'thread/read'
            return {'thread': dict(id=params['threadId'], parentThreadId='root',
                source={'subAgent': {'thread_spawn': {'parent_thread_id': 'root'}}})}
        def check_latest_input(self, thread, *, evidence_policy):
            assert thread['id'] == 'child' and evidence_policy == FINAL_POLICY
            seen.append('checked')
            return {'verified': True}
    def execute(actual_args, actual_plan, actual_requests, **kwargs):
        assert seen == ['open', 'checked']
        assert actual_args is args and actual_plan == plan and actual_requests == requests
        assert kwargs['backend'] is q
        assert kwargs['host_timing'] == plan['host_review_timing']
        assert kwargs['event_source'].independent == 'child'
        return {'tasks_observed': True}
    monkeypatch.setattr(shared, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(shared, 'CodexReadOnlyClient', Client)
    monkeypatch.setattr(shared.runner, 'execute_prepared', execute)
    assert entry.run(args) == {'tasks_observed': True}
    assert seen == ['open', 'checked', 'closed']
    assert not (tmp_path/'runs').exists()
