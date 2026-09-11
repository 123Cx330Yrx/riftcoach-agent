"""Opt-in evidence projections and grounded claim audit, frozen legacy unchanged."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
import json
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.coach_grounded_contract import EvaluationResponseModelV12
from app.providers.structured import contract_for_model
from app.harness.steps import EvaluationResult


@dataclass(frozen=True)
class AuditedEvaluationResult(EvaluationResult):
    audits: tuple[dict, ...] = ()

INFERENCE_POLICY_ID = "golden-inference-audit-v1"
INFERENCE_POLICY = """可信推断审查策略 golden-inference-audit-v1：
数值准确不等于结论成立。视野分、零死亡、补刀等结果指标不能单独证明意识、决策或稳定能力；
普通指标记录、明确待验证的录像问题可以保留。比较发育/输出时先核对位置和胜负组构成，
优先使用同位置统计，保留样本量和缺失数。混合位置均值可描述，不能据此推断某位置能力退步。
同位置差异仍不能独自证明因果或长期能力。泛泛免责声明不能消除正文或标题中的错误判断。
评估必须完成 metric_to_ability 和 cohort_comparison 两项 audits，逐条检查相关原句。
每个 claim 的 quote 必须是报告原文，evidence_refs 必须引用 inference_facts 中实际存在的键。
status=unsupported 的 claim 必须有相同 quote 的具体 issues，verdict 不得 pass。
supported 表示这些原句受支持或已恰当限定；not_applicable 仅用于完全没有此类表述，claims为空。
不要因为已存在免责声明就漏掉实质断言，也不要把明确否定能力推断或条件性问题误报为断言。
生成和修订保持事实、假设、行动的区别；修订同时校正受影响标题和建议，保持其余正确内容。
审查仍须执行所有数值、来源、引用、安全规则；audits只额外检查两类推断，不取代其他检查。
""".strip()
METRICS = ("cs_per_min", "gold_per_min", "damage_per_min", "vision_score")
ROLES = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")


def inference_facts(summary: Mapping) -> dict:
    rows = summary.get("matches", [])
    if not isinstance(rows, (list, tuple)) or len(rows) > 100:
        raise ValueError("inference_sample_scope_invalid")
    included = [r for r in rows if isinstance(r, Mapping) and r.get("included_in_aggregate") is True]
    result = {"scope:limits": {
        "included_count": len(included), "excluded_count": len(rows) - len(included),
        "unknown_role_or_outcome": sum(r.get("role") not in ROLES or type(r.get("win")) is not bool for r in included),
        "interpretation": "Descriptive selected games only; numeric results do not establish awareness, causality or stable ability. No video decision evidence supplied by this projection.",
    }}
    for role in ROLES:
        for win in (True, False):
            cohort = [r for r in included if r.get("role") == role and type(r.get("win")) is bool and r["win"] is win]
            if not cohort:
                continue
            for metric in METRICS:
                values = [Decimal(str(r[metric])) for r in cohort if type(r.get(metric)) in (int, float)
                          and math.isfinite(r[metric]) and r[metric] >= 0]
                result[f"role:{role}:{'win' if win else 'loss'}:{metric}"] = {
                    "games": len(cohort), "valid": len(values), "missing_or_invalid": len(cohort) - len(values),
                    "mean": float(round(sum(values) / len(values), 6)) if values else None,
                }
    return result


class AuditedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    explanation: str = Field(min_length=1, max_length=2000)


class InferenceAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["metric_to_ability", "cohort_comparison"]
    status: Literal["supported", "unsupported", "not_applicable"]
    claims: list[AuditedClaim] = Field(max_length=24)

    @model_validator(mode="after")
    def applicable_claims(self):
        if (self.status == "not_applicable") != (not self.claims):
            raise ValueError("audit_claims_required_for_applicable_review")
        return self


class EvaluationResponseModelV13(EvaluationResponseModelV12):
    audits: list[InferenceAudit] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def complete_consistent_audits(self):
        if {a.kind for a in self.audits} != {"metric_to_ability", "cohort_comparison"}:
            raise ValueError("both_inference_audits_required")
        for audit in self.audits:
            if audit.status == "unsupported":
                if self.verdict == "pass" or any(not any(i.quote == c.quote for i in self.issues) for c in audit.claims):
                    raise ValueError("unsupported_audit_requires_matching_issue_and_nonpass")
        return self


def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.3.0", output_model=EvaluationResponseModelV13)


def validate_audit_anchors(payload: EvaluationResponseModelV13, report: str, facts: Mapping) -> None:
    for audit in payload.audits:
        for claim in audit.claims:
            if not claim.quote.strip() or claim.quote not in report or any(ref not in facts for ref in claim.evidence_refs):
                raise ValueError("inference_audit_anchor_invalid")


def audit_prompt(prompt: str, old_contract) -> str:
    old = json.dumps(old_contract.schema_dict(), ensure_ascii=False, indent=2)
    if old not in prompt:
        raise ValueError("inference_schema_replacement_missing")
    return INFERENCE_POLICY + "\n\n" + prompt.replace(old, json.dumps(inference_response_contract().schema_dict(), ensure_ascii=False, indent=2), 1)


def inference_component_fingerprints(skill):
    import hashlib
    from pathlib import Path
    from app.evaluation.coach_grounded_contract import grounded_component_fingerprints
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = list(grounded_component_fingerprints(skill))
    values = {"evaluation_schema": inference_response_contract().schema_dict(),
              "inference_implementation": hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode("utf-8")).hexdigest()}
    for key, value in values.items():
        row = ComponentFingerprint(component_id=key, source="app.evaluation.golden_inference_audit:" + key,
                                   sha256=hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
        rows = [row if old.component_id == key else old for old in rows] if any(old.component_id == key for old in rows) else [*rows, row]
    return tuple(rows)
