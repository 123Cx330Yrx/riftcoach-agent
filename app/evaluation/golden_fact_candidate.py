"""Offline fact/scope candidate. Structural validity is never semantic approval."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.context import project_recent_form_facts
from app.evaluation.golden_inference_audit import inference_facts
from app.evaluation.golden_inference_audit_v2 import AuditedClaimV2, InferenceAuditV2
from app.evaluation.golden_inference_scope import EvaluationResponseModelV16, Scope, validate_scope
from app.evaluation.golden_inference_scope_v5 import SAMPLE_ANCHOR

NUMBER = re.compile(r"(?<![\w.])[+-]?[0-9]+(?:\.[0-9]+)?(?![\w.])", re.ASCII)


def fact_pack(summary):
    """One allowlisted value registry, plus source bindings without copied values.

    Generation's ten-row cap remains explicit; role aggregates use all selected
    rows as before. The digest binds the complete input, including row order.
    """
    facts = deepcopy(project_recent_form_facts(summary))
    facts.update(inference_facts(summary))
    rows = summary["matches"]
    ids = [r.get("match_id") for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("fact_candidate_match_identity_invalid")
    provenance = {}
    for key in facts:
        if key.startswith("facts:recent_match:"):
            index = int(key.rsplit(":", 1)[1])
            provenance[key] = {"source_path": f"/matches/{index}", "match_id": ids[index]}
        elif key.startswith("role:"):
            _, role, outcome, metric = key.split(":")
            indices = [i for i, r in enumerate(rows) if r.get("included_in_aggregate") is True
                       and r.get("role") == role and type(r.get("win")) is bool
                       and r["win"] == (outcome == "win")]
            provenance[key] = {"row_indices": indices, "metric": metric,
                               "operation": "mean_valid_nonnegative", "rounding": "half_even_6dp"}
        elif key == "facts:recent_aggregate":
            provenance[key] = {"source_path": "/recent_summary", "operation": "source_reported",
                               "recomputed": False}
    digest = hashlib.sha256(json.dumps(summary, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": "golden-fact-candidate-v1", "source_sha256": digest,
            "facts": facts, "provenance": provenance,
            "match_ids": ids, "semantic_approval": False}


class NumericBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_ref: str = Field(min_length=1, max_length=160)
    path: str = Field(pattern=r"^(?:/[A-Za-z0-9_]+)+$", max_length=160)
    token: str = Field(pattern=r"^[+-]?[0-9]+(?:\.[0-9]+)?$", max_length=32)


class FactClaim(AuditedClaimV2):
    claim_kind: Literal["direct_result", "inference"]
    scope: Scope | None
    scope_anchor: str | None = Field(max_length=20)
    numeric_bindings: list[NumericBinding] = Field(max_length=24)

    @model_validator(mode="after")
    def representation(self):
        if self.claim_kind == "direct_result":
            if self.scope is not None or self.scope_anchor is not None:
                raise ValueError("direct_result_scope_must_be_null")
            if not self.numeric_bindings:
                raise ValueError("direct_result_numeric_binding_required")
        else:
            if not self.scope or not self.scope_anchor or self.scope_anchor not in self.quote:
                raise ValueError("inference_literal_scope_required")
            if self.scope == "selected_sample" and not SAMPLE_ANCHOR.search(self.scope_anchor):
                raise ValueError("selected_sample_anchor_missing")
        return self


class FactAudit(InferenceAuditV2):
    claims: list[FactClaim] = Field(max_length=24)


class FactEvaluation(EvaluationResponseModelV16):
    audits: list[FactAudit] = Field(min_length=2, max_length=2)


def _number_at(value, path):
    for part in path.split("/")[1:]:
        if not isinstance(value, dict) or part not in value:
            raise ValueError("numeric_binding_path_missing")
        value = value[part]
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("numeric_binding_value_invalid")
    return Decimal(str(value))


def validate_candidate(payload, report, pack):
    """Validate references and reported numeric literals, not their prose meaning.

    Supports literal observations only. Differences, percent conversion, ranges,
    or other operations require an explicit future operation contract.
    """
    facts = pack["facts"]
    validate_scope(payload, report, facts)
    for audit in payload.audits:
        for claim in audit.claims:
            tokens = NUMBER.findall(claim.quote)
            for binding in claim.numeric_bindings:
                if binding.evidence_ref not in claim.evidence_refs or binding.evidence_ref not in pack["provenance"]:
                    raise ValueError("numeric_binding_unreferenced_source")
                actual = _number_at(facts[binding.evidence_ref], binding.path)
                if binding.token not in tokens:
                    raise ValueError("numeric_binding_token_not_in_quote")
                places = len(binding.token.split(".")[1]) if "." in binding.token else 0
                if places > 6:
                    raise ValueError("numeric_binding_precision_unsupported")
                rounded = actual.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
                if rounded != Decimal(binding.token) and claim.status == "supported":
                    raise ValueError("numeric_binding_value_mismatch")
            if claim.claim_kind == "direct_result" and set(tokens) != {b.token for b in claim.numeric_bindings}:
                raise ValueError("direct_result_unbound_number")
    return {"structural_validation": "passed", "semantic_approval": False}
