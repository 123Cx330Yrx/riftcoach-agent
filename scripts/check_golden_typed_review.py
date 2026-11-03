"""Offline complete-report contract witnesses and five-phase request sizing.

Analyst-authored projections are NOT repaired model results. Frozen receipts
stay immutable. No credentials, Provider construction, live runner or labels
in request data. This cannot establish semantic quality or elapsed live time.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import EvaluationRequest, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.check_golden_reassessment_feasibility import measured
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases
from scripts.check_golden_review_source_catalog import REPORT_SHA

RAW_PATH = Path("data/runs/inference_development/source-first-probe-e23c90d-v1/response.json")


def issue(inputs, block):
    return dict(severity="medium", category="unsupported_comparison", quote_ref=dict(block=block),
        evidence="所给数据仅支持当前样本。", explanation="以后和都会将有限样本外推为未来必然。",
        suggested_correction="删除未来必然结论，保留当前四场中单的有限样本观察。")


def ref(key, kind, *path):
    return dict(key=key, kind=kind, path=list(path))


def literal(source, reported, fmt="exact"):
    return dict(source=source, reported=reported, format=fmt, places=None)


def ordinary(quote_ref, sources, literals=(), kind="source_fact"):
    return dict(quote_ref=quote_ref, kind=kind, disposition="supported", sources=sources,
        literals=list(literals), explanation="分析者按完整原始来源构造的离线表示见证；不是模型输出或语义验收。")


def projection(original, inputs):
    """Explicit synthetic edits, recorded via changed_paths in the result."""
    value = deepcopy(original)
    value.update(source_digest=inputs.source.source_digest, source_checks=[], issue_resolutions=[])
    general = value["source_checks"]
    position = ref("source/position", "position_context", "goal_source")
    boundary = ref("legacy/scope:limits", "sample_boundary")
    # Obtain the exact kind from the address catalog; scope:limits is a
    # declaration boundary, not a competition result.
    boundary["kind"] = typed.build_catalog(inputs).get(boundary["key"]).kind
    general.append(ordinary(dict(block=20), [position,
        ref("source/position", "position_context", "training_positions")]))
    knowledge_literals = []
    for n in range(1, 4):
        entry = typed.build_catalog(inputs).resolve(inputs, f"knowledge/K{n}", kind="knowledge")
        for field in ("citation_id", "source_id", "title"):
            knowledge_literals.append(literal(ref(f"knowledge/K{n}", "knowledge", field), entry[field]))
    general.append(ordinary(dict(block=26), [], knowledge_literals))
    general.append(ordinary(dict(block=27), [boundary, ref("source/external_bundle", "external_bundle")], [
        literal(ref("source/official_patch", "official_patch", "patch_version"), "16.17"),
        literal(ref("source/official_patch", "official_patch", "published_at"), "2026-08-25", "date")]))
    general.append(ordinary(dict(block=28), [boundary, ref("source/deterministic", "source_declaration")], kind="boundary"))
    # Keep the whole original mixed paragraph covered while separating static
    # metadata from match counts; ordinary metadata is not a match statistic.
    text = inputs.source.blocks[24][1]
    start, end = text.index("Data Dragon"), text.index("样本仅")
    general.append(ordinary(inputs.source.reference(text[start:end]), [], [
        literal(ref("source/data_dragon", "static_catalog", "version"), "16.17.1")]))
    before = value["audits"][0]["claims"]
    new = []
    for row in before:
        block = row["quote_ref"]["block"]
        if block in (20, 26, 27, 28):
            continue
        if block == 25:
            for part in (text[:start], text[end:]):
                new.append(dict(row, quote_ref=inputs.source.reference(part),
                    evidence_refs=[7, 8, 9, 10, 11, 12, 13],
                    explanation="原始逐局记录及样本边界支持五局计数；不以请求筛选证明实际队列。"))
        else:
            new.append(row)
    value["audits"][0]["claims"] = new
    mid = [7, 9, 10, 11]
    for audit in value["audits"]:
        for row in audit["claims"]:
            row.setdefault("comparisons", [])
            row["summaries"] = []
            block = row["quote_ref"]["block"]
            if block == 21:
                row["summaries"] = [dict(operation=operation, cohort="MIDDLE", metric=metric,
                    operand_refs=mid, reported=reported) for operation, metric, reported in (
                        ("median", "cs_per_min", "8.8"), ("mean", "deaths_before_15", "1.5"))]
            if block == 10:
                row.update(evidence_refs=mid, scope_source=dict(block=3),
                    explanation="本句延续第三段明确的四场中单经济和伤害比较；不能用五局混合样本替代。",
                    comparisons=[dict(cohort="MIDDLE", metric=metric, operand_refs=mid)
                        for metric in ("gold_per_min", "damage_per_min")])
    return value


def rebind(value, source, target, old_target, new_target):
    """Explicit fixture migration by exact text, never assumed block offsets."""
    value = deepcopy(value)
    value.update(source_digest=target.source.source_digest,
        reviewed_blocks=list(range(1, len(target.source.blocks) + 1)),
        heading_reviews=[dict(block_id=i, kind="navigation") for i, (_, text) in enumerate(target.source.blocks, 1) if text.startswith("#")])
    def walk(node):
        if isinstance(node, list):
            for item in node: walk(item)
        elif isinstance(node, dict):
            for key, item in node.items():
                if key in ("quote_ref", "scope_source") and item:
                    text = source.source.resolve(item)
                    node[key] = target.source.reference(new_target if text == old_target else text)
                else: walk(item)
    walk(value)
    return value


def changed_paths(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        return [p for key in sorted(before.keys() | after.keys()) for p in (
            changed_paths(before[key], after[key], path + "/" + key) if key in before and key in after
            else [path + "/" + key])]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [p for i, (a, b) in enumerate(zip(before, after)) for p in changed_paths(a, b, path + f"/{i}")]
    return [] if before == after else [path]


def audit(args):
    summary, source, knowledge, cases = load_inputs(args.source_run, args.base_report)
    controls = select_cases(cases)
    reqs = [EvaluationRequest(summary, source, knowledge, c["report"], UTTERANCE) for c in controls]
    inputs = [typed.TypedReviewWorkflow.build_inputs(r) for r in reqs]
    if digest(inputs[0].source.report) != REPORT_SHA:
        raise ValueError("typed_frozen_report_changed")
    raw_bytes = RAW_PATH.read_bytes()
    original = strict_json(strict_json(raw_bytes)["content"])
    positive = projection(original, inputs[0])
    negative = rebind(positive, inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    target_ref = inputs[1].source.reference(controls[1]["target"])
    target = next(c for c in negative["audits"][1]["claims"] if c["quote_ref"] == target_ref)
    target.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="该句断言以后也都会如此；前段样本限定不能取消这个独立未来断言。")
    negative["audits"][1]["claims"].append(dict(quote_ref=inputs[1].source.reference("样本只有四场。"),
        decision="direct_supported", evidence_refs=[7, 9, 10, 11], comparisons=[], summaries=[],
        explanation="本段四场指前文中单子样本，记录有四场中单；该限定不能证明后续未来断言。"))
    negative.update(verdict="needs_revision", score=70, issues=[issue(inputs[1], target_ref["block"])])
    values = [positive, negative]
    # Historical output is intentionally not eligible under the new contract.
    try: typed.TypedReview.model_validate(original, strict=True)
    except ValueError as error: old_errors = [dict(location=list(e["loc"]), code=e["type"]) for e in error.errors(include_input=False, include_context=False)]
    else: raise ValueError("historical_output_unexpectedly_accepted")
    results, journals, shapes = [], [], []
    for control, current, value in zip(controls, inputs, values, strict=True):
        before = rebind(original, inputs[0], current, controls[0]["target"], control["target"])
        before.update(source_checks=[])
        state = typed.prepare(compact(before), current)
        result, journal = typed.apply(state, compact(value), inputs=current)
        results.append(result)
        journals.append(journal)
        shapes.append(dict(case_id=control["id"], report_sha256=digest(current.source.report),
            script_expected_verdict=value["verdict"], structural_verdict=result.verdict,
            first=measured(typed.request(current)), second=measured(typed.request(current, state=state)),
            source_checks=len(value["source_checks"]), summaries=journal["summaries"],
            coverage=journal["source_coverage"], synthetic_changed_paths=changed_paths(original, value)))
    # This intentionally wrong interpretation still passes structural checks.
    wrong = deepcopy(values[0])
    row = next(c for c in wrong["audits"][1]["claims"] if c["quote_ref"]["block"] == 10)
    historical = next(c for c in original["audits"][1]["claims"] if c["quote_ref"]["block"] == 10)
    row.update({k: historical[k] for k in ("comparisons", "evidence_refs", "explanation")})
    bad_result, _ = typed.apply(typed.prepare(compact(values[0]), inputs[0]), compact(wrong), inputs=inputs[0])

    # Script the actual whole-report revision+recheck data path. Every reply is
    # synthetic; fake usage is not charged, estimated or called real usage.
    replies = [compact(values[1]), compact(values[1]), reqs[0].report, compact(values[0]), compact(values[0])]
    requests = []
    def send(request):
        requests.append(request)
        response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
            finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
        sha = hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
        return Exchange(request, response, sha)
    flow = typed.TypedReviewWorkflow(send)
    evaluation = flow.evaluate(reqs[1])
    revised = flow.revise(RevisionRequest(summary, source, knowledge, reqs[1].report, evaluation))
    final = flow.evaluate(replace(reqs[1], report=revised.report))
    if final.verdict.value != "pass" or len(requests) != 5:
        raise ValueError("typed_scripted_full_path_incomplete")
    phases = [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens,
        request_sha256=hashlib.sha256(validate_request(r, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()) for r in requests]
    old_audit = strict_json(Path("data/evaluation/results/golden_source_first_result_e23c90d.json").read_text(encoding="utf-8"))
    for name, expected in old_audit["source_hashes"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected: raise ValueError("historical_receipt_changed")
    if RAW_PATH.read_bytes() != raw_bytes: raise ValueError("historical_response_changed")
    return dict(experiment=typed.EXPERIMENT_ID, evidence_kind="analyst_authored_whole_report_contract_witnesses",
        provider_calls=0, labels_sent_to_model=False, semantic_approval=False, live_qualified=False,
        historical_results_changed=False, historical_schema_errors=old_errors, shapes=shapes,
        wrong_cohort_still_structurally_passes=bad_result.verdict == "pass",
        scripted_full_revision_path=dict(exchanges=5, source_preserved=True, phases=phases,
            all_input_ceilings_within_limit=all(p["input_ceiling"] <= 63936 for p in phases),
            max_output_reservation_sum=sum(p["output_reservation"] for p in phases),
            conservative_input_plus_full_output=sum(p["input_ceiling"]+p["output_reservation"] for p in phases),
            report_token_limit=401920, admission="actual_settled_usage_plus_next_reservation",
            wall_time_limit_s=900, live_elapsed_verified=False, future_output_size_guaranteed=False),
        source_hashes=old_audit["source_hashes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("provider_calls", "semantic_approval", "wrong_cohort_still_structurally_passes", "scripted_full_revision_path")}))


if __name__ == "__main__": main()
