"""Offline numeric operations candidate; no runtime identity is issued here."""
from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.golden_fact_candidate import FactClaim, FactAudit, FactEvaluation, NUMBER, _number_at
from app.evaluation.golden_compact_coverage import Rows, ROWS, STATUS
from app.evaluation.golden_inference_scope import validate_scope
from app.evaluation.golden_inference_scope_v5 import strict_json

Ref = Annotated[str, Field(min_length=1, max_length=160)]
Path = Annotated[str, Field(pattern=r"^(?:/[A-Za-z0-9_]+)+$", max_length=160)]


class OperationBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["value", "difference", "percent", "ratio_percent"]
    operands: list[tuple[Ref, Path]] = Field(min_length=1, max_length=2)
    token: str = Field(pattern=r"^[+-]?[0-9]+(?:\.[0-9]+)?$", max_length=32)

    @model_validator(mode="after")
    def arity(self):
        if len(self.operands) != (2 if self.op in ("difference", "ratio_percent") else 1):
            raise ValueError("numeric_operation_arity_invalid")
        return self


class OperationClaim(FactClaim):
    numeric_bindings: list[OperationBinding] = Field(max_length=24)


class OperationAudit(FactAudit):
    claims: list[OperationClaim] = Field(max_length=24)


class OperationEvaluation(FactEvaluation):
    audits: list[OperationAudit] = Field(min_length=2, max_length=2)


class OperationWire(OperationEvaluation):
    coverage: Rows


def _metric_path(ref, path):
    if ref.startswith("role:") and path == "/mean":
        return ref.rsplit(":", 1)[-1]
    return path.rsplit("/", 1)[-1]


def operation_value(binding, claim, pack):
    values = []
    for ref, path in binding.operands:
        if ref not in claim.evidence_refs or ref not in pack["provenance"]:
            raise ValueError("numeric_binding_unreferenced_source")
        values.append(_number_at(pack["facts"][ref], path))
    if binding.op == "value":
        return values[0]
    if binding.op == "percent":
        # Only fractions explicitly represented as ratios may be scaled.
        ref, path = binding.operands[0]
        if not ref.startswith("facts:recent_match:") or path not in (
            "/kill_participation", "/damage_share", "/gold_share"
        ) or values[0] > 1:
            raise ValueError("numeric_percent_unit_invalid")
        return values[0] * 100
    left, right = binding.operands
    if _metric_path(*left) != _metric_path(*right):
        raise ValueError("numeric_operation_metric_mismatch")
    # A role-to-role comparison may vary outcome, but not silently mix roles.
    if left[0].startswith("role:") and right[0].startswith("role:") and left[0].split(":")[1] != right[0].split(":")[1]:
        raise ValueError("numeric_operation_role_mismatch")
    if binding.op == "difference":
        return values[0] - values[1]
    if values[1] == 0:
        raise ValueError("numeric_operation_zero_denominator")
    return values[0] / values[1] * 100


def validate_operations(payload, report, pack):
    validate_scope(payload, report, pack["facts"])
    for audit in payload.audits:
        for claim in audit.claims:
            tokens = NUMBER.findall(claim.quote)
            for binding in claim.numeric_bindings:
                actual = operation_value(binding, claim, pack)
                if binding.token not in tokens:
                    raise ValueError("numeric_binding_token_not_in_quote")
                places = len(binding.token.split(".")[1]) if "." in binding.token else 0
                if places > 6:
                    raise ValueError("numeric_binding_precision_unsupported")
                if actual.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) != Decimal(binding.token) and claim.status == "supported":
                    raise ValueError("numeric_binding_value_mismatch")
            if claim.claim_kind == "direct_result" and set(tokens) != {b.token for b in claim.numeric_bindings}:
                raise ValueError("direct_result_unbound_number")
    return {"structural_validation": "passed", "semantic_approval": False}


def expand_operations(raw, report, pack):
    value = strict_json(raw)
    if not isinstance(value, dict) or "coverage" not in value:
        raise ValueError("compact_coverage_missing")
    rows = ROWS.validate_json(json.dumps(value["coverage"]), strict=True)
    value["coverage"] = [dict(block_id=b, metric_to_ability=STATUS[m], cohort_comparison=STATUS[c], scope_ambiguous=a)
                         for b, m, c, a in rows]
    payload = OperationEvaluation.model_validate_json(json.dumps(value), strict=True)
    validate_operations(payload, report, pack)
    return payload
