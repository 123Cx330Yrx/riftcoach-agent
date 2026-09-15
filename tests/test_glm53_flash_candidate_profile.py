from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    select_candidate_profile_for_failure,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole, ToolChoiceMode


def test_candidate_plan_is_low_thinking_4096_and_never_executable() -> None:
    plan = GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN

    assert plan.provider_id == "zhipu"
    assert plan.model == "glm-5.3-flash"
    assert plan.thinking_profile.reasoning_effort == "low"
    assert plan.thinking_profile.clear_thinking is False
    assert plan.max_output_tokens == 4096
    assert plan.activation_state == "candidate"
    assert plan.execution_allowed is False
    assert plan.public_identity()["thinking_profile_id"] == (
        "glm-5.3-flash-candidate-enabled-low-replay"
    )

    with pytest.raises(FrozenInstanceError):
        plan.max_output_tokens = 2048  # type: ignore[misc]


def test_build_request_clamps_caller_budget_and_overwrites_spoofable_metadata() -> None:
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "分析最近一局。"),),
        tool_choice=ToolChoiceMode.NONE,
        temperature=0.1,
        top_p=0.1,
        max_tokens=8192,
        timeout_s=180,
        metadata={
            "candidate_profile_id": "forged",
            "runtime_profile_id": "forged-runtime",
            "unrelated": "preserved",
        },
    )

    prepared = GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.build_request(request)

    assert prepared.max_tokens == 4096
    assert prepared.timeout_s == 90.0
    assert prepared.temperature == 1.0
    assert prepared.top_p == 0.95
    assert prepared.metadata["candidate_profile_id"] == (
        "glm-5.3-flash-candidate-low-4096"
    )
    assert prepared.metadata["runtime_profile_id"] == (
        "glm-5.3-flash-runtime-low-candidate"
    )
    assert prepared.metadata["unrelated"] == "preserved"
    assert prepared.messages == request.messages
    assert prepared.tool_choice is request.tool_choice


@pytest.mark.parametrize(
    ("failure_code", "provider_error_code", "selected"),
    [
        ("provider_response_invalid", "incomplete_chat_response", True),
        ("provider_timeout", "timeout", False),
        ("provider_response_invalid", "invalid_chat_response", False),
        (None, None, False),
    ],
)
def test_selection_is_narrow_and_does_not_become_an_implicit_fallback(
    failure_code: str | None,
    provider_error_code: str | None,
    selected: bool,
) -> None:
    plan = select_candidate_profile_for_failure(
        failure_code=failure_code,
        provider_error_code=provider_error_code,
    )
    assert (plan is not None) is selected
    if plan is not None:
        assert plan.execution_allowed is False


def test_candidate_plan_rejects_forged_identity() -> None:
    with pytest.raises(ValueError, match="unsupported candidate profile identity"):
        type(GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN)(
            profile_id="other-candidate",
        )

