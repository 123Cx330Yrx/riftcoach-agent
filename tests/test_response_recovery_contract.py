from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
import json

import pytest

from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseDisposition,
    ResponseRequestContext,
)
from app.providers.response_recovery_contract import (
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
    RecoveryAttemptKind,
    RecoveryBudgetExceeded,
    RecoveryNotEligible,
    RecoveryStateError,
    ResponseAttemptOutcome,
    ResponseRecoveryBudget,
    ResponseRecoveryLedger,
    ResponseRecoveryRuntimeProfile,
    build_response_recovery_plan,
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


def _snapshot(
    *,
    finish_reason: str = "length",
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


def _candidate_decision(
    snapshot: ResponseBoundarySnapshot | None = None,
    context: ResponseRequestContext | None = None,
) -> ResponseCompletionDecision:
    return GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
        snapshot or _snapshot(),
        context or _context(),
    )


def _outcome(
    decision: ResponseCompletionDecision,
    snapshot: ResponseBoundarySnapshot,
    *,
    context: ResponseRequestContext | None = None,
    input_tokens: int | None = 120,
    output_tokens: int | None = 8192,
    elapsed_ms: int = 1_000,
) -> ResponseAttemptOutcome:
    return ResponseAttemptOutcome(
        snapshot=snapshot,
        context=context or _context(),
        decision=decision,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        elapsed_ms=elapsed_ms,
    )


def _candidate_plan(**kwargs):
    context = kwargs.pop("context", _context())
    snapshot = kwargs.pop("snapshot", _snapshot())
    return build_response_recovery_plan(
        policy=GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
        snapshot=snapshot,
        context=context,
        **kwargs,
    )


def test_candidate_runtime_is_exactly_bound_and_not_registered():
    profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1

    assert isinstance(profile, ResponseRecoveryRuntimeProfile)
    assert profile.provider_id == "zhipu"
    assert profile.model == "glm-5.3-flash"
    assert profile.profile_id == "glm-5.3-flash-runtime-v2-candidate"
    assert profile.version == "2.0.0"
    assert profile.max_output_tokens == 8192
    assert profile.max_attempts == 2
    assert profile.max_additional_calls == 1
    assert profile.activation_state == "candidate"
    with pytest.raises(FrozenInstanceError):
        profile.max_output_tokens = 2048  # type: ignore[misc]


def test_candidate_plan_is_offline_only_and_has_primary_then_one_recovery_slot():
    plan = _candidate_plan()

    assert plan.execution_allowed is False
    assert plan.activation_state == "candidate"
    assert tuple(spec.kind for spec in plan.attempts) == (
        RecoveryAttemptKind.PRIMARY,
        RecoveryAttemptKind.FRESH_RECOVERY,
    )
    assert tuple(spec.ordinal for spec in plan.attempts) == (1, 2)
    assert all(spec.max_output_tokens == 8192 for spec in plan.attempts)
    assert plan.next_action == "requires_registered_runtime"


def test_non_eligible_first_shape_gets_no_recovery_slot():
    snapshot = _snapshot(content_state="non_empty")
    context = _context()
    plan = _candidate_plan(
        snapshot=snapshot,
        context=context,
    )

    assert plan.execution_allowed is False
    assert tuple(spec.kind for spec in plan.attempts) == (
        RecoveryAttemptKind.PRIMARY,
    )
    assert plan.next_action == "terminal_fail_closed"


def test_plan_requires_exact_candidate_policy_and_profile_identity():
    with pytest.raises(ValueError, match="candidate policy"):
        build_response_recovery_plan(
            policy=GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
            snapshot=_snapshot(),
            context=_context(),
            runtime_profile=ResponseRecoveryRuntimeProfile(
                profile_id="wrong-profile",
                version="2.0.0",
                provider_id="zhipu",
                model="glm-5.3-flash",
                policy_id="glm-5.3-flash-fresh-recovery-candidate-v1",
                policy_version="1.0.0",
                agent_timeout_s=90.0,
                transport_timeout_s=120.0,
                max_output_tokens=8192,
                max_attempts=2,
                max_additional_calls=1,
                activation_state="candidate",
            ),
        )


def test_candidate_runtime_identity_cannot_be_reused_with_changed_limits():
    altered = replace(
        GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
        agent_timeout_s=120.0,
        llm_tool_timeout_s=120.0,
        transport_timeout_s=150.0,
    )

    with pytest.raises(ValueError, match="identity mismatch"):
        _candidate_plan(runtime_profile=altered)


def test_ledger_counts_each_reserved_attempt_and_observed_resources():
    plan = _candidate_plan()
    ledger = ResponseRecoveryLedger(plan)
    first = ledger.reserve_next()
    assert first.spec.kind is RecoveryAttemptKind.PRIMARY

    first_snapshot = _snapshot()
    first_record = ledger.settle(
        first,
        _outcome(
            _candidate_decision(first_snapshot),
            first_snapshot,
            input_tokens=2220,
            output_tokens=2048,
            elapsed_ms=2500,
        ),
    )
    second = ledger.reserve_next()
    assert second.spec.kind is RecoveryAttemptKind.FRESH_RECOVERY
    second_snapshot = _snapshot(
        finish_reason="stop",
        content_state="non_empty",
        reasoning_state="non_empty",
    )
    second_record = ledger.settle(
        second,
        _outcome(
            _candidate_decision(second_snapshot),
            second_snapshot,
            input_tokens=2300,
            output_tokens=500,
            elapsed_ms=1200,
        ),
    )

    snapshot = ledger.snapshot()
    assert first_record.ordinal == 1
    assert second_record.ordinal == 2
    assert snapshot.calls_reserved == 2
    assert snapshot.calls_settled == 2
    assert snapshot.input_tokens_observed == 4520
    assert snapshot.output_tokens_observed == 2548
    assert snapshot.elapsed_ms_observed == 3700
    assert snapshot.terminal_state == "complete_text"


def test_first_non_candidate_outcome_cannot_open_recovery():
    plan = _candidate_plan(
        snapshot=_snapshot(content_state="non_empty"),
        context=_context(),
    )
    ledger = ResponseRecoveryLedger(plan)
    reservation = ledger.reserve_next()
    snapshot = _snapshot(content_state="non_empty")
    ledger.settle(
        reservation,
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=100,
            output_tokens=100,
        ),
    )

    with pytest.raises(RecoveryNotEligible, match="not eligible"):
        ledger.reserve_next()


