"""Protocol preservation tests, never evidence of model semantic quality."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.evaluation.golden_review_experiment import (
    SourceIndex, compact, index_review, restore_review, validate_indexed_review,
    plan_anchor_repair, apply_anchor_patch,
    anchor_patch_request,
)
from app.evaluation.golden_evidence_scope_v8 import expand_evidence
from tests.test_golden_evidence_v8 import fixture


def example():
    value, report, pack = fixture("只在这四场中，方向一致；这不证明未来稳定。")
    value["audits"][1]["claims"] = [dict(quote=report, evidence_refs=["scope:limits"],
        explanation="限定所选四场", status="supported", claim_kind="inference",
        scope="selected_sample", scope_anchor="这四场")]
    return value, report, pack


def broken_anchor():
    value, report, pack = example()
    value["audits"][1]["claims"][0]["scope_anchor"] = "方向"
    raw = compact(value)
    plan = plan_anchor_repair(raw, report, pack)
    patch = dict(mode="reference_only", base_digest=plan.base_digest, source_digest=plan.source_digest,
                 changes=[dict(audit_index=1, claim_index=0, scope_anchor="这四场")])
    return raw, report, pack, patch


def test_lossless_roundtrip_and_same_canonical_result():
    value, report, pack = example()
    original = deepcopy(value)
    source = SourceIndex.build(report, pack)
    indexed = index_review(compact(value), source)
    assert restore_review(indexed, source) == original
    assert validate_indexed_review(indexed, source, pack) == expand_evidence(compact(value), report, pack)
    assert value == original
    assert indexed["evaluation"]["audits"][1]["claims"][0]["quote_ref"] == {"block": 1}


def test_mixed_assertions_and_full_context_are_preserved():
    report = "## 范围\n\n以下稳定仅指这四场。\n\n本次伤害较低；因此已经证明长期能力弱。\n\n该因果结论不成立。"
    source = SourceIndex.build(report, {"facts": {"f": 1}})
    for quote in ["本次伤害较低", "因此已经证明长期能力弱。", "该因果结论不成立。"]:
        assert source.resolve(source.reference(quote)) == quote
    assert [b["text"] for b in source.prompt_sources()["blocks"]] == [text for _, text in source.blocks]
    assert source.report == report


@pytest.mark.parametrize("report,quote", [
    ("**伤害** 8.81，不能证明意识。", "伤害 8.81"),
    ("第一段。\n\n第二段。", "第一段。第二段。"),
    ("重复句。\n\n重复句。", "重复句。"),
    ("| 项 | 值 |\n|---|---|\n| A | 8.81 |", "| 项 | 值 |\n| A | 8.81 |"),
])
def test_bad_copy_cross_block_and_ambiguous_source_are_rejected(report, quote):
    with pytest.raises(ValueError):
        SourceIndex.build(report, {"facts": {}}).reference(quote)


def test_ambiguous_endpoints_never_pick_first_match():
    source = SourceIndex.build("开头中段结尾，再次开头中段结尾。", {"facts": {}})
    with pytest.raises(ValueError, match="ambiguous"):
        source.resolve({"block": 1, "head": "开头", "tail": "结尾"})


def test_long_quote_uses_exact_short_endpoints_without_character_offsets():
    quote = "所选四场里的经济与伤害方向一致，解释只限这些比赛，不代表长期能力，也不预测下一场胜负。"
    source = SourceIndex.build("前缀。" + quote + "后缀。", {"facts": {}})
    ref = source.reference(quote)
    assert len(ref["head"]) <= 32 and len(ref["tail"]) <= 32
    assert source.resolve(ref) == quote


@pytest.mark.parametrize("change", ["report", "facts", "index", "duplicate", "bool_index", "injected_quote"])
def test_stale_identity_and_corrupted_references_fail(change):
    value, report, pack = example()
    source = SourceIndex.build(report, pack)
    indexed = index_review(compact(value), source)
    if change == "report": source = SourceIndex.build(report + "新增结论。", pack)
    elif change == "facts": pack["facts"]["scope:limits"] = "changed"
    elif change == "index": indexed["evaluation"]["audits"][1]["claims"][0]["evidence_refs"] = [9999]
    elif change == "duplicate": indexed["evaluation"]["reviewed_blocks"] *= 2
    elif change == "bool_index": indexed["evaluation"]["reviewed_blocks"] = [True]
    else: indexed["evaluation"]["audits"][1]["claims"][0]["quote"] = "伪造原文"
    with pytest.raises((ValueError, TypeError)):
        validate_indexed_review(indexed, source, pack)


@pytest.mark.parametrize("suffix", ["解释已完成", '{"score":99}', '``` extra'])
def test_projection_does_not_salvage_json_prefix(suffix):
    value, report, pack = example()
    with pytest.raises(ValueError):
        index_review(compact(value) + suffix, SourceIndex.build(report, pack))


def test_indexing_does_not_repair_or_approve_bad_scope():
    raw, report, pack, _ = broken_anchor()
    source = SourceIndex.build(report, pack)
    indexed = index_review(raw, source)
    assert restore_review(indexed, source) == json.loads(raw)
    with pytest.raises(ValueError, match="selected_sample_anchor_missing"):
        validate_indexed_review(indexed, source, pack)


def test_reference_patch_changes_only_anchor_and_revalidates_all_rules():
    raw, report, pack, patch = broken_anchor()
    original = json.loads(raw)
    result = apply_anchor_patch(raw, compact(patch), report, pack)
    expected = deepcopy(original)
    expected["audits"][1]["claims"][0]["scope_anchor"] = "这四场"
    assert result == expand_evidence(compact(expected), report, pack)
    assert json.loads(raw) == original


def test_model_can_decline_local_patch_when_it_discovers_semantic_problem():
    raw, report, pack, patch = broken_anchor()
    patch.update(mode="needs_reassessment", changes=[], reason="该判断需要重新核对证据")
    with pytest.raises(ValueError, match="anchor_patch_requires_reassessment"):
        apply_anchor_patch(raw, compact(patch), report, pack)


def test_complete_patch_request_has_original_evaluation_and_evidence_and_budget():
    from app.harness.steps import KnowledgeEvidence
    from tests.test_golden_evidence_runtime import summary
    raw, report, _, _ = broken_anchor()
    knowledge = KnowledgeEvidence(context="完整知识原文", source_ids=(), citations=())
    request = anchor_patch_request(raw, summary(), "完整确定性来源", knowledge, report, "review")
    prompt = request.messages[-1].content
    assert report in prompt and "完整知识原文" in prompt and "完整确定性来源" in prompt
    assert compact(json.loads(raw)) in prompt and "needs_reassessment" in prompt
    assert request.max_tokens == 32768 and request.timeout_s == 300
    with pytest.raises(ValueError, match="input_budget"):
        anchor_patch_request(raw, summary(), "事实" * 64000, knowledge, report, "review")


@pytest.mark.parametrize("change", ["score", "quote", "evidence", "scope", "unknown_target", "duplicate_target", "base", "source", "invalid_anchor"])
def test_patch_cannot_hide_errors_or_edit_unrelated_content(change):
    raw, report, pack, patch = broken_anchor()
    if change == "score": patch["score"] = 100
    elif change == "quote": patch["changes"][0]["quote"] = "改写结论"
    elif change == "evidence": patch["changes"][0]["evidence_refs"] = []
    elif change == "scope": patch["changes"][0]["scope"] = "question_or_negation"
    elif change == "unknown_target": patch["changes"][0]["claim_index"] = 1
    elif change == "duplicate_target": patch["changes"] *= 2
    elif change == "base": patch["base_digest"] = "0" * 64
    elif change == "source": patch["source_digest"] = "0" * 64
    else: patch["changes"][0]["scope_anchor"] = "不存在"
    with pytest.raises(ValueError):
        apply_anchor_patch(raw, compact(patch), report, pack)


@pytest.mark.parametrize("change", ["json_tail", "duplicate_key", "inventory", "unknown_evidence", "semantic_issue", "security"])
def test_nonreference_failures_require_reassessment(change):
    raw, report, pack, _ = broken_anchor()
    value = json.loads(raw)
    if change == "json_tail": raw += " extra"
    elif change == "duplicate_key": raw = raw.replace('"score":', '"score":1,"score":', 1)
    elif change == "inventory": value["reviewed_blocks"] = []
    elif change == "unknown_evidence": value["audits"][1]["claims"][0]["evidence_refs"] = ["invented"]
    elif change == "semantic_issue": value["audits"][1]["claims"][0]["status"] = "unsupported"
    else: value["issues"] = [dict(category="prompt_injection")]
    if change not in {"json_tail", "duplicate_key"}: raw = compact(value)
    with pytest.raises(ValueError):
        plan_anchor_repair(raw, report, pack)


def test_same_model_misclassification_remains_outside_protocol_proof():
    value, report, pack = fixture("## 长期表现已有改善")
    source = SourceIndex.build(report, pack)
    # Preserve this known limitation explicitly; indexing is not a semantic fix.
    assert validate_indexed_review(index_review(compact(value), source), source, pack).verdict == "pass"


def test_context_controls_keep_definitions_negation_and_later_conflicts_visible():
    path = Path(__file__).resolve().parents[1] / "data/evaluation/datasets/golden_context_controls_v1.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        source = SourceIndex.build(case["report"], {"facts": {}})
        assert source.resolve(source.reference(case["target"])) == case["target"]
        if case.get("must_flag"):
            assert source.resolve(source.reference(case["must_flag"])) == case["must_flag"]
        assert all(line in "\n".join(b["text"] for b in source.prompt_sources()["blocks"])
                   for line in case["report"].splitlines() if line.strip())
