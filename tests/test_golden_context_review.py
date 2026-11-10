from copy import deepcopy
from dataclasses import replace
import json
import pytest

from app.evaluation.golden_context_review import expand_context, repair_plan, apply_patch
from app.evaluation.golden_review_experiment import SourceIndex, index_review, compact
from app.evaluation.golden_context_requests import evaluation_request, patch_request
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_inference_coverage import report_blocks
from tests.test_golden_evidence_v8 import fixture
from tests import test_golden_evidence_runtime as shared


def wire(report="这四场方向一致。[K1]"):
    old, _, pack = fixture(report)
    source = SourceIndex.build(report, pack)
    old["reviewed_blocks"] = [b for b, _ in source.blocks]
    old["heading_reviews"] = [dict(block_id=b, kind="navigation") for b, t in source.blocks if t.startswith("#")]
    value = index_review(compact(old), source)["evaluation"]
    value["source_digest"] = source.source_digest
    return value, report, pack


def claim(value, report, pack, *, context=None, anchor="这四场", scope="selected_sample", quote=None):
    source = SourceIndex.build(report, pack)
    row = dict(quote_ref=source.reference(quote or report), evidence_refs=[source.evidence_keys.index("scope:limits")+1],
        explanation="按报告实际范围和证据核对", status="supported", claim_kind="inference", scope=scope,
        scope_anchor=anchor, context=context)
    value["audits"][1]["claims"] = [row]
    return row


def test_explicit_definition_keeps_own_quote_context_and_coverage():
    target = "经济和伤害是较稳定的差异项。"
    definition = "下句中的较稳定仅指这四场中单方向一致，不代表未来。"
    value, report, pack = wire(definition+"\n\n"+target+"\n\n建议[K1]")
    source = SourceIndex.build(report, pack)
    claim(value, report, pack, quote=target, context=dict(quote_ref=source.reference(definition),
        relation="defines_scope", explanation="前段明确指向下句的较稳定"))
    result = expand_context(compact(value), report, pack)
    actual = result.audits[1].claims[0]
    assert actual.quote == target and actual.context.quote == definition
    assert actual.block_id != actual.context.block_id
    assert len(result.coverage) == 3 and result.verdict == "pass"


@pytest.mark.parametrize("kind", ["nonexistent", "stale_source", "wrong_relation", "no_anchor", "unknown_evidence", "missing_block", "duplicate_heading", "extra_json", "duplicate_key"])
def test_invalid_references_never_become_accepted(kind):
    target = "## 持续存在的输出差距"
    definition = "本标题持续存在仅指这四场方向一致。"
    value, report, pack = wire(target+"\n\n"+definition)
    source = SourceIndex.build(report, pack)
    row = claim(value, report, pack, quote=target, context=dict(quote_ref=source.reference(definition),
        relation="defines_scope", explanation="本标题显式定义"))
    value["heading_reviews"][0]["kind"] = "assertion"
    if kind == "nonexistent": row["context"]["quote_ref"]["head"] = "不存在"
    if kind == "stale_source": value["source_digest"] = "0"*64
    if kind == "wrong_relation": row["context"]["relation"] = "negates"
    if kind == "no_anchor": row["scope_anchor"] = None
    if kind == "unknown_evidence": row["evidence_refs"] = [9999]
    if kind == "missing_block": value["reviewed_blocks"].pop()
    if kind == "duplicate_heading": value["heading_reviews"] *= 2
    raw = compact(value)
    if kind == "extra_json": raw += '{}'
    if kind == "duplicate_key": raw = raw.replace('"score":95', '"score":95,"score":95')
    with pytest.raises(ValueError): expand_context(raw, report, pack)


