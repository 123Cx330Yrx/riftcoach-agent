"""Offline full-report witnesses for computed partition, not model accuracy."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_partition_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.check_golden_meaning_first_review import fixtures, measured
from scripts.check_golden_provisional_reading_review import whole_body_fixture
from scripts.check_golden_typed_review import rebind, issue


def split(value, blocks, *, final=False):
    result = dict(heading_reviews=[deepcopy(h) for h in value["heading_reviews"] if h["block_id"] in blocks],
        audits=[dict(kind=a["kind"], claims=[deepcopy(c) for c in a["claims"] if c["quote_ref"]["block"] in blocks])
                for a in value["audits"]],
        source_checks=[deepcopy(c) for c in value["source_checks"] if c["quote_ref"]["block"] in blocks],
        issues=[deepcopy(i) for i in value["issues"] if i["quote_ref"]["block"] in blocks])
    for audit in result["audits"]:
        for claim in audit["claims"]:
            for op in claim["comparisons"] + claim["summaries"]:
                op.pop("operand_refs")
    for check in result["source_checks"]:
        for ref in check["sources"] + [literal["source"] for literal in check["literals"]]:
            ref.pop("kind")
    if final:
        result.update({k: deepcopy(value[k]) for k in ("issues", "score", "verdict", "summary", "passed_checks")})
        result.update(replacements=[], issue_resolutions=[])
    return result


def prepared(args):
    controls, reqs, inputs, values, _ = fixtures(args)
    values[0] = whole_body_fixture(values[0])
    values[1] = rebind(values[0], inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    ref = inputs[1].source.reference(controls[1]["target"])
    target = next(c for a in values[1]["audits"] for c in a["claims"] if c["quote_ref"] == ref)
    target.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="独立未来断言超出四场中单样本能支持的范围。")
    values[1]["audits"][1]["claims"].append(dict(quote_ref=inputs[1].source.reference("样本只有四场。"),
        decision="direct_supported", evidence_refs=[7, 9, 10, 11], comparisons=[], summaries=[],
        explanation="中单子样本确实四场，不能证明后文未来断言。"))
    values[1].update(score=70, verdict="needs_revision", issues=[issue(inputs[1], ref["block"])])
    batches = [(split(value, candidate.allocation(current)[0]),
                split(value, candidate.allocation(current)[1], final=True))
                for current, value in zip(inputs, values, strict=True)]
    return controls, reqs, inputs, values, batches


def audit(args):
    controls, reqs, inputs, values, batches = prepared(args)
    shapes = []
    for control, current, value, (first, second) in zip(controls, inputs, values, batches, strict=True):
        state = candidate.prepare(compact(first), current)
        result, journal = candidate.apply(state, compact(second), inputs=current)
        # Only operand list ordering is defined by source order in the new wire.
        native = strict_json(journal["native_final"])
        expected = deepcopy(value)
        for audit_row in expected["audits"]:
            # The merger places the first assigned group's unchanged entries
            # before the second group's; relative order within each is kept.
            audit_row["claims"].sort(key=lambda c: c["quote_ref"]["block"] not in candidate.allocation(current)[0])
            for claim in audit_row["claims"]:
                for op in claim["comparisons"] + claim["summaries"]:
                    op["operand_refs"].sort()
        assert native == expected
        shapes.append(dict(case_id=control["id"], report_sha256=digest(current.source.report),
            inputs=[measured(candidate.request(current)), measured(candidate.request(current, state=state))],
            scripted_verdict=result.verdict, complete_body_spans=len(journal["source_coverage"]),
            synthetic_output_chars=[len(compact(first)), len(compact(second))],
            native_final_equal=True, raw_first_preserved=journal["first_raw"] == compact(first)))
    # A broken first block is wholly replaced, without a strict first gate or
    # hiding its original opinion. This is a synthetic stress case, not replay.
    original = deepcopy(batches[0][0])
    selected = original["audits"][1]["claims"][0]
    block = selected["quote_ref"]["block"]
    selected["quote_ref"]["head"] = "错误的超长原始引用" * 10
    selected["extra"] = "保留原值，不能当作报告事实"
    original["audits"][1]["claims"].append(deepcopy(selected))
    old_issue = issue(inputs[0], block)
    old_issue["quote_ref"]["head"] = "错误引用" * 20
    original["issues"].append(old_issue)
    state = candidate.prepare(compact(original), inputs[0])
    final = deepcopy(batches[0][1])
    clean_block = split(values[0], [block])
    final["replacements"] = [dict(block=block, heading_review=None,
        audits=clean_block["audits"], source_checks=clean_block["source_checks"])]
    final["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=[dict(key="request/utterance", path=[])],
        explanation="合成纠错见证：用户任务明确为ShowMaker观摩，原误报无依据；仅证明结构可达。")]
    repaired, journal = candidate.apply(state, compact(final), inputs=inputs[0])
    assert journal["resolved_issues"][0]["before"] == old_issue
    assert journal["provisional_values"] == original
    stress_size = measured(candidate.request(inputs[0], state=state))
    replies = [compact(v) for v in batches[1]] + [reqs[0].report] + [compact(v) for v in batches[0]]
    requests = []
    def send(request):
        requests.append(request)
        response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
            finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
        return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    flow = candidate.ComputedPartitionWorkflow(send)
    initial = flow.evaluate(reqs[1])
    revised = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report,
        reqs[1].knowledge, reqs[1].report, initial))
    final = flow.evaluate(replace(reqs[1], report=revised.report))
    assert final.verdict.value == "pass" and flow.calls == 5
    phases = [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, synthetic_only=True,
        semantic_approval=False, production_admitted=False, shapes=shapes,
        synthetic_error_correction=dict(input_ceiling=stress_size, scripted_verdict=repaired.verdict,
            all_first_values_retained=True, original_issue_explicitly_resolved=True),
        full_scripted_path=dict(phases=phases,
            conservative_input_plus_full_output=sum(p["input_ceiling"] + p["output_reservation"] for p in phases),
            total_limit=401920, admission="actual_usage_plus_next_reservation", live_time_verified=False),
        limitations=["correct_arithmetic_does_not_select_prose_scope", "synthetic_errors_not_actual_new_model_responses",
            "large_provisional_output_can_exceed_second_input_budget", "no_latency_or_real_quality_claim"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("data/runs/golden_slice/golden_20260910_compact_1cd694d"))
    parser.add_argument("--base-report", type=Path, default=Path("data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args)
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))


if __name__ == "__main__":
    main()
