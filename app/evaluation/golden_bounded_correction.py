"""Offline, source-bound review corrections. Not a registered Coach candidate.

An immutable first review is edited explicitly, never regenerated implicitly.
Canonical validation still runs over the complete merged result. Source checks
cannot prove semantic entailment; real contrastive controls remain necessary.
"""
from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Literal

from pydantic import Field

from app.evaluation.golden_context_review import ClaimRef, IssueRef, ContextWire, expand_context
from app.evaluation.golden_context_diagnostics import collect_diagnostics
from app.evaluation.golden_integrated_review import ReviewInput, Strict
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_scope_diagnostics import bounded_feedback


class ClaimEdit(Strict):
    target_id: str = Field(pattern=r"^c[0-9]{3}$")
    value: ClaimRef
    reason: str = Field(min_length=1, max_length=500)


class IssueEdit(Strict):
    target_id: str = Field(pattern=r"^i[0-9]{3}$")
    value: IssueRef | None
    reason: str = Field(min_length=1, max_length=500)
    resolution_evidence_refs: list[int] = Field(max_length=12)


class MeaningWitness(Strict):
    disposition: Literal["literal", "defined", "negated", "clarify", "unsupported", "navigation"]
    language_ref: QuoteRef | None
    explanation: str = Field(min_length=1, max_length=500)


class MeaningReview(MeaningWitness):
    target_id: str = Field(pattern=r"^[ch][0-9]{3}$")


class AddedClaim(Strict):
    audit: Literal["metric_to_ability", "cohort_comparison"]
    value: ClaimRef
    meaning: MeaningWitness


class HeadingEdit(Strict):
    target_id: str = Field(pattern=r"^h[0-9]{3}$")
    kind: Literal["navigation", "assertion"]
    reason: str = Field(min_length=1, max_length=500)


class Correction(Strict):
    claim_edits: list[ClaimEdit] = Field(max_length=16)
    issue_edits: list[IssueEdit] = Field(max_length=12)
    added_claims: list[AddedClaim] = Field(max_length=16)
    added_issues: list[IssueRef] = Field(max_length=16)
    heading_edits: list[HeadingEdit] = Field(max_length=16)
    meaning_reviews: list[MeaningReview] = Field(max_length=64)
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    summary: str = Field(min_length=1, max_length=1200)
    passed_checks: list[str] = Field(max_length=12)


@dataclass(frozen=True)
class ReviewState:
    inputs: ReviewInput
    raw: str
    state_id: str
    entries_json: str
    mutable_claims: tuple[str, ...]
    required_reviews: tuple[str, ...]
    diagnostics_json: str

    def entries(self):
        return strict_json(self.entries_json)


def _security(value, inputs):
    if not isinstance(value, dict):
        return
    for key in ("issues", "added_issues"):
        rows = value.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            try:
                issue = IssueRef.model_validate(row, strict=True)
                inputs.source.resolve(issue.quote_ref.model_dump())
            except (ValueError, TypeError):
                continue
            if issue.category == "prompt_injection" and issue.severity == "high":
                raise ValueError("correction_security_terminal")


