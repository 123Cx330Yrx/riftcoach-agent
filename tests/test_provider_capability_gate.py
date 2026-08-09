from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.evaluation.provider_capability_gate import (
    CapabilityProbeCaseResult,
    CapabilityProbeReport,
    ExternalCallBudget,
    ExternalCallBudgetExceeded,
)


def passed_case(case_id: str) -> CapabilityProbeCaseResult:
    return CapabilityProbeCaseResult(
        case_id=case_id,
        capability="text_chat",
        status="passed",
        error_code=None,
        latency_ms=12,
        input_tokens=3,
        output_tokens=2,
        finish_reason="stop",
        resolved_model="glm-test-resolved",
        request_id_sha256="c" * 64,
        tool_call_count=0,
        repair_count=0,
        output_sha256="a" * 64,
    )


def test_case_result_is_strict_and_rejects_inconsistent_status() -> None:
    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            **passed_case("P1_text_baseline").model_dump(),
            unknown="not-allowed",
        )

    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            case_id="P2_structured_pass",
            capability="structured_output",
            status="failed",
            error_code=None,
            latency_ms=1,
            input_tokens=0,
            output_tokens=0,
            tool_call_count=0,
            repair_count=0,
        )

    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            case_id="P2_structured_pass",
            capability="structured_output",
            status="passed",
            error_code="unexpected",
            latency_ms=-1,
            input_tokens=-1,
            output_tokens=0,
            tool_call_count=0,
            repair_count=0,
            output_sha256="bad",
        )


def test_probe_report_rejects_duplicate_cases_and_wrong_admission() -> None:
    cases = [passed_case(case_id) for case_id in (
        "P1_text_baseline",
        "P2_structured_pass",
        "P3_structured_issue",
        "P4_tool_request",
        "P5_tool_final",
    )]
    report = CapabilityProbeReport(
        provider_id="zhipu",
        requested_model="glm-test",
        code_sha="b" * 40,
        documentation_snapshot_date="2026-08-09",
        run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
        max_calls=5,
        calls_used=5,
        admitted=True,
        cases=cases,
    )
    assert report.admitted is True

    with pytest.raises(ValidationError):
        CapabilityProbeReport(
            provider_id="zhipu",
            requested_model="glm-test",
            code_sha="b" * 40,
            documentation_snapshot_date="2026-08-09",
            run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
            max_calls=5,
            calls_used=5,
            admitted=True,
            cases=[cases[0], cases[0]],
        )

    with pytest.raises(ValidationError):
        CapabilityProbeReport(
            provider_id="zhipu",
            requested_model="glm-test",
            code_sha="b" * 40,
            documentation_snapshot_date="2026-08-09",
            run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
            max_calls=5,
            calls_used=4,
            admitted=True,
            cases=cases[:-1],
        )


def test_external_call_budget_counts_attempts_and_stops_before_sixth() -> None:
    budget = ExternalCallBudget(max_calls=5)
    calls: list[int] = []

    for index in range(5):
        assert budget.run(lambda value: calls.append(value) or value, index) == index

    with pytest.raises(ExternalCallBudgetExceeded):
        budget.run(lambda: calls.append(99))

    assert calls == [0, 1, 2, 3, 4]
    assert budget.calls_used == 5


def test_executed_failure_consumes_budget_but_rejected_call_does_not() -> None:
    budget = ExternalCallBudget(max_calls=1)

    with pytest.raises(RuntimeError, match="upstream"):
        budget.run(lambda: (_ for _ in ()).throw(RuntimeError("upstream")))
    assert budget.calls_used == 1

    with pytest.raises(ExternalCallBudgetExceeded):
        budget.run(lambda: "never")
    assert budget.calls_used == 1
