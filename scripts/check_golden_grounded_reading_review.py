"""Offline contract/replay evidence, never a new accepted model result."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_grounded_reading_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.check_golden_meaning_first_review import fixtures, measured
from scripts.check_golden_typed_review import rebind, issue
from scripts.audit_golden_meaning_first_result import audit as audit_history


def complete_fixture(original):
    """Analyst-authored final response covers the real first reading's spans.

    The earlier scripted fixture used shorter quotes than the real response.
    Expand those to their actual assertions and bind added summary operations.
    This changes no model output or frozen report and is never a live adapter.
    """
    value = deepcopy(original)
    for row in value["audits"][0]["claims"]:
        block = row["quote_ref"]["block"]
        if block == 5:
            row["quote_ref"] = dict(block=5)
            row["scope_source"] = dict(block=3, head="中单 4 局 2 胜")
            row["summaries"] = [dict(operation="mean", cohort="MIDDLE", metric=metric,
                operand_refs=[7, 9, 10, 11], reported=reported)
                for metric, reported in (("cs_per_min", "8.91"), ("gold_per_min", "469"))]
        if block == 21:
            row["quote_ref"]["head"] = "若选择中单"
    for row in value["audits"][1]["claims"]:
        ref = row["quote_ref"]
        if ref["block"] == 3:
            head = ref["head"]
            if head.startswith("近 5"):
                ref["tail"] = "两者应分开看"
            elif head.startswith("输局与赢局"):
                ref["tail"] = "仅指本样本，不外推长期"
            elif head.startswith("前 15"):
                ref["tail"] = "样本仅 5 局，以下是观察与假设，不是定论。"
        if ref["block"] == 14:
            ref.update(head="上表为混合位置均值", tail="早期死亡差异过小，不作为分界 [K1]。")
            # All five raw operands plus aggregate/role values used here.
            row["evidence_refs"] = [6, 7, 8, 9, 10, 11, 14, 15, 17, 18, 19, 25]
            row["comparisons"] += [dict(cohort="selected", metric=metric, operand_refs=[7, 11, 8, 9, 10])
                for metric in ("cs_per_min", "deaths_before_15")]
        if ref["block"] == 16:
            row["quote_ref"] = dict(block=16)
    return value


def audit(args):
    controls, reqs, inputs, values, old_readings = fixtures(args)
    values[0] = complete_fixture(values[0])
    values[1] = rebind(values[0], inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    target = inputs[1].source.reference(controls[1]["target"])
    row = next(c for a in values[1]["audits"] for c in a["claims"] if c["quote_ref"] == target)
    row.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="后文明确把样本关系外推为未来必然，前文样本限定不能证明这个断言。")
    values[1].update(score=70, verdict="needs_revision", issues=[issue(inputs[1], target["block"])])
    readings = [{k: r[k] for k in ("readings", "issues")} for r in old_readings]
    shapes = []
    for control, current, value, reading in zip(controls, inputs, values, readings, strict=True):
        state = candidate.prepare(compact(reading), current)
        result, journal = candidate.apply(state, compact(value), inputs=current)
        shapes.append(dict(case_id=control["id"], report_sha256=control["report_sha256"],
            first=measured(candidate.first_request(current)), second=measured(candidate.second_request(state)),
            scripted_verdict=result.verdict, protected_spans=len(journal["source_coverage"])))
    historical = audit_history(args.failed_run)
    original = strict_json((args.failed_run / "contextual_01/response-001.json").read_text(encoding="utf-8"))["content"]
    replay = candidate.prepare(original, inputs[0], legacy_replay=True)
    corrected = deepcopy(values[0])
    corrected["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[], sources=[
        dict(key="request/utterance", kind="user_request", path=[]),
        dict(key="generation/projection", kind="generation_projection", path=["player", "riot_id"])],
        explanation="用户任务明确是观摩，原始资料玩家为DK ShowMaker#KR1；正文未重复姓名不能证明属于阅读者，撤销首读误报。")]
    result, journal = candidate.apply(replay, compact(corrected), inputs=inputs[0])
    assert journal["first_raw"] == original and len(journal["resolved_issues"]) == len(replay.reading.issues)
    original_replay = dict(historical_run=historical["run_id"], first_raw_sha256=journal["first_raw_sha256"],
        identical_duplicate_occurrences=len(replay.diagnostics), original_issues=len(replay.reading.issues),
        next_input_ceiling=measured(candidate.second_request(replay)), scripted_final_verdict=result.verdict,
        first_wrong_interpretations_preserved=True, old_issue_explicitly_resolved=True,
        scripted_correction_only=True, historical_result_remains_failed=True)
    replies = [compact(readings[1]), compact(values[1]), reqs[0].report, compact(readings[0]), compact(values[0])]
    requests = []
    def send(request):
        requests.append(request)
        response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
            finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
        return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    flow = candidate.GroundedReadingWorkflow(send)
    initial = flow.evaluate(reqs[1])
    revised = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report, reqs[1].knowledge, reqs[1].report, initial))
    final = flow.evaluate(replace(reqs[1], report=revised.report))
    assert final.verdict.value == "pass" and flow.calls == 5
    assert historical == audit_history(args.failed_run)
    phases = [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, synthetic_only=True, semantic_approval=False,
        shapes=shapes, original_replay=original_replay, source_hashes=historical["source_hashes"],
        full_scripted_path=dict(phases=phases, all_inputs_within_limit=all(p["input_ceiling"] <= 63936 for p in phases),
            conservative_input_plus_full_output=sum(p["input_ceiling"] + p["output_reservation"] for p in phases),
            limit=401920, admission="actual_usage_plus_next_reservation", live_time_verified=False),
        unchanged_semantic_limits=["source_and_context_location_is_not_entailment", "wrong_sample_can_still_be_structurally_valid",
            "future_model_format_growth_and_semantic_correction_unverified"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "failed-run", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.failed_run.resolve()):
        raise ValueError("grounded_offline_output_inside_history")
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("shapes", "original_replay", "full_scripted_path")}))


if __name__ == "__main__": main()
