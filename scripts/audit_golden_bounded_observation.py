"""Audit an unchanged bounded-review response pair; never repair or regrade it."""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_bounded_correction as correction
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def audit(source_run, base_report, run_dir):
    summary, deterministic, knowledge, cases = load_inputs(source_run, base_report)
    case = next(row for row in cases if row["id"] == "stable_unbounded")
    directory = run_dir / case["id"]
    paths = [run_dir/"receipt.json", directory/"input.json",
        directory/"response-001.json", directory/"response-002.json"]
    snapshots = {p:p.read_bytes() for p in paths}
    receipt, source, first, second = [json.loads(snapshots[p]) for p in paths]
    if receipt["experiment_id"] != "golden-bounded-review-v1" or source["report"] != case["report"]:
        raise ValueError("bounded_observation_identity_mismatch")
    inputs = ReviewInput.build(EvaluationRequest(summary,deterministic,knowledge,case["report"],UTTERANCE))
    state = correction.prepare_state(first["content"],inputs)
    patch = correction.Correction.model_validate_json(second["content"],strict=True)
    edits = {row.target_id:row.value.model_dump(mode="json") for row in patch.claim_edits}
    failures = []
    for row in patch.meaning_reviews:
        entry = state.entries()[row.target_id]
        if entry["type"] != "claim":
            continue
        value = edits.get(row.target_id,entry["value"])
        try:
            correction._check_meaning(row,value,inputs.source)
        except ValueError as error:
            failures.append(dict(target_id=row.target_id,code=str(error),
                disposition=row.disposition,claim_kind=value["claim_kind"],scope=value["scope"]))
    streams = []
    for n in (1,2):
        progress = json.loads((directory/f"streams/stream-{n:03}/progress.json").read_text(encoding="utf-8"))
        reservation = json.loads((directory/f"streams/stream-{n:03}/reservation.json").read_text(encoding="utf-8"))
        streams.append(dict(ordinal=n,input_ceiling=reservation["request_metrics"]["input_token_ceiling"],
            **{key:progress[key] for key in ("state","elapsed_ms","first_visible_content_ms",
                "finish_reason","input_tokens","output_tokens")}))
    unchanged = all(p.read_bytes() == data for p,data in snapshots.items())
    if not unchanged:
        raise ValueError("bounded_historical_bytes_changed")
    return dict(audit="golden-bounded-observation-v1",provider_calls_added_by_audit=0,
        implementation_sha=receipt["head_sha"],ci_run=receipt["ci_run"],case_counts=receipt["case_counts"],
        observed_calls=receipt["reserved_calls"],returned_tokens=receipt["input_tokens"]+receipt["output_tokens"],
        unknown_usage_calls=receipt["unknown_usage_calls"],streams=streams,
        raw_model_scores=[json.loads(first["content"])["score"],patch.score],
        raw_scores_are_not_valid_evaluations=True,all_claim_meaning_conflicts=failures,
        full_workflow_passed=False,revision_attempted=False,positive_control_started=False,
        meaning_inventory_complete=set(row.target_id for row in patch.meaning_reviews)==set(state.required_reviews),
        historical_bytes_unchanged=unchanged,
        historical_sha256={p.relative_to(run_dir).as_posix():hashlib.sha256(data).hexdigest() for p,data in snapshots.items()},
        rubric_status="strict_word_definition_rule_is_assistant_authored; owner_approved_whole_context_on_2026_09_15; old_result_unchanged",
        boundary="Protocol contradictions block acceptance under either rubric. Do not relabel old cases or accept projected/repaired historical output.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source-run","base-report","run-dir"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=audit(args.source_run,args.base_report,args.run_dir)
    if args.output:
        write_new_json(args.output,result)
    print(compact(result))


if __name__ == "__main__":
    main()
