"""Measure complete source requests offline; never call a Provider or relabel a run."""
import argparse
from dataclasses import replace
from pathlib import Path

from app.evaluation import golden_integrated_review as review
from app.evaluation.golden_context_review import ContextEvaluation
from app.evaluation.golden_context_requests import revision_request
from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def budgeted(request):
    # Same token-bearing transformation as CoachBudgetedProvider. Time changes
    # use a shorter example deadline and never relax the per-call limit.
    return replace(request, timeout_s=299, temperature=1.0, top_p=0.95,
        metadata={**request.metadata, "coach_budget_contract": "coach-bounded-review-v2"})


def measure(source_run, base_report, historical_evaluation):
    summary, deterministic, knowledge, cases = load_inputs(source_run, base_report)
    rows = []
    for case in cases:
        inputs = review.ReviewInput.build(EvaluationRequest(summary, deterministic, knowledge, case["report"], UTTERANCE))
        # Every complete source block is selected for SIZE ONLY. This is not a
        # claim discovery implementation and no expected labels enter requests.
        targets = tuple({"block": i} for i in range(1, len(inputs.source.blocks)+1))
        first = budgeted(review.discovery_request(inputs))
        second = budgeted(review.assessment_request(inputs, targets, feedback={
            "errors": [{"codes": ["discovery_block_coverage_mismatch"]}], "omitted_errors": 0}))
        rows.append(dict(case_id=case["id"], source_sha256=inputs.source.source_digest,
            blocks=len(targets), discovery_input_ceiling=size(first), assessment_input_ceiling=size(second)))
    historical = ContextEvaluation.model_validate(review.strict_json(historical_evaluation.read_text(encoding="utf-8")), strict=True)
    case = next(c for c in cases if c["id"] == "stable_defined_before")
    revision = budgeted(revision_request(summary, deterministic, knowledge, case["report"], historical))
    max_first = max(r["discovery_input_ceiling"] for r in rows)
    max_second = max(r["assessment_input_ceiling"] for r in rows)
    total = 2*(max_first+max_second) + size(revision) + 5*32768
    return dict(experiment_id=review.EXPERIMENT_ID, model_calls=0, source_data_unchanged=True,
        cases=rows, revision_historical_shape_input_ceiling=size(revision),
        measured_five_call_token_reservation=total, report_token_limit=401920,
        measured_shapes_fit=total <= 401920, max_calls=5, evaluations=2, max_revisions=1,
        per_call_output_limit=32768, per_call_time_limit_s=300, shared_time_limit_s=900,
        output_profile="high", model_quality="not_evaluated",
        limitation="Measured source-block target shapes and one historical revision; not a bound for arbitrary generated spans, explanations or revised reports. Every actual request is checked. Five 300-second calls are not guaranteed within 900 seconds.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", type=Path, required=True)
    p.add_argument("--base-report", type=Path, required=True)
    p.add_argument("--historical-evaluation", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = measure(args.source_run, args.base_report, args.historical_evaluation)
    if args.output:
        write_new_json(args.output, result)
    print(review.compact(result))


if __name__ == "__main__":
    main()
