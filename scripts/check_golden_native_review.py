"""Full-source offline workflow/size witnesses, never model quality evidence."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import re

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_sources import source_catalog
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as measured
from app.harness.steps import EvaluationRequest, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases


def scripted(inputs, *, problem_block=None):
    """An explicitly non-semantic fixture. Not a model response or live input."""
    declarations = [n for n, source in source_catalog(inputs).items() if source.key == "source/deterministic"]
    rows = []
    for block, (_, text) in enumerate(inputs.source.blocks, 1):
        heading = bool(re.match(r"^#{1,6}\s", text))
        issues = [] if block != problem_block else [dict(source_ids=declarations, severity="medium", category="unsupported_comparison",
            explanation="分析者构造的流程见证：未来全称结论超出所给有限样本。",
            suggested_correction="收窄为本样本观察，未来是否延续有待验证。")]
        rows.append(dict(block=block, kind="navigation" if heading and not issues else "content",
            explanation="仅为接口/预算见证，来源存在不代表本段已获语义支持。", issues=issues))
    return dict(reviews=rows, score=70 if problem_block else 95,
        verdict="needs_revision" if problem_block else "pass", summary="离线脚本响应，不是模型评估。",
        passed_checks=[], issue_resolutions=[])


def long_explanation_stress(args, expected_inputs):
    """Compose lengthy analyst opinions; never replay them as model responses.

    The older whole-report offline fixture supplies explanations and source
    selections solely for realistic size, not an accepted semantic oracle.
    Original paragraphs and explanations are never sliced to fit a budget.
    """
    from scripts.check_golden_computed_partition_review import prepared
    from app.evaluation.golden_semantic_sources import request_data
    controls, _, inputs, fixtures, _ = prepared(args)
    assert inputs == expected_inputs
    shapes, replies = [], []
    for case, current, fixture in zip(controls, inputs, fixtures, strict=True):
        roots = source_catalog(current)
        numbers = {source.key: number for number, source in roots.items()}
        value = scripted(current)
        value.update({key: deepcopy(fixture[key]) for key in
            ("score", "verdict", "summary", "passed_checks")})
        checks = [claim for audit_row in fixture["audits"] for claim in audit_row["claims"]]
        checks += fixture["source_checks"]
        prefixed = []
        for row in value["reviews"]:
            matches = [check for check in checks if check["quote_ref"]["block"] == row["block"]]
            if matches:
                row["kind"] = "content"
                row["explanation"] = "；".join(dict.fromkeys(check["explanation"] for check in matches))
                refs = set()
                for check in matches:
                    refs.update(check.get("evidence_refs", []))
                    refs.update(numbers[source["key"]] for source in check.get("sources", []))
                    refs.update(numbers[literal["source"]["key"]] for literal in check.get("literals", []))
            row["issues"] = [dict({key: issue[key] for key in
                ("severity", "category", "explanation", "suggested_correction")}, source_ids=sorted(refs))
                for issue in fixture["issues"] if issue["quote_ref"]["block"] == row["block"]]
            if row["kind"] == "content":
                expanded = "原段：" + current.source.blocks[row["block"] - 1][1] + "。核查：" + row["explanation"]
                if len(expanded) <= 700:
                    row["explanation"] = expanded
                    prefixed.append(row["block"])
        candidate.validate(compact(value), current)
        first = deepcopy(value)
        broken_index = next(index for index, row in enumerate(first["reviews"])
            if row["kind"] == "content" and not row["issues"])
        first["score"] = str(first["score"])
        raw = compact(first)
        try:
            candidate.validate(raw, current)
            raise AssertionError("synthetic string score accepted")
        except ValueError as error:
            diagnostics = candidate.diagnostics_for(error)
        assert any(tuple(error.get("loc", ())) == ("score",)
            for error in diagnostics)
        corrected = deepcopy(value)
        corrected["issue_resolutions"] = [dict(previous_id=number, disposition="retained",
            final_issue=number, source_ids=issue["source_ids"],
            explanation="离线分析者构造：完整保留原问题，修复其他段落的编号类型；不代表模型质量验收。")
            for number, issue in enumerate(candidate.prior_issues(first), 1)]
        _, accepted, journal = candidate.validate(compact(corrected), current, previous_raw=raw)
        correction = candidate.request(current, previous_raw=raw, diagnostics=diagnostics)
        data = strict_json(correction.messages[1].content.split("[UNTRUSTED DATA]\n", 1)[1]
            .rsplit("\n[END UNTRUSTED DATA]", 1)[0])
        assert data["previous_review"] == strict_json(raw)
        assert data["previous_raw_sha256"] == digest(raw)
        assert data["previous_issues"] == candidate.prior_issues(first)
        assert journal["previous_raw"] == raw
        full_sources = request_data(current)
        source_text = full_sources.pop("deterministic_source_facts")
        assert all(data[key] == source for key, source in full_sources.items())
        assert correction.messages[2].content == ("[UNTRUSTED deterministic_source_facts]\n"
            + source_text + "\n[END UNTRUSTED deterministic_source_facts]")
        shapes.append(dict(case_id=case["id"], report_sha256=digest(current.source.report),
            source_roots=len(roots), first_raw_sha256=digest(raw), first_raw_chars=len(raw),
            max_explanation_chars=max(len(row["explanation"]) for row in value["reviews"]),
            complete_paragraphs_prefixed=prefixed, first_error_diagnostics=diagnostics,
            primary_input_ceiling=measured(candidate.request(current)),
            correction_input_ceiling=measured(correction),
            revision_input_ceiling=measured(candidate.request(current, accepted=accepted)),
            revision_workflow_eligible=accepted.verdict == "needs_revision",
            all_sources_preserved=True, first_values_and_hash_preserved=True,
            original_raw_retained_in_journal=True, first_raw_truncated=False,
            explanations_truncated=False, semantic_approval=False))
        replies.append((raw, compact(corrected)))
    return shapes, replies


def audit(args):
    summary, deterministic, knowledge, cases = load_inputs(args.source_run, args.base_report)
    controls = select_cases(cases)
    reqs = [EvaluationRequest(summary, deterministic, knowledge, c["report"], UTTERANCE) for c in controls]
    inputs = [candidate.NativeBusinessReviewWorkflow.build_inputs(req) for req in reqs]
    blocks = [next(b for b, (_, text) in enumerate(i.source.blocks, 1) if c["target"] in text)
        for c, i in zip(controls, inputs, strict=True)]
    values = [scripted(inputs[0]), scripted(inputs[1], problem_block=blocks[1])]
    shapes = []
    for case, current, value in zip(controls, inputs, values, strict=True):
        payload, _, journal = candidate.validate(compact(value), current)
        shapes.append(dict(case_id=case["id"], report_sha256=digest(current.source.report),
            blocks=len(value["reviews"]), source_roots=len(source_catalog(current)),
            input_ceiling=measured(candidate.request(current)), scripted_verdict=payload.verdict,
            complete_block_inventory=True, semantic_approval=journal["semantic_approval"]))
    first = deepcopy(values[0])
    first["extra"] = "首评所有多余原值保留，不能把接口错误变成新事实。"
    row = next(row for row in first["reviews"] if row["kind"] == "content")
    row["issues"] = dict(source_ids=[], severity="medium", category="fact_error", explanation="合成首评误报", suggested_correction="合成意见")
    corrected = deepcopy(values[0])
    corrected["issue_resolutions"] = [dict(previous_id=1, disposition="withdrawn", final_issue=None,
        source_ids=[next(n for n, e in source_catalog(inputs[0]).items() if e.key == "source/deterministic")], explanation="分析者构造的撤销见证，不证明真实来源否定该意见。")]
    raw = compact(first)
    _, _, correction_journal = candidate.validate(compact(corrected), inputs[0], previous_raw=raw)
    assert correction_journal["previous_raw"] == raw
    assert correction_journal["previous_issues"][0]["issue"] == row["issues"]
    correction_size = measured(candidate.request(inputs[0], previous_raw=raw, diagnostics=[dict(code="synthetic_bad_issue_container")]))
    oversized = deepcopy(first)
    oversized["unbounded_first_value"] = "原始意见不能截断以绕过预算" * 30000
    try:
        candidate.request(inputs[0], previous_raw=compact(oversized))
        raise AssertionError("oversized first result admitted")
    except ValueError as error:
        assert str(error) == "bounded_correction_request_budget_exceeded", str(error)
    # A false explanation with valid IDs can pass: explicitly record this limit.
    false = deepcopy(values[0])
    next(r for r in false["reviews"] if r["kind"] == "content")["explanation"] = "合成错误解释：这些比赛证明未来一定一直如此。"
    candidate.validate(compact(false), inputs[0])

    def run(replies):
        requests = []
        def send(request):
            requests.append(request)
            response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
                finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
            return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        flow = candidate.NativeBusinessReviewWorkflow(send)
        result = flow.evaluate(reqs[1])
        revised = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report,
            reqs[1].knowledge, reqs[1].report, result))
        final = flow.evaluate(replace(reqs[1], report=revised.report))
        assert final.verdict.value == "pass"
        return [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    normal = run([compact(values[1]), reqs[0].report, compact(values[0])])
    broken_negative, broken_positive = deepcopy(values[1]), deepcopy(values[0])
    broken_negative["extra"] = "需完整重评"
    broken_positive["extra"] = "需完整重评"
    second_negative = deepcopy(values[1])
    selected_row = next(r for r in values[1]["reviews"] if r["issues"])
    second_negative["issue_resolutions"] = [dict(previous_id=1, disposition="retained", final_issue=1,
        source_ids=selected_row["issues"][0]["source_ids"], explanation="完整保留同一原问题；合成状态机见证。")]
    five = run([compact(broken_negative), compact(second_negative), reqs[0].report,
        compact(broken_positive), compact(values[0])])
    long_shapes, long_replies = long_explanation_stress(args, inputs)
    long_five = run([*long_replies[1], reqs[0].report, *long_replies[0]])
    long_reservation = sum(row["input_ceiling"] + row["output_reservation"] for row in long_five)
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, synthetic_only=True,
        semantic_approval=False, production_admitted=False, full_sources_preserved=True,
        shapes=shapes, first_error_correction_input=correction_size,
        malformed_first_issue_preserved=True, oversized_first_stops_before_provider=True,
        normal_revision_path=normal, worst_case_revision_path=five,
        full_reservation=sum(r["input_ceiling"] + r["output_reservation"] for r in five), total_limit=401920,
        long_explanation_stress=dict(author="analyst_authored_offline_composition",
            source_fixture="scripts.check_golden_computed_partition_review.prepared",
            legacy_controls_used_for_size_only=True, model_response_replay=False,
            provider_calls=0, semantic_approval=False, shapes=long_shapes,
            full_five_call_path=long_five, full_reservation=long_reservation,
            total_limit=401920, full_reservation_exceeds_limit=long_reservation > 401920,
            admission="actual_usage_plus_next_reservation_no_completion_guarantee"),
        valid_source_ids_with_false_explanation_can_pass=True,
        limitations=["synthetic_block_inventory_does_not_prove_semantic_coverage",
            "source_identity_is_not_entailment", "old_positive_unique_cohort_oracle_disputed",
            "real_quality_and_latency_unmeasured", "no_production_registration"])


def observed_witnesses():
    """Current report fixtures, without projecting any historical model result."""
    from scripts.run_golden_native_review import prepare
    cases, reqs = zip(*(prepare(index) for index in range(1, 6)), strict=True)
    inputs = [candidate.NativeBusinessReviewWorkflow.build_inputs(req) for req in reqs]
    values, shapes = [], []
    for case, current in zip(cases, inputs, strict=True):
        value = scripted(current, problem_block=case["target_block"] if case["expected_report"] == "reject" else None)
        candidate.validate(compact(value), current)
        values.append(value)
        long = deepcopy(value)
        prefixed = []
        for row in long["reviews"]:
            if row["kind"] == "content":
                expanded = "原段：" + current.source.blocks[row["block"] - 1][1] + "；" + row["explanation"]
                if len(expanded) <= 700:
                    row["explanation"] = expanded
                    prefixed.append(row["block"])
        broken = deepcopy(long)
        broken["score"] = str(broken["score"])
        raw = compact(broken)
        try:
            candidate.validate(raw, current)
            raise AssertionError("string score accepted")
        except ValueError as error:
            diagnostics = candidate.diagnostics_for(error)
        correction = candidate.request(current, previous_raw=raw, diagnostics=diagnostics)
        _, wire, _ = candidate.validate(compact(long), current)
        shapes.append(dict(case_id=case["id"], report_sha256=digest(current.source.report),
            initial_input=measured(candidate.request(current)),
            long_first_chars=len(raw), long_first_prefixed_blocks=prefixed,
            correction_input=measured(correction), revision_input_shape=measured(candidate.request(current, accepted=wire)),
            revision_eligible=wire.verdict == "needs_revision", analyst_created=True, semantic_approval=False))
    def path(replies):
        requests = []
        def send(request):
            requests.append(request)
            response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
                finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
            return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        flow = candidate.NativeBusinessReviewWorkflow(send)
        initial = flow.evaluate(reqs[1])
        draft = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report,
            reqs[1].knowledge, reqs[1].report, initial))
        final = flow.evaluate(replace(reqs[1], report=draft.report))
        assert final.verdict.value == "pass"
        return [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    normal = path([compact(values[1]), reqs[0].report, compact(values[0])])
    bad_first, bad_final = deepcopy(values[1]), deepcopy(values[0])
    bad_first["score"], bad_final["score"] = "70", "95"
    corrected = deepcopy(values[1])
    previous = candidate.prior_issues(bad_first)[0]
    corrected["issue_resolutions"] = [dict(previous_id=1, disposition="retained", final_issue=1,
        source_ids=previous["source_ids"], explanation="合成首评真实保留同一问题，仅验证状态流。")]
    five = path([compact(bad_first), compact(corrected), reqs[0].report, compact(bad_final), compact(values[0])])
    return dict(author="analyst_scripted_responses", provider_calls=0, semantic_approval=False,
        all_source_reports_intact=True, shapes=shapes, normal_revision_path=normal, maximum_call_path=five,
        full_output_reservation=sum(r["input_ceiling"] + r["output_reservation"] for r in five),
        admission="actual_usage_plus_next_reservation_no_arbitrary_completion_guarantee")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("data/runs/golden_slice/golden_20260910_compact_1cd694d"))
    parser.add_argument("--base-report", type=Path, default=Path("data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--observed-controls", action="store_true")
    args = parser.parse_args()
    result = audit(args)
    if args.observed_controls:
        result["observed_controls"] = observed_witnesses()
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))


if __name__ == "__main__":
    main()
