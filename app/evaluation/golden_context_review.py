"""Explicit source references and contextual claims for the isolated 1.3.27 candidate.

References prove location, not semantic entailment. Historical validators remain
unchanged; the new canonical result retains both the claim and its context.
"""
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.coach_report import EvaluationResponseModelV11, EvaluationIssueSeverity, EvaluationIssueCategoryV11
from app.evaluation.golden_inference_audit_v2 import AuditedClaimV2, InferenceAuditV2
from app.evaluation.golden_inference_scope import Scope, EvaluationResponseModelV16, validate_scope
from app.evaluation.golden_evidence_scope_v5 import SAMPLE_ANCHOR, derived_wire, normalize_json, table_anchor_valid
from app.evaluation.golden_evidence_scope_v8 import heading_errors
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_numeric_evidence_v4 import numeric_support
from app.evaluation.golden_review_experiment import SourceIndex, QuoteRef, AnchorPatch, AnchorRepairPlan, compact, digest, _index
from app.evaluation.golden_compact_coverage import STATUS

Index = Annotated[int, Field(strict=True, ge=1)]


class ContextRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    quote_ref: QuoteRef
    relation: Literal["defines_scope", "negates"]
    explanation: str = Field(min_length=1, max_length=500)


class ClaimRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    quote_ref: QuoteRef
    evidence_refs: list[Index] = Field(min_length=1, max_length=12)
    explanation: str = Field(min_length=1, max_length=2000)
    status: Literal["supported", "unsupported"]
    claim_kind: Literal["direct_result", "inference"]
    scope: Scope | None
    scope_anchor: str | None = Field(max_length=20)
    context: ContextRef | None = None


class AuditRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["metric_to_ability", "cohort_comparison"]
    claims: list[ClaimRef] = Field(max_length=24)


class IssueRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    severity: EvaluationIssueSeverity
    category: EvaluationIssueCategoryV11
    quote_ref: QuoteRef
    evidence: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    suggested_correction: str = Field(min_length=1)


class HeadingRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    block_id: Index
    kind: Literal["navigation", "assertion"]


class ContextWire(EvaluationResponseModelV11):
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    issues: list[IssueRef]
    audits: list[AuditRef] = Field(min_length=2, max_length=2)
    reviewed_blocks: list[Index] = Field(min_length=1, max_length=64)
    heading_reviews: list[HeadingRef] = Field(max_length=64)


class ContextText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote: str = Field(min_length=1, max_length=2000)
    block_id: str
    relation: Literal["defines_scope", "negates"]
    explanation: str = Field(min_length=1, max_length=500)


class ContextClaim(AuditedClaimV2):
    block_id: str
    claim_kind: Literal["direct_result", "inference"]
    scope: Scope | None
    scope_anchor: str | None = Field(max_length=20)
    context: ContextText | None = None


class ContextAudit(InferenceAuditV2):
    claims: list[ContextClaim] = Field(max_length=24)


class ContextEvaluation(EvaluationResponseModelV16):
    audits: list[ContextAudit] = Field(min_length=2, max_length=2)


def restore(raw, report, pack):
    value = strict_json(normalize_json(raw))
    wire = ContextWire.model_validate(value, strict=True)
    source = SourceIndex.build(report, pack)
    if wire.source_digest != source.source_digest:
        raise ValueError("context_source_digest_mismatch")
    if wire.reviewed_blocks != list(range(1, len(source.blocks) + 1)):
        raise ValueError("reviewed_block_inventory_mismatch")
    value = wire.model_dump(mode="json")
    value.pop("source_digest")
    value["reviewed_blocks"] = [b for b, _ in source.blocks]
    for heading in value["heading_reviews"]:
        heading["block_id"] = _index(source.blocks, heading["block_id"])[0]
    for audit in value["audits"]:
        for claim in audit["claims"]:
            ref = claim.pop("quote_ref")
            claim["quote"] = source.resolve(ref)
            claim["block_id"] = _index(source.blocks, ref["block"])[0]
            claim["evidence_refs"] = [_index(source.evidence_keys, n) for n in claim["evidence_refs"]]
            if claim["context"]:
                context = claim["context"]
                ref = context.pop("quote_ref")
                context["quote"] = source.resolve(ref)
                context["block_id"] = _index(source.blocks, ref["block"])[0]
    for issue in value["issues"]:
        issue["quote"] = source.resolve(issue.pop("quote_ref"))
    return value


def expand_context(raw, report, pack, *, anchor_errors=None):
    value = restore(raw, report, pack)
    errors = heading_errors(value, report)
    if errors:
        raise ValueError(errors[0]["codes"][0])
    value.pop("heading_reviews")
    value = derived_wire(compact(value), report)
    value["coverage"] = [dict(block_id=b, metric_to_ability=STATUS[m], cohort_comparison=STATUS[c], scope_ambiguous=a)
                         for b, m, c, a in value["coverage"]]
    payload = ContextEvaluation.model_validate(value, strict=True)
    validate_scope(payload, report, pack["facts"])
    found_errors = []
    for ai, audit in enumerate(payload.audits):
        seen = set()
        for ci, claim in enumerate(audit.claims):
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
            context = claim.context
            if context:
                if context.block_id == claim.block_id and context.quote == claim.quote:
                    raise ValueError("context_must_add_explanatory_text")
                expected = "selected_sample" if context.relation == "defines_scope" else "question_or_negation"
                if claim.scope != expected:
                    raise ValueError("context_relation_scope_mismatch")
            anchor_text = context.quote if context else claim.quote
            valid = bool(claim.scope_anchor and claim.scope_anchor in anchor_text)
            if claim.scope == "selected_sample":
                valid = valid and bool(SAMPLE_ANCHOR.search(claim.scope_anchor))
            if not valid:
                # Only non-context anchor corrections can retain the existing
                # semantic judgments. Context changes require full reassessment.
                if context:
                    raise ValueError("context_anchor_invalid_requires_reassessment")
                found_errors.append((ai, ci))
            if not table_anchor_valid(claim, report):
                raise ValueError("table_scope_antecedent_missing")
    if anchor_errors is not None:
        anchor_errors.extend(found_errors)
    elif found_errors:
        raise ValueError("scope_anchor_invalid")
    return payload


def repair_plan(raw, report, pack):
    errors = []
    payload = expand_context(raw, report, pack, anchor_errors=errors)
    if any(i.category == "prompt_injection" for i in payload.issues) or not 1 <= len(errors) <= 4:
        raise ValueError("context_repair_requires_reassessment")
    return AnchorRepairPlan(digest(raw), SourceIndex.build(report, pack).source_digest, tuple(errors))


def apply_patch(raw, patch_raw, report, pack):
    plan = repair_plan(raw, report, pack)
    patch = AnchorPatch.model_validate(strict_json(patch_raw), strict=True)
    if (patch.base_digest, patch.source_digest) != (plan.base_digest, plan.source_digest):
        raise ValueError("context_patch_stale")
    if patch.mode == "needs_reassessment":
        raise ValueError("context_patch_requires_reassessment")
    targets = [(c.audit_index, c.claim_index) for c in patch.changes]
    if len(set(targets)) != len(targets) or set(targets) != set(plan.targets):
        raise ValueError("context_patch_wrong_targets")
    value = deepcopy(strict_json(normalize_json(raw)))
    for c in patch.changes:
        value["audits"][c.audit_index]["claims"][c.claim_index]["scope_anchor"] = c.scope_anchor
    return expand_context(compact(value), report, pack)
