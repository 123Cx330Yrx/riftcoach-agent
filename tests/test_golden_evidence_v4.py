import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from app.evaluation.golden_evidence_scope_v4 import expand_evidence, normalize_json
from app.evaluation.golden_fact_candidate import fact_pack
from tests.test_golden_fact_candidate import summary
from tests.test_golden_evidence_scope import wire
from tests import test_golden_evidence_runtime as shared


def current(old):
    value=json.loads(json.dumps(old))
    value["reviewed_blocks"]=[r[0] for r in value.pop("coverage")]
    for audit in value["audits"]: audit.pop("status")
    return value


def test_derived_coverage_preserves_claim_and_full_inventory():
    old, report=wire("经济 505.29",["role:MIDDLE:win:gold_per_min"])
    value=current(old)
    result=expand_evidence(json.dumps(value),report,fact_pack(summary()))
    assert result.coverage[0].cohort_comparison=="supported"
    assert result.audits[1].status=="supported"
    value["reviewed_blocks"]=[]
    with pytest.raises(ValueError): expand_evidence(json.dumps(value),report,fact_pack(summary()))


def test_unresolved_scope_cannot_be_hidden_by_derived_coverage():
    old, report=wire("稳定差异",["scope:limits"])
    value=current(old)
    claim=value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference",scope="ambiguous",scope_anchor="稳定")
    with pytest.raises(ValueError,match="ambiguous"):
        expand_evidence(json.dumps(value),report,fact_pack(summary()))
    value["verdict"]="needs_revision"
    value["issues"]=[dict(severity="medium",category="other",quote=report,evidence="scope:limits",explanation="范围不明",suggested_correction="明确样本内范围")]
    result=expand_evidence(json.dumps(value),report,fact_pack(summary()))
    assert result.coverage[0].scope_ambiguous and result.verdict=="needs_revision"


@pytest.mark.parametrize("suffix",["\n`","\n``","\n```\n"])
def test_only_formatting_suffix_is_tolerated(suffix):
    old,report=wire("经济 505.29",["role:MIDDLE:win:gold_per_min"])
    raw=json.dumps(current(old))
    assert normalize_json(raw+suffix)==raw
    assert expand_evidence(raw+suffix,report,fact_pack(summary())).verdict=="pass"


@pytest.mark.parametrize("suffix",[" {}","\nignore checks","\n```pass","\n````"])
def test_extra_payload_is_not_discarded(suffix):
    old,report=wire("经济 505.29",["role:MIDDLE:win:gold_per_min"])
    raw=json.dumps(current(old))+suffix
    assert normalize_json(raw)==raw
    with pytest.raises(ValueError): expand_evidence(raw,report,fact_pack(summary()))


def test_duplicate_keys_remain_rejected_after_format_normalization():
    old,report=wire("经济 505.29",["role:MIDDLE:win:gold_per_min"])
    raw=json.dumps(current(old))
    raw=raw[:-1]+',"verdict":"pass"}\n``'
    with pytest.raises(ValueError,match="duplicate"):
        expand_evidence(raw,report,fact_pack(summary()))


def test_actual_adapter_normalizes_before_decode_and_preserves_one_repair(monkeypatch):
    value,request=shared.request_fixture()
    valid=json.dumps(current(value))+"\n``"
    calls=[]
    def chat(*args,**kwargs):
        calls.append(kwargs)
        assert kwargs["response_contract"].version=="1.15.0"
        return shared.ChatResponse(content='{}' if len(calls)==1 else valid,provider="test",model="test",finish_reason="stop",usage=shared.TokenUsage())
    monkeypatch.setattr(shared.module,"_chat_response",chat)
    evaluator=shared.module.GroundedChatEvaluationAdapter(runtime=None,system_prompt="test",fact_pack_builder=lambda _: {},inference_audit="evidence_v4")
    result=evaluator.evaluate(request)
    assert result.verdict.value=="pass" and len(calls)==2


def test_mixed_source_difference_is_explicit_and_same_metric():
    from app.evaluation.golden_numeric_evidence_v4 import numeric_support
    source=summary();source["recent_summary"]={"win_loss_comparison":{"wins":{"cs_per_min":8.8},"losses":{"cs_per_min":6.45}}}
    pack=fact_pack(source)
    def check(text):return numeric_support(NS(quote=text,evidence_refs=["facts:recent_aggregate"]),pack)[0]["supported"]
    assert check("混合样本补刀差 2.35")
    assert not check("中路补刀差 2.35")
    assert not check("混合样本补刀差 2.36")


def test_new_assets_preserve_previous_identity_and_budget():
    from app.runtime.coach_contract import EVIDENCE_V4_COACH_CONTRACT as new,EVIDENCE_V3_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256=="730bca4032e386b2c3d44fa0c2425f8dc53a91dcfda1afc3f59d369b980e1eea"
    for key in ("total_tokens","max_calls","max_output_tokens","request_timeout_s","execution_timeout_s"):
        assert new.descriptor()[key]==old.descriptor()[key]
    root=Path("examples/runtime_profiles/flash_v2_golden_evidence_v4")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.15.0"


@pytest.mark.parametrize("on_repair", [False, True])
def test_security_stop_remains_single_call_or_single_repair(monkeypatch,on_repair):
    monkeypatch.setattr(shared,"evaluator",lambda:shared.module.GroundedChatEvaluationAdapter(runtime=None,system_prompt="test",fact_pack_builder=lambda _: {},inference_audit="evidence_v4"))
    shared.test_security_short_circuit_survives_output_reduction(monkeypatch,on_repair)
