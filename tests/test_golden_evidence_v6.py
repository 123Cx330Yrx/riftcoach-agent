import json
from pathlib import Path

import pytest

from app.evaluation.golden_evidence_diagnostics_v6 import collect_diagnostics
from app.evaluation.golden_evidence_scope_v5 import expand_evidence
from app.evaluation.golden_fact_candidate import fact_pack
from app.providers.errors import ProviderResponseError
from tests import test_golden_evidence_runtime as shared
from tests.test_golden_evidence_v4 import current


@pytest.mark.parametrize("second", ['"a"', '"b"'])
def test_duplicate_evidence_is_located_without_last_value_wins(second):
    raw = '{"issues":[{"evidence":"a","evidence":' + second + '}]}'
    assert collect_diagnostics(raw, "", {}) == [
        {"path": "$.issues[0].evidence", "codes": ["duplicate_json_field"]}
    ]


@pytest.mark.parametrize("repair_valid", [True, False])
def test_duplicate_response_gets_precise_single_correction(monkeypatch, repair_valid):
    value, request = shared.request_fixture()
    valid = json.dumps(current(value))
    invalid = valid.replace('"score":', '"score": 0, "score":', 1)
    calls = []

    def chat(*args, **kwargs):
        calls.append(kwargs)
        assert kwargs["response_contract"].version == "1.17.0"
        if len(calls) == 2:
            assert "duplicate_json_field" in kwargs["user_prompt"]
            assert "$.score" in kwargs["user_prompt"]
        return shared.ChatResponse(
            content=valid if repair_valid and len(calls) == 2 else invalid,
            provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage(),
        )

    monkeypatch.setattr(shared.module, "_chat_response", chat)
    evaluator = shared.module.GroundedChatEvaluationAdapter(
        runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v6"
    )
    if repair_valid:
        assert evaluator.evaluate(request).verdict.value == "pass"
    else:
        with pytest.raises(ProviderResponseError):
            evaluator.evaluate(request)
    assert len(calls) == 2


def test_ambiguous_claim_is_not_silently_removed_to_accept_response():
    value, request = shared.request_fixture()
    value = current(value)
    claim = value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference", scope="ambiguous", scope_anchor="中单")
    raw = json.dumps(value)
    errors = collect_diagnostics(raw, request.report, fact_pack(request.player_summary))
    assert any("ambiguous_exact_other_issue_missing" in e["codes"] for e in errors)
    with pytest.raises(ValueError):
        expand_evidence(raw, request.report, fact_pack(request.player_summary))


def test_revision_retains_entire_evaluation_and_evidence():
    from app.evaluation.golden_evidence_requests_v6 import revision_request
    from app.evaluation.golden_evidence_requests_v5 import revision_request as old_request
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size

    value, request = shared.request_fixture()
    canonical = expand_evidence(json.dumps(current(value)), request.report, fact_pack(request.player_summary))
    args = (request.player_summary, request.deterministic_report, request.knowledge, request.report, canonical)
    old, new = old_request(*args), revision_request(*args)
    # Only the instruction prefix changes; the complete grounded payload is identical.
    marker = json.dumps(canonical.model_dump(mode="json"), ensure_ascii=False)
    assert marker in new.messages[1].content
    assert old.messages[1].content[old.messages[1].content.index(marker):] == new.messages[1].content[new.messages[1].content.index(marker):]
    assert request.report in new.messages[1].content
    assert size(new) < size(old)


def test_new_assets_and_old_contract_remain_bound():
    from app.runtime.coach_contract import EVIDENCE_V6_COACH_CONTRACT as new, EVIDENCE_V5_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot

    assert old.snapshot().sha256 == "8c4a7c289ed8d9334b61d25455000f10e185937f63149c844a73184de1d839cb"
    for key in ("total_tokens", "max_calls", "max_output_tokens", "request_timeout_s", "execution_timeout_s", "reasoning_effort"):
        assert new.descriptor()[key] == old.descriptor()[key]
    root = Path("examples/runtime_profiles/flash_v2_golden_evidence_v6")
    runtime = RuntimeCompositionRoot.from_directories(
        skills_root=root / "skills", prompt_programs_root=root / "prompt_programs", coach_contract=new
    )
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.17.0"
