"""Frozen opinion-view comparison with network forbidden; no semantic proof."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import socket

import pytest

from scripts import run_native_editor_pair as pair
from scripts.check_native_contract_options import corrected_case3
from scripts.native_contract_options import body
from tests.test_golden_integrated_review import ReplayProvider


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**k): pytest.fail('offline pair reached network')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'create_connection',denied)


def failed_response():
    return pair.read(pair.ROOT/'data/evaluation/results/golden_native_editor_result_685993d.json')['response']['content']


def test_only_opinion_view_changes_and_no_labels_or_old_rationale_leak():
    case,req,variants,plan=pair.frozen_pair()
    locator,full=[r for _,r in variants]
    assert locator.messages[0]==full.messages[0]
    assert locator.messages[2]==full.messages[2]
    assert locator.response_contract==full.response_contract
    a,b=body(locator),body(full)
    original=b.pop('proposed_review')
    view=a.pop('proposed_review')
    assert a==b
    assert view=={'issues':[{'block':i['block']} for i in original['issues']]}
    assert a['review_sha256']==pair.digest(case['proposed_review_raw'])
    for _,r in variants:
        text=''.join(m.content or '' for m in r.messages)
        assert all(s not in text for s in ('expected_dispositions_host_only','mixed_true_false','一真一假','分析者构造的合同见证'))
        assert '不省原文和首评理由' not in text and '保留完整首评' not in text
    assert all(i['explanation'] not in locator.messages[1].content for i in original['issues'])
    assert plan['full_reservation']<=401920


def test_semantic_mismatch_does_not_change_or_skip_precommitted_second_input(tmp_path):
    case,req,variants,_=pair.frozen_pair()
    _,_,correct=corrected_case3()
    provider=ReplayProvider(lambda _,n:failed_response() if n==1 else pair.compact(correct))
    result=pair.observe_pair(provider,tmp_path,case,req,variants,clock=lambda:1000)
    assert result['protocol_complete'] and result['attempted_calls']==2
    assert result['budget_tokens']==40 and not result['semantic_approval']
    assert not pair.read(tmp_path/'outputs/locator_only/structure-result.json')['disposition_match']
    assert pair.read(tmp_path/'outputs/full_opinion/structure-result.json')['disposition_match']
    assert provider.requests[1].messages==variants[1][1].messages
    assert not result['final_review_executed'] and not result['production_admitted']
    with pytest.raises(FileExistsError): pair.observe_pair(provider,tmp_path,case,req,variants)
    assert len(provider.requests)==2


@pytest.mark.parametrize('failure',['schema','truncation','transport','identity'])
def test_execution_failure_stops_without_second_request_or_retry(tmp_path,failure):
    case,req,variants,_=pair.frozen_pair()
    class Provider(ReplayProvider):
        def chat(self,request):
            if failure=='transport':
                self._calls+=1
                raise RuntimeError('private diagnostic text')
            response=super().chat(request)
            if failure=='truncation':
                response=replace(response,finish_reason='length')
                self.last_exchange=replace(self.last_exchange,response=response)
            if failure=='identity': self.last_exchange=replace(self.last_exchange,receipt_request_sha256='0'*64)
            return response
    provider=Provider(lambda *_:'{}' if failure=='schema' else failed_response())
    result=pair.observe_pair(provider,tmp_path,case,req,variants,clock=lambda:1000)
    assert not result['protocol_complete'] and result['attempted_calls']==1
    assert result['unknown_usage_calls']==(1 if failure=='transport' else 0)
    assert 'private diagnostic text' not in pair.compact(result)
    assert not (tmp_path/'outputs/full_opinion').exists()


def test_one_shared_budget_and_original_deadline_for_two_conditions(tmp_path):
    case,req,variants,_=pair.frozen_pair()
    clock={'now':1000}
    def response(_,n):
        clock['now']=1850
        return failed_response()
    provider=ReplayProvider(response)
    result=pair.observe_pair(provider,tmp_path,case,req,variants,clock=lambda:clock['now'])
    assert result['protocol_complete'] and result['budget_calls']==2
    assert provider.requests[0].timeout_s==300 and provider.requests[1].timeout_s==50
    assert result['elapsed_seconds']==850


def test_preview_and_repeat_gate_before_credentials(tmp_path,monkeypatch):
    import dotenv
    monkeypatch.setattr(dotenv,'dotenv_values',lambda *_:pytest.fail('secrets read before gate'))
    assert pair.run(SimpleNamespace(execute=False))['max_calls']==2
    monkeypatch.setattr(pair,'verify_public_ci',lambda *_:'test-head')
    (tmp_path/pair.EXPERIMENT).mkdir()
    with pytest.raises(FileExistsError):
        pair.run(SimpleNamespace(execute=True,ci_run='test',output_root=tmp_path))
    monkeypatch.setattr(pair,'LIVE_STATUS','offline_completed')
    with pytest.raises(ValueError,match='editor_pair_offline'):
        pair.run(SimpleNamespace(execute=True))


def test_any_frozen_plan_drift_stops_before_execution(monkeypatch):
    original=pair.prepare_pair
    def changed():
        case,req,variants,plan=original()
        plan=deepcopy(plan)
        plan['conditions'][0]['policy_sha256']='0'*64
        return case,req,variants,plan
    monkeypatch.setattr(pair,'prepare_pair',changed)
    with pytest.raises(ValueError,match='frozen_plan_changed'): pair.frozen_pair()
