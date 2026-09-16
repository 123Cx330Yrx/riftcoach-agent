"""Offline contract experiment; no Provider, production registration or live entry.

Full reassessment can regroup claims while retaining every previously reviewed
source character. Coverage and source-valid issue resolutions do NOT establish
semantic correctness. Existing final validators remain authoritative.
"""
from dataclasses import dataclass

from pydantic import Field

from app.evaluation import golden_contextual_first_wire as first
from app.evaluation import golden_contextual_correction as canonical
from app.evaluation.golden_bounded_correction import _security
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_context_review import Index
from app.evaluation.golden_contextual_patch_wire import expand_value
from app.evaluation.golden_contextual_requests import request
from app.evaluation.golden_integrated_review import ReviewInput, Strict
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_review_experiment import compact, digest

EXPERIMENT_ID = "golden-full-reassessment-offline-v1"


class IssueResolution(Strict):
    target_id: str = Field(pattern=r"^i[0-9]{3,}$")
    evidence_refs: list[Index] = Field(min_length=1, max_length=12)
    explanation: str = Field(min_length=1, max_length=500)


class ReassessmentWire(first.FirstWire):
    # Exactly the same full-review capacities as the first response, rather
    # than a second, smaller patch capacity. Issue admission is bounded by
    # actual request budgets, not silently truncated to a fixed edit count.
    issue_resolutions: list[IssueResolution]


@dataclass(frozen=True)
class State:
    raw: str
    inputs: ReviewInput
    identity: str


def _read(raw, inputs, model=first.FirstWire):
    value = strict_json(normalize_json(raw))
    _security(value, inputs)
    wire = model.model_validate(value, strict=True)
    if wire.source_digest != inputs.source.source_digest:
        raise ValueError("reassessment_source_changed")
    if wire.reviewed_blocks != list(range(1, len(inputs.source.blocks) + 1)):
        raise ValueError("reassessment_block_inventory_changed")
    import re
    headings = [i for i, (_, text) in enumerate(inputs.source.blocks, 1)
                if re.match(r"^#{1,6}\s", text)]
    if [h.block_id for h in wire.heading_reviews] != headings:
        raise ValueError("reassessment_heading_inventory_changed")
    if [a.kind for a in wire.audits] != ["metric_to_ability", "cohort_comparison"]:
        raise ValueError("reassessment_audit_inventory_changed")
    for row in [c for a in wire.audits for c in a.claims] + list(wire.issues):
        inputs.source.resolve(row.quote_ref.model_dump(mode="json"))
    return wire


def prepare(raw, inputs):
    _read(raw, inputs)
    return State(raw, inputs, digest(compact(dict(raw=raw, inputs=inputs.data_json))))


def _check_state(state, inputs):
    if state.inputs != inputs or prepare(state.raw, inputs) != state:
        raise ValueError("reassessment_state_changed")


def span(source, ref):
    """Resolve the specific occurrence, including a head/tail-selected repeat."""
    quote = source.resolve(ref.model_dump(mode="json"))
    text = source.blocks[ref.block - 1][1]
    if ref.head is None:
        start = 0
    else:
        # SourceIndex.resolve has already proved the head/tail pairing unique.
        starts = [n for n in range(len(text)) if text.startswith(ref.head, n)
                  and text.startswith(quote, n)]
        if len(starts) != 1:
            raise ValueError("reassessment_span_not_unique")
        start = starts[0]
    return ref.block, start, start + len(quote)


def coverage_map(before, after, source):
    mappings = []
    for old_audit, new_audit in zip(before.audits, after.audits, strict=True):
        if old_audit.kind != new_audit.kind:
            raise ValueError("reassessment_audit_inventory_changed")
        candidates = [span(source, c.quote_ref) for c in new_audit.claims]
        for old_index, row in enumerate(old_audit.claims):
            block, start, end = span(source, row.quote_ref)
            intervals = sorted((max(start, a), min(end, b), i)
                for i, (n, a, b) in enumerate(candidates)
                if n == block and a < end and b > start)
            cursor, targets = start, []
            for left, right, index in intervals:
                if left > cursor:
                    break
                cursor = max(cursor, right)
                targets.append(index)
            if cursor < end:
                raise ValueError("reassessment_reviewed_source_lost")
            mappings.append(dict(audit=old_audit.kind, old_claim_index=old_index,
                final_claim_indices=targets, block=block, start=start, end=end))
    return mappings


def request_parts(state):
    _check_state(state, state.inputs)
    before = _read(state.raw, state.inputs)
    data = source_data(state.inputs)
    # Raw bytes remain in State/journal; the parsed view retains every first
    # judgment, explanation and issue, without host-derived field duplication.
    data["first_review"] = before.model_dump(mode="json")
    data["issue_ids"] = [f"i{i:03}" for i in range(1, len(before.issues) + 1)]
    policy = (first.FIRST_POLICY + canonical.FULL_CONTEXT_RULE +
        "\n重新审查完整报告并输出完整评估，不输出补丁或旧target的独立复核说明。"
        "首评所有判断可质疑，不能只修程序格式。可以合并重复引用、拆分同段引用；"
        "同一audit必须保留全部旧引用字符的覆盖，新增遗漏判断；不能删除错误尾句或换源。"
        "逐条核对新explanation对应的原文对象、分路、胜负组和指标，数字方向相同不能替换样本。"
        "旧issues逐字保留；确需撤销或变更时，在issue_resolutions逐项填写旧issue_ids、"
        "有效evidence_refs及解释，新问题列issues。存在引用只证明位置，不证明撤销合理。")
    return data, policy


def build_request(state):
    data, policy = request_parts(state)
    return request(data, policy, ReassessmentWire, "offline_full_reassessment")


def apply(state, raw, *, inputs):
    _check_state(state, inputs)
    before = _read(state.raw, inputs)
    after = _read(raw, inputs, ReassessmentWire)
    mapping = coverage_map(before, after, inputs.source)
    resolutions = {}
    for row in after.issue_resolutions:
        if row.target_id in resolutions:
            raise ValueError("reassessment_duplicate_issue_resolution")
        if len(set(row.evidence_refs)) != len(row.evidence_refs) or any(
                n > len(inputs.source.evidence_keys) for n in row.evidence_refs):
            raise ValueError("reassessment_resolution_source_invalid")
        resolutions[row.target_id] = row
    retained = [i.model_dump(mode="json") for i in after.issues]
    missing = {f"i{i:03}": row.model_dump(mode="json")
               for i, row in enumerate(before.issues, 1)
               if row.model_dump(mode="json") not in retained}
    if set(resolutions) != set(missing):
        raise ValueError("reassessment_issue_disposition_missing_or_extra")
    projected = after.model_dump(mode="json", exclude={"issue_resolutions"})
    for target, audit in zip(projected["audits"], after.audits, strict=True):
        target["claims"] = [expand_value(row, inputs.source) for row in audit.claims]
    result = canonical.expand_context(compact(projected), inputs.source.report,
                                      strict_json(inputs.pack_json))
    return result, dict(experiment=EXPERIMENT_ID, state_id=state.identity,
        first_raw=state.raw, final_raw=raw, final_response_sha256=digest(raw),
        source_coverage=mapping,
        resolved_issues=[dict(target_id=k, before=missing[k],
            resolution=v.model_dump(mode="json")) for k, v in resolutions.items()],
        semantic_approval=False, live_qualified=False)
