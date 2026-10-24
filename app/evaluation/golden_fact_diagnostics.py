"""Bounded diagnostics for fact operations, separate from acceptance."""
from decimal import Decimal, ROUND_HALF_UP
from pydantic import ValidationError

from app.evaluation.golden_fact_operations import OperationBinding, OperationClaim, OperationAudit, OperationWire, operation_value
from app.evaluation.golden_fact_candidate import NUMBER
from app.evaluation.golden_inference_scope_v5 import strict_json, SAMPLE_ANCHOR
from app.evaluation.golden_scope_diagnostics import _shape, collect_relations

_Binding = _shape("FactDiagnosticBinding", OperationBinding)
_Claim = _shape("FactDiagnosticClaim", OperationClaim, {"numeric_bindings": list[_Binding]})
_Audit = _shape("FactDiagnosticAudit", OperationAudit, {"claims": list[_Claim]})
_Wire = _shape("FactDiagnosticWire", OperationWire, {"audits": list[_Audit]})
_NUMERIC_CODES = {
    "numeric_binding_unreferenced_source", "numeric_binding_path_missing", "numeric_binding_value_invalid",
    "numeric_percent_unit_invalid", "numeric_operation_metric_mismatch", "numeric_operation_role_mismatch",
    "numeric_operation_zero_denominator",
}


def collect_diagnostics(raw, report, pack):
    try:
        strict_json(raw)
        wire = _Wire.model_validate_json(raw, strict=True)
    except (ValueError, TypeError):
        return [{"codes": ["invalid_json_or_schema"]}]
    rows = collect_relations(wire, report, pack["facts"], check_anchors=False)
    for ai, audit in enumerate(wire.audits):
        for ci, claim in enumerate(audit.claims):
            codes = []
            if claim.claim_kind == "direct_result":
                if claim.scope is not None or claim.scope_anchor is not None:
                    codes.append("direct_result_scope_must_be_null")
                if not claim.numeric_bindings:
                    codes.append("direct_result_numeric_binding_required")
                if set(NUMBER.findall(claim.quote)) != {b.token for b in claim.numeric_bindings}:
                    codes.append("direct_result_unbound_number")
            else:
                if not claim.scope or not claim.scope_anchor or claim.scope_anchor not in claim.quote:
                    codes.append("inference_literal_scope_required")
                if claim.scope == "selected_sample" and not SAMPLE_ANCHOR.search(claim.scope_anchor or ""):
                    codes.append("selected_sample_anchor_missing")
            location = dict(audit_index=ai, claim_index=ci, quote_excerpt=claim.quote[:80])
            if codes:
                rows.append({**location, "codes": codes})
            for bi, binding in enumerate(claim.numeric_bindings):
                codes = []
                try:
                    typed = OperationBinding.model_validate(binding.model_dump())
                except ValidationError:
                    codes.append("numeric_operation_arity_invalid")
                else:
                    try:
                        actual = operation_value(typed, claim, pack)
                    except ValueError as error:
                        code = str(error)
                        codes.append(code if code in _NUMERIC_CODES else "numeric_binding_invalid")
                    else:
                        places = len(binding.token.split(".")[1]) if "." in binding.token else 0
                        if places > 6:
                            codes.append("numeric_binding_precision_unsupported")
                        elif actual.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) != Decimal(binding.token) and claim.status == "supported":
                            codes.append("numeric_binding_value_mismatch")
                if binding.token not in NUMBER.findall(claim.quote):
                    codes.append("numeric_binding_token_not_in_quote")
                if codes:
                    rows.append({**location, "binding_index": bi, "codes": codes})
    return rows
