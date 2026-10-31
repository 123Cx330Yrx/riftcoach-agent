"""Offline comparison-contract witnesses and full historical request sizing."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from app.evaluation import golden_comparison_reassessment as candidate
from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_contextual_requests import revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.check_golden_reassessment_feasibility import measured, v10_projection
from scripts.check_golden_decision_readiness import project_for_size
from scripts.check_golden_contextual_readiness import measurement_state
from scripts.run_golden_contextual_review import select_cases


def audit(source_run, base_report, case_dir, history):
    summary, source, knowledge, cases = load_inputs(source_run, base_report)
    paths = [case_dir / name for name in ("input.json", "response-001.json", "response-002.json", "result.json")]
    frozen = {p: p.read_bytes() for p in paths}
    report = strict_json(frozen[paths[0]])["report"]
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    first = strict_json(frozen[paths[1]])["content"]
    state = full.prepare(first, inputs)
    second = strict_json(strict_json(frozen[paths[2]])["content"])
    projection = v10_projection(strict_json(first), second, inputs)
    for a in projection["audits"]:
        for c in a["claims"]:
            c["comparisons"] = []
    target = projection["audits"][1]["claims"][6]
    evidence = candidate.catalog(inputs)
    mixed = evidence["cohorts"]["selected"]
    target.update(comparisons=[dict(cohort="selected", metric=m, operand_refs=sorted(mixed["wins"] + mixed["losses"])) for m in ("gold_per_min", "damage_per_min")],
        evidence_refs=sorted(mixed["wins"] + mixed["losses"]))
    result, journal = candidate.apply(state, compact(projection), inputs=inputs)
    assert "5场" in target["explanation"]
    wrong_selector = dict(structural_verdict=result.verdict, wrong_explanation=target["explanation"],
        semantic_approval=journal["semantic_approval"],
        disposition="wrong_cohort_selection_remains_a_semantic_failure_not_automatically_detected")
    for row in target["comparisons"]:
        row["cohort"] = "MIDDLE"
    try:
        candidate.apply(state, compact(projection), inputs=inputs)
    except ValueError as error:
        wrong_operands = str(error)
    else:
        raise AssertionError("mixed_operands_must_be_rejected")
    mid = evidence["cohorts"]["MIDDLE"]
    for row in target["comparisons"]:
        row["operand_refs"] = sorted(mid["wins"] + mid["losses"])
    target.update(evidence_refs=sorted(mid["wins"] + mid["losses"]), scope_source={"block": 3},
        explanation="前文限定所选四场中单的胜负比较；该组经济和伤害的每一赢局均高于每一输局，仅支持本样本观察，不外推长期。")
    corrected, corrected_journal = candidate.apply(state, compact(projection), inputs=inputs)
    revision_size = measured(revision_request(inputs, corrected, FULL_CONTEXT_RULE,
        comparison_review=corrected_journal["comparison_bindings"]))
    frozen_shapes = []
    for case in select_cases(cases):
        target_inputs = build_inputs(EvaluationRequest(summary, source, knowledge, case["report"], UTTERANCE))
        value = strict_json(first)
        value.update(source_digest=target_inputs.source.source_digest,
            reviewed_blocks=list(range(1, len(target_inputs.source.blocks) + 1)),
            heading_reviews=[dict(block_id=i, kind="navigation")
                for i, (_, text) in enumerate(target_inputs.source.blocks, 1) if re.match(r"^#{1,6}\s", text)])
        substitutions = []
        for audit_row in value["audits"]:
            for claim in audit_row["claims"]:
                for field in ("quote_ref", "scope_source"):
                    if not claim.get(field): continue
                    text = inputs.source.resolve(claim[field])
                    try: claim[field] = target_inputs.source.reference(text)
                    except ValueError:
                        claim[field] = target_inputs.source.reference(case["target"])
                        substitutions.append(dict(field=field, before=text, after=case["target"]))
        frozen_shapes.append(dict(case_id=case["id"], projection_only=True,
            substitutions=substitutions,
            second=measured(candidate.build_request(full.prepare(compact(value), target_inputs)))))
    shapes = []
    for item in strict_json(history.read_text(encoding="utf-8"))["historical_shapes"]:
        path = Path(item["source"])
        original = path.read_bytes()
        frozen[path] = original
        raw = strict_json(original)["content"]
        old_report = ((path.parent / "revised-report.md").read_text(encoding="utf-8")
            if path.name == "response-004.json"
            else strict_json((path.parent / "input.json").read_text(encoding="utf-8"))["report"])
        request = EvaluationRequest(summary, source, knowledge, old_report, UTTERANCE)
        old_inputs = build_inputs(request)
        projected, assumptions = project_for_size(raw)
        if strict_json(projected)["source_digest"] != old_inputs.source.source_digest:
            _, end = json.JSONDecoder().raw_decode(raw.lstrip())
            rebound = measurement_state(raw.lstrip()[:end], request)
            projected, _ = project_for_size(rebound.raw)
            assumptions["source_index_rebound_for_size_only"] = True
        old_state = full.prepare(projected, old_inputs)
        row = dict(source=str(path), source_sha256=hashlib.sha256(original).hexdigest(),
            projection_only=True, baseline_second=measured(full.build_request(old_state)), **assumptions)
        try:
            row["comparison_second"] = measured(candidate.build_request(old_state))
            row["admitted"] = True
        except ValueError as error:
            row.update(admitted=False, code=str(error))
        shapes.append(row)
    if any(path.read_bytes() != data for path, data in frozen.items()):
        raise ValueError("frozen_evidence_changed")
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0,
        historical_result_changed=False, synthetic_projection_only=True,
        live_qualified=False, semantic_quality_verified=False,
        v10_second_input_ceiling=measured(candidate.build_request(state)),
        synthetic_revision_input_ceiling=revision_size, frozen_shapes=frozen_shapes,
        catalog=evidence, wrong_selector=wrong_selector,
        wrong_operand_binding=wrong_operands,
        manual_positive_projection=dict(structural_verdict=corrected.verdict, semantic_approval=False),
        historical_shapes=shapes, all_historical_shapes_fit=all(r["admitted"] for r in shapes),
        source_hashes={str(p): hashlib.sha256(data).hexdigest() for p, data in frozen.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "case-dir", "history", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source_run, args.base_report, args.case_dir, args.history)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("v10_second_input_ceiling", "wrong_operand_binding",
        "wrong_selector", "all_historical_shapes_fit", "historical_shapes")}))


if __name__ == "__main__":
    main()
