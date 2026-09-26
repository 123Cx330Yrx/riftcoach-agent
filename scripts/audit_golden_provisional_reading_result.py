"""Inspect immutable advisory-reading receipts and timing without exposing thought text."""
import argparse
import hashlib
from pathlib import Path

from app.evaluation import golden_provisional_reading_review as candidate
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.check_golden_reassessment_feasibility import measured
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def audit(args):
    directory = args.run
    originals = {p: p.read_bytes() for p in sorted(directory.rglob("*")) if p.is_file()}
    receipt = strict_json(originals[directory / "receipt.json"])
    summary, deterministic, knowledge, _ = load_inputs(args.source_run, args.base_report)
    cases = []
    for case in receipt["cases"]:
        root = directory / case["id"]
        report = strict_json(originals[root / "input.json"])["report"]
        inputs = candidate.ProvisionalReadingWorkflow.build_inputs(EvaluationRequest(summary, deterministic, knowledge, report, UTTERANCE))
        raw = strict_json(originals[root / "response-001.json"])["content"]
        first = candidate.prepare(raw, inputs)
        value = strict_json(first.value_json)
        primary = sorted({r["quote_ref"]["block"] for r in value["readings"]})
        streams = []
        for stream in sorted((root / "streams").iterdir()):
            progress = strict_json(originals[stream / "progress.json"])
            result = strict_json(originals[stream / "result.json"])
            streams.append(dict(stream=stream.name, terminal_state=result["state"], elapsed_ms=result["elapsed_ms"],
                **{k: progress.get(k) for k in ("events", "first_event_ms", "first_visible_content_ms", "last_event_ms",
                    "max_inter_event_gap_ms", "content_chars", "reasoning_chars", "input_tokens", "output_tokens", "finish_reason", "http_requests")}))
        cases.append(dict(case_id=case["id"], first_raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            first_readings=len(value["readings"]), first_issues=len(value["issues"]), primary_blocks=primary,
            first_diagnostics=list(first.diagnostics), required_body_blocks=candidate.body_blocks(inputs),
            second_request_input_ceiling=measured(candidate.second_request(first)), streams=streams,
            complete_final_response_available=(root / "response-002.json").exists(),
            original_outcome=case))
    if any(p.read_bytes() != content for p, content in originals.items()):
        raise ValueError("provisional_audit_source_changed")
    return dict(run_id=directory.name, head_sha=receipt["head_sha"], ci_run=receipt["ci_run"],
        provider_calls_by_audit=0, actual_reserved_calls=receipt["reserved_calls"], completed_calls=receipt["completed_calls"],
        known_input_tokens=receipt["input_tokens"], known_output_tokens=receipt["output_tokens"],
        unknown_usage_calls=receipt["unknown_usage_calls"], cases=cases,
        source_hashes={str(p.relative_to(directory)): hashlib.sha256(content).hexdigest() for p, content in originals.items()},
        historical_result_changed=False, semantic_approval=False, negative_revision_recheck_executed=False,
        findings=["First reading and second-request admission succeeded; target meaning was not finally accepted.",
            "Second response hit the fixed whole-call deadline while events continued; no complete verdict or usage arrived.",
            "This is not a proven network stall or an output-limit finish; the complete final review remains unverified.",
            "Heavy single-call workload is a redesign hypothesis, not a measured cause of the provider's internal latency."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "source-run", "base-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError("provisional_audit_output_inside_source_run")
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: v for k, v in result.items() if k != "source_hashes"}))


if __name__ == "__main__": main()
