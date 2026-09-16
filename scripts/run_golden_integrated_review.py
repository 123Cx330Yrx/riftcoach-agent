"""Opt-in integrated whole-report candidate, with at most one revision per report.

Default preview reads frozen inputs only. Real execution requires public checks
for this exact clean SHA. This does not register a new production Coach.
"""
import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
import re

from pydantic import TypeAdapter

from app.evaluation import golden_integrated_review as review
from app.evaluation.golden_integrated_runtime import IntegratedReviewWorkflow, ReceiptedStreamProvider, BudgetedReviewSender
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, RevisionRequest
from app.harness.adapters import _evaluation_payload
from app.providers.models import ChatResponse
from scripts.run_golden_context_controls import load_inputs, UTTERANCE, PAIRS, score
from scripts.run_golden_scope_controls import case_progress
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]


def implementation_identity(*, bounded=False, full_context=False):
    names = ("app/evaluation/golden_integrated_review.py", "app/evaluation/golden_integrated_runtime.py",
        "app/evaluation/golden_context_review.py", "app/evaluation/golden_context_diagnostics.py",
        "app/evaluation/golden_stream_bridge.py", "app/runtime/coach_budget.py",
        "scripts/run_golden_integrated_review.py")
    if bounded or full_context:
        names += ("app/evaluation/golden_bounded_correction.py",
            "app/evaluation/golden_bounded_correction_requests.py",
            "app/evaluation/golden_bounded_workflow.py", "scripts/run_golden_bounded_review.py")
    if full_context:
        names += ("app/evaluation/golden_contextual_correction.py",
            "app/evaluation/golden_contextual_sources.py", "app/evaluation/golden_contextual_validation.py",
            "app/evaluation/golden_contextual_patch_wire.py",
            "app/evaluation/golden_contextual_first_wire.py",
            "app/evaluation/golden_contextual_admission.py",
            "app/evaluation/golden_contextual_requests.py", "app/evaluation/golden_numeric_evidence_v4.py",
            "app/evaluation/golden_contextual_workflow.py", "scripts/run_golden_contextual_review.py",
            "data/evaluation/datasets/golden_contextual_reports_v2.json")
    return {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}


def observe_report(provider, directory, request, case, *, workflow_factory=IntegratedReviewWorkflow):
    sender = BudgetedReviewSender(provider)
    records = []
    def record(phase, exchange):
        ordinal = len(records)+1
        response = TypeAdapter(ChatResponse).dump_json(exchange.response).decode()
        write_new_json(directory/f"response-{ordinal:03d}.json", review.strict_json(response))
        write_new_json(directory/f"request-{ordinal:03d}.json",
            review.strict_json(validate_request(exchange.issued_request, transport_id=CAPACITY_TRANSPORT_ID).decode()))
        item = dict(ordinal=ordinal, phase=phase, request_sha256=exchange.receipt_request_sha256,
            input_tokens=exchange.response.usage.input_tokens, output_tokens=exchange.response.usage.output_tokens)
        records.append(item)
        write_new_json(directory/f"call-{ordinal:03d}.json", item)
        print(review.compact(dict(case_id=case["id"], **item)), flush=True)
    workflow = workflow_factory(sender, record=record)
    outcome = dict(id=case["id"], valid=False, matched=False, revision_attempted=False)
    try:
        initial = workflow.evaluate(request)
        if getattr(workflow, "last_journal", None) is not None:
            write_new_json(directory/"initial-correction-journal.json", workflow.last_journal)
        write_new_json(directory/"initial-evaluation.json", _evaluation_payload(initial))
        initial_score = score(case, initial)
        outcome.update(initial_score, initial_control=initial_score)
        # A wrong initial control verdict stops here; rewriting cannot erase it.
        if not outcome["matched"]:
            outcome["stop_reason"] = "initial_control_mismatch"
            return outcome
        final = initial
        if initial.verdict.value == "needs_revision":
            outcome["revision_attempted"] = True
            revised = workflow.revise(RevisionRequest(request.player_summary, request.deterministic_report,
                request.knowledge, request.report, initial))
            (directory/"revised-report.md").write_text(revised.report, encoding="utf-8")
            final = workflow.evaluate(replace(request, report=revised.report))
            if getattr(workflow, "last_journal", None) is not None:
                write_new_json(directory/"recheck-correction-journal.json", workflow.last_journal)
            write_new_json(directory/"revised-evaluation.json", _evaluation_payload(final))
        outcome.update(final_verdict=final.verdict.value, final_score=final.score,
            automatic_path_pass=final.verdict.value == "pass" and final.score >= 85 and not final.issues,
            manual_semantic_acceptance=False)
        if not outcome["automatic_path_pass"]:
            outcome["stop_reason"] = "revision_recheck_not_passed"
        return outcome
    except Exception as error:
        outcome.update(valid=False, matched=False, stop_reason="protocol_or_execution_failure", error_type=type(error).__name__)
        code = getattr(error, "code", None)
        if code is None and isinstance(error, ValueError):
            code = str(error)
        if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,80}", code):
            outcome["error_code"] = code
        outcome["interrupted"] = provider._calls > len(records)
        if workflow.last_feedback:
            write_new_json(directory/"diagnostics.json", workflow.last_feedback)
        return outcome
    finally:
        outcome.update(attempted_calls=workflow.calls, reserved_calls=provider._calls,
            completed_calls=len(records), input_tokens=sum(r["input_tokens"] for r in records),
            output_tokens=sum(r["output_tokens"] for r in records),
            unknown_usage_calls=max(0, provider._calls-len(records)))
        write_new_json(directory/"result.json", outcome)


