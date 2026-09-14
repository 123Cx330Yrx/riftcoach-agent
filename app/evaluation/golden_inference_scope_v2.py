"""Scope v2: selected-sample claims must carry an explicit local anchor."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from pydantic import Field, model_validator
from app.evaluation.golden_inference_scope import (
    SCOPE_POLICY, ScopedAudit, ScopedClaim, ScopedBlock, EvaluationResponseModelV16,
    report_blocks, validate_scope, inference_component_fingerprints as scope_fingerprints,
)
from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.providers.structured import contract_for_model

SCOPE_V2_POLICY_ID = "golden-inference-scope-v2"
SCOPE_V2_POLICY = SCOPE_POLICY + """
范围锚点规则 golden-inference-scope-v2：每条claim必须给出scope_anchor，且该短语必须逐字出现在quote中。
scope=selected_sample时，scope_anchor必须是明确的局部范围表达（如本次、样本、所选、这四场、4场、n=4、4局），
不能只写“同位置”“输局”或从报告其他段落借用全局免责声明。没有明确锚点时应标ambiguous并带澄清issue。
这不是按词拒绝“稳定”：明确写“这四场方向稳定”可以supported；长期外推仍属beyond_sample。
"""
_ANCHOR = re.compile(r"(?:本次|样本|所选|这[一二三四五六七八九十0-9]+[场局]|[0-9]+[场局]|n\s*[=:：]\s*[0-9]+)")


class AnchoredClaim(ScopedClaim):
    scope_anchor: str = Field(min_length=1, max_length=120)


class AnchoredAudit(ScopedAudit):
    claims: list[AnchoredClaim] = Field(max_length=24)


class EvaluationResponseModelV17(EvaluationResponseModelV16):
    audits: list[AnchoredAudit] = Field(min_length=2, max_length=2)
    coverage: list[ScopedBlock] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def scope_anchors_are_local_and_literal(self):
        for audit in self.audits:
            for claim in audit.claims:
                if claim.scope_anchor not in claim.quote:
                    raise ValueError("scope_anchor_must_be_in_claim_quote")
                if claim.scope == "selected_sample" and not _ANCHOR.search(claim.scope_anchor):
                    raise ValueError("selected_sample_scope_anchor_missing")
        return self


def validate_scope_v2(payload, report, facts):
    validate_scope(payload, report, facts)
    for audit in payload.audits:
        for claim in audit.claims:
            if claim.scope_anchor not in claim.quote:
                raise ValueError("scope_anchor_must_be_in_claim_quote")
            if claim.scope == "selected_sample" and not _ANCHOR.search(claim.scope_anchor):
                raise ValueError("selected_sample_scope_anchor_missing")


def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.7.0", output_model=EvaluationResponseModelV17)


def audit_prompt(prompt, old_contract):
    old = json.dumps(old_contract.schema_dict(), ensure_ascii=False, indent=2)
    if old not in prompt:
        raise ValueError("inference_schema_replacement_missing")
    return SCOPE_V2_POLICY + "\n\n" + prompt.replace(old, json.dumps(inference_response_contract().schema_dict(), ensure_ascii=False, separators=(",", ":")), 1)


def inference_component_fingerprints(skill):
    rows = list(scope_fingerprints(skill))
    for key, value in (("evaluation_schema", json.dumps(inference_response_contract().schema_dict(), sort_keys=True)),
                       ("scope_v2_implementation", Path(__file__).read_text(encoding="utf-8"))):
        row = ComponentFingerprint(component_id=key, source="app.evaluation.golden_inference_scope_v2:" + key,
                                   sha256=hashlib.sha256(value.encode()).hexdigest())
        rows = [row if old.component_id == key else old for old in rows] if any(old.component_id == key for old in rows) else [*rows, row]
    return tuple(rows)
