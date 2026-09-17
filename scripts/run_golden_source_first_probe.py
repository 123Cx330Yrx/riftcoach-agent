"""One new second-review request over a frozen failed first review.

Default is offline preview. This diagnostic never claims a fresh full workflow
or runs a negative/revision automatically. Existing failed entries stay blocked.
"""
import argparse
import hashlib
from pathlib import Path
import re

from pydantic import TypeAdapter

from app.evaluation import golden_source_first_review as candidate
from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, ReceiptedStreamProvider, validate_exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import EvaluationRequest
from app.providers.models import ChatResponse
from scripts.check_golden_reassessment_feasibility import measured
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_golden_integrated_review import implementation_identity

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data/runs/inference_development/provisional-review-c3ff392-positive-v1/contextual_01"
AUDIT = ROOT / "data/evaluation/results/golden_provisional_result_c3ff392.json"
EXPERIMENT_ID = "golden-source-first-single-second-diagnostic-v1"


def prepare(args):
    original_hashes = strict_json(AUDIT.read_text(encoding="utf-8"))["source_hashes"]
    portable_hashes = {key.replace("\\", "/"): value for key, value in original_hashes.items()}
    # Hard-bind this single diagnostic to the already reviewed bad case.
    for name in ("input.json", "response-001.json", "response-002.json", "result.json"):
        file = BASELINE / name
        key = file.relative_to(ROOT).as_posix()
        if hashlib.sha256(file.read_bytes()).hexdigest() != portable_hashes[key]:
            raise ValueError("source_first_baseline_changed")
    summary, source, knowledge, cases = load_inputs(args.source_run, args.base_report)
    case = select_cases(cases)[0]
    report = strict_json((BASELINE / "input.json").read_text(encoding="utf-8"))["report"]
    if report != case["report"]:
        raise ValueError("source_first_control_changed")
    response = strict_json((BASELINE / "response-001.json").read_text(encoding="utf-8"))
    if response["finish_reason"] != "stop":
        raise ValueError("source_first_baseline_incomplete")
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    state = provisional.prepare(response["content"], inputs)
    request = candidate.build_request(state)
    files = implementation_identity(provisional=True)
    for name in ("app/evaluation/golden_source_first_review.py", "scripts/run_golden_source_first_probe.py"):
        files[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    plan = dict(experiment_id=EXPERIMENT_ID, implementation=files,
        baseline=str(BASELINE.relative_to(ROOT)), baseline_hashes=original_hashes,
        baseline_first_is_reused_not_a_new_call=True, input_ceiling=measured(request),
        max_new_calls=1, max_output_tokens=32768, max_seconds=300, reasoning_effort="high", sdk_retries=0,
        full_workflow=False, labels_sent_to_model=False, manual_semantic_acceptance=False,
        live_status="bounded_single_diagnostic_only", production_admitted=False)
    return state, request, plan


def observe(provider, directory, state, request):
    result = dict(valid=False, completed_calls=0, input_tokens=0, output_tokens=0,
        manual_semantic_acceptance=False, full_workflow=False, reused_first_review=True)
    try:
        exchange = BudgetedReviewSender(provider)(request)  # Exactly one; no loop/retry.
        response = exchange.response
        write_new_json(directory / "response.json", strict_json(TypeAdapter(ChatResponse).dump_json(response)))
        write_new_json(directory / "request.json", strict_json(validate_request(exchange.issued_request, transport_id=CAPACITY_TRANSPORT_ID)))
        result.update(completed_calls=1, input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens, request_sha256=exchange.receipt_request_sha256)
        raw = validate_exchange(request, exchange)
        payload, journal = candidate.apply(state, raw, inputs=state.inputs)
        write_new_json(directory / "evaluation.json", payload.model_dump(mode="json"))
        write_new_json(directory / "journal.json", journal)
        result.update(valid=True, structural_verdict=payload.verdict, score=payload.score)
    except Exception as error:
        code = getattr(error, "code", str(error))
        result.update(error_type=type(error).__name__,
            error_code=code if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,80}", code) else "probe_invalid")
    finally:
        result.update(reserved_calls=provider._calls,
            unknown_usage_calls=max(0, provider._calls - result["completed_calls"]))
        write_new_json(directory / "result.json", result)
    return result


def run(args):
    state, request, plan = prepare(args)
    if not args.execute:
        print(compact(plan)); return plan
    if not re.fullmatch(r"source-first-probe-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("source_first_probe_id_invalid")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    provider = ReceiptedStreamProvider(settings=settings, directory=directory / "streams", transport_id=CAPACITY_TRANSPORT_ID)
    result = observe(provider, directory, state, request)
    print(compact(result), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", type=Path, required=True)
    p.add_argument("--base-report", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--run-id", default="")
    p.add_argument("--ci-run", default="")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    run(p.parse_args())


if __name__ == "__main__":
    main()