def test_failed_first_attempt_is_consumed_and_never_retried():
    plan = _candidate_plan(snapshot=_snapshot(usage_state="invalid"))
    ledger = ResponseRecoveryLedger(plan)
    reservation = ledger.reserve_next()
    snapshot = _snapshot(usage_state="invalid")
    decision = _candidate_decision(snapshot)
    ledger.settle(
        reservation,
        _outcome(
            decision,
            snapshot,
            input_tokens=None,
            output_tokens=None,
        ),
    )

    state = ledger.snapshot()
    assert state.calls_reserved == 1
    assert state.unknown_usage_attempts == 1
    assert state.terminal_state == "fail_closed"
    with pytest.raises(RecoveryNotEligible):
        ledger.reserve_next()


def test_second_attempt_is_the_hard_limit_even_if_it_is_candidate_eligible_again():
    plan = _candidate_plan()
    ledger = ResponseRecoveryLedger(plan)
    first = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(first, _outcome(_candidate_decision(snapshot), snapshot))
    second = ledger.reserve_next()
    ledger.settle(second, _outcome(_candidate_decision(snapshot), snapshot))

    assert ledger.snapshot().terminal_state == "fail_closed"
    with pytest.raises(RecoveryBudgetExceeded, match="maximum attempt"):
        ledger.reserve_next()


def test_budget_reservation_uses_underlying_attempts_and_cumulative_output():
    plan = _candidate_plan()
    budget = ResponseRecoveryBudget(
        max_total_input_tokens=32_000,
        max_total_output_tokens=8192,
        max_total_elapsed_ms=120_000,
    )
    ledger = ResponseRecoveryLedger(plan, budget=budget)
    first = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(
        first,
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=100,
            output_tokens=8192,
        ),
    )

    with pytest.raises(RecoveryBudgetExceeded, match="output token budget"):
        ledger.reserve_next()


