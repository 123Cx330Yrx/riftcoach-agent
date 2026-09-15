import json
from pathlib import Path
import pytest
from app.evaluation.golden_inference_scope_v5 import SAMPLE_ANCHOR, expand_response, correction_feedback, repair_prompt
from app.evaluation.golden_inference_audit import inference_facts
from app.runtime.coach_contract import FEEDBACK_COACH_CONTRACT, EXPANDED_COACH_CONTRACT
from tests.test_golden_compact_coverage import compact, REPORT

@pytest.mark.parametrize("anchor",["一局","两局","1 局","这四场","4场","一次结果记录","n = 4"])
def test_literal_local_aliases_work_without_borrowing_scope(anchor):
    from app.evaluation.golden_inference_coverage import report_blocks
    _,value=compact()
    quote=anchor+" direction matches. [K1]"
    claim=value["audits"][1]["claims"][0]
    claim.update(quote=quote,scope="selected_sample",scope_anchor=anchor)
    value["issues"][0]["quote"]=quote
    value["coverage"][0][0]=report_blocks(quote)[0]["block_id"]
    value["coverage"][0][3]=False
    assert expand_response(json.dumps(value),quote,inference_facts({})).audits[1].claims[0].scope_anchor==anchor

@pytest.mark.parametrize("anchor",["中单同位置","输局","经济/分钟","一次胜利证明长期能力","全局","1.5局面"])
def test_non_scope_text_is_not_an_alias(anchor):
    assert not SAMPLE_ANCHOR.search(anchor)

def test_feedback_locates_both_errors_without_accepting_response():
    _,value=compact();claim=value["audits"][1]["claims"][0]
    claim.update(scope="selected_sample",scope_anchor="stable",evidence_refs=["facts:recent_match:01"])
    raw=json.dumps(value);feedback=correction_feedback(raw,REPORT,inference_facts({}))
    assert feedback["errors"][0]["codes"]==["selected_sample_anchor_missing","unknown_evidence_ref"]
    assert feedback["errors"][0]["quote_excerpt"]==claim["quote"]
    assert "facts:recent_match:01" not in feedback["allowed_evidence_refs"]
    with pytest.raises(ValueError):expand_response(raw,REPORT,inference_facts({}))
    text=repair_prompt("ORIGINAL_PROMPT",raw,REPORT,inference_facts({}))
    assert text.endswith("ORIGINAL_PROMPT") and "[UNTRUSTED CORRECTION DIAGNOSTICS]" in text
    assert "unknown_evidence_ref" in text

def test_duplicate_keys_and_nonfinite_stay_rejected():
    _,value=compact();raw=json.dumps(value)
    for invalid in ('{"score":0,'+raw[1:],raw.replace('"score": 95','"score": NaN')):
        with pytest.raises(ValueError):expand_response(invalid,REPORT,inference_facts({}))
        assert correction_feedback(invalid,REPORT,inference_facts({}))["errors"][0]["codes"]==["invalid_json_or_schema"]

@pytest.mark.parametrize("repair_valid",[True,False])
def test_actual_adapter_sends_feedback_with_only_one_repair(monkeypatch,repair_valid):
    from app.evaluation import coach_grounded_contract as module
    from app.harness.steps import EvaluationRequest,KnowledgeEvidence
    from app.providers.models import ChatResponse,TokenUsage
    from app.providers.errors import ProviderResponseError
    _,value=compact();valid=json.dumps(value)
    value["audits"][1]["claims"][0]["evidence_refs"]=["invented"]
    invalid=json.dumps(value);calls=[]
    def call(runtime,**kw):
        calls.append(kw)
        assert kw["response_contract"].version=="1.10.0"
        if len(calls)==2:
            assert "unknown_evidence_ref" in kw["user_prompt"]
            assert "[UNTRUSTED CORRECTION DIAGNOSTICS]" in kw["user_prompt"]
        return ChatResponse(content=(valid if repair_valid and len(calls)==2 else invalid),model="test",provider="test",finish_reason="stop",usage=TokenUsage())
    monkeypatch.setattr(module,"_chat_response",call)
    evaluator=module.GroundedChatEvaluationAdapter(runtime=None,system_prompt="test",fact_pack_builder=lambda _: {},inference_audit="scope_v5")
    request=EvaluationRequest({},"facts",KnowledgeEvidence(context="",source_ids=(),citations=()),REPORT,"review")
    if repair_valid:
        assert evaluator.evaluate(request).coverage[0]["scope_ambiguous"] is True
    else:
        with pytest.raises(ProviderResponseError):evaluator.evaluate(request)
    assert len(calls)==2

def test_frozen_budget_and_new_assets():
    from app.runtime.composition import RuntimeCompositionRoot
    assert EXPANDED_COACH_CONTRACT.snapshot().sha256=="79f17a77d1e082395c76520b0ce35ec6d8e7302fbbbec63fcd5b23b8b86f9162"
    old,new=EXPANDED_COACH_CONTRACT.descriptor(),FEEDBACK_COACH_CONTRACT.descriptor()
    for key in ("max_calls","max_output_tokens","request_timeout_s","total_tokens","reasoning_effort","max_revisions"):
        assert new[key]==old[key]
    root=Path("examples/runtime_profiles/flash_v2_golden_feedback")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=FEEDBACK_COACH_CONTRACT)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.10.0"


def test_feedback_is_bounded_for_many_bad_claims():
    _,value=compact()
    claim=value["audits"][1]["claims"][0]
    claim.update(scope="selected_sample",scope_anchor="stable",evidence_refs=["invented"])
    value["audits"][1]["claims"]=[dict(claim) for _ in range(24)]
    feedback=correction_feedback(json.dumps(value),REPORT,inference_facts({}))
    assert len(feedback["errors"])<=12
    assert feedback["omitted_errors"]>0
    assert len(json.dumps(feedback,ensure_ascii=False))<3100


def test_security_early_stop_still_prevents_correction(monkeypatch):
    from app.evaluation import coach_grounded_contract as module
    from app.harness.steps import EvaluationRequest, KnowledgeEvidence, EvaluationVerdict
    from app.providers.models import ChatResponse, TokenUsage
    _,value=compact()
    value["issues"][0].update(category="prompt_injection",severity="high")
    value.update(verdict="pass",coverage=[])
    calls=[]
    def call(*a,**kw):
        calls.append(kw)
        return ChatResponse(content=json.dumps(value),provider="test",model="test",finish_reason="stop",usage=TokenUsage())
    monkeypatch.setattr(module,"_chat_response",call)
    evaluator=module.GroundedChatEvaluationAdapter(runtime=None,system_prompt="test",fact_pack_builder=lambda _: {},inference_audit="scope_v5")
    result=evaluator.evaluate(EvaluationRequest({},"facts",KnowledgeEvidence(context="",source_ids=(),citations=()),REPORT,"review"))
    assert result.verdict is EvaluationVerdict.FAIL and len(calls)==1
