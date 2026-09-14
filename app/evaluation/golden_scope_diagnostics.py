"""Offline diagnostics for frozen scope-v5. Never an acceptance/rewrite path."""
from copy import deepcopy
import json

from pydantic import ConfigDict, create_model

from app.evaluation.golden_compact_coverage import STATUS
from app.evaluation.golden_inference_scope_v2 import AnchoredAudit
from app.evaluation.golden_inference_scope_v4 import CompactScopeResponse
from app.evaluation.golden_inference_scope_v5 import SAMPLE_ANCHOR, strict_json
from app.evaluation.golden_inference_coverage import report_blocks


def _shape(name, source, overrides=None):
    # Retain field constraints, but collect relational errors ourselves instead
    # of losing all locations at the first after-validator failure.
    fields = {}
    for key, original in source.model_fields.items():
        field = deepcopy(original)
        annotation = (overrides or {}).get(key, field.annotation)
        fields[key] = (annotation, field)
    return create_model(name, __config__=ConfigDict(extra="forbid"), **fields)


_AuditShape = _shape("DiagnosticAuditShape", AnchoredAudit)
_WireShape = _shape("DiagnosticWireShape", CompactScopeResponse,
                    {"audits": list[_AuditShape]})


def collect_diagnostics(raw, report, facts):
    """Return all structural relations, not a semantic verdict or valid payload.

    Excerpts are untrusted data. The full offline ledger is intentionally not
    sent to a provider; bounded_feedback is the separately bounded projection.
    """
    try:
        strict_json(raw)
        wire = _WireShape.model_validate_json(raw, strict=True)
    except (ValueError, TypeError):
        return [{"codes": ["invalid_json_or_schema"]}]
    return collect_relations(wire, report, facts)


def collect_relations(wire, report, facts, *, check_anchors=True):
    """Shared relation ledger; never mutates the supplied diagnostic shape."""
    errors = []

    def add(codes, **location):
        if codes:
            errors.append({**location, "codes": codes})

    add(["pass_with_issues"] if wire.verdict == "pass" and wire.issues else [])
    add(["revision_without_issues"] if wire.verdict == "needs_revision" and not wire.issues else [])
    add(["both_inference_audits_required"] if {a.kind for a in wire.audits} !=
        {"metric_to_ability", "cohort_comparison"} else [])
    blocks = report_blocks(report)
    inventory = [b["block_id"] for b in blocks]
    inventory_valid = [r[0] for r in wire.coverage] == inventory
    add([] if inventory_valid else ["coverage_inventory_mismatch"])
    for ai, audit in enumerate(wire.audits):
        expected = ("unsupported" if any(c.status == "unsupported" for c in audit.claims)
                    else "supported" if audit.claims else "not_applicable")
        add([] if audit.status == expected else ["audit_claim_aggregate_mismatch"], audit_index=ai)
        for ci, claim in enumerate(audit.claims):
            codes = []
            exact = [i for i in wire.issues if i.quote == claim.quote]
            if claim.scope == "ambiguous":
                if not any(i.category == "other" for i in exact):
                    codes.append("ambiguous_exact_other_issue_missing")
                if wire.verdict == "pass":
                    codes.append("ambiguous_requires_nonpass")
            if claim.status == "unsupported":
                if not exact:
                    codes.append("unsupported_exact_issue_missing")
                if wire.verdict == "pass":
                    codes.append("unsupported_requires_nonpass")
            if check_anchors and claim.scope_anchor not in claim.quote:
                codes.append("scope_anchor_not_in_quote")
            if check_anchors and claim.scope == "selected_sample" and not SAMPLE_ANCHOR.search(claim.scope_anchor):
                codes.append("selected_sample_anchor_missing")
            if any(ref not in facts for ref in claim.evidence_refs):
                codes.append("unknown_evidence_ref")
            if not any(claim.quote in b["text"] for b in blocks):
                codes.append("quote_not_in_single_block")
            add(codes, audit_index=ai, claim_index=ci, quote_excerpt=claim.quote[:80])
        if not inventory_valid:
            continue  # No positional joining against stale/reordered inventories.
        column = 1 if audit.kind == "metric_to_ability" else 2
        statuses = [STATUS[r[column]] for r in wire.coverage]
        aggregate = ("unsupported" if "unsupported" in statuses else
                     "supported" if "supported" in statuses else "not_applicable")
        add([] if aggregate == audit.status else ["coverage_audit_aggregate_mismatch"], audit_index=ai)
        for bi, (block, status) in enumerate(zip(blocks, statuses)):
            claims = [c for c in audit.claims if c.quote in block["text"]]
            codes = []
            if (status == "unsupported") != any(c.status == "unsupported" for c in claims):
                codes.append("coverage_unsupported_claim_mismatch")
            if status == "not_applicable" and claims:
                codes.append("coverage_applicable_claim_mismatch")
            add(codes, audit_index=ai, block_index=bi)
    if inventory_valid:
        for bi, (block, row) in enumerate(zip(blocks, wire.coverage)):
            ambiguous = any(c.scope == "ambiguous" and c.quote in block["text"]
                            for a in wire.audits for c in a.claims)
            add([] if row[3] == ambiguous else ["scope_coverage_claim_mismatch"], block_index=bi)
    return errors


def bounded_feedback(errors):
    """At most 12 rows and 3000 JSON characters, including omission count.

    Evidence keys stay in the original fact registry; duplicating an unbounded
    registry here would defeat the feedback size limit.
    """
    result = {"errors": [], "omitted_errors": len(errors)}
    for row in errors:
        candidate = {"errors": [*result["errors"], row],
                     "omitted_errors": result["omitted_errors"] - 1}
        if len(candidate["errors"]) <= 12 and len(json.dumps(candidate, ensure_ascii=False)) <= 3000:
            result = candidate
    return result
