from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionMode,
    ResponseDisposition,
    ResponseRequestContext,
    require_registered_response_completion_policy,
    resolve_response_completion_policy,
)


def _snapshot(
    *,
    finish_reason: str | None = "length",
    content_state: str = "empty",
    reasoning_state: str = "non_empty",
    tool_call_count: int = 0,
    usage_state: str = "valid",
) -> ResponseBoundarySnapshot:
    return ResponseBoundarySnapshot(
        finish_reason=finish_reason,
        content_state=content_state,
        reasoning_content_state=reasoning_state,
        tool_call_count=tool_call_count,
        usage_state=usage_state,
    )


def _context(
    *,
    phase: str = "agent_initial",
    response_contract: bool = False,
    tools: bool = False,
    tool_side_effects: bool = False,
    timeout_s: float = 90.0,
    token_budget: int = 8192,
) -> ResponseRequestContext:
    return ResponseRequestContext(
        phase=phase,
        has_response_contract=response_contract,
        has_tools=tools,
        has_tool_side_effects=tool_side_effects,
        remaining_timeout_s=timeout_s,
        remaining_token_budget=token_budget,
    )


def test_registered_flash_policy_is_immutable_and_exactly_bound():
    policy = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1

    assert policy.mode is ResponseCompletionMode.STRICT
    assert policy.policy_id == "glm-5.3-flash-response-completion-v1"
    assert policy.version == "1.0.0"
    assert policy.provider_id == "zhipu"
    assert policy.model == "glm-5.3-flash"
    assert policy.runtime_profile_id == "glm-5.3-flash-runtime-v1"
    assert policy.runtime_profile_version == "1.0.0"
    assert policy.max_output_tokens == 2048
    assert policy.max_additional_calls == 0

    with pytest.raises(FrozenInstanceError):
        policy.max_output_tokens = 8192  # type: ignore[misc]


def test_policy_resolution_requires_provider_model_and_runtime_identity():
    assert resolve_response_completion_policy(
        provider_id="zhipu",
        model="glm-5.3-flash",
        runtime_profile_id="glm-5.3-flash-runtime-v1",
        runtime_profile_version="1.0.0",
    ) == GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1

    assert resolve_response_completion_policy(
        provider_id="zhipu",
        model="glm-5.2",
        runtime_profile_id="glm-5.3-flash-runtime-v1",
        runtime_profile_version="1.0.0",
    ) is None
    assert resolve_response_completion_policy(
        provider_id="deepseek",
        model="glm-5.3-flash",
        runtime_profile_id="glm-5.3-flash-runtime-v1",
        runtime_profile_version="1.0.0",
    ) is None
    assert resolve_response_completion_policy(
        provider_id="zhipu",
        model="glm-5.3-flash",
        runtime_profile_id="glm-5.3-flash-runtime-v1",
        runtime_profile_version="9.9.9",
    ) is None


def test_candidate_policy_is_not_registered_or_implicitly_activated():
    candidate = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1

    assert candidate.mode is ResponseCompletionMode.CANDIDATE_FRESH_RECOVERY
    assert candidate.activation_state == "candidate"
    assert candidate.max_output_tokens == 8192
    assert candidate.max_additional_calls == 1
    assert resolve_response_completion_policy(
        provider_id=candidate.provider_id,
        model=candidate.model,
        runtime_profile_id=candidate.runtime_profile_id,
        runtime_profile_version=candidate.runtime_profile_version,
    ) is None
    with pytest.raises(ValueError, match="registered"):
        require_registered_response_completion_policy(candidate)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(None, 2048), (1, 1), (4096, 2048)],
)
def test_policy_clamps_output_without_allowing_a_caller_to_raise_the_cap(
    requested: int | None,
    expected: int,
):
    assert (
        GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.clamp_output_tokens(requested)
        == expected
    )


@pytest.mark.parametrize("requested", [0, -1, True, 1.5, "2048"])
def test_policy_rejects_malformed_output_budget(requested):
    with pytest.raises(ValueError):
        GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.clamp_output_tokens(requested)


def test_strict_policy_fails_closed_for_the_observed_reasoning_only_length_case():
    decision = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(
        _snapshot(),
        _context(token_budget=2048),
    )

    assert decision.disposition is ResponseDisposition.FAIL_CLOSED
    assert decision.reason_code == "length_reasoning_only"
    assert decision.error_code == "incomplete_chat_response"
    assert decision.candidate_eligible is False
    assert decision.continuation_allowed is False
    assert decision.max_additional_calls == 0


def test_candidate_policy_only_marks_the_exact_shape_and_still_cannot_execute():
    decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
        _snapshot(),
        _context(),
    )

    assert decision.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE
    assert decision.reason_code == "fresh_recovery_shape_eligible"
    assert decision.error_code == "incomplete_chat_response"
    assert decision.candidate_eligible is True
    assert decision.continuation_allowed is False
    assert decision.max_additional_calls == 0


