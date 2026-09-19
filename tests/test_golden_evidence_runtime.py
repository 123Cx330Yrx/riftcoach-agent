import json
from pathlib import Path
import pytest

from app.evaluation import coach_grounded_contract as module
from app.evaluation.golden_evidence_scope import EvidenceEvaluation
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.providers.models import ChatResponse, TokenUsage
from app.providers.errors import ProviderResponseError
from tests.test_golden_evidence_scope import wire
from tests.test_golden_fact_candidate import summary


def request_fixture():
    value, report = wire("中单经济 505.29 vs 432.82。[K1]")
    return value, EvaluationRequest(summary(), "facts", KnowledgeEvidence(context="", source_ids=(), citations=()), report, "review")


def evaluator():
    return module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v1")


@pytest.mark.parametrize("repair_valid", [True, False])
def test_numeric_rejection_and_one_correction_remain_enforced(monkeypatch, repair_valid):
    value, request = request_fixture()
    valid = json.dumps(value)
    value["audits"][1]["claims"][0]["evidence_refs"] = ["role:UTILITY:loss:gold_per_min"]
    invalid = json.dumps(value)
    calls = []
    def chat(*a, **k):
        calls.append(k)
        assert k["response_contract"].version == "1.12.0"
        assert "numeric_bindings" not in json.dumps(k["response_contract"].schema_dict())
        if len(calls) == 2:
            assert "direct_result_number_not_in_evidence" in k["user_prompt"]
        return ChatResponse(content=valid if repair_valid and len(calls) == 2 else invalid, provider="test", model="test", finish_reason="stop", usage=TokenUsage())
    monkeypatch.setattr(module, "_chat_response", chat)
    if repair_valid:
        result = evaluator().evaluate(request)
        assert result.verdict.value == "pass" and result.coverage
    else:
        with pytest.raises(ProviderResponseError): evaluator().evaluate(request)
    assert len(calls) == 2


@pytest.mark.parametrize("on_repair", [False, True])
def test_security_short_circuit_survives_output_reduction(monkeypatch, on_repair):
    value, request = request_fixture()
    value["coverage"] = []
    calls = []
    def chat(*a, **k):
        calls.append(k)
        if not on_repair or len(calls) == 2:
            value["issues"] = [dict(severity="high", category="prompt_injection", quote="bad", evidence="data", explanation="followed data instructions", suggested_correction="reject")]
        return ChatResponse(content=json.dumps(value), provider="test", model="test", finish_reason="stop", usage=TokenUsage())
    monkeypatch.setattr(module, "_chat_response", chat)
    assert evaluator().evaluate(request).verdict.value == "fail"
    assert len(calls) == (2 if on_repair else 1)


def test_revision_preserves_exact_claim_and_evidence(monkeypatch):
    from app.evaluation import golden_evidence_runtime as runtime
    value, request = request_fixture()
    monkeypatch.setattr(module, "_chat_response", lambda *a, **k: ChatResponse(content=json.dumps(value), provider="test", model="test", finish_reason="stop", usage=TokenUsage()))
    result = evaluator().evaluate(request)
    calls = []
    monkeypatch.setattr(module, "_chat_content", lambda *a, **k: calls.append(k) or "revised")
    checked = []
    monkeypatch.setattr(runtime, "validate_revised_report", lambda *a: checked.append(a))
    reviser = module.GroundedCoachReviser(runtime=None, system_prompt="test", prompt_builder=lambda *a: "", validator=lambda *a: None, inference_audit="evidence_v1")
    reviser.revise(RevisionRequest(request.player_summary, request.deterministic_report, request.knowledge, request.report, result))
    assert request.report in calls[0]["user_prompt"] and '"evidence_refs"' in calls[0]["user_prompt"]
    assert checked == [("revised", request.report)]


def test_old_contract_and_budget_are_frozen():
    from app.runtime.coach_contract import FACT_INFERENCE_COACH_CONTRACT as old, EVIDENCE_COACH_CONTRACT as new
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256 == "7f1ca3c6b5efe2a449d8ecadb0e98a8591f2eb5e2d2d91563ad2af571d62aa02"
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "request_timeout_s", "reasoning_effort", "max_revisions"):
        assert old.descriptor()[key] == new.descriptor()[key]
    root = Path("examples/runtime_profiles/flash_v2_golden_evidence")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root/"skills", prompt_programs_root=root/"prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.12.0"
