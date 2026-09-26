"""Policy delivery and frozen-boundary checks, not model quality scores."""
from pathlib import Path

import pytest

from app.evaluation.golden_inference_scope_v3 import (
    SCOPE_V3_POLICY, inference_response_contract, validate_scope_v2,
)
from app.evaluation.golden_inference_scope_v2 import EvaluationResponseModelV17
from app.evaluation.golden_inference_audit import inference_facts
from app.runtime.coach_contract import SCOPE_V2_COACH_CONTRACT, SCOPE_V3_COACH_CONTRACT
from tests.test_golden_inference_scope_v2 import anchored_payload


def test_frozen_v2_identity_and_resource_limits_are_preserved():
    assert SCOPE_V2_COACH_CONTRACT.snapshot().sha256 == "8d96f008ffa5f902ae7c8dbf84367c34dec3690678a2fbec5faf23ec3a742533"
    old, new = SCOPE_V2_COACH_CONTRACT.descriptor(), SCOPE_V3_COACH_CONTRACT.descriptor()
    for key in ("request_policy", "reasoning_effort", "max_calls", "max_revisions",
                "max_input_tokens", "max_output_tokens", "request_timeout_s"):
        assert new[key] == old[key]
    assert inference_response_contract().schema_dict() == EvaluationResponseModelV17.model_json_schema()


def test_new_assets_resolve_without_replacing_v2():
    from app.runtime.composition import RuntimeCompositionRoot
    root = Path("examples/runtime_profiles/flash_v2_golden_scope_v3")
    runtime = RuntimeCompositionRoot.from_directories(
        skills_root=root / "skills", prompt_programs_root=root / "prompt_programs",
        coach_contract=SCOPE_V3_COACH_CONTRACT)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.8.0"


def test_ambiguous_original_still_requires_issue_and_full_coverage():
    p = anchored_payload()
    validate_scope_v2(EvaluationResponseModelV17.model_validate(p),
                      "A stable difference. [K1]", inference_facts({}))
    p.update(verdict="pass", issues=[])
    with pytest.raises(ValueError, match="ambiguous_scope_requires_clarification"):
        EvaluationResponseModelV17.model_validate(p)


def test_actual_evaluator_delivers_only_consolidated_policy(monkeypatch):
    from app.evaluation import coach_grounded_contract as module
    from app.harness.steps import EvaluationRequest, KnowledgeEvidence

    class Captured(Exception):
        pass

    def capture(runtime, **kwargs):
        prompt = kwargs["user_prompt"]
        assert prompt.count(SCOPE_V3_POLICY) == 1
        assert "golden-report-coverage-v1" not in prompt
        assert "golden-inference-scope-v2" not in prompt
        assert "coverage只输出block_id和两类状态" not in prompt
        assert "单个block内连续原文" in prompt
        assert "scope_ambiguous" in prompt and "scope_anchor" in prompt
        assert "输局的稳定同位置差距" in prompt
        assert kwargs["response_contract"].version == "1.8.0"
        raise Captured

    monkeypatch.setattr(module, "_chat_response", capture)
    evaluator = module.GroundedChatEvaluationAdapter(
        runtime=None, system_prompt="test", fact_pack_builder=lambda _: {},
        inference_audit="scope_v3")
    with pytest.raises(Captured):
        evaluator.evaluate(EvaluationRequest({}, "facts",
            KnowledgeEvidence(context="", source_ids=(), citations=()),
            "输局的稳定同位置差距 [K1]", "review"))