@pytest.mark.parametrize(
    ("snapshot", "context", "reason"),
    [
        (_snapshot(content_state="non_empty"), _context(), "length_partial_content"),
        (_snapshot(reasoning_state="empty"), _context(), "length_without_reasoning"),
        (_snapshot(tool_call_count=1), _context(), "length_with_tool_calls"),
        (_snapshot(), _context(phase="agent_after_tool"), "recovery_phase_not_allowed"),
        (_snapshot(), _context(response_contract=True), "recovery_response_contract_present"),
        (_snapshot(), _context(tools=True), "recovery_tools_present"),
        (_snapshot(), _context(tool_side_effects=True), "recovery_tool_side_effects_present"),
        (_snapshot(), _context(timeout_s=29.9), "recovery_timeout_insufficient"),
        (_snapshot(), _context(token_budget=8191), "recovery_token_budget_insufficient"),
        (_snapshot(usage_state="invalid"), _context(), "usage_unavailable"),
    ],
)
def test_candidate_policy_rejects_every_non_whitelisted_recovery_shape(
    snapshot: ResponseBoundarySnapshot,
    context: ResponseRequestContext,
    reason: str,
):
    decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(snapshot, context)

    assert decision.disposition is ResponseDisposition.FAIL_CLOSED
    assert decision.reason_code == reason
    assert decision.error_code in {
        "incomplete_chat_response",
        "provider_usage_unavailable",
    }
    assert decision.candidate_eligible is False
    assert decision.continuation_allowed is False
    assert decision.max_additional_calls == 0


def test_stop_with_text_is_a_complete_deliverable_and_never_a_recovery():
    decision = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(
        _snapshot(
            finish_reason="stop",
            content_state="non_empty",
            reasoning_state="non_empty",
        ),
        _context(),
    )

    assert decision.disposition is ResponseDisposition.COMPLETE_TEXT
    assert decision.reason_code == "complete_text"
    assert decision.error_code is None
    assert decision.candidate_eligible is False
    assert decision.continuation_allowed is False


def test_tool_calls_remain_a_normal_tool_round_not_a_hidden_retry():
    decision = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(
        _snapshot(
            finish_reason="tool_calls",
            content_state="empty",
            reasoning_state="non_empty",
            tool_call_count=1,
        ),
        _context(tools=True),
    )

    assert decision.disposition is ResponseDisposition.TOOL_CALLS_READY
    assert decision.reason_code == "tool_calls_ready"
    assert decision.error_code is None
    assert decision.continuation_allowed is False


@pytest.mark.parametrize(
    ("finish_reason", "error_code", "reason"),
    [
        ("content_filter", "incomplete_chat_response", "content_filter"),
        (
            "insufficient_system_resource",
            "incomplete_chat_response",
            "insufficient_system_resource",
        ),
        (None, "invalid_chat_response", "missing_finish_reason"),
        ("vendor_unknown", "invalid_finish_reason", "unknown_finish_reason"),
    ],
)
def test_non_deliverable_or_unknown_finish_reasons_fail_closed(
    finish_reason: str | None,
    error_code: str,
    reason: str,
):
    decision = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(
        _snapshot(finish_reason=finish_reason),
        _context(),
    )

    assert decision.disposition is ResponseDisposition.FAIL_CLOSED
    assert decision.error_code == error_code
    assert decision.reason_code == reason
    assert decision.continuation_allowed is False


@pytest.mark.parametrize(
    ("snapshot", "error_code", "reason"),
    [
        (
            _snapshot(finish_reason="stop", content_state="empty", reasoning_state="non_empty"),
            "invalid_chat_response",
            "stop_without_text",
        ),
        (
            _snapshot(finish_reason="stop", content_state="non_empty", tool_call_count=1),
            "invalid_tool_call_response",
            "stop_with_tool_calls",
        ),
        (
            _snapshot(finish_reason="tool_calls", tool_call_count=0),
            "invalid_tool_call_response",
            "tool_finish_without_calls",
        ),
    ],
)
def test_finish_reason_and_payload_shape_must_agree(
    snapshot: ResponseBoundarySnapshot,
    error_code: str,
    reason: str,
):
    decision = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(
        snapshot,
        _context(),
    )

    assert decision.disposition is ResponseDisposition.FAIL_CLOSED
    assert decision.error_code == error_code
    assert decision.reason_code == reason


@pytest.mark.parametrize(
    "kwargs",
    [
        {"finish_reason": "bad reason"},
        {"content_state": "raw text"},
        {"reasoning_state": "raw reasoning"},
        {"tool_call_count": -1},
        {"usage_state": "raw usage"},
    ],
)
def test_boundary_snapshot_accepts_only_sanitized_states(kwargs):
    with pytest.raises(ValueError):
        _snapshot(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"phase": "user_supplied"},
        {"timeout_s": -1},
        {"token_budget": -1},
        {"tools": 1},
    ],
)
def test_request_context_is_a_trusted_bounded_shape(kwargs):
    with pytest.raises(ValueError):
        _context(**kwargs)

