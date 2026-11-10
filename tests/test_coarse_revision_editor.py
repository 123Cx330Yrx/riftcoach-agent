"""Actual workflow/budget with scripted IO; never live generation evidence."""
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import coarse_revision_editor as editor
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_boundary_examples import RoleBoundaryExamplesReviewWorkflow as Current
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import frozen_cases
from app.evaluation.source_patch_editor import report_inputs
from app.harness.steps import RevisionRequest
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, ToolCall, TokenUsage
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider as CoachBudgetedProvider
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT as CONTRACT
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.reviewer_roles import RoleRoutedProvider, role_for_request
from tests.test_reviewer_role_proposal import providers
from tests.test_native_editor_product_budget import offline

BEFORE = '所选全部 5 局的每一个指标均值都被辅助局拉低，包括视野分与 15 分钟前死亡，应按位置分开解读。'
AFTER = '所选全部 5 局中，辅助局拉低了补刀、经济和伤害的均值，却拉高了视野分与 15 分钟前死亡的均值，应按位置分开解读。'


@lru_cache
def cases():
    fixtures = json.loads(Path('tests/fixtures/coarse_edit_initial_reviews_20261001.json').read_bytes())
    requests = {row['key']:req for row,req in frozen_cases()[0]}
    result = {}
    for row in fixtures['cases']:
        req = requests[row['key']]
        inputs = Current.build_inputs(req)
        assert digest(req.report) == row['report_sha256']
        assert digest(inputs.data_json) == row['input_sha256']
        _, accepted, _ = Current.validate_review(row['initial_raw'], inputs)
        result[row['key']] = req, inputs, accepted, row['initial_raw']
    return result


def operation():
    return dict(block=4, before=BEFORE, after=AFTER, source_ids=[31,32],
                reason='HOST-AUTHORED synthetic operation for numeric-direction correction.')


