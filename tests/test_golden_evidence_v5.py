import json
from pathlib import Path
import pytest
from app.evaluation.golden_evidence_scope_v5 import expand_evidence
from app.evaluation.golden_fact_candidate import fact_pack
from tests.test_golden_fact_candidate import summary
from tests.test_golden_evidence_scope import wire
from tests.test_golden_evidence_v4 import current
from tests import test_golden_evidence_runtime as shared


@pytest.mark.parametrize("anchor,valid",[("单局复盘",True),("单局观察",True),("单局限",False),("同位置",False)])
def test_literal_single_game_alias_without_broadening_to_non_scope_words(anchor,valid):
    old,report=wire(anchor,["scope:limits"])
    value=current(old);claim=value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference",scope="selected_sample",scope_anchor=anchor)
    if valid:
        assert expand_evidence(json.dumps(value),report,fact_pack(summary())).verdict=="pass"
    else:
        with pytest.raises(ValueError,match="anchor_missing"):
            expand_evidence(json.dumps(value),report,fact_pack(summary()))


def test_new_adapter_and_asset_identity(monkeypatch):
    from app.runtime.coach_contract import EVIDENCE_V5_COACH_CONTRACT as new,EVIDENCE_V4_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256=="c4043c1f1625cc30353e6a6718d747f95826ff66aa615ec4d5d42605b3f63a27"
    for key in ("total_tokens","max_calls","max_output_tokens","request_timeout_s","execution_timeout_s"):
        assert new.descriptor()[key]==old.descriptor()[key]
    root=Path("examples/runtime_profiles/flash_v2_golden_evidence_v5")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.16.0"
    value,request=shared.request_fixture()
    calls=[]
    def chat(*args,**kwargs):
        calls.append(kwargs)
        assert kwargs["response_contract"].version=="1.16.0"
        return shared.ChatResponse(content=json.dumps(current(value)),provider="test",model="test",finish_reason="stop",usage=shared.TokenUsage())
    monkeypatch.setattr(shared.module,"_chat_response",chat)
    evaluator=shared.module.GroundedChatEvaluationAdapter(runtime=None,system_prompt="test",fact_pack_builder=lambda _: {},inference_audit="evidence_v5")
    assert evaluator.evaluate(request).verdict.value=="pass" and len(calls)==1
