import json
from pathlib import Path

import pytest

from app.evaluation import coach_grounded_contract as legacy
from app.evaluation.golden_fact_runtime import issued_request
from app.evaluation.golden_fact_requests import evaluation_request
from app.evaluation.golden_fact_operations import OperationEvaluation
from app.evaluation.golden_fact_diagnostics import collect_diagnostics
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_compact_coverage import encode_coverage
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.providers.models import ChatResponse, TokenUsage
from app.providers.errors import ProviderResponseError
from tests.test_golden_fact_candidate import summary
from tests.test_golden_fact_operations import operation_payload, WIN


def fixture():
    value, report = operation_payload("经济 505.29。[K1]", "value", [WIN], "505.29")
    canonical = OperationEvaluation.model_validate(value)
    value = canonical.model_dump(mode="json")
    value["coverage"] = encode_coverage(canonical.coverage)
    return value, EvaluationRequest(summary(), "facts", KnowledgeEvidence(context="", source_ids=(), citations=()), report, "review")


def evaluator():
    return legacy.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="fact_v1")


@pytest.mark.parametrize("repair_valid", [True, False])
def test_shared_one_repair_preserves_canonical_bindings(monkeypatch, repair_valid):
    value, request = fixture()
    valid = json.dumps(value)
    value["audits"][1]["claims"][0]["numeric_bindings"][0]["operands"][0][1] = "/missing"
    invalid = json.dumps(value)
    calls = []

    def chat(*args, **kwargs):
        calls.append(kwargs)
        assert kwargs["response_contract"].version == "1.11.0"
        if len(calls) == 2:
            assert "numeric_binding_path_missing" in kwargs["user_prompt"]
            assert '"binding_index":0' in kwargs["user_prompt"]
        return ChatResponse(content=valid if repair_valid and len(calls) == 2 else invalid,
                            provider="test", model="test", finish_reason="stop", usage=TokenUsage())

    monkeypatch.setattr(legacy, "_chat_response", chat)
    if repair_valid:
        result = evaluator().evaluate(request)
        assert result.coverage[0]["cohort_comparison"] == "supported"
        assert result.audits[1]["claims"][0]["numeric_bindings"][0]["operands"] == [WIN]
        assert result.verdict.value == "pass"
    else:
        with pytest.raises(ProviderResponseError): evaluator().evaluate(request)
    assert len(calls) == 2


@pytest.mark.parametrize("on_repair", [False, True])
def test_typed_security_is_terminal_even_with_bad_coverage(monkeypatch, on_repair):
    value, request = fixture()
    value["coverage"] = []
    calls = []

    def chat(*args, **kwargs):
        calls.append(kwargs)
        if not on_repair or len(calls) == 2:
            value["issues"] = [dict(severity="high", category="prompt_injection", quote="bad instruction",
                                    evidence="data", explanation="data instruction followed", suggested_correction="reject")]
        return ChatResponse(content=json.dumps(value), provider="test", model="test", finish_reason="stop", usage=TokenUsage())
    monkeypatch.setattr(legacy, "_chat_response", chat)
    result = evaluator().evaluate(request)
    assert result.verdict.value == "fail" and len(calls) == (2 if on_repair else 1)


def test_diagnostics_localize_numeric_and_scope_issue_relationships():
    value, request = fixture()
    claim = value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference", scope="ambiguous", scope_anchor="经济")
    claim["numeric_bindings"][0]["operands"].append(WIN)
    rows = collect_diagnostics(json.dumps(value), request.report, fact_pack(request.player_summary))
    assert any("ambiguous_exact_other_issue_missing" in r["codes"] and r["claim_index"] == 0 for r in rows)
    assert any("numeric_operation_arity_invalid" in r["codes"] and r["binding_index"] == 0 for r in rows)


def test_budget_is_checked_before_provider_io(monkeypatch):
    _, request = fixture()
    monkeypatch.setattr(legacy, "_chat_response", lambda *a, **k: pytest.fail("unexpected provider call"))
    request = EvaluationRequest(request.player_summary, "huge " * 70000, request.knowledge, request.report, request.user_utterance)
    with pytest.raises(ValueError, match="input_budget_exceeded"):
        evaluator().evaluate(request)


def test_revision_carries_validated_operations_and_runs_report_validator(monkeypatch):
    from app.evaluation import golden_fact_runtime as runtime
    value, request = fixture()
    monkeypatch.setattr(legacy, "_chat_response", lambda *a, **k: ChatResponse(content=json.dumps(value), provider="test", model="test", finish_reason="stop", usage=TokenUsage()))
    evaluation = evaluator().evaluate(request)
    calls = []
    monkeypatch.setattr(legacy, "_chat_content", lambda *a, **k: calls.append(k) or "revised")
    validated = []
    monkeypatch.setattr(runtime, "validate_revised_report", lambda revised, original: validated.append((revised, original)))
    reviser = legacy.GroundedCoachReviser(runtime=None, system_prompt="test", prompt_builder=lambda *a: "", validator=lambda *a: None, inference_audit="fact_v1")
    result = reviser.revise(RevisionRequest(request.player_summary, request.deterministic_report, request.knowledge, request.report, evaluation))
    assert result.report == "revised" and validated == [("revised", request.report)]
    assert '"numeric_bindings"' in calls[0]["user_prompt"] and '"operands"' in calls[0]["user_prompt"]


def test_issued_assets_preserve_old_contract_and_budget():
    from app.runtime.coach_contract import FACT_INFERENCE_COACH_CONTRACT as new, FEEDBACK_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256 == "bcf8dcf628a68d0adec58882da4b36f1e5725322327546e386fec640de600680"
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "request_timeout_s", "reasoning_effort", "max_revisions"):
        assert new.descriptor()[key] == old.descriptor()[key]
    root = Path("examples/runtime_profiles/flash_v2_golden_fact")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root/"skills", prompt_programs_root=root/"prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.11.0"


def test_valid_direct_fact_has_no_scope_diagnostic_and_raw_duplicates_are_not_lost():
    value, request = fixture()
    raw = json.dumps(value)
    pack = fact_pack(request.player_summary)
    assert collect_diagnostics(raw, request.report, pack) == []
    assert collect_diagnostics('{"score":0,' + raw[1:], request.report, pack) == [{"codes": ["invalid_json_or_schema"]}]


def test_direct_and_numeric_errors_are_bounded_data_only():
    from app.evaluation.golden_scope_diagnostics import bounded_feedback
    value, request = fixture()
    claim = value["audits"][1]["claims"][0]
    claim["scope_anchor"] = "fake"
    claim["numeric_bindings"][0]["operands"][0][1] = "/missing"
    value["audits"][1]["claims"] = [claim] * 24
    rows = collect_diagnostics(json.dumps(value), request.report, fact_pack(request.player_summary))
    assert len(rows) == 48
    assert rows[0]["codes"] == ["direct_result_scope_must_be_null"]
    assert rows[1]["codes"] == ["numeric_binding_path_missing"]
    bounded = bounded_feedback(rows)
    assert len(bounded["errors"]) <= 12 and len(json.dumps(bounded, ensure_ascii=False)) <= 3000
    assert len(bounded["errors"]) + bounded["omitted_errors"] == len(rows)
