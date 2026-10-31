"""One decision representation across discovery and bounded correction.

Only the host derives redundant classification/status/anchor fields. A first
review is always provisional: even a source-valid sample label can be wrong.
The second review retains every claim/issue and runs full canonical validation.
"""
from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from app.evaluation import golden_contextual_correction as canonical
from app.evaluation.golden_bounded_correction import ReviewState
from app.evaluation.golden_bounded_correction_requests import PreparedCorrection, UntitledSchema, source_data
from app.evaluation.golden_context_review import HeadingRef, Index, IssueRef
from app.evaluation.golden_contextual_patch_wire import (
    DECISION_POLICY, POLICY, DecisionValue, PatchWire, apply_wire, correction_data, expand_value,
)
from app.evaluation.golden_contextual_requests import request
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest


class FirstClaim(DecisionValue):
    quote_ref: QuoteRef


class FirstAudit(Strict):
    kind: Literal["metric_to_ability", "cohort_comparison"]
    claims: list[FirstClaim] = Field(max_length=24)


class FirstWire(UntitledSchema, Strict):
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_blocks: list[Index] = Field(min_length=1, max_length=64)
    heading_reviews: list[HeadingRef] = Field(max_length=64)
    audits: list[FirstAudit] = Field(min_length=2, max_length=2)
    issues: list[IssueRef]
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    summary: str = Field(min_length=1, max_length=1200)
    passed_checks: list[str] = Field(max_length=12)


FIRST_POLICY = DECISION_POLICY + """审查完整报告的事实、数值、来源、安全、位置、样本、因果和能力推断。
source_digest复制输入；reviewed_blocks按顺序填写全部block编号。恰好两个audits，按metric_to_ability、cohort_comparison排序，各只填kind和claims；检查全部相关陈述，不以清空claims换通过。同一audit同一原句只列一次。
每条claim必须有quote_ref；全段用{block:编号}，只审一句用同段唯一head/tail，不截断数字或拼接。每个完整断言给一次decision及解释，scope_source只引用解释此判断范围的真实原文。
heading_reviews按顺序覆盖全部Markdown标题，给block_id及kind；assertion须有完整标题claim。coverage与其他派生字段由程序计算，不输出。
普通事实、安全、来源问题也可独立列issue。解释简洁但须说明原文含义、比较对象及证据关系；正确数字或引用存在不等于推断成立。
"""


@dataclass(frozen=True)
class DecisionState:
    raw: str
    base: ReviewState


def first_request(inputs):
    return request(source_data(inputs), FIRST_POLICY + canonical.FULL_CONTEXT_RULE,
        FirstWire, "full_context_first_decision")


def prepare_state(raw, inputs):
    value = strict_json(normalize_json(raw))
    canonical.previous._security(value, inputs)
    wire = FirstWire.model_validate(value, strict=True)
    projected = wire.model_dump(mode="json")
    for audit, rows in zip(projected["audits"], wire.audits, strict=True):
        audit["claims"] = [expand_value(row, inputs.source, provisional=True) for row in rows.claims]
    # Missing sample anchors remain invalid and diagnosable; they are never
    # invented. Source identity, inventory and security checks still run here.
    return DecisionState(raw, canonical.prepare_state(compact(projected), inputs))


def build_correction(state):
    if prepare_state(state.raw, state.base.inputs) != state:
        raise ValueError("contextual_first_state_changed")
    from app.evaluation.golden_contextual_admission import require_correction_reachability
    require_correction_reachability(state.base)
    data = correction_data(state.base)
    wire = FirstWire.model_validate(strict_json(normalize_json(state.raw)), strict=True)
    n = 0
    for audit in wire.audits:
        for row in audit.claims:
            n += 1
            # Send the actual model decision/reason/reference, not another copy
            # of host-derived fields the second model would need to reconcile.
            data["review_state"][f"c{n:03}"] = row.model_dump(mode="json")
    req = request(data, POLICY + canonical.FULL_CONTEXT_RULE, PatchWire, "full_context_correction")
    return PreparedCorrection(state, req)


def merge_correction(state, raw, *, inputs):
    if state.base.inputs != inputs or prepare_state(state.raw, inputs) != state:
        raise ValueError("contextual_first_state_changed")
    result, journal = apply_wire(state.base, raw, inputs=inputs)
    journal["first_decision_wire"] = dict(raw=state.raw, response_sha256=digest(state.raw),
        canonical_state_id=state.base.state_id, first_accepted=False,
        derived_fields_are_host_owned=True)
    return result, journal
