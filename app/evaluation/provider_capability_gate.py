"""Strict, sanitized evidence contracts for real Provider admission probes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
CodeShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]

MANDATORY_CASE_IDS = (
    "P1_text_baseline",
    "P2_structured_pass",
    "P3_structured_issue",
    "P4_tool_request",
    "P5_tool_final",
)


class CapabilityProbeCaseResult(BaseModel):
    """One public, sanitized capability observation without raw model text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    capability: Literal["text_chat", "structured_output", "tool_calling"]
    status: Literal["passed", "failed", "skipped"]
    error_code: NonBlankText | None = None
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    finish_reason: NonBlankText | None = None
    resolved_model: NonBlankText | None = None
    request_id_sha256: Sha256Text | None = None
    tool_call_count: int = Field(ge=0)
    repair_count: int = Field(ge=0)
    output_sha256: Sha256Text | None = None

    @model_validator(mode="after")
    def validate_status_evidence(self) -> "CapabilityProbeCaseResult":
        if self.status == "passed":
            if self.error_code is not None:
                raise ValueError("passed capability case cannot have an error code.")
            if self.output_sha256 is None:
                raise ValueError("passed capability case requires an output digest.")
        else:
            if self.error_code is None:
                raise ValueError("failed or skipped capability case needs an error code.")
            if self.output_sha256 is not None:
                raise ValueError("non-passed capability case cannot expose output digest.")
        if self.status == "skipped" and any(
            (
                self.latency_ms,
                self.input_tokens,
                self.output_tokens,
                self.tool_call_count,
                self.repair_count,
            )
        ):
            raise ValueError("skipped capability case cannot contain call metrics.")
        return self


class CapabilityProbeReport(BaseModel):
    """Versioned public evidence for exactly one P1-P5 microprobe run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    provider_id: NonBlankText
    requested_model: NonBlankText
    code_sha: CodeShaText
    documentation_snapshot_date: Annotated[
        str,
        StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ]
    run_timestamp_utc: datetime
    max_calls: int = Field(ge=1, le=20)
    calls_used: int = Field(ge=0)
    admitted: bool
    cases: tuple[CapabilityProbeCaseResult, ...]
    estimated_cost: float | None = Field(default=None, ge=0)
    cost_note: NonBlankText = "No verified unit-price snapshot was applied."

    @model_validator(mode="after")
    def validate_report_consistency(self) -> "CapabilityProbeReport":
        if self.calls_used > self.max_calls:
            raise ValueError("calls_used cannot exceed max_calls.")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("capability case ids must be unique.")
        executed_count = sum(case.status != "skipped" for case in self.cases)
        if self.calls_used != executed_count:
            raise ValueError("calls_used must equal the number of executed cases.")
        by_id = {case.case_id: case for case in self.cases}
        expected_admission = all(
            by_id.get(case_id) is not None
            and by_id[case_id].status == "passed"
            for case_id in MANDATORY_CASE_IDS
        )
        if self.admitted is not expected_admission:
            raise ValueError("admitted must match all mandatory case results.")
        return self


class ExternalCallBudgetExceeded(RuntimeError):
    """Raised before an external call would exceed the approved hard limit."""


ReturnT = TypeVar("ReturnT")


class ExternalCallBudget:
    """Count attempted external calls and reject before crossing the limit."""

    def __init__(self, *, max_calls: int) -> None:
        if isinstance(max_calls, bool) or not isinstance(max_calls, int):
            raise ValueError("max_calls must be an integer.")
        if not 1 <= max_calls <= 20:
            raise ValueError("max_calls must be between 1 and 20.")
        self.max_calls = max_calls
        self._calls_used = 0

    @property
    def calls_used(self) -> int:
        return self._calls_used

    def run(
        self,
        operation: Callable[..., ReturnT],
        *args: Any,
        **kwargs: Any,
    ) -> ReturnT:
        if self._calls_used >= self.max_calls:
            raise ExternalCallBudgetExceeded(
                "real Provider call budget has been exhausted."
            )
        self._calls_used += 1
        return operation(*args, **kwargs)
