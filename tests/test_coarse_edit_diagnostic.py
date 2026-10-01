"""Bounded diagnostic control flow using explicitly synthetic host/model IO."""
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.runtime.reviewer_roles import RoleRoutedProvider
from scripts import run_coarse_edit_diagnostic as runner
from scripts import review_independence_contract as identity
from tests.test_coarse_revision_editor import operation, cases
from tests.test_native_editor_product_budget import offline
from tests.test_reviewer_role_proposal import providers


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')


class Host:
    def __init__(self,plan,fault):
        self.plan,self.fault,self.events=plan,fault,{}

    def fetch(self,*,event_id,binding):
        if self.fault=='host_unavailable': raise ValueError('synthetic_host_unavailable')
        return self.events[event_id]

    def adjudicate(self,path,remaining):
        required=json.loads(path.read_bytes())
        bound=required['binding']
        submission={}
        for role in ('primary','independent'):
            principal=self.plan['review_principals'][role]['principal_id']
            accepted=not (self.fault=='host_reject' and role=='independent')
            review=dict(binding=bound,
                stage_assessment=dict(stage=bound['stage'],stage_sha256=required['stage_sha256'],
                    reviewer=principal,source_review='Synthetic full-source judgment for control-flow tests only.',
                    accepted=accepted,defects=[] if accepted else [dict(kind='wrong_final_report',detail='Synthetic rejection.')]),
                report_assessment=dict(report_sha256=bound['report_sha256'],reviewer=principal,
                    source_review='Synthetic judgment; no real quality assertion.',facts_and_sources_correct=accepted,
                    correct_content_preserved=accepted,identity_and_goal_preserved=accepted,true_errors_fixed=accepted))
            if role=='primary':
                review['primary_attestation']=identity.make_primary_attestation(review,plan=self.plan,bound=bound)
            else:
                event_id=f'synthetic-independent/turn/{path.parent.name}'
                event=dict(schema_version=identity.VERSION,event_kind=identity.EVENT_KIND,state='completed',
                    host_review_evidence_policy=identity.FINAL_POLICY,author_principal_id=principal,
                    root_thread_id='synthetic-root',binding=bound,review_sha256=identity.review_digest(review),
                    event_id=event_id,dispatch_id='synthetic-dispatch',raw_event_sha256='a'*64,review=review.copy())
                self.events[event_id]=event
                review['independent_source_event']=event
            submission[role]=review
        if self.fault=='missing_report': submission['independent'].pop('report_assessment')
        return submission


def scripted(monkeypatch,fault):
    generator,reviewer=providers()
    edits=[]
    def generate(request):
        ops=[operation()] if not edits else []
        if fault=='policy': ops[0]['after']+=' '+request.messages[0].content.splitlines()[0]
        if fault=='keep_changed' and edits:
            text=cases()['claim-scope:1'][1].source.blocks[0][1]
            ops=[dict(block=1,before=text,after=text+' unnecessary',source_ids=[32],reason='Synthetic bad keep.')]
        edits.append(request)
        response=ChatResponse(provider='zhipu',model='glm-5.3-flash',content=None,
            finish_reason='tool_calls',tool_calls=(ToolCall(id='edit',name='submit_source_edits',arguments=dict(edits=ops)),),
            usage=TokenUsage(input_tokens=20,output_tokens=10))
        generator.last_exchange=Exchange(request,response,hashlib.sha256(validate_request(request,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        if fault=='transport':
            raise RuntimeError('Synthetic incomplete request')
        return response
    def review(request):
        arguments=dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
        if fault=='fresh_failed': arguments['score']=60; arguments['verdict']='fail'
        response=ChatResponse(provider='zhipu',model='glm-5.3',content=None,
            finish_reason='tool_calls',tool_calls=(ToolCall(id='review',name='submit_report_review',arguments=arguments),),
            usage=TokenUsage(input_tokens=20,output_tokens=10))
        reviewer.last_exchange=Exchange(request,response,hashlib.sha256(validate_request(request,transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
        return response
    monkeypatch.setattr(generator,'chat',generate)
    monkeypatch.setattr(reviewer,'chat',review)
    router=RoleRoutedProvider(generator,reviewer,source_projection=runner.CONTRACT.descriptor()['source_projection'])
    return lambda _:router


def test_preparation_is_fixed_input_three_call_diagnostic_without_admission():
    plan=prepared()
    assert plan['budget']['max_calls']==3 and plan['budget']['max_tokens']==290304
    assert plan['budget']['max_active_seconds']==900
    assert plan['role_calls']=={'glm-5.3-flash':2,'glm-5.3':1}
    assert not plan['execution_authorized'] and not plan['original15_qualified'] and not plan['product_admitted']
    assert plan['historical_initial_inputs']==2
    assert [r['key'] for r in plan['cells']]==list(runner.KEYS)


@pytest.mark.parametrize('fault,expected_calls',[(None,3),('policy',1),('host_reject',1),('host_unavailable',1),
    ('missing_report',1),('fresh_failed',2),('keep_changed',3),('transport',1),('budget',0)])
def test_first_failure_stops_preserves_receipts_and_never_borrows_qualification(tmp_path,monkeypatch,fault,expected_calls):
    plan=json.loads(compact(prepared()))
    if fault=='budget': plan['budget']['max_tokens']=1
    host=Host(plan,fault)
    factory=scripted(monkeypatch,fault)
    result=runner.observe(factory,tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['calls']==expected_calls,result
    assert result['diagnostic_accepted']==(fault is None),result
    assert result['product_admitted'] is False and result['original15_qualified'] is False
    assert json.loads((tmp_path/'result.json').read_bytes())==result
    assert result['unknown_reserved_tokens']>0 if fault=='transport' else result['unknown_reserved_tokens']==0
    if fault not in ('transport','budget'):
        assert (tmp_path/'necessary-edit/response.json').exists()
        assert result['known_tokens']==expected_calls*30
    if fault is None:
        assert [r['role'] for r in result['attempts']]==['revision','review','revision']
        assert len(result['stages'])==3 and result['timing']['completed_host_waits']==3
    if expected_calls<2:
        assert not (tmp_path/'conditional-fresh').exists()


def test_closed_directory_is_rejected_before_ci_credentials_or_host(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'prepare',lambda **_:prepared())
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    def forbidden(*args,**kwargs): pytest.fail('closed batch touched external setup')
    monkeypatch.setattr(runner,'verify_public_ci',forbidden)
    monkeypatch.setattr(runner,'load_role_settings',forbidden)
    args=SimpleNamespace(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent',execute=True)
    with pytest.raises(ValueError,match='closed_or_exists'): runner.run(args)
