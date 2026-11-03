"""Evidence-level model output with local numeric support verification."""
import json
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.golden_inference_audit_v2 import AuditedClaimV2, InferenceAuditV2
from app.evaluation.golden_inference_scope import Scope, EvaluationResponseModelV16, validate_scope
from app.evaluation.golden_inference_scope_v5 import SAMPLE_ANCHOR as PREVIOUS_SAMPLE_ANCHOR, strict_json
from app.evaluation.golden_compact_coverage import Rows, ROWS, STATUS
from app.evaluation.golden_numeric_evidence_v4 import numeric_support
from app.evaluation.golden_scope_diagnostics import _shape, collect_relations


SAMPLE_ANCHOR = re.compile(PREVIOUS_SAMPLE_ANCHOR.pattern + r"|上表|单局(?![势面部限])")


def table_anchor_valid(claim, report):
    if claim.scope != "selected_sample" or "上表" not in (claim.scope_anchor or ""):
        return True
    start = report.find(claim.quote)
    return start >= 0 and bool(re.search(r"(?m)^\|.+\|[ \t]*$", report[:start]))


class EvidenceClaim(AuditedClaimV2):
    claim_kind: Literal["direct_result", "inference"]
    scope: Scope | None
    scope_anchor: str | None = Field(max_length=20)

    @model_validator(mode="after")
    def representation(self):
        if self.claim_kind == "direct_result":
            if self.scope is not None or self.scope_anchor is not None:
                raise ValueError("direct_result_scope_must_be_null")
        elif not self.scope or not self.scope_anchor or self.scope_anchor not in self.quote:
            raise ValueError("inference_literal_scope_required")
        elif self.scope == "selected_sample" and not SAMPLE_ANCHOR.search(self.scope_anchor):
            raise ValueError("selected_sample_anchor_missing")
        return self


class EvidenceAudit(InferenceAuditV2):
    claims: list[EvidenceClaim] = Field(max_length=24)


class EvidenceEvaluation(EvaluationResponseModelV16):
    audits: list[EvidenceAudit] = Field(min_length=2, max_length=2)


class WireAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["metric_to_ability", "cohort_comparison"]
    claims: list[EvidenceClaim] = Field(max_length=24)


from app.evaluation.coach_report import EvaluationResponseModelV11
from app.evaluation.golden_inference_coverage import report_blocks


class EvidenceWire(EvaluationResponseModelV11):
    audits: list[WireAudit] = Field(min_length=2, max_length=2)
    reviewed_blocks: list[str] = Field(min_length=1, max_length=64)


def normalize_json(raw):
    # Preserve raw journal evidence; only tolerate a formatting-only suffix.
    if not isinstance(raw, str):
        return raw
    candidate = raw.lstrip()
    try:
        value, end = json.JSONDecoder().raw_decode(candidate)
    except ValueError:
        return raw
    suffix = candidate[end:]
    if isinstance(value, dict) and re.fullmatch(r"[ \t\r\n]*`{1,3}[ \t\r\n]*", suffix):
        return candidate[:end]
    return raw


def derived_wire(raw, report):
    value = strict_json(normalize_json(raw))
    blocks = report_blocks(report)
    if value.get("reviewed_blocks") != [b["block_id"] for b in blocks]:
        raise ValueError("reviewed_block_inventory_mismatch")
    value.pop("reviewed_blocks")
    for audit in value["audits"]:
        claims = audit["claims"]
        audit["status"] = "unsupported" if any(c["status"] == "unsupported" for c in claims) else "supported" if claims else "not_applicable"
    rows = []
    for block in blocks:
        statuses = []
        ambiguous = False
        for kind in ("metric_to_ability", "cohort_comparison"):
            claims = [c for a in value["audits"] if a["kind"] == kind for c in a["claims"] if c["quote"] in block["text"]]
            statuses.append("U" if any(c["status"] == "unsupported" for c in claims) else "S" if claims else "N")
            ambiguous = ambiguous or any(c["scope"] == "ambiguous" for c in claims)
        rows.append([block["block_id"], *statuses, ambiguous])
    value["coverage"] = rows
    return value


def expand_evidence(raw, report, pack):
    normalized = normalize_json(raw)
    EvidenceWire.model_validate_json(normalized, strict=True)
    value = derived_wire(normalized, report)
    rows = ROWS.validate_json(json.dumps(value["coverage"]), strict=True)
    value["coverage"] = [dict(block_id=b, metric_to_ability=STATUS[m], cohort_comparison=STATUS[c], scope_ambiguous=a)
                         for b, m, c, a in rows]
    payload = EvidenceEvaluation.model_validate_json(json.dumps(value), strict=True)
    validate_scope(payload, report, pack["facts"])
    for audit in payload.audits:
        for claim in audit.claims:
            if not table_anchor_valid(claim, report):
                raise ValueError("table_scope_antecedent_missing")
            if claim.claim_kind != "direct_result":
                continue
            if not any(ref in pack["provenance"] for ref in claim.evidence_refs):
                raise ValueError("direct_result_value_source_required")
            if claim.status == "supported" and any(not r["supported"] for r in numeric_support(claim, pack)):
                raise ValueError("direct_result_number_not_in_evidence")
    return payload


_Claim = _shape("EvidenceDiagnosticClaim", EvidenceClaim)
_Audit = _shape("EvidenceDiagnosticAudit", EvidenceAudit, {"claims": list[_Claim]})
from app.evaluation.golden_evidence_scope_v3 import _Wire



def collect_diagnostics(raw, report, pack):
    try:
        value = derived_wire(raw, report)
        wire = _Wire.model_validate_json(json.dumps(value), strict=True)
    except (ValueError, TypeError, KeyError, AttributeError):
        return [{"codes": ["invalid_json_or_schema_or_review_inventory"]}]
    rows = collect_relations(wire, report, pack["facts"], check_anchors=False)
    for ai, audit in enumerate(wire.audits):
        for ci, claim in enumerate(audit.claims):
            codes = []
            if not table_anchor_valid(claim, report):
                codes.append("table_scope_antecedent_missing")
            if claim.claim_kind == "direct_result":
                if claim.scope is not None or claim.scope_anchor is not None:
                    codes.append("direct_result_scope_must_be_null")
                if not any(ref in pack["provenance"] for ref in claim.evidence_refs):
                    codes.append("direct_result_value_source_required")
                if claim.status == "supported" and any(not r["supported"] for r in numeric_support(claim, pack)):
                    codes.append("direct_result_number_not_in_evidence")
            else:
                if not claim.scope or not claim.scope_anchor or claim.scope_anchor not in claim.quote:
                    codes.append("inference_literal_scope_required")
                if claim.scope == "selected_sample" and not SAMPLE_ANCHOR.search(claim.scope_anchor or ""):
                    codes.append("selected_sample_anchor_missing")
            if codes:
                rows.append(dict(audit_index=ai, claim_index=ci, quote_excerpt=claim.quote[:80], codes=codes))
    return rows
