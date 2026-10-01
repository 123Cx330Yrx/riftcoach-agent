"""Reproduce first-phase failure and inspect the offline provisional replacement."""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation import golden_reassessment_feasibility as strict
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.check_golden_reassessment_feasibility import measured
from scripts.check_golden_decision_readiness import project_for_size
from scripts.check_golden_contextual_readiness import measurement_state
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def audit(args):
    summary, source, knowledge, _ = load_inputs(args.source_run, args.base_report)
    files = [args.case_dir / name for name in ("input.json", "response-001.json", "result.json")]
    originals = {p: p.read_bytes() for p in files}
    report = strict_json(originals[files[0]])["report"]
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    response = strict_json(originals[files[1]])
    raw = response["content"]
    try: strict.prepare(raw, inputs)
    except ValueError as error:
        strict_failure = (error.errors(include_input=False, include_context=False, include_url=False)
            if hasattr(error, "errors") else str(error))
    else: raise ValueError("expected_first_phase_failure_missing")
    state = provisional.prepare(raw, inputs)
    value, protections, diagnostics = provisional.inspect(raw, inputs)
    target_ref = inputs.source.reference("经济和伤害是较稳定的差异项。")
    rows = []
    for item in strict_json(args.history.read_text(encoding="utf-8"))["historical_shapes"]:
        path = Path(item["source"])
        original = path.read_bytes()
        originals[path] = original
        old_raw = strict_json(original)["content"]
        old_report = ((path.parent / "revised-report.md").read_text(encoding="utf-8")
            if path.name == "response-004.json"
            else strict_json((path.parent / "input.json").read_text(encoding="utf-8"))["report"])
        request = EvaluationRequest(summary, source, knowledge, old_report, UTTERANCE)
        old_inputs = build_inputs(request)
        projected, assumptions = project_for_size(old_raw)
        if strict_json(projected)["source_digest"] != old_inputs.source.source_digest:
            _, end = json.JSONDecoder().raw_decode(old_raw.lstrip())
            rebound = measurement_state(old_raw.lstrip()[:end], request)
            projected, _ = project_for_size(rebound.raw)
            assumptions["source_index_rebound_for_size_only"] = True
        entry = dict(source=str(path), projection_only=True, **assumptions)
        try:
            entry.update(second=measured(provisional.build_request(provisional.prepare(projected, old_inputs))), admitted=True)
        except ValueError as error:
            entry.update(admitted=False, code=str(error))
        rows.append(entry)
    if any(p.read_bytes() != data for p, data in originals.items()):
        raise ValueError("frozen_evidence_changed")
    return dict(experiment=provisional.EXPERIMENT_ID, provider_calls=0,
        original_live_result=strict_json(originals[files[2]]), strict_first_failure=strict_failure,
        original_finish_reason=response["finish_reason"], provisional_diagnostics=diagnostics,
        second_request_input_ceiling=measured(provisional.build_request(state)),
        reviewed_source_obligations=[dict(audit=a.kind, refs=[c.quote_ref.model_dump(mode="json") for c in a.claims])
            for a in protections.audits],
        target_omitted_in_first=all(c.get("quote_ref", {}).get("block") != target_ref["block"]
            for a in value["audits"] for c in a["claims"]),
        target_discovery_still_requires_full_second_review=True,
        historical_shapes=rows, historical_result_changed=False,
        semantic_approval=False, live_qualified=False,
        source_hashes={str(p): hashlib.sha256(data).hexdigest() for p, data in originals.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "case-dir", "history", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("strict_first_failure", "provisional_diagnostics",
        "second_request_input_ceiling", "target_omitted_in_first", "historical_shapes")}))


if __name__ == "__main__":
    main()
