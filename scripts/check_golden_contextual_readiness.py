"""Measure complete contextual requests using frozen historical state shapes.

Historical responses are inputs for size measurement only, never accepted or
regraded as new-standard model results.
"""
import argparse
from pathlib import Path

from app.evaluation import golden_contextual_correction as contextual
from app.evaluation.golden_bounded_correction import prepare_state
from app.evaluation.golden_context_requests import revision_request
from app.evaluation.golden_context_review import expand_context
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases


def audit(source_run,base_report,bounded_run,context_pair):
    summary,deterministic,knowledge,cases=load_inputs(source_run,base_report)
    first=[dict(case_id=c["id"],input_ceiling=size(contextual.first_request(ReviewInput.build(
        EvaluationRequest(summary,deterministic,knowledge,c["report"],UTTERANCE))))) for c in select_cases(cases)]
    shapes=[]
    for directory,filename,case_id in (
        (bounded_run/"stable_unbounded","response-001.json","stable_unbounded"),
        (context_pair,"response-001.json","stable_unbounded"),
        (context_pair,"response-003.json","stable_defined_before")):
        case=next(c for c in cases if c["id"]==case_id)
        inputs=ReviewInput.build(EvaluationRequest(summary,deterministic,knowledge,case["report"],UTTERANCE))
        raw=strict_json((directory/filename).read_text(encoding="utf-8"))["content"]
        state=prepare_state(raw,inputs)
        shapes.append(dict(source=str(directory/filename),input_ceiling=size(contextual.correction_request(state).request)))
    case=next(c for c in cases if c["id"]=="stable_defined_before")
    inputs=ReviewInput.build(EvaluationRequest(summary,deterministic,knowledge,case["report"],UTTERANCE))
    raw=strict_json((context_pair/"response-003.json").read_text(encoding="utf-8"))["content"]
    canonical=expand_context(raw,case["report"],strict_json(inputs.pack_json))
    revision_size=size(revision_request(summary,deterministic,knowledge,case["report"],canonical))
    return dict(experiment=contextual.EXPERIMENT_ID,standard_id=contextual.STANDARD_ID,
        first_requests=first,historical_correction_shapes=shapes,historical_revision_input_ceiling=revision_size,
        provider_calls=0,historical_results_regraded=False,
        admission="settled_actual_tokens + next_request_input_ceiling + next_output_cap <= 401920",
        max_calls=5,max_output_per_call=32768,max_seconds_per_call=300,max_seconds_per_report=900,
        conditional_readiness=True,completion_guaranteed=False,semantic_quality_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source-run","base-report","bounded-run","context-pair","output"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    result=audit(args.source_run,args.base_report,args.bounded_run,args.context_pair)
    write_new_json(args.output,result)
    print(compact(result))


if __name__ == "__main__": main()
