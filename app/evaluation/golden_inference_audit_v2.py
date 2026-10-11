"""Per-claim status for mixed supported and unsupported statements; v1 is frozen."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from pydantic import Field, model_validator
from typing import Literal
from app.evaluation.golden_inference_audit import (AuditedClaim, InferenceAudit, INFERENCE_POLICY as V1_POLICY, inference_facts, validate_audit_anchors, inference_component_fingerprints as v1_fingerprints)
from app.evaluation.coach_grounded_contract import EvaluationResponseModelV12
from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.providers.structured import contract_for_model

INFERENCE_POLICY_ID = "golden-inference-audit-v2"
INFERENCE_POLICY = V1_POLICY.replace("golden-inference-audit-v1", INFERENCE_POLICY_ID) + """
每个claim单独填写status=supported或unsupported；同一类审查允许同时包含正确和错误原句。
audit.status由claims推导：任一claim unsupported则整类unsupported；全部supported则supported；无claim才not_applicable。
只有unsupported的claim必须匹配issues；不得为了满足整类unsupported而把正确免责声明列为错误。
"""

class AuditedClaimV2(AuditedClaim):
    status: Literal["supported", "unsupported"]

class InferenceAuditV2(InferenceAudit):
    claims: list[AuditedClaimV2] = Field(max_length=24)

    @model_validator(mode="after")
    def aggregate_status(self):
        expected = "unsupported" if any(c.status == "unsupported" for c in self.claims) else "supported" if self.claims else "not_applicable"
        if self.status != expected:
            raise ValueError("audit_status_must_match_claim_statuses")
        return self

class EvaluationResponseModelV14(EvaluationResponseModelV12):
    audits: list[InferenceAuditV2] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def consistent_claims(self):
        if {a.kind for a in self.audits} != {"metric_to_ability", "cohort_comparison"}:
            raise ValueError("both_inference_audits_required")
        for audit in self.audits:
            for claim in audit.claims:
                if claim.status == "unsupported" and (self.verdict == "pass" or not any(i.quote == claim.quote for i in self.issues)):
                    raise ValueError("unsupported_claim_requires_issue_and_nonpass")
        return self

def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.4.0", output_model=EvaluationResponseModelV14)

def audit_prompt(prompt, old_contract):
    old = json.dumps(old_contract.schema_dict(), ensure_ascii=False, indent=2)
    if old not in prompt: raise ValueError("inference_schema_replacement_missing")
    return INFERENCE_POLICY + "\n\n" + prompt.replace(old, json.dumps(inference_response_contract().schema_dict(), ensure_ascii=False, indent=2), 1)

def inference_component_fingerprints(skill):
    rows = list(v1_fingerprints(skill))
    values = {"evaluation_schema": inference_response_contract().schema_dict(), "inference_v2_implementation": hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest()}
    for key, value in values.items():
        row = ComponentFingerprint(component_id=key, source="app.evaluation.golden_inference_audit_v2:" + key, sha256=hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
        rows = [row if old.component_id == key else old for old in rows] if any(old.component_id == key for old in rows) else [*rows, row]
    return tuple(rows)