def test_quoted_negation_supported_but_later_wrong_claim_still_requires_issue():
    target = "伤害低就是失败原因。"
    denial = "上面引文是错误说法，结果不能单独证明因果。"
    value, report, pack = wire("> "+target+"\n\n"+denial+"\n\n但已证明长期能力差。")
    source = SourceIndex.build(report, pack)
    claim(value, report, pack, quote=target, anchor="不能", scope="question_or_negation",
        context=dict(quote_ref=source.reference(denial), relation="negates", explanation="明确否定上文"))
    assert expand_context(compact(value), report, pack).audits[1].claims[0].context.relation == "negates"
    bad = deepcopy(value["audits"][1]["claims"][0])
    bad.update(quote_ref=source.reference("但已证明长期能力差。"), context=None, scope="beyond_sample", scope_anchor="长期", status="unsupported")
    value["audits"][1]["claims"].append(bad)
    with pytest.raises(ValueError, match="unsupported_claim_requires_issue"):
        expand_context(compact(value), report, pack)


def patch_fixture():
    value, report, pack = wire()
    claim(value, report, pack, anchor="同位置")
    raw = compact(value)
    plan = repair_plan(raw, report, pack)
    patch = dict(mode="reference_only", base_digest=plan.base_digest, source_digest=plan.source_digest,
        changes=[dict(audit_index=1, claim_index=0, scope_anchor="这四场")])
    return raw, patch, report, pack


def test_patch_changes_only_diagnosed_anchor_and_full_validation_runs():
    raw, patch, report, pack = patch_fixture()
    result = apply_patch(raw, compact(patch), report, pack)
    assert result.verdict == "pass" and result.audits[1].claims[0].scope_anchor == "这四场"
    patch["changes"][0]["scope_anchor"] = "不存在"
    with pytest.raises(ValueError): apply_patch(raw, compact(patch), report, pack)


@pytest.mark.parametrize("kind", ["stale", "duplicate", "wrong_target", "semantic_change", "escape"])
def test_patch_rejects_stale_unrelated_and_semantic_edits(kind):
    raw, patch, report, pack = patch_fixture()
    if kind == "stale": patch["base_digest"] = "0"*64
    if kind == "duplicate": patch["changes"] *= 2
    if kind == "wrong_target": patch["changes"][0]["audit_index"] = 0
    if kind == "semantic_change": patch["changes"][0]["status"] = "supported"
    if kind == "escape": patch.update(mode="needs_reassessment", changes=[], reason="发现判断错误")
    with pytest.raises(ValueError): apply_patch(raw, compact(patch), report, pack)


def test_numeric_guard_and_missing_issue_survive_new_representation():
    value, report, pack = wire("中单经济999999/分。")
    source = SourceIndex.build(report, pack)
    row = claim(value, report, pack)
    row.update(claim_kind="direct_result", scope=None, scope_anchor=None, evidence_refs=[source.evidence_keys.index("facts:recent_aggregate")+1])
    with pytest.raises(ValueError, match="direct_result_number_not_in_evidence"):
        expand_context(compact(value), report, pack)


@pytest.mark.parametrize("mode", ["patch", "escape", "reassessment", "second_invalid", "security"])
def test_runtime_uses_one_correction_and_preserves_security(monkeypatch, mode):
    from app.evaluation import coach_grounded_contract as module
    from app.evaluation import golden_context_runtime as runtime
    raw, patch, report, pack = patch_fixture()
    _, request = shared.request_fixture()
    request = replace(request, report=report)
    calls = []
    value = json.loads(raw)
    if mode in {"reassessment", "second_invalid"}: value["reviewed_blocks"] = []
    if mode == "escape": patch.update(mode="needs_reassessment", changes=[], reason="需要更改判断")
    def chat(*a, **k):
        calls.append(k)
        content = compact(value)
        if mode == "security":
            secured = deepcopy(value)
            secured["issues"] = [dict(severity="high", category="prompt_injection", quote_ref={"block":1},
                evidence="报告文本", explanation="不可信指令", suggested_correction="停止")]
            content = compact(secured)
        elif len(calls) == 2:
            if mode in {"patch", "escape"}:
                assert k["response_contract"].name == "coach_reference_correction"
                content = compact(patch)
            elif mode == "reassessment":
                valid = json.loads(raw)
                valid["audits"][1]["claims"][0]["scope_anchor"] = "这四场"
                content = compact(valid)
        return shared.ChatResponse(content=content, provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage())
    monkeypatch.setattr(module, "_chat_response", chat)
    adapter = module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="context_v1")
    if mode in {"escape", "second_invalid"}:
        with pytest.raises(shared.ProviderResponseError): adapter.evaluate(request)
    else:
        result = adapter.evaluate(request)
        assert result.verdict.value == ("fail" if mode == "security" else "pass")
    assert len(calls) == (1 if mode == "security" else 2)


