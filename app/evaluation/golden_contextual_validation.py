"""Current candidate validation, isolated from frozen 1.3.27 fingerprints.

Reuse source restoration and scope checks. The validation walk is kept here
because changing the frozen context module would invalidate historical assets.
Validation and per-claim feedback share the same checks, so one early error
cannot hide later representation defects from the correction request.
"""
import re
from types import SimpleNamespace

from app.evaluation import golden_context_review as context
from app.evaluation.golden_context_diagnostics import collect_diagnostics
from app.evaluation.golden_contextual_sources import numeric_support


def sample_anchor_valid(anchor, text):
    if context.SAMPLE_ANCHOR.search(anchor):
        return True
    # A cohort noun can point to an explicit sample limitation in the same
    # cited passage. Bare outcome/position words still do not establish scope.
    return bool(re.search(r"(?:输|赢|胜|负|败)局", anchor)
                and context.SAMPLE_ANCHOR.search(text))


def claim_errors(claim, report, pack):
    codes = []
    if len(set(claim.evidence_refs)) != len(claim.evidence_refs):
        codes.append("duplicate_evidence_reference")
    if claim.claim_kind == "direct_result":
        if claim.scope is not None or claim.scope_anchor is not None or claim.context is not None:
            codes.append("direct_result_scope_must_be_null")
        if not any(ref in pack["provenance"] for ref in claim.evidence_refs):
            codes.append("direct_result_value_source_required")
        if claim.status == "supported" and any(not r["supported"] for r in numeric_support(claim,pack)):
            codes.append("direct_result_number_not_in_evidence")
        return codes
    if claim.scope is None:
        codes.append("inference_scope_required")
    linked = claim.context
    if linked:
        if linked.block_id == claim.block_id and linked.quote == claim.quote:
            codes.append("context_must_add_explanatory_text")
        expected = "selected_sample" if linked.relation == "defines_scope" else "question_or_negation"
        if claim.scope != expected:
            codes.append("context_relation_scope_mismatch")
    anchor_text = linked.quote if linked else claim.quote
    valid = bool(claim.scope_anchor and claim.scope_anchor in anchor_text)
    if claim.scope == "selected_sample":
        valid = valid and sample_anchor_valid(claim.scope_anchor, anchor_text)
    if not valid:
        codes.append("context_anchor_invalid_requires_reassessment" if linked else "scope_anchor_invalid")
    if not context.table_anchor_valid(claim,report):
        codes.append("table_scope_antecedent_missing")
    return codes


def expand_context(raw, report, pack):
    value = context.restore(raw, report, pack)
    errors = context.heading_errors(value, report)
    if errors:
        raise ValueError(errors[0]["codes"][0])
    value.pop("heading_reviews")
    value = context.derived_wire(context.compact(value), report)
    value["coverage"] = [dict(block_id=b, metric_to_ability=context.STATUS[m],
        cohort_comparison=context.STATUS[c], scope_ambiguous=a)
        for b, m, c, a in value["coverage"]]
    payload = context.ContextEvaluation.model_validate(value, strict=True)
    context.validate_scope(payload, report, pack["facts"])
    for audit in payload.audits:
        seen = set()
        for claim in audit.claims:
            key = (claim.block_id, claim.quote)
            if key in seen:
                raise ValueError("duplicate_context_claim")
            seen.add(key)
            codes = claim_errors(claim,report,pack)
            if codes:
                raise ValueError(codes[0])
    return payload


def diagnostics(raw, report, pack):
    detailed = collect_diagnostics(raw, report, pack, expand=expand_context, numeric=numeric_support)
    try:
        value = context.restore(raw,report,pack)
    except (ValueError,TypeError,AttributeError):
        return detailed
    targets, codebook, explanation_details = [], [], []
    def add(target,codes):
        if not codes:
            return
        for code in codes:
            if code not in codebook:
                codebook.append(code)
        targets.append([target,[codebook.index(code)+1 for code in codes]])
    n = 0
    for audit in value["audits"]:
        seen = set()
        for row in audit["claims"]:
            n += 1
            claim = context.ContextClaim.model_validate(row,strict=True)
            codes = claim_errors(claim,report,pack)
            # Explanations may introduce new numbers absent from the quote.
            # A failed local lookup is a review hint, not proof the report is
            # false: arithmetic prose can exceed the bounded numeric operators.
            missing = [item['token'] for item in numeric_support(SimpleNamespace(
                quote=claim.explanation,evidence_refs=claim.evidence_refs),pack) if not item['supported']]
            if missing:
                codes.append('review_explanation_numbers_need_source_check')
                explanation_details.append(dict(target_id=f'c{n:03}',explanation_numbers=missing))
            key = (claim.block_id,claim.quote)
            if key in seen:
                codes.append("duplicate_context_claim")
            seen.add(key)
            exact = [i for i in value["issues"] if i["quote"] == claim.quote]
            if claim.status == "unsupported" and (not exact or value["verdict"] == "pass"):
                codes.append("unsupported_claim_requires_issue_and_nonpass")
            if claim.scope == "ambiguous" and (value["verdict"] == "pass" or not any(i["category"] == "other" for i in exact)):
                codes.append("ambiguous_scope_requires_clarification_issue_and_nonpass")
            if claim.claim_kind == "inference" and claim.scope == "beyond_sample" and claim.status != "unsupported":
                codes.append("correction_unsupported_must_remain_unsupported")
            add(f"c{n:03}",codes)
    headings = {row["block_id"]:f"h{i:03}" for i,row in enumerate(value["heading_reviews"],1)}
    for row in context.heading_errors(value,report):
        if row.get("block_id") in headings:
            add(headings[row["block_id"]],row["codes"])
    if not targets:
        return detailed
    matrix = dict(codes=["per_target_validation_errors"],codebook=codebook,targets=targets,
        repair_rule="targets每行为[target_id,codebook一基编号列表]，逐项修完全部错误。先按原文重判类型：保留direct_result则scope/scope_anchor/context均null；实际有推断则准确分类和引用范围，不能靠改标签掩盖事实或外推问题。")
    # The compact matrix precedes optional verbose/source-navigation details,
    # so the existing feedback cap cannot hide later claims behind early ones.
    details = []
    for row in detailed:
        if "audit_index" in row and "claim_index" in row:
            number = sum(len(a["claims"]) for a in value["audits"][:row["audit_index"]])+row["claim_index"]+1
            extra = {k:row[k] for k in ("unsupported_numbers","invalid_anchor","field") if k in row}
            if extra:
                details.append(dict(target_id=f"c{number:03}",**extra))
        elif any(code not in codebook for code in row.get("codes",[])):
            details.append(row)
    return [matrix,*explanation_details,*details]
