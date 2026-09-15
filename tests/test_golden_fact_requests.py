import json

from app.evaluation.golden_fact_requests import evaluation_request, revision_request, response_contract, POLICY
from app.evaluation.coach_grounded_contract import evaluation_response_contract_v12
from app.evaluation.golden_fact_operations import OperationEvaluation
from app.harness.steps import KnowledgeEvidence
from tests.test_golden_fact_operations import operation_payload, WIN
from tests.test_golden_fact_candidate import summary


def test_full_request_replaces_old_schema_and_reuses_one_fact_registry():
    knowledge = KnowledgeEvidence(context="", source_ids=(), citations=())
    request = evaluation_request(summary(), "Deterministic facts", knowledge, "经济 505.29。", "review")
    prompt = request.messages[1].content
    assert prompt.count(POLICY) == 1
    schema = json.dumps(response_contract().schema_dict(), ensure_ascii=False, separators=(",", ":"))
    assert prompt.count(schema) == 1
    assert json.dumps(evaluation_response_contract_v12().schema_dict(), ensure_ascii=False, indent=2) not in prompt
    assert '"generation_facts"' not in prompt
    assert '"inference_facts"' in prompt
    assert "SECURITY POLICY" in prompt
    assert request.max_tokens == 16384 and request.timeout_s == 180
    assert request.response_contract.name == "offline_fact_candidate"


def test_correction_keeps_policy_and_complete_original_context():
    knowledge = KnowledgeEvidence(context="", source_ids=(), citations=())
    args = (summary(), "Deterministic facts", knowledge, "经济 505.29。", "review")
    base = evaluation_request(*args)
    repaired = evaluation_request(*args, diagnostics=[{"codes": ["numeric_binding_value_mismatch"]}])
    assert repaired.messages[1].content.endswith(base.messages[1].content)
    assert "[UNTRUSTED CORRECTION DIAGNOSTICS]" in repaired.messages[1].content
    assert "only correction attempt" in repaired.messages[1].content


def test_revision_preserves_canonical_claims_and_math_evidence():
    value, report = operation_payload("经济 505.29。", "value", [WIN], "505.29")
    evaluation = OperationEvaluation.model_validate(value)
    request = revision_request(summary(), "facts", KnowledgeEvidence(context="", source_ids=(), citations=()), report, evaluation)
    prompt = request.messages[1].content
    assert '"numeric_bindings"' in prompt and '"operands"' in prompt
    assert '"report_blocks"' not in prompt
    assert request.response_contract is None
    assert request.max_tokens == 16384 and request.timeout_s == 180
