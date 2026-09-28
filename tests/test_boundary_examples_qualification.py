"""Strict same-version qualification cannot borrow successful diagnostic tails."""
import hashlib
import json
from types import SimpleNamespace as NS
import pytest
from app.evaluation import boundary_examples_qualification as q
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import run_boundary_examples_qualification as runner, qualify_role_observations as audit
from tests.test_role_observation_qualification import make_run, change, seal


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


def test_full15_actual_executor_drafts_and_strict_gate(make_run,tmp_path):
    plan,_ = q.prepare_qualification()
    run,sealed = make_run(tuple(r['key'] for r in plan['cases']),profile=q.PROFILE,host_drafts=True)
    result = audit.qualify([run],evidence_root=tmp_path,output_directory=tmp_path/'audit',closed_exports=[sealed],profile=q.PROFILE)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert not result['production_admitted'] and not result['actual_product_task_qualified']
    change(run/'claim-scope-4/independent-final-review.json',lambda d:d.update(accepted=False))
    with pytest.raises(ValueError,match='sealed_file_hash'): q.validate_qualification(result,evidence_root=tmp_path)


def test_saved_handoff_in_separate_process(make_run,tmp_path):
    run,sealed = make_run(('claim-scope:4',),profile=q.PROFILE,host_process=True)
    result = audit.qualify([run],evidence_root=tmp_path,output_directory=tmp_path/'audit',closed_exports=[sealed],profile=q.PROFILE)
    assert result['validated_inputs'] == 1 and not result['review_controls_qualified']


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
