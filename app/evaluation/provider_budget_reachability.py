"""No-I/O budget reachability evidence for real domain Provider gates.

This module deliberately separates exact Provider Usage evidence from a local
tokenizer-free request-length projection.  It has no Provider construction,
credential or network surface.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.agent.context import ContextSizer, DeterministicContextSizer
from app.providers.models import ChatRequest, MessageRole

from .provider_adoption import (
    ExperimentFailureCode,
    deepseek_experiment_policy,
)
from .provider_domain_readmission import FreshProviderDomainExperimentRecord


Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

V2_RESULT_SHA256 = (
    "877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a"
)
_V2_FIRST_CASE_ID = "adoption_v2_form_baseline"
_REQUIRED_STAGES = (
    "agent_initial",
    "agent_after_tool",
    "evaluation",
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RequestEnvelopeMeasurement(_FrozenModel):
    """Body-free local measurement of one production ChatRequest."""

    stage: Literal["agent_initial", "agent_after_tool", "evaluation"]
    message_count: int = Field(gt=0)
    message_roles: tuple[Literal["system", "user", "assistant", "tool"], ...]
    local_context_units: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_envelope(self) -> "RequestEnvelopeMeasurement":
        if len(self.message_roles) != self.message_count:
            raise ValueError("message_count must match the body-free role list")
        return self


class LengthProjectionStage(_FrozenModel):
    stage: Literal["agent_initial", "agent_after_tool", "evaluation"]
    local_context_units: int = Field(gt=0)
    projected_input_tokens: int = Field(gt=0)


class LengthCalibratedProjection(_FrozenModel):
    """A risk projection, explicitly not a Provider tokenizer measurement."""

    method: Literal["length_calibrated_not_provider_tokenizer"]
    calibration_stage: Literal["agent_initial"]
    calibration_local_context_units: int = Field(gt=0)
    calibration_actual_input_tokens: int = Field(gt=0)
    stages: tuple[LengthProjectionStage, ...]
    projected_input_tokens_total: int = Field(gt=0)
    known_output_tokens: int = Field(ge=0)
    projected_tokens_before_future_outputs: int = Field(gt=0)
    exact_provider_token_count: Literal[False] = False

    @model_validator(mode="after")
    def validate_projection(self) -> "LengthCalibratedProjection":
        if tuple(row.stage for row in self.stages) != _REQUIRED_STAGES:
            raise ValueError("projection must follow the required production stages")
        if self.projected_input_tokens_total != sum(
            row.projected_input_tokens for row in self.stages
        ):
            raise ValueError("projected input total is inconsistent")
        if self.projected_tokens_before_future_outputs != (
            self.projected_input_tokens_total + self.known_output_tokens
        ):
            raise ValueError("projected observed token total is inconsistent")
        first = self.stages[0]
        if (
            first.local_context_units != self.calibration_local_context_units
            or first.projected_input_tokens
            != self.calibration_actual_input_tokens
        ):
            raise ValueError("first projection stage must be the actual calibration")
        return self


class DeepSeekV2BudgetAdjudication(_FrozenModel):
    """Public-safe exact V2 verdict plus a separately labelled projection."""

    schema_version: Literal["1.0"] = "1.0"
    source_result_sha256: Sha256Text
    source_experiment_id: Sha256Text
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    case_id: Literal["adoption_v2_form_baseline"]
    required_stages: tuple[
        Literal["agent_initial", "agent_after_tool", "evaluation"], ...
    ]
    observed_normalized_response_count: Literal[1]
    observed_input_tokens: int = Field(gt=0)
    observed_output_tokens: int = Field(ge=0)
    observed_total_tokens: int = Field(gt=0)
    case_token_limit: int = Field(gt=0)
    per_request_output_cap: int = Field(gt=0)
    next_call_reserved_total: int = Field(gt=0)
    exact_minimum_case_limit_for_next_call: int = Field(gt=0)
    case_limit_shortfall: int = Field(gt=0)
    next_call_reachable: Literal[False]
    complete_path_reachable: Literal[False]
    complete_path_exact_token_requirement: None = None
    length_projection: LengthCalibratedProjection
    recommended_v3_case_token_limit: None = None
    decision: Literal["new_budget_design_required_before_v3_io"]
    external_provider_calls: Literal[0] = 0

    @model_validator(mode="after")
    def validate_adjudication(self) -> "DeepSeekV2BudgetAdjudication":
        if self.required_stages != _REQUIRED_STAGES:
            raise ValueError("required stages have drifted")
        if self.observed_total_tokens != (
            self.observed_input_tokens + self.observed_output_tokens
        ):
            raise ValueError("observed token total is inconsistent")
        expected_reservation = (
            self.observed_total_tokens + self.per_request_output_cap
        )
        if (
            self.next_call_reserved_total != expected_reservation
            or self.exact_minimum_case_limit_for_next_call
            != expected_reservation
        ):
            raise ValueError("next-call reservation calculation is inconsistent")
        if self.case_limit_shortfall != (
            expected_reservation - self.case_token_limit
        ):
            raise ValueError("case token shortfall is inconsistent")
        if expected_reservation <= self.case_token_limit:
            raise ValueError("V2 evidence does not prove an unreachable next call")
        return self


def measure_request_envelopes(
    requests: tuple[ChatRequest, ...],
    *,
    sizer: ContextSizer | None = None,
) -> tuple[RequestEnvelopeMeasurement, ...]:
    """Measure safe request shape without retaining any message body."""

    if not requests or not all(isinstance(row, ChatRequest) for row in requests):
        raise ValueError("requests must contain ChatRequest values")
    context_sizer = sizer or DeterministicContextSizer()
    rows: list[RequestEnvelopeMeasurement] = []
    for request in requests:
        if request.response_contract is not None:
            stage = "evaluation"
        elif any(message.role is MessageRole.TOOL for message in request.messages):
            stage = "agent_after_tool"
        else:
            stage = "agent_initial"
        rows.append(
            RequestEnvelopeMeasurement(
                stage=stage,
                message_count=len(request.messages),
                message_roles=tuple(
                    message.role.value for message in request.messages
                ),
                local_context_units=context_sizer.estimate_messages(
                    request.messages
                ),
            )
        )
    measured = tuple(rows)
    if tuple(row.stage for row in measured) != _REQUIRED_STAGES:
        raise ValueError("request envelopes do not cover the required domain path")
    return measured


def adjudicate_deepseek_v2_budget_reachability(
    *,
    result_path: str | Path,
    request_envelopes: tuple[RequestEnvelopeMeasurement, ...],
) -> DeepSeekV2BudgetAdjudication:
    """Prove V2 is unreachable without Provider construction or credential I/O."""

    if tuple(row.stage for row in request_envelopes) != _REQUIRED_STAGES:
        raise ValueError("request envelopes do not match the required path")
    raw = Path(result_path).read_bytes()
    result_sha = hashlib.sha256(raw).hexdigest()
    if result_sha != V2_RESULT_SHA256:
        raise ValueError("V2 result SHA-256 does not match immutable evidence")
    record = FreshProviderDomainExperimentRecord.model_validate_json(raw)
    domain = record.domain_result
    policy = deepseek_experiment_policy()

    _validate_v2_result_semantics(record)
    first = domain.cases[0]
    observation = first.observation
    assert observation is not None
    case_resource = next(
        row
        for row in domain.resources.case_resources
        if row.case_id == _V2_FIRST_CASE_ID
    )
    observed_total = observation.input_tokens + observation.output_tokens
    next_reserved_total = observed_total + policy.max_output_tokens_per_request
    projection = _build_length_projection(
        request_envelopes=request_envelopes,
        actual_input_tokens=observation.input_tokens,
        known_output_tokens=observation.output_tokens,
    )

    return DeepSeekV2BudgetAdjudication(
        source_result_sha256=result_sha,
        source_experiment_id=record.experiment_id,
        provider_id=policy.provider_id,
        requested_model=policy.model,
        case_id=_V2_FIRST_CASE_ID,
        required_stages=_REQUIRED_STAGES,
        observed_normalized_response_count=1,
        observed_input_tokens=observation.input_tokens,
        observed_output_tokens=observation.output_tokens,
        observed_total_tokens=observed_total,
        case_token_limit=case_resource.max_observed_tokens,
        per_request_output_cap=policy.max_output_tokens_per_request,
        next_call_reserved_total=next_reserved_total,
        exact_minimum_case_limit_for_next_call=next_reserved_total,
        case_limit_shortfall=(
            next_reserved_total - case_resource.max_observed_tokens
        ),
        next_call_reachable=False,
        complete_path_reachable=False,
        length_projection=projection,
        decision="new_budget_design_required_before_v3_io",
    )


def _validate_v2_result_semantics(
    record: FreshProviderDomainExperimentRecord,
) -> None:
    domain = record.domain_result
    policy = deepseek_experiment_policy()
    first = domain.cases[0] if domain.cases else None
    observation = first.observation if first is not None else None
    case_resources = {
        row.case_id: row for row in domain.resources.case_resources
    }
    first_resource = case_resources.get(_V2_FIRST_CASE_ID)
    if (
        record.admitted
        or not record.held_out_executed
        or domain.preparation.provider_id != policy.provider_id
        or domain.preparation.requested_model != policy.model
        or tuple(row.case_id for row in domain.cases)
        != record.admission.execution_plan.case_ids
        or tuple(row.status for row in domain.cases)
        != ("executed", "skipped", "skipped")
        or domain.domain_calls_used != 1
        or domain.domain_total_tokens != 3440
        or domain.resources.stop_code
        is not ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
        or first is None
        or observation is None
        or first.case_id != _V2_FIRST_CASE_ID
        or observation.normalized_response_count != 1
        or observation.safe_provider_error_code != "token_budget_exhausted"
        or observation.agent_status != "failed"
        or observation.agent_stop_reason != "provider_error"
        or observation.input_tokens != 3241
        or observation.output_tokens != 199
        or first_resource is None
        or first_resource.calls_used != 1
        or first_resource.max_calls != 4
        or first_resource.input_tokens != observation.input_tokens
        or first_resource.output_tokens != observation.output_tokens
        or first_resource.total_tokens != 3440
        or first_resource.max_observed_tokens != 4000
    ):
        raise ValueError("V2 budget evidence semantics have drifted")


def _build_length_projection(
    *,
    request_envelopes: tuple[RequestEnvelopeMeasurement, ...],
    actual_input_tokens: int,
    known_output_tokens: int,
) -> LengthCalibratedProjection:
    first_units = request_envelopes[0].local_context_units
    ratio = Decimal(actual_input_tokens) / Decimal(first_units)
    stages = tuple(
        LengthProjectionStage(
            stage=row.stage,
            local_context_units=row.local_context_units,
            projected_input_tokens=(
                actual_input_tokens
                if index == 0
                else int(
                    (Decimal(row.local_context_units) * ratio).to_integral_value(
                        rounding=ROUND_CEILING
                    )
                )
            ),
        )
        for index, row in enumerate(request_envelopes)
    )
    projected_input_total = sum(row.projected_input_tokens for row in stages)
    return LengthCalibratedProjection(
        method="length_calibrated_not_provider_tokenizer",
        calibration_stage="agent_initial",
        calibration_local_context_units=first_units,
        calibration_actual_input_tokens=actual_input_tokens,
        stages=stages,
        projected_input_tokens_total=projected_input_total,
        known_output_tokens=known_output_tokens,
        projected_tokens_before_future_outputs=(
            projected_input_total + known_output_tokens
        ),
        exact_provider_token_count=False,
    )
