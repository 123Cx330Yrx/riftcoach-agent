"""Offline diagnostics for the next candidate; never repair or accept a response.

Keep full context blocks visible for inspection. Source candidates are navigation
only; they do not establish a semantic relation or correct model verdict.
"""
from types import SimpleNamespace
import re

from app.evaluation.golden_context_review import restore, expand_context
from app.evaluation.golden_context_review import ContextWire
from app.evaluation.golden_review_experiment import SourceIndex
from app.evaluation.golden_numeric_evidence_v4 import numeric_support
from app.evaluation.golden_scope_diagnostics import bounded_feedback
from app.evaluation.golden_evidence_scope_v5 import normalize_json, SAMPLE_ANCHOR
from app.evaluation.golden_inference_scope_v5 import strict_json


def collect_diagnostics(raw, report, pack):
    rows = []
    try:
        expand_context(raw, report, pack)
    except (ValueError, TypeError, AttributeError) as error:
        code = str(error) if re.fullmatch(r"[a-z_]{1,100}", str(error)) else "invalid_json_or_context_schema"
        rows.append({"codes": [code]})
    try:
        wire = ContextWire.model_validate(strict_json(normalize_json(raw)), strict=True)
    except (ValueError, TypeError, AttributeError):
        return rows
    source = SourceIndex.build(report, pack)
    if wire.source_digest != source.source_digest:
        return rows  # Never interpret references against a different source.
    inventory = list(range(1, len(source.blocks) + 1))
    if wire.reviewed_blocks != inventory:
        rows.append(dict(codes=["reviewed_block_inventory_mismatch"],
            expected=inventory, actual=wire.reviewed_blocks))
    # Diagnose each typed reference directly, even if a different reference or
    # the global inventory failed. This never constructs an accepted result.
    for ai, audit in enumerate(wire.audits):
        for ci, typed in enumerate(audit.claims):
            location = dict(audit_index=ai, claim_index=ci,
                quote_ref=typed.quote_ref.model_dump(exclude_none=True))
            try:
                quote = source.resolve(location["quote_ref"])
                evidence = [source.evidence_keys[n-1] for n in typed.evidence_refs
                    if 1 <= n <= len(source.evidence_keys)]
                if len(evidence) != len(typed.evidence_refs):
                    rows.append(dict(location, codes=["source_index_invalid"], field="evidence_refs"))
                    continue
                anchor_text = source.resolve(typed.context.quote_ref.model_dump()) if typed.context else quote
            except ValueError:
                rows.append(dict(location, codes=["source_reference_invalid"],
                    repair_rule="按完整source_index重新定位原句及上下文，不拼接或改写原文。"))
                continue
            claim = dict(typed.model_dump(), quote=quote, evidence_refs=evidence)
            if typed.claim_kind == "inference":
                valid = bool(typed.scope_anchor and typed.scope_anchor in anchor_text)
                if typed.scope == "selected_sample":
                    valid = valid and bool(SAMPLE_ANCHOR.search(typed.scope_anchor))
                if not valid:
                    rows.append(dict(location, codes=["scope_anchor_invalid"],
                        scope=typed.scope, invalid_anchor=typed.scope_anchor,
                        anchor_source_ref=(typed.context.quote_ref.model_dump(exclude_none=True)
                            if typed.context else location["quote_ref"]),
                        repair_rule="锚点须逐字来自对应原句或已引用上下文；先重审真实范围和指代，不能编造定义。"))
                continue
            if claim["claim_kind"] != "direct_result" or claim["status"] != "supported":
                continue
            actual = numeric_support(SimpleNamespace(**claim), pack)
            missing = [v for v in actual if not v["supported"]]
            if not missing:
                continue
            candidates = {v["token"]: v for v in numeric_support(
                SimpleNamespace(**dict(claim, evidence_refs=sorted(pack["provenance"]))), pack)}
            rows.append(dict(location, codes=["direct_result_number_not_in_evidence"], unsupported_numbers=[
                    {"token": v["token"], "source_candidates": candidates[v["token"]]["candidates"][:2]}
                    for v in missing[:6]], repair_rule="候选仅为来源导航，须核对对象、位置、胜负组和单位；队列号应引用实际单局queue_id。"))
    return rows


def feedback(raw, report, pack):
    return bounded_feedback(collect_diagnostics(raw, report, pack))


def context_inspection(raw, report, pack):
    """Full original link pairs for manual/next-stage review, not model labels."""
    value = restore(raw, report, pack)
    blocks = dict(SourceIndex.build(report, pack).blocks)
    return [dict(audit_index=ai, claim_index=ci, claim_quote=c["quote"],
        claim_block=blocks[c["block_id"]], referenced_quote=c["context"]["quote"],
        context_block=blocks[c["context"]["block_id"]], relation=c["context"]["relation"],
        explanation=c["context"]["explanation"], semantic_verdict="not_determined_by_program")
        for ai, a in enumerate(value["audits"]) for ci, c in enumerate(a["claims"]) if c["context"]]
