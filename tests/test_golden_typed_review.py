"""Complete offline typed-source review and known semantic limits."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_typed_source_checks import SourceCheck, SourceLiteral, validate_checks, render_literal
from app.evaluation.golden_contextual_requests import restore
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_review_source_catalog import source_input
from tests.test_golden_comparison_reassessment import inputs_for, assessment
from tests.test_golden_bounded_correction import issue
from tests.test_golden_integrated_review import ReplayProvider


def values(inputs):
    before, final = assessment(inputs)
    for value in (before, final):
        value.update(source_checks=[], issue_resolutions=[])
        for audit in value["audits"]:
            for claim in audit["claims"]:
                claim.setdefault("comparisons", [])
                claim["summaries"] = []
    return before, final


def check(quote_ref, *, key="source/official_patch", kind="official_patch", path=("patch_version",), reported="16.17", fmt="exact"):
    source = dict(key=key, kind=kind, path=list(path))
    return dict(quote_ref=quote_ref, kind="source_fact", disposition="supported", sources=[source],
        literals=[dict(source=source, reported=reported, format=fmt, places=None)], explanation="按原始来源字段核对，非模型质量证明。")


def source_scenario(report="官方补丁16.17。"):
    original = source_input()
    # Rebuild report identity with unchanged source/knowledge data.
    from app.evaluation.golden_review_experiment import SourceIndex
    data = strict_json(original.data_json)
    source = SourceIndex.build(report, strict_json(original.pack_json))
    data["source_index"] = source.prompt_sources()
    inputs = replace(original, source=source, data_json=compact(data))
    before, final = values(inputs)
    for value in (before, final):
        for audit in value["audits"]:
            audit["claims"] = []
        value["source_checks"] = [check(dict(block=1))]
    return inputs, before, final


def test_real_source_checks_survive_review_without_becoming_numeric_inference():
    inputs, before, final = source_scenario()
    state = typed.prepare(compact(before), inputs)
    result, journal = typed.apply(state, compact(final), inputs=inputs)
    assert result.verdict == "pass"
    assert all(not audit.claims for audit in result.audits)
    assert journal["source_checks"][0]["literals"][0]["matches"]
    assert journal["first_raw"] == compact(before)
    assert journal["provisional_diagnostics"] == []
    assert not journal["semantic_approval"] and journal["general_coverage"]


@pytest.mark.parametrize("mutation", ["wrong_kind", "wrong_value", "missing_literal", "drop_check", "wrong_path"])
def test_source_failures_and_omitted_obligations_remain_blocking(mutation):
    inputs, before, final = source_scenario()
    if mutation == "wrong_kind": final["source_checks"][0]["literals"][0]["source"]["kind"] = "external_snapshot"
    if mutation == "wrong_value":
        final["source_checks"][0]["literals"][0]["source"].update(key="source/data_dragon", kind="static_catalog", path=["version"])
    if mutation == "missing_literal": final["source_checks"][0]["literals"] = []
    if mutation == "drop_check": final["source_checks"] = []
    if mutation == "wrong_path": final["source_checks"][0]["sources"][0]["path"] = ["unknown"]
    with pytest.raises(ValueError): typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_bad_source_value_can_be_reported_for_revision_but_not_cleared_to_pass():
    inputs, before, final = source_scenario("官方补丁16.18。")
    for value in (before, final): value["source_checks"][0]["literals"][0]["reported"] = "16.18"
    final["source_checks"][0]["disposition"] = "unsupported"
    final.update(issues=[issue(inputs, inputs.source.report, "fact_error")], verdict="needs_revision", score=70)
    result, _ = typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    assert result.verdict == "needs_revision"
    final.update(issues=[], verdict="pass")
    with pytest.raises(ValueError): typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_prior_general_issue_requires_explicit_resolution_and_unchanged_source_coverage():
    inputs, before, final = source_scenario()
    before.update(issues=[issue(inputs, inputs.source.report, "fact_error")], verdict="needs_revision", score=70)
    with pytest.raises(ValueError, match="issue_disposition"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    final["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=final["source_checks"][0]["sources"], explanation="原始官方补丁字段证明首评误报。")]
    result, journal = typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    assert result.verdict == "pass" and journal["issue_resolution_sources"][0]["sources"]
    final["issue_resolutions"][0]["sources"] = []
    with pytest.raises(ValueError, match="resolution_evidence"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_misclassified_source_fact_can_change_lane_without_losing_original_text():
    inputs, before, final = source_scenario()
    before["source_checks"] = []
    before["audits"][0]["claims"] = [dict(quote_ref=dict(block=1), decision="direct_supported",
        evidence_refs=[1], explanation="首评误分类；引用也不构成证明。")]
    result, journal = typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    assert result.verdict == "pass"
    assert journal["source_coverage"][0]["final_lanes"] == ["source_checks"]
    final["source_checks"] = []
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_invalid_first_source_span_protects_whole_real_block():
    inputs, before, final = source_scenario()
    before["source_checks"][0]["quote_ref"] = dict(block=1, head="不存在", tail="不存在")
    state = typed.prepare(compact(before), inputs)
    assert state.source_refs[0].head is None
    typed.apply(state, compact(final), inputs=inputs)
    before["source_checks"][0]["quote_ref"]["block"] = 999
    with pytest.raises(ValueError, match="unknown_source_block"): typed.prepare(compact(before), inputs)


@pytest.mark.parametrize("key,kind,path", [("legacy/facts:recent_aggregate", "aggregate", []),
    ("source/position", "position_context", ["observed", 0, "averages", "cs_per_min"])])
def test_source_lane_cannot_accept_match_statistics(key, kind, path):
    inputs, before, final = source_scenario()
    final["source_checks"][0]["sources"] = [dict(key=key, kind=kind, path=path)]
    with pytest.raises(ValueError, match="match_requires_audit"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_first_opinions_isolated_and_original_source_data_lossless():
    inputs, before, _ = source_scenario()
    built = typed.request(inputs, state=typed.prepare(compact(before), inputs))
    changed = deepcopy(before)
    changed["source_checks"][0].update(explanation="FIRST_OPINION_SENTINEL", disposition="unsupported")
    changed.update(score=0, verdict="fail", summary="FIRST_OPINION_SENTINEL")
    assert built == typed.request(inputs, state=typed.prepare(compact(changed), inputs))
    assert "FIRST_OPINION_SENTINEL" not in str(built.messages)
    message = built.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0]
    data = strict_json(message)
    data["deterministic_source_facts"] = strict_json(inputs.data_json)["deterministic_source_facts"]
    restored = restore(data)
    for key, value in source_data(inputs).items(): assert restored[key] == value


@pytest.mark.parametrize("operation,reported", [("mean", "8.91"), ("median", "8.8")])
def test_whole_role_statistics_use_correct_operations_and_all_members(operation, reported):
    inputs = inputs_for(report=f"所选四场中单补刀统计为{reported}。")
    before, final = values(inputs)
    row = final["audits"][1]["claims"][0]
    row["comparisons"] = []
    members = typed.comparison.catalog(inputs)["cohorts"]["MIDDLE"]
    refs = sorted(members["wins"] + members["losses"])
    row["summaries"] = [dict(operation=operation, cohort="MIDDLE", metric="cs_per_min", operand_refs=refs, reported=reported)]
    result, journal = typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    assert result.verdict == "pass" and journal["summaries"][0]["matches"]
    row["summaries"][0]["operand_refs"].pop()
    with pytest.raises(ValueError, match="summary_members"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_wrong_operation_is_not_repaired_to_match_the_reported_number():
    inputs = inputs_for(report="所选四场中单补刀中位数约8.8。")
    before, final = values(inputs)
    row = final["audits"][1]["claims"][0]
    row["comparisons"] = []
    row["summaries"] = [dict(operation="mean", cohort="MIDDLE", metric="cs_per_min",
        operand_refs=row["evidence_refs"], reported="8.8")]
    with pytest.raises(ValueError, match="summary_value_mismatch"):
        typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)


@pytest.mark.parametrize("mutation", ["duplicate", "other_role", "uncited", "missing_value", "ratio_out_of_range"])
def test_summary_cannot_change_members_or_use_invalid_values(mutation):
    inputs = inputs_for(report="所选四场中单补刀均值8.91。")
    if mutation in ("missing_value", "ratio_out_of_range"):
        pack = strict_json(inputs.pack_json)
        metric = "kill_participation" if mutation == "ratio_out_of_range" else "cs_per_min"
        key = next(k for k in pack["facts"] if k.startswith("facts:recent_match:"))
        pack["facts"][key][metric] = 1.2 if mutation == "ratio_out_of_range" else None
        inputs = replace(inputs, pack_json=compact(pack))
    before, final = values(inputs)
    row = final["audits"][1]["claims"][0]
    row["comparisons"] = []
    row["summaries"] = [dict(operation="mean", cohort="MIDDLE", metric="kill_participation" if mutation == "ratio_out_of_range" else "cs_per_min",
        operand_refs=list(row["evidence_refs"]), reported="8.91")]
    if mutation == "duplicate": row["summaries"][0]["operand_refs"].append(row["evidence_refs"][0])
    if mutation == "other_role": row["summaries"][0]["operand_refs"] += typed.comparison.catalog(inputs)["cohorts"]["UTILITY"]["losses"]
    if mutation == "uncited": row["evidence_refs"].pop()
    with pytest.raises(ValueError, match="typed_summary_(members_invalid|value_missing)"):
        typed.validate_summaries(typed.TypedReview.model_validate(final, strict=True), inputs)
    if mutation in ("missing_value", "ratio_out_of_range"):
        row["decision"] = "direct_unsupported"
        ledger = typed.validate_summaries(typed.TypedReview.model_validate(final, strict=True), inputs)
        assert ledger[0]["actual"] is None and ledger[0]["missing_refs"]


def test_summary_percent_is_explicit_and_keeps_source_ratio_units():
    inputs = inputs_for(report="所选四场中单平均参团率52%。")
    pack = strict_json(inputs.pack_json)
    for key, value in pack["facts"].items():
        if key.startswith("facts:recent_match:"): value["kill_participation"] = .52
    inputs = replace(inputs, pack_json=compact(pack))
    _, final = values(inputs)
    row = final["audits"][1]["claims"][0]
    row["comparisons"] = []
    row["summaries"] = [dict(operation="mean", cohort="MIDDLE", metric="kill_participation",
        operand_refs=row["evidence_refs"], reported="52%")]
    ledger = typed.validate_summaries(typed.TypedReview.model_validate(final, strict=True), inputs)
    assert ledger[0]["actual"] == "0.52" and ledger[0]["rendered"] == "52%"


def test_wrong_cohort_still_requires_manual_semantic_rejection():
    inputs = inputs_for()
    before, final = values(inputs)
    _, wrong = assessment(inputs, cohort="selected")
    final["audits"] = wrong["audits"]
    for a in final["audits"]:
        for c in a["claims"]: c["summaries"] = []
    result, journal = typed.apply(typed.prepare(compact(before), inputs), compact(final), inputs=inputs)
    assert result.verdict == "pass" and not journal["semantic_approval"]
    # Structural consistency is insufficient: both bindings/explanation can
    # jointly use the wrong sample. This MUST fail live manual acceptance.


def test_injection_cannot_be_cleared_by_second_review():
    inputs, before, _ = source_scenario()
    before["issues"] = [dict(issue(inputs, inputs.source.report), category="prompt_injection", severity="high")]
    with pytest.raises(ValueError, match="security_terminal"): typed.prepare(compact(before), inputs)


@pytest.mark.parametrize("value,fmt,places,reported", [
    ("2026-08-25T18:00:00Z", "date", None, "2026-08-25"),
    ("2026-08-25T18:00:00+00:00", "timestamp", None, "2026-08-25T18:00:00Z"),
    (.52, "percent", 0, "52%"), (2, "tier", None, "T2"), (8.805, "rounded", 2, "8.81")])
def test_typed_literal_rendering(value, fmt, places, reported):
    literal = SourceLiteral.model_validate(dict(source=dict(key="source/official_patch", kind="official_patch", path=[]),
        reported=reported, format=fmt, places=places), strict=True)
    assert render_literal(value, literal) == reported


def test_five_call_revision_flow_keeps_source_checks_and_same_original_inputs():
    good_text, bad_text = "官方补丁16.17。", "官方补丁16.18。"
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n" + bad_text + "\n\n建议核对单局。[K1]"
    revised = report.replace(bad_text, good_text)
    base = source_input()
    data = strict_json(base.data_json)
    from tests.test_golden_fact_candidate import summary
    req = EvaluationRequest(summary(), data["deterministic_source_facts"], KnowledgeEvidence.empty(), report, "检查观摩报告")
    inputs = typed.TypedReviewWorkflow.build_inputs(req)
    fixed_inputs = typed.TypedReviewWorkflow.build_inputs(replace(req, report=revised))
    def response(current, text, failed):
        first, final = values(current)
        ref = current.source.reference(text)
        for value in (first, final):
            for a in value["audits"]: a["claims"] = []
            value["source_checks"] = [check(ref, reported="16.18" if failed else "16.17")]
            if failed:
                value["source_checks"][0]["disposition"] = "unsupported"
                value.update(issues=[issue(current, text, "fact_error")], verdict="needs_revision", score=70)
        return first, final
    first, final = response(inputs, bad_text, True)
    fixed_first, fixed_final = response(fixed_inputs, good_text, False)
    replies = [compact(first), compact(final), revised, compact(fixed_first), compact(fixed_final)]
    provider = ReplayProvider(lambda _, n: replies[n-1])
    sender = BudgetedReviewSender(provider)
    flow = typed.TypedReviewWorkflow(sender)
    initial = flow.evaluate(req)
    assert initial.verdict.value == "needs_revision"
    accepted, _ = typed.apply(typed.prepare(compact(first), inputs), compact(final), inputs=inputs)
    with pytest.raises(ValueError, match="evaluation_changed"):
        flow.build_revision(None, accepted.model_copy(update={"summary": "forged"}), inputs)
    result = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, report, initial))
    sent = strict_json(provider.requests[2].messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    assert sent["accepted_evaluation"] == typed.TypedReview.model_validate(final, strict=True).model_dump(mode="json")
    sent["deterministic_source_facts"] = data["deterministic_source_facts"]
    for key, value in source_data(inputs).items(): assert restore(sent)[key] == value
    with pytest.raises(ValueError, match="source_changed"):
        flow.evaluate(replace(req, report=result.report, deterministic_report="changed"))
    final = flow.evaluate(replace(req, report=result.report))
    assert final.verdict.value == "pass"
    assert flow.calls == sender.budget.calls == len(provider.requests) == 5
    assert sender.budget.tokens == 100
    assert flow.last_journal["source_checks"][0]["literals"][0]["matches"]
