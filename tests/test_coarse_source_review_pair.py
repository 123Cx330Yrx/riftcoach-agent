"""Diagnostic execution boundaries, not claims about model accuracy."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation.golden_journal import write_new_json
from scripts import run_coarse_source_review_pair as runner
from scripts.run_review_model_comparison import observe
from tests.test_review_model_comparison import fake_provider, decision
from tests.test_role_review_notes import tool_response


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def replies(prepared):
    plan,variants=prepared
    refs=runner.coarse.source_catalog(variants[0][1])['roots']
    full=next(r['source_id'] for r in refs if r['key']==runner.coarse.FACTS_KEY)
    bad=dict(score=62,verdict='needs_revision',issues=[dict(block=10,severity='high',
        category='unsupported_comparison',source_ids=[full],explanation='Synthetic future extrapolation finding.',
        suggested_correction='Remove the future prediction and preserve the sample observation.')],
        issue_resolutions=[],advisories=[])
    good=dict(score=95,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
    return bad,good


def test_preparation_preserves_real_inputs_and_no_product_switch(prepared):
    plan,variants=prepared
    assert [c['key'] for c in plan['cells']]==['observed:2','observed:1']
    assert plan['proposed_diagnostic_budget']['max_calls']==2
    assert plan['proposed_diagnostic_budget']['max_seconds_total']==600
    assert not plan['production_admitted'] and not plan['review_controls_qualified']
    for (_,inputs,request),cell in zip(variants,plan['cells'],strict=True):
        assert runner.coarse.restore_request(request,inputs)==runner.Workflow.make_request(inputs)
        raw=runner.validate_request(request,transport_id=runner.REVIEW_MODEL_TRANSPORT_ID)
        assert hashlib.sha256(raw).hexdigest()==cell['request_sha256']
        assert b'expected_initial' not in raw


def test_response_cannot_be_inspected_against_another_report(prepared):
    _,variants=prepared
    bad,_=replies(prepared)
    provider=fake_provider([tool_response(bad)])
    provider.chat(variants[0][2])
    with pytest.raises(ValueError,match='request_binding_mismatch'):
        runner.inspect_response(variants[0][2],provider.last_exchange,variants[1][1])


@pytest.mark.parametrize('failure',[None,'host','leaf','missing_severity','wrong_verdict','not_ready','head_drift'])
def test_pair_stops_without_retry_or_edit_and_saves_first_accounting(prepared,tmp_path,failure):
    plan,variants=prepared
    bad,good=replies(prepared)
    if failure=='leaf': bad['issues'][0]['source_ids']=[15,19]
    if failure=='missing_severity': bad['issues'][0].pop('severity')
    if failure=='wrong_verdict': bad=good
    provider=fake_provider([tool_response(bad),tool_response(good)])
    gates=[]
    def ready(directory,row,actual,remaining):
        assert not (directory/row['key']).exists()
        gates.append(row['key'])
        if failure=='not_ready' and len(gates)==2:
            raise ValueError('task_observation_ready_deadline')
    def host(path,remaining):
        verdict=json.loads(path.with_name('journal.json').read_text())['parsed_review']['verdict']
        expected='needs_revision' if path.parent.name=='observed-2' else 'pass'
        return decision(failure!='host' and verdict==expected)(path,remaining)
    def head():
        if failure=='head_drift': raise ValueError('changed_checkout')
    result=observe(provider,tmp_path,variants,plan,inspect_response=runner.inspect_response,
        adjudicate=host,before_case=ready,before_send=head,clock=lambda:0)
    assert result['pair_accepted'] is (failure is None)
    assert provider._calls==(2 if failure is None else 0 if failure=='head_drift' else 1)
    assert result['unknown_usage_calls']==0
    assert (tmp_path/'observed-2/accounting.json').exists()
    if failure=='not_ready':
        assert not (tmp_path/'observed-1').exists()
        first=json.loads((tmp_path/'observed-2/accounting.json').read_text())
        assert first['host_accepted'] and first['batch_elapsed_seconds']==0
    assert not result['production_admitted']


@pytest.mark.parametrize('defect',[None,'hash','input','independent','defects','late','absent'])
def test_file_host_requires_bound_independent_inspection(prepared,tmp_path,defect):
    plan,_=prepared
    cell=plan['cells'][0]
    arm=tmp_path/cell['id'];arm.mkdir()
    path=arm/'response.json';write_new_json(path,dict(public='offline'))
    write_new_json(arm/'journal.json',dict(parsed_review=dict(verdict='needs_revision')))
    value=dict(accepted=True,response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        input_sha256=cell['input_sha256'],report_sha256=cell['report_sha256'],
        defects=[],source_review='Synthetic independent review fixture; no semantic assertion.')
    other=deepcopy(value)
    if defect=='input': other['input_sha256']='0'*64
    if defect=='independent': other['accepted']=False
    if defect=='defects': other['defects']=[dict(kind='unsupported_source')]
    independent=arm/'independent-review.json';write_new_json(independent,other)
    value['independent_sha256']=hashlib.sha256(independent.read_bytes()).hexdigest()
    if defect=='hash': value['response_sha256']='0'*64
    if defect not in ('late','absent'): write_new_json(arm/'host-decision.json',value)
    now=[0.0]
    def sleep(delay):
        now[0]+=delay
        if defect=='late' and now[0]>=1: write_new_json(arm/'host-decision.json',value)
    if defect is None:
        assert runner.adjudicate_file(path,1,plan,clock=lambda:now[0],sleep=sleep)['accepted']
    else:
        with pytest.raises(ValueError): runner.adjudicate_file(path,1,plan,clock=lambda:now[0],sleep=sleep)
    assert now[0]<=1


def test_execute_requires_frozen_plan_and_ci_before_credentials(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'run')
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'closed')
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('credentials accessed'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('CI accessed'))
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=tmp_path/'unused',ci_run='1',plan_sha='bad'))
    (tmp_path/'run').mkdir()
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed experiment prepared'))
    with pytest.raises(ValueError,match='closed_or_exists'):
        runner.run(NS(execute=True))
