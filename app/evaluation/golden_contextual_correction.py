"""Owner-approved whole-context standard with one authoritative semantic label.

The current wire rejects legacy meaning-field patches. Review notes explain decisions; classification
and source identity come only from final claims, avoiding contradictory copies.
"""
from typing import Literal
import re

from pydantic import Field

from app.evaluation import golden_bounded_correction as previous
from app.evaluation import golden_bounded_correction_requests as requests
from app.evaluation.golden_context_review import ClaimRef, IssueRef
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_contextual_validation import expand_context, diagnostics
from app.evaluation.golden_contextual_requests import request as table_request


STANDARD_ID = "whole-context-acceptance-v1"
EXPERIMENT_ID = "golden-contextual-bounded-review-v10"


def replace_rules(policy, changes):
    for old, new in changes:
        if policy.count(old) != 1:
            raise ValueError("contextual_policy_source_drift")
        policy = policy.replace(old,new)
    return policy


FULL_CONTEXT_RULE = "按完整上下文验收：若同一组样本、比较对象和含义已清楚限定且无无依据外推，可selected_sample并通过；不要求每句重复范围或专门定义稳定/持续等词。额外措辞优化不单独阻断。仅相邻、泛泛免责声明或正确数字不能支持实际长期、未来或因果断言；后文独立错误仍须检出。真正无法确定范围、对象或存在冲突才要求澄清。"

CORRECTION_POLICY = replace_rules(requests.CORRECTION_POLICY, [
    ("meaning_reviews恰好逐项覆盖required_reviews，允许乱序，不得遗漏或重复；每个新增claim也须meaning。",
     "review_notes逐项覆盖required_reviews，允许乱序，不得遗漏或重复；每个新增claim须review_note。若额外给新增claim附说明，编号按added_claims顺序从已有claim数+1继续；它只作补充说明，不能代替新增claim或创建另一套判断。"),
    ("literal仅为直接事实；defined仅在原文明确表达样本范围及用词含义时使用，language_ref引用实际定义，可在同句或前后文；negated引用明确否定原句的文字。",
     "最终判断只在claim_kind/scope/context表达一次；不要再填写disposition或language_ref。review_notes解释判断依据，来源引用只在最终claim的quote_ref/context中提供。"),
    ("这两类explanation必须说明文字如何确切指向本句及定义/否定了什么，不能以均值正确、背景样本或一种可能解读替代关系证据。", FULL_CONTEXT_RULE),
    ("无法确定含义则clarify，必须改成ambiguous并补other澄清issue；明确无依据的长期/未来/因果结论则unsupported，不能混为数值错误。",
     "实际不能确定范围或对象时scope=ambiguous并补other澄清issue；明确无依据的长期/未来/因果结论则beyond_sample/unsupported并列issue，不能混为数值错误。"),
    ("其他disposition的language_ref为null；navigation只用于无断言的标题。泛泛免责声明不能取消后文外推；引用后明确否定的错误说法不当作作者支持的断言。",
     "标题kind=navigation仅用于无断言标题；有断言须有完整标题claim。泛泛免责声明不能取消后文外推；引用后明确否定的错误说法不当作作者支持的断言。"),
    ("引用存在不证明关系，不能借相邻主题猜定义。",
     "引用存在不证明关系，须解释该范围如何适用于同一组样本及比较对象，并核查后文有无冲突。"),
]) + "\nreview_explanation_numbers_need_source_check指评估解释中的数值尚未被局部算子核实，不自动表示报告错误。逐项核对指标、位置与胜负组；原claim.explanation若算错或混组，须用claim_edits修正解释及证据，不能只在review_notes说已核对。确实可复算但算子未覆盖时解释具体运算，勿为通过而删报告的正确事实。"


def prepare_state(raw, inputs):
    return previous.prepare_state(raw, inputs, review_all_claims=True, diagnose=diagnostics)


class ReviewNote(Strict):
    target_id: str = Field(pattern=r"^[ch][0-9]{3}$")
    explanation: str = Field(min_length=1,max_length=500)


class AddedClaim(Strict):
    audit: Literal["metric_to_ability", "cohort_comparison"]
    value: ClaimRef
    review_note: str = Field(min_length=1,max_length=500)


