"""Exercise compact wire through real adapters, without Provider I/O."""
import json
from pathlib import Path
import pytest
from app.evaluation import coach_grounded_contract as module
from app.evaluation.golden_inference_scope_v4 import SCOPE_V4_POLICY
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence, EvaluationVerdict
from app.providers.models import ChatResponse, TokenUsage
from app.providers.errors import ProviderResponseError
from app.runtime.coach_contract import SCOPE_V3_COACH_CONTRACT, SCOPE_V4_COACH_CONTRACT
from tests.test_golden_compact_coverage import compact, REPORT

KNOWLEDGE = KnowledgeEvidence(context="", source_ids=(), citations=())

def response(raw):
    return ChatResponse(content=raw, model="test", provider="test", finish_reason="stop", usage=TokenUsage())

def evaluate(monkeypatch, raws, calls):
    def fake(runtime, **kwargs):
        calls.append(kwargs)
        assert kwargs["response_contract"].version == "1.9.0"
        assert kwargs["user_prompt"].count(SCOPE_V4_POLICY) == 1
        assert "每项只含block_id" not in kwargs["user_prompt"]
        return response(raws[len(calls)-1])
    monkeypatch.setattr(module, "_chat_response", fake)
    return module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test",
        fact_pack_builder=lambda _: {}, inference_audit="scope_v4").evaluate(
            EvaluationRequest({}, "facts", KNOWLEDGE, REPORT, "review"))

def test_canonical_evidence_reaches_revision(monkeypatch):
    original, wire = compact()
    calls=[]
    result=evaluate(monkeypatch,[json.dumps(wire)],calls)
    assert len(calls)==1
    assert result.verdict is EvaluationVerdict.NEEDS_REVISION
    assert list(result.coverage)==original.model_dump(mode="json")["coverage"]
    assert list(result.audits)==original.model_dump(mode="json")["audits"]
    assert list(result.issues)==original.model_dump(mode="json")["issues"]
    def revision(runtime, **kwargs):
        data=json.loads(kwargs["user_prompt"].split("[UNTRUSTED REVISION DATA-ONLY]\n")[1])
        assert data["evaluation"]["coverage"]==list(result.coverage)
        assert data["evaluation"]["audits"]==list(result.audits)
        assert data["evaluation"]["issues"]==list(result.issues)
        from app.report_validation import COACH_REPORT_HEADINGS
        return "\n\n".join(COACH_REPORT_HEADINGS) + "\n" + REPORT
    monkeypatch.setattr(module,"_chat_content",revision)
    module.GroundedCoachReviser(runtime=None,system_prompt="test",prompt_builder=lambda *a:"",
        validator=lambda *a:None,inference_audit="scope_v4").revise(
            RevisionRequest({},"facts",KNOWLEDGE,REPORT,result))

@pytest.mark.parametrize("kind",["bad_bool","hidden_ambiguity","missing_issue","bad_anchor","bad_evidence","duplicate_key"])
@pytest.mark.parametrize("repair_valid",[True,False])
def test_invalid_wire_uses_only_existing_repair(monkeypatch,kind,repair_valid):
    _,wire=compact(); valid=json.dumps(wire)
    if kind=="bad_bool": wire["coverage"][0][3]=1
    elif kind=="hidden_ambiguity": wire["coverage"][0][3]=False
    elif kind=="missing_issue": wire.update(verdict="pass",issues=[])
    elif kind=="bad_anchor": wire["audits"][1]["claims"][0]["scope_anchor"]="invented"
    elif kind=="bad_evidence": wire["audits"][1]["claims"][0]["evidence_refs"]=["invented"]
    invalid=json.dumps(wire)
    if kind=="duplicate_key": invalid='{"score":0,'+invalid[1:]
    calls=[]
    if repair_valid:
        assert evaluate(monkeypatch,[invalid,valid],calls).verdict is EvaluationVerdict.NEEDS_REVISION
    else:
        with pytest.raises(ProviderResponseError): evaluate(monkeypatch,[invalid,invalid],calls)
    assert [c["harness_step"] for c in calls]==["evaluate","evaluate_repair"]

def test_security_finding_stops_before_coverage_repair(monkeypatch):
    _,wire=compact()
    wire["issues"][0].update(category="prompt_injection",severity="high")
    wire["verdict"]="pass"
    wire["coverage"]=[]
    calls=[]
    assert evaluate(monkeypatch,[json.dumps(wire)],calls).verdict is EvaluationVerdict.FAIL
    assert len(calls)==1

def test_new_assets_and_frozen_high_profile():
    from app.runtime.composition import RuntimeCompositionRoot
    assert SCOPE_V3_COACH_CONTRACT.snapshot().sha256=="577a2fd5faed690396004d37ef083c0040c9fd7a2adeb8972d06867e21ac4084"
    old,new=SCOPE_V3_COACH_CONTRACT.descriptor(),SCOPE_V4_COACH_CONTRACT.descriptor()
    for key in ("request_policy","reasoning_effort","max_calls","max_revisions","max_input_tokens","max_output_tokens","request_timeout_s"):
        assert new[key]==old[key]
    root=Path("examples/runtime_profiles/flash_v2_golden_scope_v4")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=SCOPE_V4_COACH_CONTRACT)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.9.0"
