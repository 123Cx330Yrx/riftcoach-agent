"""Tail diagnostic bookkeeping and real workflow boundaries, with fake IO."""
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.role_qualification import frozen_cases
from app.providers.models import ChatResponse,TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_role_review_containment as runner
from tests.test_role_review_notes import tool_response,request_data


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def test_fixture_retains_rejected_review_and_all_sources_without_expected_labels(prepared):
    plan,(source,response,initial,editor)=prepared
    assert not plan['initial_review_accepted']
    assert not plan['review_controls_qualified']
    assert plan['budget']['max_calls']==2
    old,new=request_data(initial),request_data(editor)
    assert '中单局为 27–43' in new['accepted_review']['issues'][0]['explanation']
    assert new['accepted_review']['issues']==response.tool_calls[0].arguments['issues']
    assert {k:v for k,v in new.items() if k!='accepted_review'}==old
    assert initial.messages[2:]==editor.messages[2:]
    assert 'expected_initial' not in editor.messages[1].content
    assert 'actual_middle_vision_scores' not in editor.messages[1].content
    assert plan['editor_input_ceiling']+32768<=96768


@pytest.mark.parametrize('failure',[None,'host','malformed_final','timeout'])
def test_only_tail_is_billed_and_final_is_fresh(prepared,monkeypatch,tmp_path,failure):
    correct=next(s.report for f,s in frozen_cases()[0] if f['key']=='claim-scope:1')
    edited=ChatResponse(content=correct,provider='zhipu',model='glm-5.3-flash',finish_reason='stop',usage=TokenUsage(10,10))
    arguments=dict(score=95,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
    if failure=='malformed_final':
        del arguments['score']
    replies=[edited,tool_response(arguments)]
    issued=[]
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        issued.append(json.loads(raw))
        if failure=='timeout':
            raise TimeoutError('simulated transport interruption')
        reply=replies.pop(0)
        assert reply.model==environ['LLM_MODEL']
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        return reply
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model):return NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport')
    def adjudicate(path,remaining):
        return dict(accepted=failure!='host',response_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    result=runner.observe(factory,tmp_path,*prepared,adjudicate=adjudicate)
    assert result['tail_accepted'] is (failure is None)
    assert result['offline_initial_injections']==1 and not result['initial_review_accepted']
    assert not result['review_controls_qualified'] and not result['production_admitted']
    assert len(issued)==(1 if failure in ('host','timeout') else 2)
    assert result['accounting']['reserved_calls']==len(issued)
    assert result['accounting']['unknown_usage_calls']==(1 if failure=='timeout' else 0)
    first=json.JSONDecoder().raw_decode(issued[0]['messages'][1]['content'].split('[UNTRUSTED DATA]\n',1)[1])[0]
    assert '中单局为 27–43' in first['accepted_review']['issues'][0]['explanation']
    if len(issued)==2:
        final=json.JSONDecoder().raw_decode(issued[1]['messages'][1]['content'].split('[UNTRUSTED DATA]\n',1)[1])[0]
        assert not {'accepted_review','previous_review','previous_issues'} & final.keys()
        assert '27–43' not in issued[1]['messages'][1]['content']
        assert [r['text'] for r in final['source_index']['blocks']]==[b[1] for b in runner.Workflow.build_inputs(
            runner.replace(prepared[1][0],report=correct)).source.blocks]
    if failure=='malformed_final':
        assert result['error_code']=='containment_reassessment_forbidden'
        assert (tmp_path/'transport/tail/review/response-002.json').exists()


def test_time_used_by_before_send_cannot_leak_a_request(prepared,tmp_path):
    def settings(model):return NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport')
    class Clock:
        now=0
        def __call__(self):return self.now
    clock=Clock()
    def before():clock.now=601
    result=runner.observe(factory,tmp_path,*prepared,clock=clock,before_send=before)
    assert result['error_code']=='containment_tail_budget'
    assert result['accounting']['reserved_calls']==0


def test_closed_batch_and_wrong_preparation_never_read_keys(prepared,monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('read credentials'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('reached CI'))
    monkeypatch.setattr(runner,'prepare',lambda:prepared)
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'closed.json')
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=tmp_path/'unused',ci_run='fake',plan_sha='wrong'))
    runner.CLOSED_RESULT.write_text('{}')
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed batch prepared'))
    with pytest.raises(ValueError,match='batch_closed'):
        runner.run(NS(execute=True))