def test_requests_keep_complete_sources_and_reject_oversize():
    _, request = shared.request_fixture()
    built = evaluation_request(request.player_summary, request.deterministic_report, request.knowledge, request.report, request.user_utterance)
    text = built.messages[1].content
    assert request.report in text and '"source_index"' in text
    assert built.max_tokens == 32768 and built.timeout_s == 300
    with pytest.raises(ValueError, match="input_budget_exceeded"):
        evaluation_request(request.player_summary, "X"*70000, request.knowledge, request.report, request.user_utterance)


def test_new_identity_resolves_without_changing_old_snapshots(tmp_path):
    from pathlib import Path
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT as new, EVIDENCE_V8_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    old_root = Path("examples/runtime_profiles/flash_v2_golden_evidence_v8")
    RuntimeCompositionRoot.from_directories(skills_root=old_root/"skills", prompt_programs_root=old_root/"prompt_programs", coach_contract=old)
    root = Path("examples/runtime_profiles/flash_v2_golden_context")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root/"skills", prompt_programs_root=root/"prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.20.0"
    from tests.test_coach_contract_repair import GroundedProvider
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    product = runtime.build_offline_coach_runtime(runs_root=tmp_path,
        provider=GroundedProvider(provider_name="zhipu", model_name="glm-5.3-flash"),
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs")))
    assert product._execution_factory._evaluator_factory(None).inference_audit == "context_v1"
    assert product._execution_factory._reviser_factory(None).inference_audit == "context_v1"
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "request_timeout_s", "reasoning_effort", "max_revisions"):
        assert old.descriptor()[key] == new.descriptor()[key]


def test_revision_receives_context_verbatim(monkeypatch):
    from app.evaluation import golden_context_runtime as runtime
    from app.evaluation import coach_grounded_contract as module
    from app.harness.steps import RevisionRequest
    from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
    value, report, pack = wire("标题较稳定。\n\n该标题仅指这四场方向一致。[K1]")
    source = SourceIndex.build(report, pack)
    claim(value, report, pack, quote="标题较稳定。", context=dict(quote_ref={"block":2}, relation="defines_scope", explanation="显式标题指代"))
    payload = expand_context(compact(value), report, pack)
    base = module.GroundedChatEvaluationAdapter._result(payload)
    result = CoveredEvaluationResult(**base.__dict__, audits=tuple(a.model_dump(mode="json") for a in payload.audits), coverage=tuple(c.model_dump(mode="json") for c in payload.coverage))
    calls=[]
    monkeypatch.setattr(module, "_chat_content", lambda *a, **k: calls.append(k) or report)
    monkeypatch.setattr(runtime, "validate_revised_report", lambda *a: None)
    _, request = shared.request_fixture()
    reviser = module.GroundedCoachReviser(runtime=None, system_prompt="test", prompt_builder=lambda *a:"", validator=lambda *a:None, inference_audit="context_v1")
    reviser.revise(RevisionRequest(request.player_summary, request.deterministic_report, request.knowledge, report, result))
    assert '"context": {' in calls[0]["user_prompt"]
    assert "该标题仅指这四场方向一致。[K1]" in calls[0]["user_prompt"]