def exchange(request, *, edits=None, name='submit_source_edits', content=None):
    response = ChatResponse(provider='zhipu', model='glm-5.3-flash', content=content,
        finish_reason='tool_calls', tool_calls=(ToolCall(id='synthetic-edit',name=name,
            arguments=dict(edits=[operation()] if edits is None else edits)),),
        usage=TokenUsage(input_tokens=10, output_tokens=10))
    return Exchange(request, response, hashlib.sha256(validate_request(request,
        transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())


def test_current_sources_findings_full_final_and_preserved_bytes():
    req, inputs, accepted, _ = cases()['claim-scope:4']
    prepared = editor.edit_request(inputs, accepted)
    assert prepared.messages[1:] == Current.make_request(inputs, accepted=accepted).messages[1:]
    assert role_for_request(prepared,source_projection=PROJECTION) == 'revision'
    result = editor.inspect_edit_exchange(prepared,exchange(prepared),inputs,accepted)
    assert result.report == req.report.replace(BEFORE,AFTER)
    assert [r['source_id'] for r in result.journal['operations'][0]['selected_sources']] == [31,32]
    final = Current.make_request(report_inputs(inputs,result.report))
    assert result.journal['final_review_request_sha256'] == hashlib.sha256(
        validate_request(final,transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
    assert not result.journal['semantic_approval'] and not result.journal['production_admitted']
    good, source, verdict, _ = cases()['claim-scope:1']
    request = editor.edit_request(source,verdict)
    kept = editor.inspect_edit_exchange(request,exchange(request,edits=[]),source,verdict)
    assert kept.report == good.report


@pytest.mark.parametrize('fault', ['unknown_source','row_reference','overlap','anchor','citation','policy',
    'model','receipt','tool','prose','finish','extra_tool','issued_messages','issued_metadata','accepted'])
def test_rejects_bad_edits_and_misbound_actual_responses(fault):
    _, inputs, accepted, _ = cases()['claim-scope:4']
    request = editor.edit_request(inputs,accepted)
    op = operation()
    if fault == 'unknown_source': op['source_ids']=[9999]
    if fault == 'row_reference': op['source_ids']=[1]
    if fault == 'anchor': op['before']='NONEXISTENT'
    if fault == 'citation': op['after']+=' [K9999]'
    if fault == 'policy': op['after']+=' '+request.messages[0].content.splitlines()[0]
    reply = exchange(request,edits=[op,op] if fault=='overlap' else [op])
    if fault == 'model': reply=replace(reply,response=replace(reply.response,model='glm-5.3'))
    if fault == 'receipt': reply=replace(reply,receipt_request_sha256='0'*64)
    if fault == 'tool': reply=exchange(request,name='submit_report_review')
    if fault == 'prose': reply=exchange(request,content='unexpected prose')
    if fault == 'finish': reply=replace(reply,response=replace(reply.response,finish_reason='length'))
    if fault == 'extra_tool': reply=replace(reply,response=replace(reply.response,tool_calls=(
        *reply.response.tool_calls,replace(reply.response.tool_calls[0],id='extra-edit'))))
    if fault == 'issued_messages': reply=exchange(replace(request,messages=request.messages[:-1]))
    if fault == 'issued_metadata': reply=exchange(replace(request,metadata={**request.metadata,'review_phase':'native_business_review'}))
    if fault == 'accepted': accepted=accepted.model_copy(update={'score':81})
    with pytest.raises(ValueError): editor.inspect_edit_exchange(request,reply,inputs,accepted)
    assert inputs.source.report.count(BEFORE)==1


def setup_flow(monkeypatch, *, fault=None):
    req, inputs, accepted, raw = cases()['claim-scope:4']
    generator, reviewer = providers()
    recorded = []
    review_calls = []
    def generate(request):
        if request.metadata.get('harness_step')=='revise':
            op=operation()
            if fault=='policy': op['after']+=' '+request.messages[0].content.splitlines()[0]
            ex=exchange(request,edits=[op])
            if fault=='tool': ex=exchange(request,name='submit_report_review')
        else:
            response=ChatResponse(provider='zhipu',model='glm-5.3-flash',content='synthetic generation',
                finish_reason='stop',usage=TokenUsage(input_tokens=size(request),output_tokens=request.max_tokens))
            ex=Exchange(request,response,hashlib.sha256(validate_request(request,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        generator.last_exchange=ex
        return ex.response
    def review(request):
        review_calls.append(request)
        arguments=json.loads(raw) if len(review_calls)==1 else dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
        ex=exchange(request,name='submit_report_review')
        response=replace(ex.response,model='glm-5.3',tool_calls=(ToolCall(id='synthetic-review',name='submit_report_review',arguments=arguments),))
        reviewer.last_exchange=replace(ex,response=response)
        return response
    monkeypatch.setattr(generator,'chat',generate)
    monkeypatch.setattr(reviewer,'chat',review)
    router=RoleRoutedProvider(generator,reviewer,source_projection=PROJECTION)
    budget=CoachBudgetedProvider(router,coach_contract=CONTRACT)
    # Two synthetic generation turns exercise ONE ledger, not natural generation.
    for i in (1,2):
        budget.chat(ChatRequest(messages=(ChatMessage(role=MessageRole.USER,content='synthetic generation'),),
            max_tokens=32768,timeout_s=300,metadata={'agent_loop_iteration':i}))
    flow=editor.CoarseRevisionWorkflow(SharedBudgetReviewSender(budget),record=lambda *args:recorded.append(args))
    first=flow.evaluate(req)
    revision=RevisionRequest(req.player_summary,req.deterministic_report,req.knowledge,req.report,first)
    return req,flow,budget,router,revision,recorded,review_calls


def test_same_workflow_five_calls_fresh_exact_report_and_no_second_revision(monkeypatch):
    req,flow,budget,router,revision,recorded,reviews=setup_flow(monkeypatch)
    draft=flow.revise(revision)
    assert draft.report==req.report.replace(BEFORE,AFTER)
    assert flow.evaluate(replace(req,report=draft.report)).verdict.value=='pass'
    assert [r['role'] for r in router.attempts]==['generation','generation','review','revision','review']
    assert budget.calls==5 and budget.reserved_tokens==0 and budget.tokens<=401920
    assert flow._expected_recheck.source.report==draft.report
    assert reviews[-1].messages==Current.make_request(flow._expected_recheck).messages
    assert flow.last_edit_journal['assembled_report']==draft.report
    assert len(recorded)==3
    with pytest.raises(ValueError): flow.revise(revision)


@pytest.mark.parametrize('fault',['policy','tool','tokens','changed_source','changed_fresh'])
def test_failure_stops_before_further_requests_and_keeps_completed_usage(monkeypatch,fault):
    req,flow,budget,router,revision,recorded,reviews=setup_flow(monkeypatch,fault=fault)
    if fault=='tokens': budget.tokens=401920
    if fault=='changed_source': revision=replace(revision,report=revision.report+' changed')
    if fault=='changed_fresh':
        draft=flow.revise(revision)
        with pytest.raises(ValueError): flow.evaluate(replace(req,report=draft.report+' changed'))
    else:
        with pytest.raises(Exception): flow.revise(revision)
    calls=budget.calls
    assert calls==(3 if fault in ('tokens','changed_source') else 4)
    assert len(reviews)==1
    assert budget.reserved_tokens==0
    if fault in ('policy','tool'):
        assert recorded[-1][0]=='native_business_revision'
        assert router.attempts[-1]['status']=='completed'
        assert flow.last_edit_journal is None and flow.stopped
    assert flow.stopped
    valid_revision=replace(revision,report=req.report)
    with pytest.raises(Exception): flow.revise(valid_revision)
    if flow._expected_recheck is not None:
        with pytest.raises(Exception): flow.evaluate(replace(req,report=flow._expected_recheck.source.report))
    with pytest.raises(Exception): flow.evaluate(req)
    assert budget.calls==calls
