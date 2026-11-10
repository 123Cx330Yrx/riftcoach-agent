"""Opt-in scope clarification; frozen coverage v1 remains unchanged."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from app.evaluation.golden_inference_coverage import (
    COVERAGE_POLICY, BlockCoverage, EvaluationResponseModelV15, report_blocks,
    validate_coverage, inference_component_fingerprints as coverage_fingerprints,
)
from app.evaluation.golden_inference_audit_v2 import AuditedClaimV2, InferenceAuditV2
from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.providers.structured import contract_for_model

SCOPE_POLICY_ID = "golden-inference-scope-v1"
SCOPE_POLICY = COVERAGE_POLICY + """
范围判定 golden-inference-scope-v1：每条audit claim另填scope：selected_sample（明确只描述所选样本）、
beyond_sample（长期/未来/能力外推）、ambiguous（适用范围含混）、question_or_negation（待验证或否定断言）。
每段coverage另填scope_ambiguous布尔值。该段有范围含混原句则true，且必须有同段scope=ambiguous的claim。
样本内逐行一致或正确均值可以supported，不能因为样本少或出现“稳定”字样就拒绝。
长期/未来/因果结论需相应证据；不能因数字正确或附带小样本免责声明就支持外推。
未限定含义的“稳定差异/可靠指标”等需澄清，不能自行猜成长期或样本内；明确局部定义、否定和问题不因此含混。
ambiguous的status表示现有证据支持情况，范围含混独立于事实真假：不强迫写成unsupported。
但每条ambiguous必须匹配quote完全相同、category=other的issue，写明范围待澄清和具体改法，verdict不能pass。
修订时明确位置、所选场次、指标和观察范围；不编造长期历史，不用全局免责声明代替局部改写。
复评重新检查完整正文包括新增句。scope和scope_ambiguous只输出在评估JSON，修订仍完整Markdown。
"""
Scope = Literal["selected_sample", "beyond_sample", "ambiguous", "question_or_negation"]

class ScopedClaim(AuditedClaimV2):
    scope: Scope

class ScopedAudit(InferenceAuditV2):
    claims: list[ScopedClaim] = Field(max_length=24)

class ScopedBlock(BlockCoverage):
    scope_ambiguous: bool

class EvaluationResponseModelV16(EvaluationResponseModelV15):
    audits: list[ScopedAudit] = Field(min_length=2, max_length=2)
    coverage: list[ScopedBlock] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unresolved_scope_requires_revision(self):
        for audit in self.audits:
            for claim in audit.claims:
                if claim.scope == "ambiguous" and (self.verdict == "pass" or not any(
                    i.quote == claim.quote and i.category == "other" for i in self.issues
                )):
                    raise ValueError("ambiguous_scope_requires_clarification_issue_and_nonpass")
        return self


def validate_scope(payload, report, facts):
    validate_coverage(payload, report, facts)
    for block, item in zip(report_blocks(report), payload.coverage):
        ambiguous = any(c.scope == "ambiguous" and c.quote in block["text"]
                        for a in payload.audits for c in a.claims)
        if item.scope_ambiguous != ambiguous:
            raise ValueError("scope_coverage_claim_mismatch")


def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.6.0", output_model=EvaluationResponseModelV16)


def audit_prompt(prompt, old_contract):
    old = json.dumps(old_contract.schema_dict(), ensure_ascii=False, indent=2)
    if old not in prompt:
        raise ValueError("inference_schema_replacement_missing")
    return SCOPE_POLICY + "\n\n" + prompt.replace(old, json.dumps(inference_response_contract().schema_dict(), ensure_ascii=False, separators=(",", ":")), 1)


def inference_component_fingerprints(skill):
    rows = list(coverage_fingerprints(skill))
    for key, value in (("evaluation_schema", json.dumps(inference_response_contract().schema_dict(), sort_keys=True)),
                       ("scope_implementation", Path(__file__).read_text(encoding="utf-8"))):
        row = ComponentFingerprint(component_id=key, source="app.evaluation.golden_inference_scope:" + key,
                                   sha256=hashlib.sha256(value.encode()).hexdigest())
        rows = [row if old.component_id == key else old for old in rows] if any(old.component_id == key for old in rows) else [*rows, row]
    return tuple(rows)