def test_budget_overrun_is_recorded_after_provider_attempt_and_fails_closed():
    plan = _candidate_plan()
    ledger = ResponseRecoveryLedger(
        plan,
        budget=ResponseRecoveryBudget(
            max_total_input_tokens=100,
            max_total_output_tokens=16_384,
            max_total_elapsed_ms=10,
        ),
    )
    reservation = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(
        reservation,
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=101,
            output_tokens=1,
            elapsed_ms=11,
        ),
    )

    state = ledger.snapshot()
    assert state.calls_settled == 1
    assert state.budget_exceeded is True
    assert state.terminal_state == "fail_closed"


def test_per_attempt_output_cap_is_enforced_even_inside_cumulative_budget():
    ledger = ResponseRecoveryLedger(_candidate_plan())
    reservation = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(
        reservation,
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=100,
            output_tokens=8193,
        ),
    )

    state = ledger.snapshot()
    assert state.output_tokens_observed == 8193
    assert state.budget_exceeded is True
    assert state.terminal_state == "fail_closed"


def test_additional_call_budget_can_disable_recovery_without_changing_plan():
    ledger = ResponseRecoveryLedger(
        _candidate_plan(),
        budget=ResponseRecoveryBudget(
            max_attempts=2,
            max_additional_calls=0,
            max_total_input_tokens=32_000,
            max_total_output_tokens=16_384,
            max_total_elapsed_ms=180_000,
        ),
    )
    reservation = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(
        reservation,
        _outcome(_candidate_decision(snapshot), snapshot),
    )

    with pytest.raises(RecoveryBudgetExceeded, match="additional-call budget"):
        ledger.reserve_next()


def test_budget_override_can_reduce_but_never_increase_candidate_limits():
    with pytest.raises(ValueError, match="increase the planned output"):
        ResponseRecoveryLedger(
            _candidate_plan(),
            budget=ResponseRecoveryBudget(
                max_attempts=2,
                max_additional_calls=1,
                max_total_input_tokens=32_000,
                max_total_output_tokens=16_385,
                max_total_elapsed_ms=180_000,
            ),
        )


def test_ledger_rejects_concurrent_or_duplicate_settlement():
    ledger = ResponseRecoveryLedger(_candidate_plan())
    reservation = ledger.reserve_next()
    with pytest.raises(RecoveryStateError, match="in flight"):
        ledger.reserve_next()

    snapshot = _snapshot()
    outcome = _outcome(_candidate_decision(snapshot), snapshot)
    ledger.settle(reservation, outcome)
    with pytest.raises(RecoveryStateError, match="unknown reservation"):
        ledger.settle(reservation, outcome)


def test_settlement_must_use_the_reserved_attempt_kind_and_body_free_outcome():
    ledger = ResponseRecoveryLedger(_candidate_plan())
    reservation = ledger.reserve_next()
    snapshot = _snapshot()
    outcome = _outcome(_candidate_decision(snapshot), snapshot)
    assert "raw_response" not in asdict(outcome)
    with pytest.raises(TypeError):
        ResponseAttemptOutcome(  # type: ignore[call-arg]
            snapshot=snapshot,
            context=_context(),
            decision=_candidate_decision(snapshot),
            raw_response="secret body",
        )
    ledger.settle(reservation, outcome)


def test_recovery_trace_is_sanitized_and_identity_stable():
    plan = _candidate_plan()
    ledger = ResponseRecoveryLedger(plan)
    first = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(first, _outcome(_candidate_decision(snapshot), snapshot))
    second = ledger.reserve_next()
    final_snapshot = _snapshot(
        finish_reason="stop",
        content_state="non_empty",
        reasoning_state="non_empty",
    )
    ledger.settle(
        second,
        _outcome(_candidate_decision(final_snapshot), final_snapshot),
    )

    trace = ledger.trace()
    payload = trace.as_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert payload["schema_version"] == "1.0"
    assert payload["attempts"][0]["attempt_kind"] == "primary"
    assert payload["attempts"][1]["attempt_kind"] == "fresh_recovery"
    assert payload["attempts"][0]["runtime_profile_id"] == (
        "glm-5.3-flash-runtime-v2-candidate"
    )
    assert "secret body" not in encoded
    assert "raw_response" not in encoded
    assert "prompt" not in payload
    assert "request_id" not in payload
    assert "tool_arguments" not in payload["attempts"][0]
    assert "content" not in payload["attempts"][0]
    assert "reasoning" not in payload["attempts"][0]

    with pytest.raises(ValueError, match="sanitized"):
        replace(trace.attempts[0], content_state="secret body")
    with pytest.raises(ValueError, match="reason_code"):
        replace(trace.attempts[0], reason_code=None)


