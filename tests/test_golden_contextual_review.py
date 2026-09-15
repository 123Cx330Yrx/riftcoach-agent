"""Protocol/control-flow tests; scripted fixtures cannot establish model quality."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.evaluation import golden_contextual_correction as contextual
from app.evaluation.golden_contextual_correction import prepare_state
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_fact_candidate import summary
from tests.test_golden_integrated_review import ReplayProvider


def patch(state):
    return dict(claim_edits=[], issue_edits=[], added_claims=[], added_issues=[], heading_edits=[],
        review_notes=[dict(target_id=k, explanation="核对完整上下文的同一比较及后文冲突") for k in state.required_reviews],
        score=95, verdict="pass", summary="脚本化审查", passed_checks=[])


def scenario():
    context = "这四场中单的经济和伤害逐行方向一致，仅指本样本，不外推长期。"
    target = "经济和伤害是较稳定的差异项。"
    inputs, first = fixture(context+"\n\n"+target)
    first["audits"][1]["claims"] = [claim(inputs,target,context=dict(
        quote_ref=inputs.source.reference(context),relation="defines_scope",explanation="同一组样本及经济伤害比较"))]
    state = prepare_state(compact(first),inputs)
    return inputs, state, patch(state)


def test_final_context_is_single_source_of_classification_and_reference():
    inputs,state,edit = scenario()
    result,journal = contextual.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict == "pass"
    assert result.audits[1].claims[0].context.quote == inputs.source.blocks[0][1]
    assert journal["meaning_fields_derived_from_final_claims"]
    assert journal["standard_id"] == contextual.STANDARD_ID and not journal["semantic_approval"]
    assert journal["meaning_reviews"][0]["disposition"] == "defined"
    assert journal["meaning_reviews"][0]["language_ref"]["block"] == 1
    assert "专门定义" in contextual.FULL_CONTEXT_RULE


@pytest.mark.parametrize("mutation",["v1", "duplicate", "missing", "unknown", "disposition", "language_ref", "suffix", "state", "null_scope", "bad_context", "bad_evidence", "contradictory_context"])
def test_invalid_or_legacy_correction_is_rejected(mutation):
    inputs,state,edit = scenario()
    row = deepcopy(state.entries()["c001"]["value"])
    if mutation == "v1": edit["meaning_reviews"] = edit.pop("review_notes")
    elif mutation == "duplicate": edit["review_notes"] *= 2
    elif mutation == "missing": edit["review_notes"] = []
    elif mutation == "unknown": edit["review_notes"][0]["target_id"] = "c999"
    elif mutation in {"disposition","language_ref"}: edit["review_notes"][0][mutation] = None
    elif mutation == "state": state = replace(state,state_id="changed")
    elif mutation in {"null_scope","bad_context","bad_evidence","contradictory_context"}:
        if mutation == "null_scope": row["scope"] = None
        if mutation == "bad_context": row["context"]["quote_ref"]["block"] = 999
        if mutation == "bad_evidence": row["evidence_refs"] = [999]
        if mutation == "contradictory_context": row["context"]["relation"] = "negates"
        edit["claim_edits"] = [dict(target_id="c001",value=row,reason="脚本错误")]
    raw = compact(edit) + ("{}" if mutation == "suffix" else "")
    with pytest.raises(ValueError): contextual.apply_correction(state,raw,inputs=inputs)


def test_real_future_claim_still_requires_issue_and_cannot_pass():
    target="所有未来输局的经济和伤害都会更低。"
    inputs,first=fixture("这四场仅供参考。\n\n"+target)
    first["audits"][1]["claims"]=[claim(inputs,target,scope="beyond_sample",scope_anchor="未来",status="unsupported")]
    state=prepare_state(compact(first),inputs)
    edit=patch(state)
    with pytest.raises(ValueError): contextual.apply_correction(state,compact(edit),inputs=inputs)
    edit.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)])
    result,_=contextual.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict == "needs_revision" and result.issues[0].quote == target
    edit["verdict"]="pass"
    with pytest.raises(ValueError): contextual.apply_correction(state,compact(edit),inputs=inputs)


def test_existing_fact_issue_cannot_disappear_without_resolution_evidence():
    inputs,first=fixture("错误数值。")
    first.update(score=70,verdict="needs_revision",issues=[issue(inputs,inputs.source.report,"fact_error")])
    state=prepare_state(compact(first),inputs)
    edit=patch(state); edit.update(score=70,verdict="needs_revision")
    result,_=contextual.apply_correction(state,compact(edit),inputs=inputs)
    assert result.issues[0].category == "fact_error"
    edit["issue_edits"]=[dict(target_id="i001",value=None,reason="脚本试图删除",resolution_evidence_refs=[])]
    with pytest.raises(ValueError,match="resolution_needs_evidence"):
        contextual.apply_correction(state,compact(edit),inputs=inputs)


def test_heading_assertion_addition_and_security_still_checked():
    inputs,first=fixture("## 所有未来输局都会更差")
    state=prepare_state(compact(first),inputs); edit=patch(state)
    row=claim(inputs,inputs.source.report,scope="beyond_sample",scope_anchor="未来",status="unsupported")
    edit.update(score=70,verdict="needs_revision",
        heading_edits=[dict(target_id="h001",kind="assertion",reason="有未来断言")],
        added_claims=[dict(audit="cohort_comparison",value=row,review_note="未来无证据")],
        added_issues=[issue(inputs,inputs.source.report)])
    result,_=contextual.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict == "needs_revision"
    edit["added_claims"]=[]
    with pytest.raises(ValueError,match="heading_claim_missing"):
        contextual.apply_correction(state,compact(edit),inputs=inputs)
    edit["added_issues"][0].update(category="prompt_injection",severity="high")
    with pytest.raises(ValueError,match="security_terminal"):
        contextual.apply_correction(state,compact(edit),inputs=inputs)


def test_complete_five_call_revision_rechecks_same_sources():
    target,fixed="所有未来输局都会更差。","这四场仅作样本观察。"
    report="\n\n".join(COACH_REPORT_HEADINGS)+"\n\n"+target+"\n\n建议核对单局。[K1]"
    revised=report.replace(target,fixed)
    inputs,first=fixture(report); after,second=fixture(revised)
    first["audits"][1]["claims"]=[claim(inputs,target,scope="beyond_sample",scope_anchor="未来",status="unsupported")]
    second["audits"][1]["claims"]=[claim(after,fixed)]
    correction=patch(prepare_state(compact(first),inputs))
    correction.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)])
    recheck=patch(prepare_state(compact(second),after))
    from tests.test_golden_contextual_patch_wire import wire_patch
    replies=[compact(first),compact(wire_patch(correction)),revised,compact(second),compact(wire_patch(recheck))]
    provider=ReplayProvider(lambda _,n:replies[n-1]); sender=BudgetedReviewSender(provider)
    flow=ContextualCorrectionWorkflow(sender)
    req=EvaluationRequest(summary(),"完整来源",KnowledgeEvidence.empty(),report,"检查观摩报告")
    initial=flow.evaluate(req)
    output=flow.revise(RevisionRequest(req.player_summary,req.deterministic_report,req.knowledge,report,initial))
    with pytest.raises(ValueError,match="recheck_source_changed"):
        flow.evaluate(replace(req,report=output.report,deterministic_report="changed"))
    final=flow.evaluate(replace(req,report=output.report))
    assert final.verdict.value == "pass" and flow.calls == sender.budget.calls == 5
    assert flow.last_journal["standard_id"] == contextual.STANDARD_ID
    with pytest.raises(ValueError): flow.evaluate(req)


def test_new_manifest_identity_and_preview_are_offline(monkeypatch,tmp_path):
    from scripts import run_golden_integrated_review as runner
    from scripts.run_golden_context_controls import MANIFEST as OLD_MANIFEST
    from scripts.run_golden_contextual_review import select_cases
    import json
    old=json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    # Private original report is not available on public CI; build a minimal
    # identity fixture while testing the real frozen manifest separately.
    cases=[dict(c,report="fixture",target="fixture") for c in old["cases"]]
    import scripts.run_golden_contextual_review as entry
    monkeypatch.setattr(entry,"digest",lambda report: "bad")
    with pytest.raises(ValueError,match="source_report_changed"): select_cases(cases)
    selected=[dict(cases[0],id="contextual_01",source_case_id="stable_unbounded")]
    monkeypatch.setattr(entry,"select_cases",lambda _:selected)
    monkeypatch.setattr(runner,"load_inputs",lambda *_:(summary(),"完整来源",KnowledgeEvidence.empty(),cases))
    monkeypatch.setattr(runner,"verify_public_ci",lambda *_:pytest.fail("preview called CI"))
    monkeypatch.setattr(runner,"ReceiptedStreamProvider",lambda **_:pytest.fail("preview constructed provider"))
    plan=runner.run(SimpleNamespace(source_run=tmp_path,base_report=tmp_path,pair=1,execute=False),full_context=True)
    assert plan["standard_id"] == contextual.STANDARD_ID and not plan["labels_sent_to_model"]
    assert plan["reasoning_effort"] == "high" and plan["max_output_per_call"] == 32768


def test_requests_carry_complete_view_and_only_one_decision_schema():
    inputs,state,_=scenario()
    first=contextual.first_request(inputs); second=contextual.correction_request(state).request
    for request in (first,second):
        assert "generation_view" in request.messages[0].content
        assert contextual.FULL_CONTEXT_RULE in request.messages[0].content
        assert request.max_tokens == 32768 and request.timeout_s == 300
        assert request.messages[2].content.endswith("完整来源\n[END UNTRUSTED deterministic_source_facts]")
    schema=compact(contextual.CorrectionWire.model_json_schema())
    assert '"review_notes"' in schema
    assert all('"'+name+'"' not in schema for name in ("meaning_reviews","disposition","language_ref"))
