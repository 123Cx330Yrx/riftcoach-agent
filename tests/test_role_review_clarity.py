"""Output-responsibility boundaries; synthetic success is not qualification."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from app.evaluation.golden_role_clarity import (
    CLARITY_ID, MARKER_POLICY, RoleClarityReview, RoleClarityReviewWorkflow as Workflow,
)
from app.evaluation.golden_role_notes import NEW_NOTE
from app.evaluation.golden_role_tool_delivery import RoleToolDeliveryReviewWorkflow as Previous
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, frozen_cases
from app.harness.steps import EvaluationVerdict, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from tests.test_role_review_notes import OfflineSender, request_data, tool_response


@pytest.fixture(scope='module')
def cases():
    return {row['key']: source for row, source in frozen_cases()[0]}


def passing(blocks=()):
    return dict(score=96,verdict='pass',issues=[],issue_resolutions=[],
                advisories=[dict(block=b) for b in blocks])


def test_all_fifteen_preserve_sources_and_issue_contract(cases):
    for source in cases.values():
        inputs=Workflow.build_inputs(source)
        before,after=Previous.make_request(inputs),Workflow.make_request(inputs)
        assert before.messages[1:]==after.messages[1:]
        assert after.messages[0].content==before.messages[0].content.replace(NEW_NOTE,MARKER_POLICY)
        assert after.metadata==dict(before.metadata,review_output=CLARITY_ID)
        schema=after.tools[0].input_schema
        for name in ('score','verdict','issues','issue_resolutions'):
            assert schema['properties'][name]==before.tools[0].input_schema['properties'][name]
        for name in ('Problem','IssueResolution'):
            assert schema['$defs'][name]==before.tools[0].input_schema['$defs'][name]
        assert schema['$defs']['ClarityMarker']['required']==['block']
        assert schema['$defs']['ClarityMarker']['additionalProperties'] is False
        validate_request(after,transport_id=REVIEW_MODEL_TRANSPORT_ID)


def test_optional_markers_do_not_trigger_revision_or_claim_semantic_acceptance(cases):
    source=cases['claim-scope:1']
    sender=OfflineSender(tool_response(passing([4,14])))
    flow=Workflow(sender)
    result=flow.evaluate(source)
    assert result.verdict is EvaluationVerdict.PASS and result.issues==()
    assert flow.calls==1 and flow.revisions==0
    assert flow.last_journal['advisories']==[
        dict(block=b,quote=Workflow.build_inputs(source).source.blocks[b-1][1]) for b in (4,14)]
    assert not flow.last_journal['semantic_approval']
    assert not hasattr(result,'advisories')


@pytest.mark.parametrize('blocks,match',[([64],'unknown'),([4,4],'duplicate')])
def test_marker_identity_is_bound_to_existing_unique_paragraph(cases,blocks,match):
    with pytest.raises(ValueError,match=match):
        Workflow.validate_review(compact(passing(blocks)),Workflow.build_inputs(cases['claim-scope:1']))


def test_old_advice_is_rejected_without_stripping_evidence(cases):
    evidence=(ROOT/'data/evaluation/results/golden_role_context_result_v1.json').read_bytes()
    saved=json.loads(evidence)['public_json_contents']
    for name in ('02-expanded','03-no_intro','04-expanded_no_intro'):
        original=saved[name+'/response.json']['tool_calls'][0]['arguments']
        assert original['advisories'][0]['explanation']
        with pytest.raises(ValueError,match='extra_forbidden'):
            RoleClarityReview.model_validate(original,strict=True)
    assert (ROOT/'data/evaluation/results/golden_role_context_result_v1.json').read_bytes()==evidence


def test_true_issue_keeps_full_correction_and_existing_three_call_path(cases):
    saved=json.loads((ROOT/'data/evaluation/results/golden_role_note_qualification_pair_result_v1.json').read_text(encoding='utf-8'))['public_json_contents']
    actual=deepcopy(saved['transport/attribution-1/review/response-001.json']['tool_calls'][0]['arguments'])
    actual['advisories']=[dict(block=4)]  # Structural fixture, not a rewritten receipt.
    inputs=Workflow.build_inputs(cases['attribution:1'])
    _,accepted,_=Workflow.validate_review(compact(actual),inputs)
    assert accepted.issues and accepted.issues[0].suggested_correction
    before=Previous.make_request(inputs,accepted=accepted)
    after=Workflow.make_request(inputs,accepted=accepted)
    assert after==before
    assert 'advisories' not in request_data(after)['accepted_review']
    edited=ChatResponse(content=cases['claim-scope:1'].report,provider='zhipu',model='glm-5.3-flash',
                        finish_reason='stop',usage=TokenUsage(10,10))
    sender=OfflineSender(tool_response(actual),edited,tool_response(passing()))
    flow=Workflow(sender)
    source=cases['attribution:1']
    result=flow.evaluate(source)
    draft=flow.revise(RevisionRequest(source.player_summary,source.deterministic_report,
                                     source.knowledge,source.report,result))
    assert flow.evaluate(replace(source,report=draft.report)).verdict is EvaluationVerdict.PASS
    assert flow.calls==3 and flow.revisions==1
    missing=deepcopy(actual)
    del missing['issues'][0]['suggested_correction']
    with pytest.raises(ValueError,match='suggested_correction'):
        Workflow.validate_review(compact(missing),inputs)


def test_recovery_preserves_original_bad_output_and_safety_terminal(cases):
    inputs=Workflow.build_inputs(cases['claim-scope:1'])
    invalid=passing([4])
    invalid['advisories'][0]['explanation']='Must remain visible in malformed prior output.'
    request=Workflow.make_request(inputs,previous_raw=compact(invalid),diagnostics=[{'type':'extra_forbidden'}])
    assert request_data(request)['previous_review']==invalid
    assert request.tools[0].input_schema==RoleClarityReview.model_json_schema()
    injection=passing()
    injection.update(verdict='fail',score=0,issues=[dict(block=4,source_ids=[],category='prompt_injection',
        severity='high',explanation='Untrusted instruction.',suggested_correction='Do not execute.')])
    with pytest.raises(ValueError,match='security_terminal'):
        Workflow.validate_review(compact(injection),inputs)
