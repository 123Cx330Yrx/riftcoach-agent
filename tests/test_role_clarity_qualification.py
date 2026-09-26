"""New qualification uses real role receipt machinery with offline replies."""
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow
from app.evaluation.role_qualification import frozen_cases,replay_case
from app.providers.models import ChatResponse,TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_role_clarity_qualification as runner
from scripts.run_role_qualification_pair import observe
from tests.test_role_review_notes import tool_response


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def accepted(path,remaining):
    assert remaining>0
    return dict(accepted=True,response_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_three_controls_have_new_identity_full_inputs_and_closed_gate(prepared,monkeypatch,tmp_path):
    plan,requests=prepared
    assert [c['key'] for c in plan['cases']]==list(runner.KEYS)
    assert plan['identity']['contract']['version']=='1.5.2'
    assert plan['batch_budget']['max_calls']==12
    assert plan['batch_budget']['max_seconds']==2400
    assert plan['batch_budget']['max_tokens']==997376
    assert plan['batch_budget']['estimated_uncached_cny']=='15.843328'
    assert all(b'expected_initial' not in raw for raw in requests.values())
    closed=tmp_path/'closed.json'; closed.write_text('{}')
    monkeypatch.setattr(runner,'CLOSED_RESULT',closed)
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed batch read inputs'))
    with pytest.raises(ValueError,match='batch_closed'):
        runner.run(NS(execute=True))


@pytest.mark.parametrize('host_reject',[False,True])
def test_staged_current_workflows_use_role_receipts_and_stop_on_rejection(prepared,tmp_path,monkeypatch,host_reject):
    sources={f['key']:s for f,s in frozen_cases()[0]}
    good=dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[dict(block=4)])
    bad=dict(score=80,verdict='needs_revision',issues=[dict(block=4,severity='medium',category='fact_error',
        source_ids=[1],explanation='Synthetic actionable conflict.',suggested_correction='Use supported cohort scope.')],
        issue_resolutions=[],advisories=[])
    edited=ChatResponse(content=sources['claim-scope:1'].report,provider='zhipu',model='glm-5.3-flash',
                        finish_reason='stop',usage=TokenUsage(10,10))
    queue=[tool_response(good),tool_response(bad),edited,tool_response(good),tool_response(bad),edited,tool_response(good)]
    calls=[]
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        calls.append(json.loads(raw))
        answer=queue.pop(0)
        assert answer.model==environ['LLM_MODEL']
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        return answer
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model):
        return NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport')
    def adjudicate(path,remaining):
        return dict(accepted(path,remaining),accepted=not host_reject)
    result=observe(factory,tmp_path,prepared[0],adjudicate=adjudicate,
        workflow_type=RoleClarityReviewWorkflow,replay=replay_case,success_field='batch_accepted')
    assert result['batch_accepted'] is (not host_reject)
    assert len(calls)==(1 if host_reject else 7)
    assert not result['production_admitted'] and not result['review_controls_qualified']
    assert all(r['accounting']['unknown_usage_calls']==0 for r in result['cases'])
    if not host_reject:
        assert [r['accounting']['reserved_calls'] for r in result['cases']]==[1,3,3]


def test_preview_does_not_load_credentials_and_bad_plan_stops_before_ci(prepared,monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('preview read credentials'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('bad plan reached CI'))
    assert runner.run(NS(execute=False,output=None))['provider_requests']==0
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'not-closed.json')
    monkeypatch.setattr(runner,'prepare',lambda:prepared)
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=tmp_path/'unused',ci_run='fake',plan_sha='wrong'))


def test_closed_preview_keeps_executed_identity_and_request_bytes(monkeypatch):
    monkeypatch.setattr(runner,'prepare_qualification',lambda:pytest.fail('historical preview used current candidate'))
    plan,requests=runner.prepare()
    assert plan==json.loads(runner.PREPARATION.read_text(encoding='utf-8'))
    assert runner.canonical_sha(plan)=='abf2686d68190dd4c45d6287062eade65bf642a4e6e557f0537e2ba1222f7339'
    assert len(requests)==3
    evidence=json.loads(runner.CLOSED_RESULT.read_text(encoding='utf-8'))
    for key,raw in requests.items():
        assert hashlib.sha256(raw).hexdigest()==evidence['original_file_sha256'][key.replace(':','-')+'-prepared-request.json']
    assert runner.run(NS(execute=False,output=None))['historical_closed']


def test_closed_preview_rejects_changed_public_evidence(monkeypatch,tmp_path):
    changed=tmp_path/'changed.json'
    changed.write_bytes(runner.CLOSED_RESULT.read_bytes()+b'\n')
    monkeypatch.setattr(runner,'CLOSED_RESULT',changed)
    with pytest.raises(ValueError,match='historical_evidence_changed'):
        runner.prepare()
