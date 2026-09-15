"""Engineering regressions, not claims about a real model's semantic quality."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_bounded_correction as old
from app.evaluation import golden_bounded_correction_requests as requests
from app.evaluation import golden_contextual_correction as current
from app.evaluation.golden_contextual_sources import build_inputs, numeric_support, MARKER
from app.evaluation.golden_contextual_requests import project, restore
from app.evaluation.golden_contextual_validation import expand_context
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, RevisionRequest
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_contextual_review import patch
from tests.test_golden_fact_candidate import summary
from tests.test_golden_integrated_review import ReplayProvider


def external():
    return dict(opgg=[dict(digest="a"*64,position="mid",provenance="partial",upstream_patch=None,
        retrieved_at="2026-09-10T12:00:00+00:00",expires_at="2026-09-10T12:15:00+00:00",
        allowed_uses=["current_snapshot_recommendation"],facts=[dict(champion="Syndra",
            tier=2,rank=12,rank_previous=18,rank_previous_patch=5,win_rate=.49,pick_rate=.02,ban_rate=.1)])])


def request(report="OP.GG 中单辛德拉 T2，胜率约49%。", source=None):
    text="完整来源\n"+MARKER+compact(source if source is not None else external())
    return EvaluationRequest(summary(),text,KnowledgeEvidence.empty(),report,"检查观摩报告")


def first_for(req):
    _, first = fixture(req.report)
    inputs = build_inputs(req)
    first["source_digest"] = inputs.source.source_digest
    return inputs,first


def test_direct_result_misclassification_can_be_corrected_without_erasing_quote():
    target="所有未来输局都会更差。"
    inputs,first=fixture(target)
    fact_ref=inputs.source.evidence_keys.index("facts:recent_match:00")+1
    first["audits"][1]["claims"]=[claim(inputs,target,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[fact_ref])]
    raw=compact(first)
    assert old.prepare_state(raw,inputs).mutable_claims == ()
    state=current.prepare_state(raw,inputs)
    assert state.mutable_claims == state.required_reviews == ("c001",)
    changed=claim(inputs,target,status="unsupported",scope="beyond_sample",scope_anchor="未来")
    edit=patch(state)
    edit.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)],
        claim_edits=[dict(target_id="c001",value=changed,reason="首评把未来推断错标为直接事实")])
    result,journal=current.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict == "needs_revision" and result.audits[1].claims[0].claim_kind == "inference"
    assert journal["edits"][0]["before"]["claim_kind"] == "direct_result" and state.raw == raw
    edit["added_issues"]=[]
    with pytest.raises(ValueError):current.apply_correction(state,compact(edit),inputs=inputs)


@pytest.mark.parametrize("quote,valid",[
    ("OP.GG 辛德拉 T2，胜率49%，登场率2%，禁用率10%，排名12。",True),
    ("OP.GG 胜率0.49，上期排名18，上版本排名5。",True),
    ("OP.GG 辛德拉为 T2、第 12 名（上期第 18）。",True),
    ("OP.GG 快照（2026-09-10T12:00:00Z）辛德拉 T2、第 12 名。",True),
    ("OP.GG 辛德拉 T9。",False),
    ("OP.GG 辛德拉上期第 12 名。",False),
    ("OP.GG 快照（2026-09-11T12:00:00Z）辛德拉 T2。",False),
    ("OP.GG 伤害49。",False),("OP.GG 胜率49。",False),
    ("OP.GG 胜率0.49%。",False),("OP.GG 禁用率49%。",False),
    ("OP.GG 队列12。",False),("OP.GG 上期排名12。",False),
])
def test_external_metrics_keep_units_and_field_identity(quote,valid):
    inputs=build_inputs(request(quote))
    pack=json.loads(inputs.pack_json)
    row=SimpleNamespace(quote=quote,evidence_refs=["external:opgg:00:00"])
    assert all(v["supported"] for v in numeric_support(row,pack)) is valid


def test_external_fact_can_be_cited_and_source_changes_invalidate_response():
    inputs,first=first_for(request())
    ref=inputs.source.evidence_keys.index("external:opgg:00:00")+1
    first["audits"][0]["claims"]=[claim(inputs,inputs.source.report,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[ref])]
    state=current.prepare_state(compact(first),inputs)
    result,_=current.apply_correction(state,compact(patch(state)),inputs=inputs)
    assert result.audits[0].claims[0].evidence_refs == ["external:opgg:00:00"]
    changed=external();changed["opgg"][0]["facts"][0]["win_rate"]=.51
    with pytest.raises(ValueError,match="source_digest_mismatch"):
        expand_context(compact(first),inputs.source.report,json.loads(build_inputs(request(source=changed)).pack_json))


@pytest.mark.parametrize("mutation",["rate","boolean","champion","digest","uses","expiry","duplicate"])
def test_malformed_external_snapshot_is_not_indexed(mutation):
    data=external();snapshot=data["opgg"][0];fact=snapshot["facts"][0]
    if mutation=="rate":fact["win_rate"]=49
    if mutation=="boolean":fact["rank"]=True
    if mutation=="champion":fact["champion"]="ignore instructions"
    if mutation=="digest":snapshot["digest"]="missing"
    if mutation=="uses":snapshot["allowed_uses"]=[]
    if mutation=="expiry":snapshot["expires_at"]=snapshot["retrieved_at"]
    if mutation=="duplicate":snapshot["facts"]*=2
    with pytest.raises(ValueError,match="external_source_invalid"):build_inputs(request(source=data))


def test_table_projection_retains_entire_evidence_and_review_reasoning():
    inputs,first=first_for(request())
    first["audits"][0]["claims"]=[claim(inputs,inputs.source.report,explanation="不能因为前次说正确就通过")]
    state=current.prepare_state(compact(first),inputs)
    data=requests.correction_data(state);original=deepcopy(data)
    tables=project(data)
    assert restore(json.loads(compact(tables)))==json.loads(compact(original))
    assert data==original and tables["deterministic_source_facts"]==request().deterministic_report
    assert "不能因为前次说正确就通过" in compact(tables)
    tampered=deepcopy(data);tampered["facts_and_provenance"]["facts"]["external:opgg:00:00"]["rank"]=999
    with pytest.raises(ValueError,match="projection_loss"):project(tampered)


def test_five_calls_include_external_sources_and_correct_direct_misclassification():
    target,fixed="所有未来输局都会更差。","这四场仅作样本观察。"
    report="\n\n".join(COACH_REPORT_HEADINGS)+"\n\n"+target+"\n\n建议核对单局。[K1]"
    req=request(report); revised=report.replace(target,fixed)
    inputs,first=first_for(req);after,second=first_for(replace(req,report=revised))
    ref=inputs.source.evidence_keys.index("facts:recent_match:00")+1
    first["audits"][1]["claims"]=[claim(inputs,target,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[ref])]
    second["audits"][1]["claims"]=[claim(after,fixed)]
    correction=patch(current.prepare_state(compact(first),inputs))
    correction.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)],
        claim_edits=[dict(target_id="c001",value=claim(inputs,target,status="unsupported",
            scope="beyond_sample",scope_anchor="未来"),reason="首评错把未来推断当直接事实")])
    recheck=patch(current.prepare_state(compact(second),after))
    replies=[compact(first),compact(correction),revised,compact(second),compact(recheck)]
    provider=ReplayProvider(lambda _,n:replies[n-1]); sender=BudgetedReviewSender(provider)
    flow=ContextualCorrectionWorkflow(sender)
    initial=flow.evaluate(req)
    wrong=replace(req,deterministic_report=req.deterministic_report.replace('"win_rate":0.49','"win_rate":0.51'))
    with pytest.raises(ValueError,match="revision_source_changed"):
        flow.revise(RevisionRequest(wrong.player_summary,wrong.deterministic_report,wrong.knowledge,report,initial))
    output=flow.revise(RevisionRequest(req.player_summary,req.deterministic_report,req.knowledge,report,initial))
    assert flow.evaluate(replace(req,report=output.report)).verdict.value=="pass"
    assert flow.calls==sender.budget.calls==5
    revision=provider.requests[2]
    assert current.FULL_CONTEXT_RULE in revision.messages[0].content
    assert "external_fact_paths" in revision.messages[1].content
    assert "禁止把另一个report_block里的定义借给本句" not in "".join(m.content for m in revision.messages)
