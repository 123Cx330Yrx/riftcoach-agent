"""Measure v1 executable requests; distinguish reservation sums from hard guards.

The original offline-v1 result remains immutable. This audit does not call a
Provider and cannot establish actual usage, latency or semantic correctness.
"""
import argparse
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from scripts.check_golden_bounded_correction import measure


def audit(source_run, base_report, context_pair):
    result = measure(source_run, base_report, context_pair)
    ready = all(row["preparation_passed"] for row in result["historical_state_requests"])
    result.update(experiment="golden-bounded-review-readiness-v1", runtime_implemented=True,
        candidate_adopted=False, conditional_development_readiness=ready,
        original_result="data/evaluation/results/golden_bounded_correction_offline_v1.json",
        decision="eligible_for_conditional_bounded_development_after_same_sha_ci" if ready else "request_preparation_failed",
        actual_enforcement=dict(per_request_input_limit=64000, per_call_output_limit=32768,
            total_actual_tokens=401920, max_calls=5, report_seconds=900,
            before_io="settled_actual_tokens + next_request_input_ceiling + next_output_cap <= 401920",
            after_io="input_usage <= reserved_input_ceiling and output_usage <= output_cap; otherwise stop"),
        proof_tests="tests/test_golden_bounded_workflow.py",
        server_schema_mode="json_object_only; complete schema still in prompt and local validation",
        estimator_changed=False, limits_changed=False,
        completion_guaranteed=False, mandatory_correction=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "context-pair"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=audit(args.source_run,args.base_report,args.context_pair)
    if args.output:
        write_new_json(args.output,result)
    print(compact(result))


if __name__ == "__main__":
    main()
