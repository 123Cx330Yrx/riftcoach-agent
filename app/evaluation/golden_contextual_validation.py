"""Current candidate validation, isolated from frozen 1.3.27 fingerprints.

Reuse source restoration and scope checks. The validation walk is kept here
because changing the frozen context module would invalidate historical assets.
Only the numeric checker differs: it recognizes indexed external statistics.
"""
from app.evaluation import golden_context_review as context
from app.evaluation.golden_context_diagnostics import collect_diagnostics
from app.evaluation.golden_contextual_sources import numeric_support


def expand_context(raw, report, pack):
    value = context.restore(raw, report, pack)
    errors = context.heading_errors(value, report)
    if errors:
        raise ValueError(errors[0]["codes"][0])
    value.pop("heading_reviews")
    value = context.derived_wire(context.compact(value), report)
    value["coverage"] = [dict(block_id=b, metric_to_ability=context.STATUS[m],
        cohort_comparison=context.STATUS[c], scope_ambiguous=a)
        for b, m, c, a in value["coverage"]]
    payload = context.ContextEvaluation.model_validate(value, strict=True)
    context.validate_scope(payload, report, pack["facts"])
    for audit in payload.audits:
        seen = set()
        for claim in audit.claims:
            key = (claim.block_id, claim.quote)
            if key in seen:
                raise ValueError("duplicate_context_claim")
            seen.add(key)
            if len(set(claim.evidence_refs)) != len(claim.evidence_refs):
                raise ValueError("duplicate_evidence_reference")
            if claim.claim_kind == "direct_result":
                if claim.scope is not None or claim.scope_anchor is not None or claim.context is not None:
                    raise ValueError("direct_result_scope_must_be_null")
                if not any(ref in pack["provenance"] for ref in claim.evidence_refs):
                    raise ValueError("direct_result_value_source_required")
                if claim.status == "supported" and any(not r["supported"] for r in numeric_support(claim, pack)):
                    raise ValueError("direct_result_number_not_in_evidence")
                continue
            if claim.scope is None:
                raise ValueError("inference_scope_required")
            linked = claim.context
            if linked:
                if linked.block_id == claim.block_id and linked.quote == claim.quote:
                    raise ValueError("context_must_add_explanatory_text")
                expected = "selected_sample" if linked.relation == "defines_scope" else "question_or_negation"
                if claim.scope != expected:
                    raise ValueError("context_relation_scope_mismatch")
            anchor_text = linked.quote if linked else claim.quote
            valid = bool(claim.scope_anchor and claim.scope_anchor in anchor_text)
            if claim.scope == "selected_sample":
                valid = valid and bool(context.SAMPLE_ANCHOR.search(claim.scope_anchor))
            if not valid:
                raise ValueError("context_anchor_invalid_requires_reassessment" if linked else "scope_anchor_invalid")
            if not context.table_anchor_valid(claim, report):
                raise ValueError("table_scope_antecedent_missing")
    return payload


def diagnostics(raw, report, pack):
    return collect_diagnostics(raw, report, pack, expand=expand_context, numeric=numeric_support)
