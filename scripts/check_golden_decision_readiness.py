"""Offline size projections, never acceptance or rewriting of historical output."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_contextual_first_wire as first
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases
from scripts.check_golden_contextual_readiness import measurement_state


def project_for_size(raw):
    """Choose legacy labels only for dimensions; NOT a semantic migration.

    Some historical labels conflict. Record those conflicts, preserve reasoning
    and references, and never run this converter in a real evaluation workflow.
    """
    value, end = json.JSONDecoder().raw_decode(raw.lstrip())
    value = strict_json(raw.lstrip()[:end])
    projected = deepcopy(value)
    conflicts = 0
    for audit in projected["audits"]:
        for n, row in enumerate(audit["claims"]):
            scope = row["scope"]
            direct = row["claim_kind"] == "direct_result"
            if direct and any(row.get(key) is not None for key in ("scope", "scope_anchor", "context")):
                conflicts += 1
            label = "direct" if direct else dict(selected_sample="sample",question_or_negation="negated",
                ambiguous="ambiguous",beyond_sample="beyond_sample")[scope]
            if label not in ("ambiguous", "beyond_sample"):
                label += "_" + row["status"]
            context = row.get("context")
            explanation = row["explanation"]
            if context and context["explanation"] not in explanation:
                explanation += "；" + context["explanation"]
            audit["claims"][n] = dict(decision=label,quote_ref=row["quote_ref"],
                evidence_refs=row["evidence_refs"],explanation=explanation,
                scope_source=context["quote_ref"] if context and (direct or scope in (
                    "selected_sample", "question_or_negation")) else None)
    return compact(projected), dict(legacy_conflicts=conflicts,
        excluded_suffix_chars_for_sizing=len(raw.lstrip()[end:]), semantic_migration=False)


def audit(source_run, base_report, history, latest):
    summary, source, knowledge, cases = load_inputs(source_run, base_report)
    result = dict(experiment=first.canonical.EXPERIMENT_ID,provider_calls=0,
        projection_only=True,historical_results_regraded=False,semantic_quality_verified=False,
        completion_guaranteed=False,first_requests=[],historical_shapes=[])
    for case in select_cases(cases):
        inputs = ContextualCorrectionWorkflow.build_inputs(EvaluationRequest(
            summary,source,knowledge,case["report"],UTTERANCE))
        result["first_requests"].append(dict(case_id=case["id"],input_ceiling=size(first.first_request(inputs))))
    paths = [Path(row["source"]) for row in strict_json(history.read_text(encoding="utf-8"))["recent_failure_shapes"]]
    paths.extend([latest/"contextual_01"/"response-001.json",
        Path("data/runs/inference_development/contextual-review-68e8670-source-v8/contextual_02/response-004.json")])
    for path in paths:
        original = path.read_bytes()
        raw = strict_json(original)["content"]
        report = strict_json((path.parent/"input.json").read_text(encoding="utf-8"))["report"]
        if path.name == "response-004.json":
            report = (path.parent/"revised-report.md").read_text(encoding="utf-8")
        review_request = EvaluationRequest(summary,source,knowledge,report,UTTERANCE)
        inputs = ContextualCorrectionWorkflow.build_inputs(review_request)
        projected, assumptions = project_for_size(raw)
        if strict_json(projected)["source_digest"] != inputs.source.source_digest:
            _, end = json.JSONDecoder().raw_decode(raw.lstrip())
            rebound = measurement_state(raw.lstrip()[:end],review_request)
            projected, _ = project_for_size(rebound.raw)
            assumptions["source_index_rebound_for_size_only"] = True
        state = first.prepare_state(projected,inputs)
        request = first.build_correction(state).request
        if original != path.read_bytes():
            raise ValueError("historical_response_changed")
        result["historical_shapes"].append(dict(source=str(path),source_sha256=hashlib.sha256(original).hexdigest(),
            input_ceiling=size(request),claims=len(state.base.mutable_claims),reviews=len(state.base.required_reviews),
            source_bytes_unchanged=True,**assumptions))
    result["measured_requests_fit"] = all(row["input_ceiling"] <= 63936 for row in (
        result["first_requests"] + result["historical_shapes"]))
    result["limits"] = dict(max_calls_per_report=5,max_revisions=1,max_output_per_call=32768,
        max_seconds_per_call=300,max_tokens_per_report=401920,max_seconds_per_report=900,reasoning_effort="high")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "history", "latest", "output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args = parser.parse_args()
    result = audit(args.source_run,args.base_report,args.history,args.latest)
    write_new_json(args.output,result)
    print(compact(result))


if __name__ == "__main__":
    main()