def run(args, *, bounded=False, full_context=False):
    if bounded and full_context:
        raise ValueError("review_mode_conflict")
    if full_context and args.execute:
        from app.evaluation.golden_contextual_admission import require_live_qualification
        require_live_qualification()
    first_request = review.discovery_request
    workflow_factory = IntegratedReviewWorkflow
    experiment_id, prefix = review.EXPERIMENT_ID, "integrated-review"
    if bounded:
        from app.evaluation.golden_bounded_workflow import BoundedCorrectionWorkflow, EXPERIMENT_ID
        from app.evaluation.golden_bounded_correction_requests import first_request
        workflow_factory, experiment_id, prefix = BoundedCorrectionWorkflow, EXPERIMENT_ID, "bounded-review"
    summary, deterministic, knowledge, cases = load_inputs(args.source_run, args.base_report)
    selected = [c for c in cases if c["pair"] == PAIRS[args.pair-1]]
    if full_context:
        from app.evaluation.golden_contextual_correction import first_request, EXPERIMENT_ID, STANDARD_ID
        from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
        from scripts.run_golden_contextual_review import select_cases, MANIFEST
        selected = select_cases(cases)
        workflow_factory, experiment_id, prefix = ContextualCorrectionWorkflow, EXPERIMENT_ID, "contextual-review"
    requests = [EvaluationRequest(summary, deterministic, knowledge, c["report"], UTTERANCE) for c in selected]
    discovery_sizes = [size(first_request(workflow_factory.build_inputs(r))) for r in requests]
    plan = dict(experiment_id=experiment_id, implementation=implementation_identity(bounded=bounded, full_context=full_context),
        scope="complete_report_development_candidate_not_production", pair=args.pair,
        selected_cases=[c["id"] for c in selected], discovery_input_ceilings=discovery_sizes,
        report_sha256=[c["report_sha256"] for c in selected], labels_sent_to_model=False,
        max_calls_per_report=5, max_calls=5*len(selected), max_revisions_per_report=1,
        max_tokens_per_report=401920, max_seconds_per_report=900,
        max_output_per_call=32768, max_seconds_per_call=300, reasoning_effort="high", sdk_retries=0,
        stop_policy="stop_pair_on_protocol_transport_or_semantic_failure; manual_review_required_for_acceptance")
    if bounded or full_context:
        plan["first_review_input_ceilings"] = plan.pop("discovery_input_ceilings")
        plan["budget_admission"] = "each_request_reserved_against_remaining_actual_usage_no_completion_guarantee"
    if full_context:
        from app.evaluation.golden_contextual_admission import LIVE_STATUS, LIVE_BLOCK_REASON
        plan.pop("pair")
        plan.update(standard_id=STANDARD_ID, manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            source_case_ids=[c["source_case_id"] for c in selected],
            live_status=LIVE_STATUS, live_block_reason=LIVE_BLOCK_REASON)
    if not args.execute:
        print(review.compact(plan)); return plan
    if not re.fullmatch(prefix+r"-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("integrated_run_id_invalid")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root/args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory/"plan.json", plan)
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    rows, started = [], []
    try:
        settings = load_zhipu_settings(dotenv_values(args.env_file))
        for case, request in zip(selected, requests):
            case_dir = directory/case["id"]
            case_dir.mkdir()
            write_new_json(case_dir/"input.json", dict(report=request.report, report_sha256=case["report_sha256"]))
            provider = ReceiptedStreamProvider(settings=settings, directory=case_dir/"streams", transport_id=CAPACITY_TRANSPORT_ID)
            started.append(case["id"])
            result = observe_report(provider, case_dir, request, case, workflow_factory=workflow_factory)
            rows.append(result)
            print(review.compact(result), flush=True)
            if result.get("stop_reason"):
                break
    finally:
        # Include accounting saved in observe_report's finally even when an
        # interrupt prevents its return. Such a case is not a finalized result.
        accounting = [review.strict_json((directory/c/"result.json").read_text(encoding="utf-8"))
            for c in started if (directory/c/"result.json").exists()]
        receipt = dict(plan, cases=rows, case_counts=case_progress(selected, started,
            [r for r in rows if not r.get("interrupted")]),
            reserved_calls=sum(r["reserved_calls"] for r in accounting), completed_calls=sum(r["completed_calls"] for r in accounting),
            input_tokens=sum(r["input_tokens"] for r in accounting), output_tokens=sum(r["output_tokens"] for r in accounting),
            unknown_usage_calls=sum(r["unknown_usage_calls"] for r in accounting),
            manual_semantic_acceptance=False)
        write_new_json(directory/"receipt.json", receipt)
        print(review.compact({k:v for k,v in receipt.items() if k not in ("cases", "implementation")}), flush=True)


def main(*, bounded=False, full_context=False):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", type=Path, required=True)
    p.add_argument("--base-report", type=Path, required=True)
    p.add_argument("--pair", type=int, choices=range(1, 6), default=1)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--run-id", default="")
    p.add_argument("--ci-run", default="")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--output-root", type=Path, default=ROOT/"data/runs/inference_development")
    run(p.parse_args(), bounded=bounded, full_context=full_context)


if __name__ == "__main__":
    main()
