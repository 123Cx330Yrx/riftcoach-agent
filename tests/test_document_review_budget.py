"""Explicit router/contract with scripted endpoints; no product admission."""
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from app.evaluation.document_review_qualification import CONTRACT, ProviderFactory, Workflow
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.runtime.document_review_roles import DocumentRoleRoutedProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider as Budget
from tests.test_report_document_workflow import DocumentResponses
from tests.test_reviewer_role_proposal import compiled
from tests.test_native_editor_product_budget import offline


def router(mode,ceiling=False):
    generator=DocumentResponses(mode=mode,ceiling=ceiling)
    reviewer=DocumentResponses(mode=mode,ceiling=ceiling)
    reviewer.model_name='glm-5.3'
    reviewer.thinking_profile_id=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id
    reviewer.transport_id=REVIEW_MODEL_TRANSPORT_ID
    return DocumentRoleRoutedProvider(generator,reviewer,
        source_projection=CONTRACT.descriptor()['source_projection'])


@pytest.mark.parametrize('mode,ceiling', [('success',False),('success',True),('recovery',False)])
def test_generation_review_edit_fresh_shared_five_call_budget(compiled,mode,ceiling):
    roles=router(mode,ceiling)
    budget=Budget(roles,clock=lambda:0,coach_contract=CONTRACT)
    for request in compiled[0]: budget.chat(request)
    flow=Workflow(SharedBudgetReviewSender(budget))
    req=roles.generator.req
    initial=flow.evaluate(req)
    draft=flow.revise(RevisionRequest(req.player_summary,req.deterministic_report,
        req.knowledge,req.report,initial))
    if mode=='recovery':
        with pytest.raises(ProviderResponseError,match='external_call_budget_exhausted'):
            flow.evaluate(replace(req,report=draft.report))
        expected=['generation','generation','review','review','revision']
    else:
        assert flow.evaluate(replace(req,report=draft.report)).verdict.value=='pass'
        expected=['generation','generation','review','revision','review']
    assert [r['role'] for r in roles.attempts]==expected
    assert budget.calls==5 and budget.tokens<=401920
    assert all(len(r.messages)==4 for r in roles.reviewer.requests)
    with pytest.raises(ProviderResponseError):budget.chat(compiled[0][0])
    assert len(roles.attempts)==5


def test_unknown_real_receipt_remains_reserved_and_stops(tmp_path,monkeypatch):
    from app.evaluation import golden_stream_bridge as bridge
    from app.evaluation.document_review_qualification import frozen_cases, read_calls, summarize_role_calls
    from scripts.run_role_coach_development import summarize_calls
    def child(*args,**kwargs):raise TimeoutError('scripted no usage response')
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model):return NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory=ProviderFactory(generator_settings=settings('glm-5.3-flash'),reviewer_settings=settings('glm-5.3'),
        transport_root=tmp_path/'transport',source_projection=CONTRACT.descriptor()['source_projection'])
    budget=Budget(factory('unknown'),clock=lambda:0,coach_contract=CONTRACT)
    request=Workflow.make_request(Workflow.build_inputs(frozen_cases()[0][0][1]))
    with pytest.raises(Exception):budget.chat(request)
    assert budget.calls==1 and budget.tokens==0 and budget.reserved_tokens>0 and budget.stopped
    summary=summarize_calls(tmp_path/'transport/unknown',coach_contract=CONTRACT,summary_reader=summarize_role_calls)
    assert summary['reserved_calls']==summary['unknown_usage_calls']==1
    assert summary['total_estimated_uncached_cny'] is None
    with pytest.raises(ProviderResponseError):budget.chat(request)
    assert len(read_calls(tmp_path/'transport/unknown'))==1


def test_oversized_request_stops_before_transport(tmp_path):
    roles=router('success')
    budget=Budget(roles,clock=lambda:0,coach_contract=CONTRACT)
    r=Workflow.make_request(Workflow.build_inputs(roles.generator.req))
    r=replace(r,messages=(*r.messages[:-1],replace(r.messages[-1],content='x'*350000)))
    with pytest.raises(ProviderResponseError,match='token_budget_exhausted'):budget.chat(r)
    assert budget.calls==0 and roles.attempts==[]