def prepare_state(raw, inputs, *, review_all_claims=False, diagnose=collect_diagnostics):
    value = strict_json(raw)
    _security(value, inputs)
    wire = ContextWire.model_validate(value, strict=True)
    if wire.source_digest != inputs.source.source_digest:
        raise ValueError("correction_source_changed")
    if wire.reviewed_blocks != list(range(1, len(inputs.source.blocks)+1)):
        raise ValueError("correction_inventory_not_patchable")
    expected_headings = [i for i, (_, text) in enumerate(inputs.source.blocks, 1) if re.match(r"^#{1,6}\s", text)]
    if [h.block_id for h in wire.heading_reviews] != expected_headings:
        raise ValueError("correction_heading_inventory_not_patchable")
    if [a.kind for a in wire.audits] != ["metric_to_ability", "cohort_comparison"]:
        raise ValueError("correction_audit_inventory_invalid")
    diagnostics = diagnose(raw, inputs.source.report, strict_json(inputs.pack_json))
    diagnosed = {(d.get("audit_index"), d.get("claim_index")) for d in diagnostics}
    entries, mutable, required, issue_quotes = {}, [], [], set()
    for i, issue in enumerate(wire.issues, 1):
        quote = inputs.source.resolve(issue.quote_ref.model_dump())
        issue_quotes.add(quote)
        entries[f"i{i:03}"] = dict(type="issue", index=i-1, value=value["issues"][i-1])
    n = 0
    for ai, audit in enumerate(wire.audits):
        for ci, claim in enumerate(audit.claims):
            quote = inputs.source.resolve(claim.quote_ref.model_dump())
            n += 1
            key = f"c{n:03}"
            entries[key] = dict(type="claim", audit_index=ai, claim_index=ci, value=value["audits"][ai]["claims"][ci])
            if review_all_claims or claim.claim_kind == "inference" or (ai, ci) in diagnosed or quote in issue_quotes:
                mutable.append(key)
                required.append(key)
    for i, heading in enumerate(wire.heading_reviews, 1):
        key = f"h{i:03}"
        entries[key] = dict(type="heading", index=i-1, value=value["heading_reviews"][i-1])
        required.append(key)
    if len(required) > 64:
        raise ValueError("correction_review_limit")
    identity = digest(compact(dict(raw=raw, inputs=inputs.data_json)))
    return ReviewState(inputs, raw, identity, compact(entries), tuple(mutable), tuple(required),
        compact(bounded_feedback(diagnostics)))


def _same_source(old, new, source):
    before, after = source.resolve(old), source.resolve(new)
    if old["block"] != new["block"] or before not in after:
        raise ValueError("correction_cannot_reassign_or_shrink_source")


def _unique(rows):
    result = {}
    for row in rows:
        if row.target_id in result:
            raise ValueError("correction_duplicate_target")
        result[row.target_id] = row
    return result


def _check_meaning(review, claim, source):
    disposition = review.disposition
    if disposition == "navigation":
        raise ValueError("correction_claim_cannot_be_navigation")
    expected = {"literal": None, "defined": "selected_sample", "negated": "question_or_negation",
                "clarify": "ambiguous", "unsupported": "beyond_sample"}[disposition]
    if claim["scope"] != expected or (disposition == "literal") != (claim["claim_kind"] == "direct_result"):
        raise ValueError("correction_meaning_does_not_match_final_claim")
    if disposition == "unsupported" and claim["status"] != "unsupported":
        raise ValueError("correction_unsupported_must_remain_unsupported")
    if disposition in {"defined", "negated"}:
        if review.language_ref is None:
            raise ValueError("correction_language_evidence_required")
        language = source.resolve(review.language_ref.model_dump())
        context = claim.get("context")
        anchor_ref = context["quote_ref"] if context else claim["quote_ref"]
        if review.language_ref.block != anchor_ref["block"]:
            raise ValueError("correction_language_source_mismatch")
        anchor_text = source.resolve(anchor_ref)
        if language not in anchor_text or not claim["scope_anchor"] or claim["scope_anchor"] not in language:
            raise ValueError("correction_language_must_support_claim_context")
    elif review.language_ref is not None:
        raise ValueError("correction_unexpected_language_evidence")


