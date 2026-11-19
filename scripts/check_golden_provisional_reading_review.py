"""Whole-body, unmodified failure replay and five-call offline witnesses.

All final responses here are explicitly analyst-authored fixtures. They prove
contract reachability, never model quality; no live adapter imports this file.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_provisional_reading_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.check_golden_meaning_first_review import fixtures, measured
from scripts.check_golden_grounded_reading_review import complete_fixture
from scripts.check_golden_typed_review import rebind, issue
from scripts.audit_golden_meaning_first_result import audit as audit_meaning
from scripts.audit_golden_grounded_reading_result import audit as audit_grounded


def whole_body_fixture(original):
    value = complete_fixture(original)
    for audit in value["audits"]:
        for row in audit["claims"]:
            ref = row["quote_ref"]
            if ref["block"] in (6, 11, 21):
                row["quote_ref"] = dict(block=ref["block"])
            elif ref["block"] == 3:
                if ref["head"].startswith("近 5"): ref["tail"] += "。"
                elif ref["head"].startswith(("输局与赢局", "混合样本")): ref["tail"] += "；"
            elif ref["block"] == 14 and ref["head"].startswith("输局中艾尼维亚"):
                ref["tail"] += "。"
    return value


def audit(args):
    controls, reqs, inputs, values, old_readings = fixtures(args)
    values[0] = whole_body_fixture(values[0])
    values[1] = rebind(values[0], inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    target = inputs[1].source.reference(controls[1]["target"])
    row = next(c for a in values[1]["audits"] for c in a["claims"] if c["quote_ref"] == target)
    row.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="该独立断言声称未来必然如此，前文四场样本限定不能证明它。")
    values[1]["audits"][1]["claims"].append(dict(quote_ref=inputs[1].source.reference("样本只有四场。"),
        decision="direct_supported", evidence_refs=[7, 9, 10, 11], comparisons=[], summaries=[],
        explanation="前文中单子样本有四场，但该事实不能证明未来必然结论。"))
    values[1].update(score=70, verdict="needs_revision", issues=[issue(inputs[1], target["block"])])
    readings = [{k: r[k] for k in ("readings", "issues")} for r in old_readings]
    shapes = []
    for control, current, value, reading in zip(controls, inputs, values, readings, strict=True):
        state = candidate.prepare(compact(reading), current)
        result, journal = candidate.apply(state, compact(value), inputs=current)
        shapes.append(dict(case_id=control["id"], report_sha256=control["report_sha256"],
            first=measured(candidate.first_request(current)), second=measured(candidate.second_request(state)),
            scripted_verdict=result.verdict, required_body_blocks=journal["required_body_blocks"],
            protected_spans=len(journal["source_coverage"])))
    history, replays = [], []
    for directory, audit_fn in ((args.meaning_run, audit_meaning), (args.grounded_run, audit_grounded)):
        historical = audit_fn(directory)
        original = strict_json((directory / "contextual_01/response-001.json").read_text(encoding="utf-8"))["content"]
        replay = candidate.prepare(original, inputs[0])
        corrected = deepcopy(values[0])
        old_issues = strict_json(replay.value_json)["issues"]
        if old_issues:
            assert len(old_issues) == 1
            corrected["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[], sources=[
                dict(key="request/utterance", kind="user_request", path=[]),
                dict(key="generation/projection", kind="generation_projection", path=["player", "riot_id"])],
                explanation="用户任务是ShowMaker观摩，资料玩家为DK ShowMaker#KR1；不能从条件建议把观摩对象换成阅读者，故撤销误报。")]
        result, journal = candidate.apply(replay, compact(corrected), inputs=inputs[0])
        assert journal["first_raw"] == original
        assert len(journal["resolved_issues"]) == len(old_issues)
        assert historical == audit_fn(directory)
        history.append(historical)
        replays.append(dict(run_id=directory.name, first_raw_sha256=journal["first_raw_sha256"],
            diagnostics=list(replay.diagnostics), original_issues=len(old_issues),
            next_input_ceiling=measured(candidate.second_request(replay)), scripted_verdict=result.verdict,
            original_values_preserved=True, historical_result_remains_failed=True))
    replies = [compact(readings[1]), compact(values[1]), reqs[0].report, compact(readings[0]), compact(values[0])]
    requests = []
    def send(request):
        requests.append(request)
        response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
            finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
        return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    flow = candidate.ProvisionalReadingWorkflow(send)
    initial = flow.evaluate(reqs[1])
    revised = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report, reqs[1].knowledge, reqs[1].report, initial))
    final = flow.evaluate(replace(reqs[1], report=revised.report))
    assert final.verdict.value == "pass" and flow.calls == 5
    phases = [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, synthetic_only=True, semantic_approval=False,
        shapes=shapes, original_replays=replays, historical_audits=history,
        full_scripted_path=dict(phases=phases, all_inputs_within_limit=all(p["input_ceiling"] <= 63936 for p in phases),
            conservative_input_plus_full_output=sum(p["input_ceiling"] + p["output_reservation"] for p in phases),
            limit=401920, admission="actual_usage_plus_next_reservation", live_time_verified=False),
        limitations=["coverage_is_not_semantic_correctness", "wrong_sample_can_still_be_structurally_valid",
            "future_model_format_and_growth_unverified"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "meaning-run", "grounded-run", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for directory in (args.meaning_run, args.grounded_run):
        if args.output.resolve().is_relative_to(directory.resolve()):
            raise ValueError("provisional_offline_output_inside_history")
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: v for k, v in result.items() if k != "historical_audits"}))


if __name__ == "__main__": main()
