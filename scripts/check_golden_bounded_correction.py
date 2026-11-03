"""Measure the offline state-preserving prototype against frozen complete reports.

No Provider, candidate runtime, historical rewrite or synthetic quality claim.
Historical ContextWire responses supply actual state sizes, not new outcomes.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_bounded_correction import prepare_state
from app.evaluation import golden_bounded_correction_requests as requests
from app.evaluation.golden_context_requests import revision_request
from app.evaluation.golden_context_review import ContextEvaluation
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.check_golden_integrated_workflow import budgeted, size
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def measure(source_run, base_report, context_pair):
    summary, deterministic, knowledge, cases = load_inputs(source_run, base_report)
    sources = [context_pair / name for name in (
        "response-001.json", "response-003.json", "stable_defined_before-evaluation.json")]
    snapshots = {p: p.read_bytes() for p in sources}
    first_rows, state_rows = [], []
    for case in cases:
        inputs = ReviewInput.build(EvaluationRequest(summary, deterministic, knowledge, case["report"], UTTERANCE))
        data = requests.source_data(inputs)
        original = strict_json(inputs.data_json)
        restored = dict(data)
        restored["generation_facts"] = requests.restore_generation(
            restored.pop("generation_view"), data["facts_and_provenance"]["facts"])
        if compact(restored) != compact(original):
            # Object key order is immaterial, but values and types are not.
            if json.dumps(restored, sort_keys=True, ensure_ascii=False) != json.dumps(original, sort_keys=True, ensure_ascii=False):
                raise ValueError("full_source_round_trip_failed")
        req = requests.first_request(inputs)
        first_rows.append(dict(case_id=case["id"], source_digest=inputs.source.source_digest,
            input_ceiling=size(budgeted(req)), full_source_round_trip=True))
        if case["id"] not in {"stable_unbounded", "stable_defined_before"}:
            continue
        path = sources[0 if case["id"] == "stable_unbounded" else 1]
        state = prepare_state(strict_json(path.read_text(encoding="utf-8"))["content"], inputs)
        request = requests._request(requests.correction_data(state), requests.CORRECTION_POLICY,
            requests.CorrectionWire, "correction")
        # A non-executable sensitivity measurement: even deleting all prior
        # state is not a legal optimization, but exposes its maximum size share.
        no_state = requests.correction_data(state)
        for field in ("review_state", "mutable_claims", "required_reviews", "diagnostics"):
            no_state.pop(field)
        no_state_request = requests._request(no_state, requests.CORRECTION_POLICY,
            requests.CorrectionWire, "correction")
        try:
            requests.correction_request(state)
            ready, error = True, None
        except ValueError as exc:
            ready, error = False, str(exc)
        state_rows.append(dict(case_id=case["id"], historical_response=path.name,
            historical_sha256=hashlib.sha256(snapshots[path]).hexdigest(),
            state_id=state.state_id, mutable_claims=len(state.mutable_claims),
            required_reviews=len(state.required_reviews), input_ceiling=size(budgeted(request)),
            unusable_without_state_input_ceiling=size(budgeted(no_state_request)),
            preparation_passed=ready, preparation_error=error))
    historical = ContextEvaluation.model_validate(strict_json(sources[2].read_text(encoding="utf-8")), strict=True)
    defined = next(case for case in cases if case["id"] == "stable_defined_before")
    revision_size = size(budgeted(revision_request(summary, deterministic, knowledge, defined["report"], historical)))
    first_max = max(row["input_ceiling"] for row in first_rows)
    correction_max = max(row["input_ceiling"] for row in state_rows)
    envelope = 2 * (first_max + correction_max) + revision_size + 5 * 32768
    for path, original_bytes in snapshots.items():
        if path.read_bytes() != original_bytes:
            raise ValueError("historical_evidence_changed")
    return dict(experiment="golden-bounded-correction-offline-v1", provider_calls=0,
        prototype_implemented=True, runtime_implemented=False, candidate_adopted=False,
        semantic_quality="not_evaluated", historical_bytes_unchanged=True,
        first_requests=first_rows, historical_state_requests=state_rows,
        revision_historical_shape_input_ceiling=revision_size,
        measured_five_call_envelope=envelope, report_token_limit=401920,
        unusable_no_state_five_call_envelope=2 * (first_max + max(
            row["unusable_without_state_input_ceiling"] for row in state_rows)) + revision_size + 5 * 32768,
        measured_shapes_fit=envelope <= 401920,
        per_request_preparation_limit=63936, per_request_input_limit=64000,
        output_profile="high", per_call_output_limit=32768,
        max_calls=5, max_revisions=1, per_call_time_limit_s=300, report_time_limit_s=900,
        decision="offline_only_no_paid_readiness",
        limitations=["Two saved first-review states, not future-state or revised-report maxima.",
            "Envelope uses full output reservations; it is not actual usage. Actual usage settlement may permit runs with these shapes.",
            "Five 300-second calls do not establish completion within 900 seconds.",
            "Exact reconstruction is a data property, not proof the model understands the compact view.",
            "Source references and scripted merge tests do not establish semantic entailment or control accuracy."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "context-pair"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = measure(args.source_run, args.base_report, args.context_pair)
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))


if __name__ == "__main__":
    main()
