"""Read-only diagnosis of the failed batch, with an explicitly synthetic codec view.

Never overwrites a response or treats a locally decoded first opinion as a model
correction. No Provider is constructed and all original byte hashes are checked.
"""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.evaluation import golden_partition_review as candidate
from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest, QuoteRef
from app.harness.steps import EvaluationRequest
from scripts.check_golden_meaning_first_review import measured
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def object_projection(value):
    result, changes = deepcopy(value), []
    for i, row in enumerate(candidate.rows(result)):
        for field, keys in (("quote_ref", ("block", "head", "tail")), ("scope_source", ("block", "head", "tail"))):
            old = row.get(field)
            if isinstance(old, list) and 1 <= len(old) <= 3:
                row[field] = dict(zip(keys, old, strict=False))
                changes.append(dict(row=i, field=field, before=old, after=deepcopy(row[field])))
        for field, keys in (("comparisons", ("cohort", "metric")),
                ("summaries", ("cohort", "metric", "operation", "reported"))):
            for j, old in enumerate(row.get(field, [])):
                if isinstance(old, list) and len(old) == len(keys):
                    row[field][j] = dict(zip(keys, old, strict=True))
                    changes.append(dict(row=i, field=field, index=j, before=old, after=deepcopy(row[field][j])))
    return result, changes


def error_code(action):
    try:
        action()
    except (ValueError, TypeError) as error:
        return str(error).splitlines()[0]
    return None


def audit(args):
    directory = args.run
    originals = {p: p.read_bytes() for p in sorted(directory.rglob("*")) if p.is_file()}
    receipt = strict_json(originals[directory / "receipt.json"])
    root = directory / "contextual_01"
    raw = strict_json(originals[root / "response-001.json"])["content"]
    report = strict_json(originals[root / "input.json"])["report"]
    summary, deterministic, knowledge, _ = load_inputs(args.source_run, args.base_report)
    inputs = candidate.ComputedPartitionWorkflow.build_inputs(EvaluationRequest(summary, deterministic, knowledge, report, UTTERANCE))
    value = strict_json(normalize_json(raw))
    try:
        candidate.Partial.model_validate(value, strict=True)
        schema_errors = []
    except ValueError as error:
        schema_errors = [dict(code=e["type"], location=list(e["loc"]))
            for e in error.errors(include_input=False, include_context=False)]
    projected, changes = object_projection(value)
    projected_schema_error = error_code(lambda: candidate.Partial.model_validate(projected, strict=True))
    locations, coverage = [], {}
    for i, row in enumerate(candidate.rows(projected)):
        for field in ("quote_ref", "scope_source"):
            if row.get(field) is None: continue
            failure = error_code(lambda: inputs.source.resolve(row[field]))
            if failure: locations.append(dict(row=i, field=field, code=failure))
        try:
            block, start, end = typed.full.span(inputs.source, QuoteRef.model_validate(row["quote_ref"], strict=True))
            coverage.setdefault(block, set()).update(range(start, end))
        except ValueError:
            pass
    missing = [dict(block=b, missing_chars="".join(c for i, c in enumerate(inputs.source.blocks[b-1][1])
                if i not in coverage.get(b, set()))) for b in candidate.body_blocks(inputs)
                if b in candidate.allocation(inputs)[0]]
    missing = [r for r in missing if r["missing_chars"]]
    native, operand_ledger = candidate.expand_operands(projected, inputs)
    native["issue_resolutions"] = []
    native, source_ledger = candidate.expand_source_kinds(native, inputs)
    claim_checks = []
    for ai, audit_row in enumerate(native["audits"]):
        for ci, row in enumerate(audit_row["claims"]):
            claim = typed.TypedClaim.model_validate(row, strict=True)
            wire = SimpleNamespace(audits=[SimpleNamespace(kind=audit_row["kind"], claims=[claim])])
            claim_checks.append(dict(audit=ai, claim=ci, block=claim.quote_ref.block,
                comparison_error=error_code(lambda: typed.comparison.validate_bindings(wire, inputs, typed.comparison.catalog(inputs))),
                summary_error=error_code(lambda: typed.validate_summaries(wire, inputs))))
    source_checks = []
    catalog = typed.build_catalog(inputs)
    for i, row in enumerate(native["source_checks"]):
        source_checks.append(dict(index=i, block=row["quote_ref"]["block"],
            refs=[dict(source=ref, error=error_code(lambda ref=ref: catalog.resolve(inputs, **ref))) for ref in row["sources"]]))
    # Observe the real admission function; do not bypass its rejection.
    captured, check = [], candidate.budget_check
    def observe(request):
        captured.append(request)
        return check(request)
    with patch.object(candidate, "budget_check", observe):
        projection_admission_error = error_code(lambda: candidate.request(inputs,
            state=candidate.prepare(compact(projected), inputs)))
    progress = strict_json(originals[root / "streams/stream-001/progress.json"])
    terminal = strict_json(originals[root / "streams/stream-001/result.json"])
    if any(p.read_bytes() != content for p, content in originals.items()):
        raise ValueError("partition_audit_history_changed")
    return dict(run_id=directory.name, head_sha=receipt["head_sha"], ci_run=receipt["ci_run"],
        provider_calls_by_audit=0, actual_calls=receipt["reserved_calls"],
        known_input_tokens=receipt["input_tokens"], known_output_tokens=receipt["output_tokens"],
        unknown_usage_calls=receipt["unknown_usage_calls"], original_outcome=receipt["cases"],
        elapsed_ms=terminal["elapsed_ms"], stream={k: progress.get(k) for k in (
            "first_event_ms", "first_visible_content_ms", "last_event_ms", "max_inter_event_gap_ms", "finish_reason", "content_chars")},
        raw_sha256=digest(raw), raw_schema_errors=schema_errors,
        raw_admission_error=error_code(lambda: candidate.prepare(raw, inputs)),
        diagnostic_projection=dict(analyst_created=True, not_a_model_correction=True, changes=changes,
            schema_error=projected_schema_error, reference_errors=locations, missing_first_body_characters=missing,
            assertion_headings=[h for h in projected["heading_reviews"] if h["kind"] == "assertion"],
            claim_checks=claim_checks, source_checks=source_checks,
            next_input_ceiling=measured(captured[0]) if captured else None,
            next_admission_error=projection_admission_error),
        observed_target=[r for a in projected["audits"] for r in a["claims"] if r["quote_ref"]["block"] == 10],
        scope_oracle=dict(status="engineering_expectation_disputed", frozen_label_changed=False,
            expected_unique_cohort_confirmed_by_user=False,
            evidence="docs/plans/2026-09-19-review-oracle-provenance.md"),
        findings=["Output used positional input notation instead of its required object schema.",
            "The target selected five mixed matches. An independent provenance audit found the prior unique four-MIDDLE expectation was an engineering interpretation, not an explicit user ruling; neither semantic failure nor success is established by that selection alone.",
            "Assertion-labelled headings lack matching full-title claims; body coverage, comparison evidence and source paths also fail.",
            "No final batch, negative case, revision or recheck ran. Final correction ability is not established."],
        source_hashes={str(p.relative_to(directory)): hashlib.sha256(content).hexdigest() for p, content in originals.items()},
        historical_result_changed=False, semantic_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--base-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError("partition_audit_output_inside_history")
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("run_id", "actual_calls", "known_input_tokens", "known_output_tokens",
        "unknown_usage_calls", "elapsed_ms", "raw_admission_error", "findings")}))


if __name__ == "__main__":
    main()