def apply_correction(state, raw, *, inputs, prepare=prepare_state, expand=expand_context):
    """Offline merge; a future caller must first verify its actual exchange.

    Return both a fully validated result and an explicit edit journal. No old
    file is rewritten and no invalid partial result is exposed as accepted.
    """
    if state.inputs != inputs or prepare(state.raw, inputs) != state:
        raise ValueError("correction_state_changed")
    value = strict_json(raw)
    _security(value, inputs)
    patch = Correction.model_validate(value, strict=True)
    _security({"issues": [e.value.model_dump(mode="json") for e in patch.issue_edits if e.value]}, inputs)
    entries = state.entries()
    merged = deepcopy(strict_json(state.raw))
    reviews = _unique(patch.meaning_reviews)
    if set(reviews) != set(state.required_reviews):
        raise ValueError("correction_meaning_inventory_mismatch")
    edits, resolutions = [], []
    for key, edit in _unique(patch.claim_edits).items():
        if key not in state.mutable_claims:
            raise ValueError("correction_claim_not_mutable")
        old = entries[key]
        new = edit.value.model_dump(mode="json")
        _same_source(old["value"]["quote_ref"], new["quote_ref"], inputs.source)
        merged["audits"][old["audit_index"]]["claims"][old["claim_index"]] = new
        edits.append(dict(target_id=key, before=old["value"], after=new, reason=edit.reason))
    issue_changes = _unique(patch.issue_edits)
    for key, edit in issue_changes.items():
        if key not in entries or entries[key]["type"] != "issue":
            raise ValueError("correction_unknown_issue")
        refs = edit.resolution_evidence_refs
        if len(set(refs)) != len(refs) or any(type(n) is not int or not 1 <= n <= len(inputs.source.evidence_keys) for n in refs):
            raise ValueError("correction_resolution_source_invalid")
        before = entries[key]["value"]
        after = edit.value.model_dump(mode="json") if edit.value else None
        if after:
            _same_source(before["quote_ref"], after["quote_ref"], inputs.source)
        if before["category"] != "other" and (after is None or after != before) and not refs:
            raise ValueError("correction_fact_issue_resolution_needs_evidence")
        resolutions.append(dict(target_id=key, before=before, after=after, reason=edit.reason,
            resolution_evidence_refs=refs))
    merged["issues"] = [issue_changes[f"i{i:03}"].value.model_dump(mode="json")
        if f"i{i:03}" in issue_changes else issue
        for i, issue in enumerate(merged["issues"], 1)
        if f"i{i:03}" not in issue_changes or issue_changes[f"i{i:03}"].value is not None]
    for key, edit in _unique(patch.heading_edits).items():
        if key not in entries or entries[key]["type"] != "heading":
            raise ValueError("correction_unknown_heading")
        old = entries[key]
        merged["heading_reviews"][old["index"]]["kind"] = edit.kind
        edits.append(dict(target_id=key, before=old["value"],
            after=merged["heading_reviews"][old["index"]], reason=edit.reason))
    for extra in patch.added_claims:
        inputs.source.resolve(extra.value.quote_ref.model_dump())
        _check_meaning(extra.meaning, extra.value.model_dump(mode="json"), inputs.source)
        next(a for a in merged["audits"] if a["kind"] == extra.audit)["claims"].append(extra.value.model_dump(mode="json"))
    merged["issues"].extend(i.model_dump(mode="json") for i in patch.added_issues)
    for key, review in reviews.items():
        entry = entries[key]
        if entry["type"] == "claim":
            claim = merged["audits"][entry["audit_index"]]["claims"][entry["claim_index"]]
            _check_meaning(review, claim, inputs.source)
        else:
            heading = merged["heading_reviews"][entry["index"]]
            if heading["kind"] == "navigation":
                if review.disposition != "navigation" or review.language_ref is not None:
                    raise ValueError("correction_navigation_review_mismatch")
            else:
                claims = [c for a in merged["audits"] for c in a["claims"]
                    if c["quote_ref"]["block"] == heading["block_id"]
                    and inputs.source.resolve(c["quote_ref"]) == inputs.source.blocks[heading["block_id"]-1][1]]
                if not claims:
                    raise ValueError("correction_heading_claim_missing")
                for claim in claims:
                    _check_meaning(review, claim, inputs.source)
    for field in ("score", "verdict", "summary", "passed_checks"):
        merged[field] = getattr(patch, field)
    # Additions and edits must satisfy every old numerical/source/issue/coverage
    # rule together. An unchanged numeric defect is not forgiven by scope success.
    result = expand(compact(merged), inputs.source.report, strict_json(inputs.pack_json))
    return result, dict(state_id=state.state_id, edits=edits, issue_resolutions=resolutions,
        added_claims=[r.model_dump(mode="json") for r in patch.added_claims],
        added_issues=[r.model_dump(mode="json") for r in patch.added_issues],
        meaning_reviews=[r.model_dump(mode="json") for r in patch.meaning_reviews],
        semantic_approval=False)
