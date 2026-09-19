"""Offline full-request measurement and an explicit adverse semantic projection.

No Provider is constructed. Every modification below is a synthetic witness;
the historical response and failure receipt are never repaired or regraded.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from app.evaluation import golden_reassessment_feasibility as candidate
from app.evaluation import golden_contextual_first_wire as first
from app.evaluation.golden_contextual_requests import revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases
from scripts.check_golden_decision_readiness import project_for_size
from scripts.check_golden_contextual_readiness import measurement_state


def v10_projection(before, patch, inputs):
    """Explicitly constructed demonstration, never an automatic repair path."""
    value = deepcopy(before)
    claims = [c for a in value["audits"] for c in a["claims"]]
    for update in patch["claim_updates"]:
        row = claims[int(update["target_id"][1:]) - 1]
        row.update({k: v for k, v in update.items() if k != "target_id"})
    text = inputs.source.blocks[2][1]
    cuts = (0, text.index("混合样本"), text.index("前 15 分钟死亡"), len(text))
    for row, start, end in zip(claims[3:6], cuts[:-1], cuts[1:], strict=True):
        row["quote_ref"] = inputs.source.reference(text[start:end])
        if row["decision"].startswith("sample_"):
            row["scope_source"] = {"block": 3}
    value["issue_resolutions"] = []
    return value


def measured(request):
    issued = replace(request, metadata={**request.metadata,
        "coach_budget_contract": "coach-bounded-review-v2"})
    return size(issued)


def audit(source_run, base_report, case_dir, history):
    summary, source, knowledge, cases = load_inputs(source_run, base_report)
    paths = [case_dir / name for name in ("input.json", "response-001.json", "response-002.json", "result.json")]
    originals = {p: p.read_bytes() for p in paths}
    report = strict_json(originals[paths[0]])["report"]
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    raw = strict_json(originals[paths[1]])["content"]
    before = strict_json(raw)
    patch = strict_json(strict_json(originals[paths[2]])["content"])
    state = candidate.prepare(raw, inputs)
    projection = v10_projection(before, patch, inputs)
    accepted, journal = candidate.apply(state, compact(projection), inputs=inputs)
    wrong = accepted.audits[1].claims[6]
    assert "5场" in wrong.explanation and wrong.quote == "经济和伤害是较稳定的差异项。"
    result = dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0,
        historical_result_changed=False, synthetic_projection_only=True,
        live_qualified=False, semantic_quality_verified=False,
        whole_block_strategy=dict(blocks=len(inputs.source.blocks),
            headings=len(before["heading_reviews"]),
            multi_decision_block=3,
            decisions=[c["decision"] for c in before["audits"][1]["claims"][:3]],
            disposition="one_decision_per_block_is_insufficient_for_mixed_assertions"),
        full_reassessment=dict(input_ceiling=measured(candidate.build_request(state)),
            old_claims=sum(len(a["claims"]) for a in before["audits"]),
            final_claims=sum(len(a.claims) for a in accepted.audits),
            old_source_ranges_covered=len(journal["source_coverage"])),
        semantic_counterexample=dict(structural_verdict=accepted.verdict,
            target_quote=wrong.quote, wrong_explanation=wrong.explanation,
            reason="four_mid_comparison_was_replaced_with_five_mixed_role_games",
            expected_disposition="reject_semantic_acceptance_even_if_structural_pass"),
        frozen_requests=[])
    # Both report shapes: input construction is real, every reused first-review
    # label is a synthetic sizing assumption, not a new evaluation response.
    for case in select_cases(cases):
        target_inputs = build_inputs(EvaluationRequest(summary, source, knowledge, case["report"], UTTERANCE))
        shape = deepcopy(before)
        shape["source_digest"] = target_inputs.source.source_digest
        shape["reviewed_blocks"] = list(range(1, len(target_inputs.source.blocks) + 1))
        shape["heading_reviews"] = [dict(block_id=i, kind="navigation")
            for i, (_, text) in enumerate(target_inputs.source.blocks, 1)
            if re.match(r"^#{1,6}\s", text)]
        remapped = []
        for audit in shape["audits"]:
            for row in audit["claims"]:
                for field in ("quote_ref", "scope_source"):
                    if not row.get(field):
                        continue
                    old_text = inputs.source.resolve(row[field])
                    try:
                        row[field] = target_inputs.source.reference(old_text)
                    except ValueError:
                        # Controls intentionally differ in target/heading. This
                        # explicitly labelled substitution is for sizing only.
                        row[field] = target_inputs.source.reference(case["target"])
                        remapped.append(dict(field=field, before=old_text, after=case["target"]))
        shape_state = candidate.prepare(compact(shape), target_inputs)
        result["frozen_requests"].append(dict(case_id=case["id"], projection_only=True,
            source_substitutions_for_size=remapped,
            first=measured(first.first_request(target_inputs)),
            second=measured(candidate.build_request(shape_state))))
    # Final review object is solely used to measure a full revision request.
    result["synthetic_revision_input_ceiling"] = measured(revision_request(inputs, accepted, FULL_CONTEXT_RULE))
    historical_shapes = []
    for item in strict_json(history.read_text(encoding="utf-8"))["historical_shapes"]:
        path = Path(item["source"])
        original = path.read_bytes()
        old_raw = strict_json(original)["content"]
        old_report = ((path.parent / "revised-report.md").read_text(encoding="utf-8")
            if path.name == "response-004.json"
            else strict_json((path.parent / "input.json").read_text(encoding="utf-8"))["report"])
        evaluation_request = EvaluationRequest(summary, source, knowledge, old_report, UTTERANCE)
        old_inputs = build_inputs(evaluation_request)
        projection_raw, assumptions = project_for_size(old_raw)
        if strict_json(projection_raw)["source_digest"] != old_inputs.source.source_digest:
            _, end = json.JSONDecoder().raw_decode(old_raw.lstrip())
            rebound = measurement_state(old_raw.lstrip()[:end], evaluation_request)
            projection_raw, _ = project_for_size(rebound.raw)
            assumptions["source_index_rebound_for_size_only"] = True
        projected_state = candidate.prepare(projection_raw, old_inputs)
        historical_shapes.append(dict(source=str(path), source_sha256=hashlib.sha256(original).hexdigest(),
            projection_only=True, phase="recheck" if path.name == "response-004.json" else "initial",
            first=measured(first.first_request(old_inputs)),
            second=measured(candidate.build_request(projected_state)), **assumptions))
        if path.read_bytes() != original:
            raise ValueError("frozen_evidence_changed")
    result["historical_shapes"] = historical_shapes
    # A schema-permitted, large first response must be refused before another
    # request if its complete state cannot fit. No truncation of state allowed.
    large = deepcopy(before)
    for a in large["audits"]:
        row = deepcopy(a["claims"][0])
        row["explanation"] = "完整说明" * 125
        a["claims"] = [deepcopy(row) for _ in range(24)]
    large_state = candidate.prepare(compact(large), inputs)
    try:
        candidate.build_request(large_state)
    except ValueError as error:
        result["large_state_preflight"] = dict(rejected=True, code=str(error),
            first_claims=48, explanation_chars_per_claim=500)
    else:
        result["large_state_preflight"] = dict(rejected=False)
    result["budget_policy"] = "actual_settled_usage_plus_next_request_reservation; no_completion_guarantee"
    result["source_hashes"] = {str(p): hashlib.sha256(data).hexdigest() for p, data in originals.items()}
    if any(p.read_bytes() != data for p, data in originals.items()):
        raise ValueError("frozen_evidence_changed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "case-dir", "history", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    value = audit(args.source_run, args.base_report, args.case_dir, args.history)
    write_new_json(args.output, value)
    print(compact(value))


if __name__ == "__main__":
    main()
