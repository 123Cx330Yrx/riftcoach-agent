"""Read-only full final-response inspection, with a labelled format-only witness.

The witness deliberately retains incorrect semantics. Never changes a response,
receipt or expected label; no Provider and no live acceptance are involved.
"""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace

from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation.golden_contextual_patch_wire import expand_value
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def audit(args):
    summary, source, knowledge, _ = load_inputs(args.source_run, args.base_report)
    paths = [args.case_dir / n for n in ("input.json", "response-001.json", "response-002.json", "result.json")]
    original = {p: p.read_bytes() for p in paths}
    report = strict_json(original[paths[0]])["report"]
    first, final = [strict_json(original[p])["content"] for p in paths[1:3]]
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    state = provisional.prepare(first, inputs)
    _, protections, _ = provisional.inspect(first, inputs)
    wire = full._read(final, inputs, comparison.ComparisonWire)
    coverage = full.coverage_map(protections, wire, inputs.source)
    evidence = comparison.catalog(inputs)
    findings = []
    for a in wire.audits:
        for i, claim in enumerate(a.claims):
            codes = []
            try:
                comparison.validate_bindings(SimpleNamespace(audits=[SimpleNamespace(kind=a.kind, claims=[claim])]), inputs, evidence)
            except ValueError as e: codes.append(str(e))
            try: expand_value(claim, inputs.source)
            except ValueError as e: codes.append(str(e))
            findings.append(dict(audit=a.kind, claim_index=i, block=claim.quote_ref.block,
                quote=inputs.source.resolve(claim.quote_ref.model_dump(mode="json")),
                codes=codes, explanation=claim.explanation,
                comparisons=[c.model_dump(mode="json") for c in claim.comparisons]))
    # Explicit synthetic witness: supply missing redundant operands and the
    # real contextual link, while preserving the model's WRONG target meaning.
    projection = deepcopy(strict_json(final))
    edits = []
    for a in projection["audits"]:
        for i, c in enumerate(a["claims"]):
            needed = {n for b in c["comparisons"] for n in b["operand_refs"]}
            if not needed.issubset(c["evidence_refs"]):
                edits.append(dict(audit=a["kind"], claim_index=i, field="evidence_refs", before=c["evidence_refs"]))
                c["evidence_refs"] = sorted(set(c["evidence_refs"]) | needed)
            if c["quote_ref"]["block"] == 10:
                edits.append(dict(audit=a["kind"], claim_index=i, field="scope_source", before=c.get("scope_source")))
                c["scope_source"] = {"block": 3}
    witness = dict(synthetic_only=True, edits=edits, semantic_approval=False)
    try:
        accepted, _ = provisional.apply(state, compact(projection), inputs=inputs)
        witness.update(structural_verdict=accepted.verdict)
    except ValueError as e: witness.update(error=str(e))
    if any(p.read_bytes() != b for p, b in original.items()):
        raise ValueError("frozen_evidence_changed")
    return dict(provider_calls=0, historical_result_changed=False,
        original_result=strict_json(original[paths[3]]), protected_ranges=len(coverage),
        final_claims=findings, format_only_witness=witness,
        manual_findings=[
            "Target block10 still substitutes selected five mixed-role games for four MIDDLE games.",
            "Training median and overall mean in block21 are incorrectly decorated with win/loss comparison bindings.",
            "Two complete stop responses do not establish semantic acceptance or a working revision/recheck."],
        source_hashes={str(p): hashlib.sha256(b).hexdigest() for p, b in original.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "case-dir", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    result = audit(args)
    write_new_json(args.output, result)
    print(compact(dict(failures=[r for r in result["final_claims"] if r["codes"]],
        format_only_witness=result["format_only_witness"], manual_findings=result["manual_findings"])))


if __name__ == "__main__":
    main()
