"""One explicitly selected observed-report control, with original receipt gates.

Preview is local/read-only. Labels stay in the scorer, never in model input.
This runner does not register a production Coach or publish a report.
"""
import argparse
import hashlib
from pathlib import Path
import re

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs
from scripts.run_golden_integrated_review import observe_report
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/datasets/golden_observed_review_controls_v1.json"


def score_case(case, result):
    """Location/category match is only a development signal, not entailment."""
    flagged = [i for i in result.issues if case["target"] in i["quote"]]
    accepted = result.verdict.value == "pass" and result.score >= 85 and not result.issues
    matched = accepted if case["expected_report"] == "accept" else result.verdict.value != "pass" and bool(flagged)
    return dict(id=case["id"], valid=True, matched=matched,
        verdict=result.verdict.value, score=result.score, expected_report=case["expected_report"],
        target_location_flagged=bool(flagged),
        suggested_category_matched=any(i["category"] in case["expected_categories"] for i in flagged),
        semantic_approval=False)


def prepare(case_index):
    dataset = candidate.strict_json(DATASET.read_text(encoding="utf-8"))
    bindings = dataset["source_bindings"]
    for item in bindings["files"]:
        if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("native_control_source_changed")
    summary, deterministic, knowledge, _ = load_inputs(ROOT / bindings["source_run"], ROOT / bindings["base_report"])
    cases = dataset["cases"]
    if not 1 <= case_index <= len(cases):
        raise ValueError("native_control_case_index_invalid")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("native_control_duplicate_identity")
    for case in cases:
        if digest(case["report"]) != case["report_sha256"] or case["report"].count(case["target"]) != 1:
            raise ValueError("native_control_report_changed")
        if case["expected_report"] not in ("accept", "reject"):
            raise ValueError("native_control_label_invalid")
    case = cases[case_index - 1]
    req = EvaluationRequest(summary, deterministic, knowledge, case["report"], dataset["user_utterance"])
    return case, req


def run(args):
    if args.execute:
        candidate.require_live_qualification()
    case, req = prepare(args.case_index)
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    plan = dict(experiment_id=candidate.EXPERIMENT_ID, selected_cases=[case["id"]],
        manifest_sha256=hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        report_sha256=digest(req.report), input_sha256=digest(inputs.data_json),
        first_input_ceiling=size(candidate.request(inputs)), labels_sent_to_model=False,
        source_scope="complete_observed_report_analyst_development_control_not_holdout",
        max_calls_per_report=5, max_revisions_per_report=1, max_tokens_per_report=401920,
        max_seconds_per_report=900, max_output_per_call=32768, max_seconds_per_call=300,
        reasoning_effort="high", sdk_retries=0, live_status=candidate.LIVE_STATUS,
        live_block_reason=candidate.LIVE_BLOCK_REASON, production_admitted=False,
        manual_between_cases=True, semantic_approval=False)
    if not args.execute:
        print(compact(plan))
        return plan
    if not re.fullmatch(r"native-review-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("native_run_id_invalid")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    case_dir = directory / case["id"]
    case_dir.mkdir()
    write_new_json(case_dir / "input.json", dict(report=req.report, report_sha256=case["report_sha256"]))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    outcome = None
    try:
        settings = load_zhipu_settings(dotenv_values(args.env_file))
        provider = ReceiptedStreamProvider(settings=settings, directory=case_dir / "streams", transport_id=CAPACITY_TRANSPORT_ID)
        outcome = observe_report(provider, case_dir, req, case,
            workflow_factory=candidate.NativeBusinessReviewWorkflow, score_case=score_case)
        print(compact(outcome), flush=True)
        return outcome
    finally:
        saved = case_dir / "result.json"
        accounting = candidate.strict_json(saved.read_text(encoding="utf-8")) if saved.exists() else {}
        receipt = dict(plan, cases=[outcome] if outcome is not None else [],
            reserved_calls=accounting.get("reserved_calls", 0),
            completed_calls=accounting.get("completed_calls", 0),
            input_tokens=accounting.get("input_tokens", 0), output_tokens=accounting.get("output_tokens", 0),
            unknown_usage_calls=accounting.get("unknown_usage_calls", 0), manual_semantic_acceptance=False)
        write_new_json(directory / "receipt.json", receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-index", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