def test_settlement_recomputes_decision_instead_of_trusting_caller_flags():
    ledger = ResponseRecoveryLedger(_candidate_plan())
    first = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(first, _outcome(_candidate_decision(snapshot), snapshot))
    second = ledger.reserve_next()
    forged = ResponseCompletionDecision(
        disposition=ResponseDisposition.COMPLETE_TEXT,
        reason_code="complete_text",
        error_code=None,
        candidate_eligible=False,
        continuation_allowed=False,
        max_additional_calls=0,
    )

    with pytest.raises(RecoveryStateError, match="does not match policy"):
        ledger.settle(second, _outcome(forged, snapshot))


def test_trace_totals_match_ledger_and_attempt_ordinals_are_contiguous():
    ledger = ResponseRecoveryLedger(_candidate_plan())
    first = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(
        first,
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=12,
            output_tokens=13,
            elapsed_ms=14,
        ),
    )
    second = ledger.reserve_next()
    final_snapshot = _snapshot(
        finish_reason="stop",
        content_state="non_empty",
        reasoning_state="non_empty",
    )
    ledger.settle(
        second,
        _outcome(
            _candidate_decision(final_snapshot),
            final_snapshot,
            input_tokens=15,
            output_tokens=16,
            elapsed_ms=17,
        ),
    )

    trace = ledger.trace()
    assert tuple(row.ordinal for row in trace.attempts) == (1, 2)
    assert trace.calls_attempted == ledger.snapshot().calls_reserved == 2
    assert trace.input_tokens_observed == 27
    assert trace.output_tokens_observed == 29
    assert trace.elapsed_ms_observed == 31


def test_plan_and_trace_reject_forged_decisions_or_terminal_state():
    plan = _candidate_plan()
    forged = ResponseCompletionDecision(
        disposition=ResponseDisposition.COMPLETE_TEXT,
        reason_code="complete_text",
        error_code=None,
        candidate_eligible=False,
        continuation_allowed=False,
        max_additional_calls=0,
    )
    with pytest.raises(ValueError, match="initial decision"):
        replace(plan, initial_decision=forged)
    with pytest.raises(ValueError, match="plan identity"):
        replace(plan, model="other-model")
    with pytest.raises(ValueError, match="plan identity"):
        replace(plan, plan_id="another-plan")

    ledger = ResponseRecoveryLedger(plan)
    reservation = ledger.reserve_next()
    snapshot = _snapshot()
    ledger.settle(reservation, _outcome(_candidate_decision(snapshot), snapshot))
    trace = ledger.trace()
    with pytest.raises(ValueError, match="terminal_state"):
        replace(trace, terminal_state="not-a-state")
    with pytest.raises(ValueError):
        replace(trace, calls_attempted=True)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"profile_id": "unsafe profile"},
        {"version": "2"},
        {"max_attempts": 3},
        {"max_additional_calls": 2},
        {"max_output_tokens": 0},
        {"agent_timeout_s": 0},
    ],
)
def test_candidate_runtime_rejects_unbounded_or_malformed_contracts(kwargs):
    values = dict(
        profile_id="glm-5.3-flash-runtime-v2-candidate",
        version="2.0.0",
        provider_id="zhipu",
        model="glm-5.3-flash",
        policy_id="glm-5.3-flash-fresh-recovery-candidate-v1",
        policy_version="1.0.0",
        agent_timeout_s=90.0,
        transport_timeout_s=120.0,
        max_output_tokens=8192,
        max_attempts=2,
        max_additional_calls=1,
        activation_state="candidate",
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        ResponseRecoveryRuntimeProfile(**values)


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens"),
    [(None, 1), (1, None), (-1, 1), (1, -1)],
)
def test_attempt_outcome_usage_is_consistent_and_non_negative(input_tokens, output_tokens):
    snapshot = _snapshot()
    with pytest.raises(ValueError):
        _outcome(
            _candidate_decision(snapshot),
            snapshot,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
