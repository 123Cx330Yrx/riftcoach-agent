"""Frozen actual initial review followed by bounded offline provider doubles."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.role_qualification import frozen_cases
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_coarse_revision_tail as runner
from tests.test_role_review_notes import tool_response, request_data


def test_fixture_preserves_actual_review_and_editor_sources():
    plan,prepared=runner.prepare()
    source,response,initial,editor=prepared
    assert plan['initial_review_accepted'] and plan['offline_initial_injections']==1
    assert request_data(editor)['accepted_review']['issues']==response.tool_calls[0].arguments['issues']
    assert request_data(editor)['accepted_review']['issues'][0]['source_ids']==[27,38,39]
    assert 'table_rows_by_id' in request_data(editor)['source_index']
    assert not {'previous_review','advisories'} & request_data(editor)['accepted_review'].keys()
    assert not plan['actual_product_task_qualified'] and not plan['production_admitted']


def test_unfrozen_execution_stops_before_credentials(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'run')
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'no-result')
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('unfrozen reached CI'))
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=None,ci_run=None,plan_sha=None))


def test_closed_tail_cannot_restart_and_preview_reconstructs_frozen_plan(monkeypatch):
    plan,_=runner.prepare()
    assert runner.canonical_sha(plan)=='2a123d0e09f2cdfcc6500df49226c35c0f79e49c804871be865bf50cbe9bf04b'
    assert runner.sha(runner.CLOSED_RESULT)==runner.CLOSED_SHA
    preview=runner.run(NS(execute=False,output=None))
    assert preview['historical_closed'] and not preview['execution_enabled']
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed batch reached preparation'))
    with pytest.raises(ValueError,match='closed_or_exists'):
        runner.run(NS(execute=True))


def test_closed_tail_preserves_exact_requests_and_nonqualification_flags():
    saved=json.loads(runner.CLOSED_RESULT.read_bytes())
    assert saved['exact_tail_replay_verified']
    assert saved['result']['tail_accepted'] and saved['result']['final_score']==96
    assert saved['provider_requests']==2 and saved['unknown_usage_calls']==0
    assert saved['offline_initial_injections']==1
    assert not any(saved[k] for k in ('review_controls_qualified','actual_product_task_qualified','production_admitted'))
    plan,prepared=runner.prepare()
    from dataclasses import replace
    from app.evaluation.golden_stream_bridge import REQUEST,CAPACITY_TRANSPORT_ID,REVIEW_MODEL_TRANSPORT_ID
    public=saved['public_json_contents']
    for name,expected,transport in (
        ('generation/request-001.json',prepared[3],CAPACITY_TRANSPORT_ID),
        ('review/request-002.json',runner.Workflow.make_request(runner.Workflow.build_inputs(
            replace(prepared[0],report=public['revision.json']['report']))),REVIEW_MODEL_TRANSPORT_ID)):
        relative='transport/tail/'+name
        actual=REQUEST.validate_json(json.dumps(public[relative]),strict=True)
        metadata=dict(actual.metadata); metadata.pop('coach_budget_contract',None)
        assert replace(actual,metadata=metadata,timeout_s=expected.timeout_s)==expected
        assert 0 < actual.timeout_s <= expected.timeout_s
        # Public JSON preserves values, not original object-key byte order.
        # The seal's raw hashes are verified against original files separately.


def test_old_product_router_cannot_silently_accept_new_projection():
    from app.runtime.reviewer_roles import role_for_request
    _,prepared=runner.prepare()
    for request in prepared[2:]:
        with pytest.raises(ValueError,match='source_projection_required'):
            role_for_request(request)


@pytest.mark.parametrize('failure',[None,'hash','defects','disagreement'])
def test_file_host_requires_bound_independent_review(tmp_path,failure):
    stage=tmp_path/'revision.json'
    stage.write_text('{"report":"offline"}')
    other=dict(stage='revision',response_sha256=runner.sha(stage),accepted=True,defects=[],source_review='Complete offline source comparison.')
    if failure=='hash': other['response_sha256']='0'*64
    if failure=='defects': other['defects']=['unsupported claim']
    if failure=='disagreement': other['accepted']=False
    independent=tmp_path/'revision-independent.json'
    write_new_json(independent,other)
    decision=dict(stage='revision',response_sha256=runner.sha(stage),accepted=True,defects=[],
        source_review='Primary offline inspection.',independent_sha256=runner.sha(independent))
    write_new_json(tmp_path/'revision-host-decision.json',decision)
    if failure is None:
        assert runner.adjudicate_file(stage,5)['accepted']
    else:
        with pytest.raises(ValueError,match='host_binding'): runner.adjudicate_file(stage,5)


@pytest.mark.parametrize('failure',[None,'host','malformed','timeout'])
def test_actual_factory_budget_edit_and_fresh_final(monkeypatch,tmp_path,failure):
    plan,prepared=runner.prepare()
    correct=next(s.report for f,s in frozen_cases()[0] if f['key']=='observed:1')
    final=dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
    if failure=='malformed': del final['score']
    replies=[ChatResponse(content=correct,model='glm-5.3-flash',provider='zhipu',
        finish_reason='stop',usage=TokenUsage(10,10)),tool_response(final)]
    requests=[]
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        requests.append(json.loads(raw))
        if failure=='timeout': raise TimeoutError('offline')
        response=replies.pop(0)
        assert response.model==environ['LLM_MODEL']
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        return response
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model): return NS(model=model,api_key='offline',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport',source_projection=runner.PROJECTION)
    def host(path,remaining):
        return dict(accepted=failure!='host',response_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    result=runner.observe(factory,tmp_path,plan,prepared,workflow_type=runner.Workflow,
        initial_review_accepted=True,coach_contract=runner.COARSE_ROLE_COACH_CONTRACT,adjudicate=host)
    assert result['tail_accepted'] is (failure is None), result
    assert result['initial_review_accepted'] and result['offline_initial_injections']==1
    assert len(requests)==(1 if failure in ('host','timeout') else 2)
    assert result['accounting']['reserved_calls']==len(requests)
    assert result['accounting']['unknown_usage_calls']==(1 if failure=='timeout' else 0)
    if len(requests)==2:
        fresh=json.JSONDecoder().raw_decode(requests[1]['messages'][1]['content'].split('[UNTRUSTED DATA]\n',1)[1])[0]
        assert not {'accepted_review','previous_review','previous_issues'} & fresh.keys()
    if failure is None:
        from app.evaluation.coarse_role_qualification import read_calls
        calls=read_calls(tmp_path/'transport/tail')
        assert [c['binding']['role'] for c in calls]==['revision','review']
