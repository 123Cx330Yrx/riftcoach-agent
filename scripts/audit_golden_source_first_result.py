"""Inspect the whole frozen response without repairing it or calling a Provider.

Component checks deliberately continue past envelope/schema failure. They are
diagnostics, never an alternative path to acceptance or a new model judgment.
"""
import argparse
import hashlib
from pathlib import Path
from types import SimpleNamespace

from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation import golden_context_review as context
from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation.golden_contextual_first_wire import FirstClaim
from app.evaluation.golden_contextual_patch_wire import expand_value
from app.evaluation.golden_contextual_validation import claim_errors
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from scripts.run_golden_source_first_probe import prepare


def errors(error):
    if hasattr(error, "errors"):
        return [dict(code=e["type"], location=list(e["loc"]))
                for e in error.errors(include_input=False, include_context=False)]
    return [dict(code=str(error))]


def inspect_response(state, raw):
    inputs = state.inputs
    value = strict_json(raw)
    pack = strict_json(inputs.pack_json)
    result = dict(component_checks_only=True, response_repaired=False,
                  semantic_approval=False, schema_errors=[], claims=[])
    try:
        full._read(raw, inputs, comparison.ComparisonWire)
    except ValueError as error:
        result["schema_errors"] = errors(error)
    after = []
    for ai, audit in enumerate(value["audits"]):
        claims = []
        for ci, item in enumerate(audit["claims"]):
            entry = dict(audit=audit["kind"], claim_index=ci,
                         block=item["quote_ref"]["block"], errors=[],
                         explanation=item["explanation"],
                         comparisons_present="comparisons" in item)
            result["claims"].append(entry)
            # Read existing common fields without inventing missing bindings.
            row = FirstClaim.model_validate(
                {k: v for k, v in item.items() if k != "comparisons"}, strict=True)
            claims.append(row)
            entry["quote"] = inputs.source.resolve(item["quote_ref"])
            entry["evidence_keys"] = [inputs.source.evidence_keys[n - 1]
                                      for n in row.evidence_refs]
            try:
                bound = comparison.ComparisonClaim.model_validate(item, strict=True)
                comparison.validate_bindings(SimpleNamespace(audits=[
                    SimpleNamespace(kind=audit["kind"], claims=[bound])]),
                    inputs, comparison.catalog(inputs))
            except ValueError as error:
                entry["errors"].extend(errors(error))
            try:
                expanded = expand_value(row, inputs.source)
                single = {k: v for k, v in value.items() if k != "issue_resolutions"}
                single["audits"] = [dict(kind=a["kind"], claims=[expanded] if i == ai else [])
                                    for i, a in enumerate(value["audits"])]
                restored = context.restore(compact(single), inputs.source.report, pack)
                claim = context.ContextClaim.model_validate(
                    restored["audits"][ai]["claims"][0], strict=True)
                entry["errors"].extend(dict(code=code) for code in
                    claim_errors(claim, inputs.source.report, pack))
            except ValueError as error:
                entry["errors"].extend(errors(error))
        after.append(SimpleNamespace(kind=audit["kind"], claims=claims))
    _, before, _ = provisional.inspect(state.raw, inputs)
    try:
        result["protected_range_count"] = len(full.coverage_map(
            before, SimpleNamespace(audits=after), inputs.source))
    except ValueError as error:
        result["coverage_errors"] = errors(error)
    result["issues"] = value["issues"]
    result["issue_resolutions"] = value["issue_resolutions"]
    result["old_issues"] = strict_json(state.raw)["issues"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "probe-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    state, _, _ = prepare(args)
    paths = [args.probe_dir / name for name in
             ("plan.json", "request.json", "response.json", "result.json")]
    original = {p: p.read_bytes() for p in paths}
    response = strict_json(original[paths[2]])
    result = inspect_response(state, response["content"])
    result.update(provider_calls_by_audit=0,
        original_result=strict_json(original[paths[3]]),
        finish_reason=response["finish_reason"],
        source_hashes={p.as_posix(): hashlib.sha256(b).hexdigest()
                       for p, b in original.items()})
    if any(p.read_bytes() != b for p, b in original.items()):
        raise ValueError("source_first_receipt_changed")
    write_new_json(args.output, result)
    print(compact(dict(schema_errors=result["schema_errors"],
        claim_failures=[dict(audit=r["audit"], block=r["block"], errors=r["errors"])
                        for r in result["claims"] if r["errors"]],
        protected_range_count=result.get("protected_range_count"))))


if __name__ == "__main__":
    main()