class ContextualCorrection(Strict):
    claim_edits: list[previous.ClaimEdit] = Field(max_length=16)
    issue_edits: list[previous.IssueEdit] = Field(max_length=12)
    added_claims: list[AddedClaim] = Field(max_length=16)
    added_issues: list[IssueRef] = Field(max_length=16)
    heading_edits: list[previous.HeadingEdit] = Field(max_length=16)
    review_notes: list[ReviewNote] = Field(max_length=64)
    score: int = Field(ge=0,le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    summary: str = Field(min_length=1,max_length=1200)
    passed_checks: list[str] = Field(max_length=12)


class CorrectionWire(requests.UntitledSchema, ContextualCorrection):
    pass


def first_request(inputs):
    from app.evaluation.golden_contextual_first_wire import first_request as build
    return build(inputs)


def correction_request(state):
    from app.evaluation.golden_contextual_patch_wire import PatchWire, POLICY, correction_data
    return requests.PreparedCorrection(state,table_request(
        correction_data(state),POLICY+FULL_CONTEXT_RULE,PatchWire,"full_context_correction"))


def _witness(claim, explanation):
    scope = claim["scope"]
    dispositions = {
        "selected_sample":"defined", "question_or_negation":"negated",
        "ambiguous":"clarify", "beyond_sample":"unsupported"}
    if claim["claim_kind"] != "direct_result" and scope not in dispositions:
        raise ValueError("contextual_inference_scope_required")
    disposition = "literal" if claim["claim_kind"] == "direct_result" else dispositions[scope]
    ref = None
    if disposition in {"defined","negated"}:
        ref = claim["context"]["quote_ref"] if claim.get("context") else claim["quote_ref"]
    return dict(disposition=disposition,language_ref=ref,explanation=explanation)


def _resolve_anchor(claim, source, target_id, journal):
    """Restore display whitespace only, with an explicit, unique source span.

    Never change words, punctuation, digits, context identity or scope. In
    particular, whitespace between ASCII word characters is not removable.
    """
    anchor = claim.get("scope_anchor")
    if not anchor:
        return
    ref = claim["context"]["quote_ref"] if claim.get("context") else claim["quote_ref"]
    text = source.resolve(ref)
    if anchor in text or re.search(r"[A-Za-z0-9]\s+[A-Za-z0-9]",anchor):
        return
    chars = re.sub(r"\s+","",anchor)
    if not chars:
        return
    pattern = re.escape(chars[0])
    for left,right in zip(chars,chars[1:]):
        ascii_word_pair = all(c.isascii() and c.isalnum() for c in (left,right))
        pattern += ("" if ascii_word_pair else r"\s*") + re.escape(right)
    matches = list(re.finditer(pattern,text))
    if len(matches) != 1 or len(matches[0].group()) > 20:
        return
    resolved = matches[0].group()
    claim["scope_anchor"] = resolved
    journal.append(dict(target_id=target_id,field="scope_anchor",before=anchor,after=resolved,
        source_ref=ref,operation="unique_display_whitespace_resolution"))


def apply_correction(state, raw, *, inputs):
    if state.inputs != inputs or prepare_state(state.raw, inputs) != state:
        raise ValueError("correction_state_changed")
    value = previous.strict_json(raw)
    previous._security(value,inputs)
    patch = ContextualCorrection.model_validate(value,strict=True)
    notes = previous._unique(patch.review_notes)
    claim_count = sum(row["type"] == "claim" for row in state.entries().values())
    added_ids = [f"c{claim_count+i:03}" for i in range(1,len(patch.added_claims)+1)]
    required = set(state.required_reviews)
    if not required <= set(notes) or not set(notes) <= required | set(added_ids):
        raise ValueError("contextual_review_inventory_mismatch")
    supplemental = [dict(target_id=key,added_claim_index=added_ids.index(key),
        explanation=note.explanation) for key,note in notes.items() if key not in required]
    notes = {key:note for key,note in notes.items() if key in required}
    anchor_resolutions = []
    values = patch.model_dump(mode="json")
    for row in values["claim_edits"]:
        _resolve_anchor(row["value"],inputs.source,row["target_id"],anchor_resolutions)
    for key,row in zip(added_ids,values["added_claims"],strict=True):
        _resolve_anchor(row["value"],inputs.source,key,anchor_resolutions)
    patch = ContextualCorrection.model_validate(values,strict=True)
    entries = state.entries()
    edits = previous._unique(patch.claim_edits)
    headings = previous._unique(patch.heading_edits)
    claims = {key:edits[key].value.model_dump(mode="json") if key in edits else row["value"]
              for key,row in entries.items() if row["type"] == "claim"}
    payload = patch.model_dump(mode="json",exclude={"review_notes","added_claims"})
    payload["added_claims"] = [dict(audit=row.audit,value=row.value.model_dump(mode="json"),
        meaning=_witness(row.value.model_dump(mode="json"),row.review_note)) for row in patch.added_claims]
    payload["meaning_reviews"] = []
    for key,note in notes.items():
        entry = entries[key]
        if entry["type"] == "claim":
            witness = _witness(claims[key],note.explanation)
        else:
            kind = headings[key].kind if key in headings else entry["value"]["kind"]
            if kind == "navigation":
                witness = dict(disposition="navigation",language_ref=None,explanation=note.explanation)
            else:
                block = entry["value"]["block_id"]
                candidates = [row for row in [*claims.values(),*(r["value"] for r in payload["added_claims"])]
                    if row["quote_ref"]["block"] == block and inputs.source.resolve(row["quote_ref"]) == inputs.source.blocks[block-1][1]]
                if not candidates:
                    raise ValueError("correction_heading_claim_missing")
                witness = _witness(candidates[0],note.explanation)
        payload["meaning_reviews"].append(dict(target_id=key,**witness))
    result,journal = previous.apply_correction(state,compact(payload),inputs=inputs,
        prepare=prepare_state,expand=expand_context)
    journal.update(protocol=EXPERIMENT_ID,standard_id=STANDARD_ID,
        model_review_notes=[row.model_dump(mode="json") for row in patch.review_notes],
        supplemental_added_claim_notes=supplemental,anchor_resolutions=anchor_resolutions,
        meaning_fields_derived_from_final_claims=True)
    return result,journal
