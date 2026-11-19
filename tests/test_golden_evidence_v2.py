import json
from pathlib import Path
import pytest

from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_evidence_scope_v2 import expand_evidence
from app.evaluation.golden_evidence_requests_v2 import POLICY
from tests.test_golden_fact_candidate import summary
from tests.test_golden_evidence_scope import wire
from tests import test_golden_evidence_runtime as shared


def test_aggregate_window_label_is_not_a_missing_statistic():
    source = summary()
    source["recent_summary"] = {"win_loss_comparison": {"wins": {"deaths_before_15": 2.5}, "losses": {"deaths_before_15": 2.67}}}
    value, report = wire("| 15 分钟前死亡 | 2.5 | 2.67 |", ["facts:recent_aggregate"])
    result = expand_evidence(json.dumps(value), report, fact_pack(source))
    assert result.verdict == "pass"
    value, report = wire("| 16 分钟前死亡 | 2.5 | 2.67 |", ["facts:recent_aggregate"])
    with pytest.raises(ValueError, match="number_not_in_evidence"):
        expand_evidence(json.dumps(value), report, fact_pack(source))


def test_anchor_instruction_distinguishes_length_from_prefix_positions():
    assert "scope_anchor取原句1到20字符" not in POLICY
    assert "不要求在开头" in POLICY and "例如quote中有“这四场”" in POLICY
    assert "不自动定义稳定判断的含义" in POLICY
    value, report = wire("观察结果：仅指这四场方向一致。", ["scope:limits"])
    claim = value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference", scope="selected_sample", scope_anchor="这四场")
    expand_evidence(json.dumps(value), report, fact_pack(summary()))
    claim["scope_anchor"] = "观察结果"
    with pytest.raises(ValueError, match="anchor_missing"):
        expand_evidence(json.dumps(value), report, fact_pack(summary()))


@pytest.mark.parametrize("repair_valid", [True, False])
def test_new_adapter_keeps_single_correction(monkeypatch, repair_valid):
    value, request = shared.request_fixture()
    valid = json.dumps(value)
    value["audits"][1]["claims"][0]["evidence_refs"] = ["role:UTILITY:loss:gold_per_min"]
    calls = []
    def chat(*a, **k):
        calls.append(k)
        assert k["response_contract"].version == "1.13.0"
        return shared.ChatResponse(content=valid if repair_valid and len(calls) == 2 else json.dumps(value), provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage())
    monkeypatch.setattr(shared.module, "_chat_response", chat)
    evaluator = shared.module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v2")
    if repair_valid:
        assert evaluator.evaluate(request).verdict.value == "pass"
    else:
        with pytest.raises(shared.ProviderResponseError): evaluator.evaluate(request)
    assert len(calls) == 2


@pytest.mark.parametrize("on_repair", [False, True])
def test_new_adapter_keeps_security_stop(monkeypatch, on_repair):
    monkeypatch.setattr(shared, "evaluator", lambda: shared.module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v2"))
    shared.test_security_short_circuit_survives_output_reduction(monkeypatch, on_repair)


def test_version_assets_and_budget():
    from app.runtime.coach_contract import EVIDENCE_COACH_CONTRACT as old, EVIDENCE_V2_COACH_CONTRACT as new
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256 == "ef2f3852912fea2ed68296564a75f538dba8e2abdac67e6e38344cc6ce3a3141"
    for key in ("max_calls", "max_output_tokens", "request_timeout_s", "total_tokens", "reasoning_effort"):
        assert old.descriptor()[key] == new.descriptor()[key]
    root = Path("examples/runtime_profiles/flash_v2_golden_evidence_v2")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root/"skills", prompt_programs_root=root/"prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.13.0"
