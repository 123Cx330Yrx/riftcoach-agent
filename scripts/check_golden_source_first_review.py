"""Measure source-first full requests against archived shapes without a Provider."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from app.evaluation import golden_source_first_review as candidate
from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_contextual_requests import revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.check_golden_reassessment_feasibility import measured
from scripts.check_golden_decision_readiness import project_for_size
from scripts.check_golden_contextual_readiness import measurement_state
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases


def audit(args):
    summary, source, knowledge, cases = load_inputs(args.source_run, args.base_report)
    originals = {}
    def read(path):
        originals[path] = path.read_bytes()
        return strict_json(originals[path])
    response = read(args.case_dir / "response-001.json")
    report = read(args.case_dir / "input.json")["report"]
    inputs = build_inputs(EvaluationRequest(summary, source, knowledge, report, UTTERANCE))
    state = provisional.prepare(response["content"], inputs)
    old, new = provisional.build_request(state), candidate.build_request(state)
    data = candidate.request_data(state)
    # The original deterministic text, including legacy interpretations, stays
    # byte-identical: changing it too would confound this bounded diagnostic.
    assert new.messages[2] == old.messages[2]
    rows = []
    for item in strict_json(args.history.read_text(encoding="utf-8"))["historical_shapes"]:
        path = Path(item["source"])
        raw = read(path)["content"]
        old_report = ((path.parent / "revised-report.md").read_text(encoding="utf-8")
            if path.name == "response-004.json" else read(path.parent / "input.json")["report"])
        request = EvaluationRequest(summary, source, knowledge, old_report, UTTERANCE)
        old_inputs = build_inputs(request)
        projected, assumptions = project_for_size(raw)
        if strict_json(projected)["source_digest"] != old_inputs.source.source_digest:
            _, end = json.JSONDecoder().raw_decode(raw.lstrip())
            rebound = measurement_state(raw.lstrip()[:end], request)
            projected, _ = project_for_size(rebound.raw)
            assumptions["source_index_rebound_for_size_only"] = True
        built = candidate.build_request(provisional.prepare(projected, old_inputs))
        rows.append(dict(source=str(path), projection_only=True, **assumptions, second=measured(built)))
    frozen = []
    for case in select_cases(cases):
        current = build_inputs(EvaluationRequest(summary, source, knowledge, case["report"], UTTERANCE))
        shape = deepcopy(strict_json(response["content"]))
        shape["source_digest"] = current.source.source_digest
        shape["reviewed_blocks"] = list(range(1, len(current.source.blocks) + 1))
        shape["heading_reviews"] = [dict(block_id=i, kind="navigation")
            for i, (_, text) in enumerate(current.source.blocks, 1) if re.match(r"^#{1,6}\s", text)]
        changes = []
        for a in shape["audits"]:
            for row in a["claims"]:
                for key in ("quote_ref", "scope_source"):
                    if not row.get(key): continue
                    text = inputs.source.resolve(row[key])
                    try: row[key] = current.source.reference(text)
                    except ValueError:
                        row[key] = current.source.reference(case["target"])
                        changes.append(dict(field=key, before=text, after=case["target"]))
        built = candidate.build_request(provisional.prepare(compact(shape), current))
        frozen.append(dict(case_id=case["id"], projection_for_size_only=True,
            substitutions=changes, first=measured(candidate.SourceFirstReviewWorkflow.build_first(current)),
            second=measured(built)))
    # Format-only witness is deliberately semantically wrong, not regraded.
    final = read(args.case_dir / "response-002.json")["content"]
    projection = strict_json(final)
    for a in projection["audits"]:
        for row in a["claims"]:
            row["evidence_refs"] = sorted(set(row["evidence_refs"]) |
                {n for c in row["comparisons"] for n in c["operand_refs"]})
            if row["quote_ref"]["block"] == 10: row["scope_source"] = {"block": 3}
    result, journal = candidate.apply(state, compact(projection), inputs=inputs)
    revision = revision_request(inputs, result, FULL_CONTEXT_RULE,
        comparison_review=journal["comparison_bindings"])
    if any(p.read_bytes() != value for p, value in originals.items()):
        raise ValueError("frozen_evidence_changed")
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0,
        second_old=measured(old), second_new=measured(new),
        protected_source=data["protected_source"], previous_issues_preserved=True,
        full_deterministic_source_unchanged=True,
        frozen_shapes=frozen, historical_shapes=rows,
        revision_shape_only=measured(revision),
        known_wrong_semantics_still_structurally_pass=result.verdict == "pass",
        semantic_approval=False, full_live_qualified=False,
        source_hashes={str(p): hashlib.sha256(value).hexdigest() for p, value in originals.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("source-run", "base-report", "case-dir", "history", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    args = p.parse_args()
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("second_old", "second_new", "frozen_shapes", "historical_shapes", "revision_shape_only")}))


if __name__ == "__main__":
    main()
