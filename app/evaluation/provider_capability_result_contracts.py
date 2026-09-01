"""Strict readers for immutable, body-free historical capability evidence.

The provider-capability directory contains a small number of diagnostic
results written before the current GLM-5.3 Flash contracts settled.  Those
files are retained as audit evidence and must remain byte-for-byte readable,
but they must not make newer contracts more permissive.  The models in this
module are therefore deliberately separate from the current probe models and
bind each historical shape to its producer identity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.evaluation.glm53_flash_capability_matrix import MatrixSourceIdentity


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


SafeSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")]
SafeModel = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
]
# ---------------------------------------------------------------------------
# RQ-181 response-completion diagnostic (the producer lived on a side branch)

class ResponseDiagnosticRequest(_FrozenModel):
    ordinal: int = Field(ge=1, le=4)
    phase: Literal[
        "agent_initial",
        "agent_after_tool",
        "evaluation",
        "evaluation_repair",
        "revision",
        "unknown",
    ]
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[Literal["system", "user", "assistant", "tool"], ...]
    tool_definition_count: int = Field(ge=0, le=32)
    tool_choice: Literal["auto", "none", "required"]
    has_response_contract: bool
    requested_max_tokens: int | None = Field(default=None, ge=1, le=8192)
    effective_timeout_s: float = Field(gt=0, le=300)
    temperature: float = Field(ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)


class ResponseDiagnosticObservation(_FrozenModel):
    request: ResponseDiagnosticRequest
    response_received: bool
    sdk_latency_ms: int = Field(ge=0)
    finish_reason: Literal[
        "stop",
        "tool_calls",
        "length",
        "content_filter",
        "insufficient_system_resource",
        "missing",
        "unknown",
    ] | None = None
    content_state: Literal[
        "not_observed",
        "missing",
        "null",
        "empty",
        "non_empty",
        "non_string",
    ] = "not_observed"
    reasoning_content_state: Literal[
        "not_observed",
        "missing",
        "null",
        "empty",
        "non_empty",
        "non_string",
    ] = "not_observed"
    tool_calls_state: Literal[
        "not_observed",
        "missing",
        "null",
        "empty",
        "non_empty",
        "non_string",
    ] = "not_observed"
    tool_call_count: int = Field(ge=0, le=32)
    resolved_model: SafeModel | None = None
    usage_state: Literal["not_observed", "missing", "null", "valid", "invalid"] = (
        "not_observed"
    )
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    request_id_sha256: SafeSha | None = None
    sdk_error_class: Literal[
        "authentication",
        "permission",
        "rate_limit",
        "timeout",
        "connection",
        "http_status",
        "sdk_error",
    ] | None = None
    adapter_error_code: SafeCode | None = None
    adapter_error_stage: Literal[
        "transport",
        "response_shape",
        "content",
        "tool_calls",
        "reasoning",
        "finish_reason",
        "usage",
        "chat_response",
        "unknown",
    ] | None = None
    normalized: bool
    settled: bool

    @model_validator(mode="after")
    def validate_observation(self) -> "ResponseDiagnosticObservation":
        if self.settled and not self.normalized:
            raise ValueError("a settled response must be normalized")
        if self.normalized and not self.response_received:
            raise ValueError("a normalized response must have been received")
        if self.usage_state == "valid":
            if self.response_received is not True:
                raise ValueError("valid usage requires a received response")
        elif any((self.input_tokens, self.output_tokens, self.cached_input_tokens)):
            raise ValueError("unavailable usage cannot carry token counts")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input tokens")
        if not self.response_received and any(
            value is not None
            for value in (
                self.finish_reason,
                self.resolved_model,
                self.request_id_sha256,
            )
        ):
            raise ValueError("an unreceived response cannot carry response metadata")
        return self


class GLM53FlashResponseDiagnostic(_FrozenModel):
    """The exact RQ-181 schema, kept separate from current runtime contracts."""

    schema_version: Literal["1.0"]
    experiment_id: Literal[
        "b1e4a1fc51bed23803b5f94acbd2a652330d5847061dbb7b60022c88da4ff1b9"
    ]
    run_timestamp_utc: datetime
    provider_id: Literal["zhipu"]
    requested_model: Literal["glm-5.3-flash"]
    base_url: Literal["https://open.bigmodel.cn/api/paas/v4/"]
    implementation_sha: Literal["7cb66d218389c0e7d7aa7b2b1969a4678402f857"]
    diagnostic_code_sha: Literal["447c11e85b6da53fe678d68e25d96b589c0d6ca2"]
    runtime_profile_id: Literal["glm-5.3-flash-runtime-v1"]
    runtime_profile_version: Literal["1.0.0"]
    case_id: Literal["flash_gate_baseline_01"]
    max_provider_calls: Literal[4]
    max_case_tokens: Literal[4000]
    explicit_real_call_confirmed: Literal[True]
    provider_calls_attempted: int = Field(ge=0, le=4)
    normalized_response_count: int = Field(ge=0, le=4)
    settled_response_count: int = Field(ge=0, le=4)
    first_failure_ordinal: int | None = Field(default=None, ge=1, le=4)
    agent_status: SafeCode | None = None
    agent_stop_reason: SafeCode | None = None
    safe_provider_error_code: SafeCode | None = None
    terminal_status: SafeCode | None = None
    terminal_reason: SafeCode | None = None
    execution_exception: SafeCode | None = None
    observations: tuple[ResponseDiagnosticObservation, ...] = Field(
        min_length=1, max_length=4
    )

    @model_validator(mode="after")
    def validate_report(self) -> "GLM53FlashResponseDiagnostic":
        if self.provider_calls_attempted != len(self.observations):
            raise ValueError("provider call count must match observations")
        if self.normalized_response_count != sum(
            row.normalized for row in self.observations
        ):
            raise ValueError("normalized count must match observations")
        if self.settled_response_count != sum(
            row.settled for row in self.observations
        ):
            raise ValueError("settled count must match observations")
        failure_ordinals = tuple(
            row.request.ordinal
            for row in self.observations
            if row.sdk_error_class is not None or row.adapter_error_code is not None
        )
        expected_failure = failure_ordinals[0] if failure_ordinals else None
        if self.first_failure_ordinal != expected_failure:
            raise ValueError("first failure ordinal must match observations")
        if self.cached_input_total > self.input_total:
            raise ValueError("cached input cannot exceed input")
        return self

    @property
    def input_total(self) -> int:
        return sum(row.input_tokens for row in self.observations)

    @property
    def cached_input_total(self) -> int:
        return sum(row.cached_input_tokens for row in self.observations)


# ---------------------------------------------------------------------------
# RQ-188 intermediate transport/generation split reports.

LegacyFinishReason = Literal[
    "stop",
    "tool_calls",
    "length",
    "content_filter",
    "insufficient_system_resource",
    "missing",
    "unknown",
]
LegacyFieldState = Literal[
    "not_observed",
    "missing",
    "null",
    "empty",
    "non_empty",
    "non_string",
]
LegacyChunkShape = Literal[
    "not_observed",
    "choices_empty",
    "delta_content",
    "delta_reasoning",
    "delta_other",
    "malformed",
]
LegacyVariant = Literal[
    "minimal_transport_control",
    "frozen_short_nonstream",
    "frozen_stream_first_chunk",
]


class LegacySplitRequestSummary(_FrozenModel):
    ordinal: int = Field(ge=1, le=3)
    variant: LegacyVariant
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[Literal["system", "user", "assistant", "tool"], ...]
    message_shape_sha256: SafeSha
    max_tokens: int = Field(ge=1, le=8192)
    timeout_s: float = Field(gt=0, le=90)
    stream: bool
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    thinking_type: Literal["disabled", "enabled"]
    reasoning_effort: Literal["none", "low", "max"]

    @model_validator(mode="after")
    def validate_reasoning_shape(self) -> "LegacySplitRequestSummary":
        if self.thinking_type == "disabled" and self.reasoning_effort != "none":
            raise ValueError("disabled thinking requires the historical none effort")
        if self.thinking_type == "enabled" and self.reasoning_effort == "none":
            raise ValueError("enabled thinking requires an explicit effort")
        return self


class LegacySplitObservation(_FrozenModel):
    ordinal: int = Field(ge=1, le=3)
    variant: LegacyVariant
    status: Literal["observed", "failed", "skipped"]
    request: LegacySplitRequestSummary
    external_calls: Literal[0, 1]
    skip_reason: SafeCode | None = None
    response_received: bool = False
    stream_opened: bool = False
    first_chunk_observed: bool = False
    generation_observed: bool = False
    marker_match: bool | None = None
    create_latency_ms: int = Field(ge=0)
    first_chunk_latency_ms: int | None = Field(default=None, ge=0)
    sdk_latency_ms: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    completion_state: Literal["complete", "partial", "not_observed"] = "not_observed"
    finish_reason: LegacyFinishReason | None = None
    content_state: LegacyFieldState = "not_observed"
    reasoning_state: LegacyFieldState = "not_observed"
    usage_state: Literal["valid", "missing", "invalid"] = "missing"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    chunk_count: int = Field(default=0, ge=0, le=16_384)
    first_chunk_shape: LegacyChunkShape = "not_observed"
    resolved_model: SafeModel | None = None
    request_id_sha256: SafeSha | None = None
    sdk_error_class: Literal[
        "authentication",
        "permission",
        "rate_limit",
        "timeout",
        "connection",
        "http_status",
        "sdk_error",
    ] | None = None
    error_code: SafeCode | None = None
    error_stage: SafeCode | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "LegacySplitObservation":
        if self.external_calls == 0 and self.status != "skipped":
            raise ValueError("zero-call observations must be skipped")
        if self.status == "skipped":
            if self.skip_reason is None or self.external_calls != 0:
                raise ValueError("skipped observations need a reason and zero calls")
            if any(
                (
                    self.response_received,
                    self.stream_opened,
                    self.first_chunk_observed,
                    self.generation_observed,
                )
            ):
                raise ValueError("skipped observations cannot claim execution")
        elif self.external_calls != 1 or self.skip_reason is not None:
            raise ValueError("executed observations need exactly one call")
        if self.first_chunk_observed:
            if not self.request.stream or not self.stream_opened:
                raise ValueError("first chunk requires an opened stream")
            if self.first_chunk_latency_ms is None:
                raise ValueError("first chunk needs a latency")
        if self.request.stream and self.generation_observed and not self.first_chunk_observed:
            raise ValueError("stream generation requires a first chunk")
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("valid usage needs input and output counts")
            if self.cached_input_tokens is None:
                raise ValueError("valid usage needs cache count")
            if self.cached_input_tokens > self.input_tokens:
                raise ValueError("cached input cannot exceed input")
        elif any(
            value is not None
            for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens)
        ):
            raise ValueError("unavailable usage cannot carry token counts")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed observations need an error code")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("only failed observations may carry an error code")
        if self.status == "observed" and not (
            self.response_received or self.first_chunk_observed
        ):
            raise ValueError("observed observations need a response or first chunk")
        if self.first_chunk_shape != "not_observed" and not self.first_chunk_observed:
            raise ValueError("chunk shape requires a first chunk")
        return self


class LegacySplitBudget(_FrozenModel):
    max_real_calls: Literal[3]
    max_observed_tokens: Literal[64_000]
    max_output_tokens_per_request: Literal[8192]
    sdk_max_retries: Literal[0]


class LegacySplitResources(_FrozenModel):
    calls_used: int = Field(ge=0, le=3)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=64_000)
    latency_ms: int = Field(ge=0)
    within_token_budget: bool

    @model_validator(mode="after")
    def validate_resources(self) -> "LegacySplitResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total mismatch")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.within_token_budget != (self.total_tokens <= 64_000):
            raise ValueError("token budget status mismatch")
        return self


class LegacySplitVerdictsOriginal(_FrozenModel):
    transport_reachable: Literal[False]
    frozen_short_generation_observed: Literal[True]
    stream_first_chunk_observed: Literal[True]
    long_window_baseline_observed: Literal[False]
    interpretation_code: Literal["stream_first_byte_only_control_unresolved"]
    candidate_registered: Literal[False]
    production_admitted: Literal[False]


class LegacySplitVerdictsCorrected(_FrozenModel):
    minimal_control_observed: Literal[False]
    transport_reachable: Literal[True]
    frozen_short_generation_observed: Literal[True]
    stream_first_chunk_observed: Literal[True]
    long_window_baseline_observed: Literal[False]
    interpretation_code: Literal["endpoint_reachable_control_variant_rejected"]
    candidate_registered: Literal[False]
    production_admitted: Literal[False]


class _LegacySplitReportCommon(_FrozenModel):
    schema_version: Literal["1.0"]
    experiment_name: Literal["g53-8-transport-generation-split-v1"]
    evidence_class: Literal["dirty_worktree_real_api_observation"]
    provider_id: Literal["zhipu"]
    requested_model: Literal["glm-5.3-flash"]
    base_url: Literal["https://open.bigmodel.cn/api/paas/v4/"]
    implementation_sha: Literal["eca01ce1393286dbbe83992c2985f600ea2b30b0"]
    diagnostic_code_sha: GitSha
    case_id: Literal["flash_gate_baseline_01"]
    baseline_experiment_id: Literal[
        "a3895dd12c506f493efcd9c7842e8ab6e3ef1a8f099204ca07779a8e4c316245"
    ]
    baseline_result_sha256: Literal[
        "3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263"
    ]
    input_plan_sha256: SafeSha
    prompt_context_snapshot_sha256: SafeSha
    observation_scope: Literal["vendor_raw_transport_only"]
    thinking_profile_id: Literal["glm-5.3-flash-enabled-max-replay"]
    explicit_real_call_confirmed: Literal[True]
    source_identity: MatrixSourceIdentity
    source_identity_after: MatrixSourceIdentity
    source_identity_stable: bool
    budget: LegacySplitBudget
    resources: LegacySplitResources
    calls_attempted: Literal[3]
    cost_status: Literal["unknown"]
    run_timestamp_utc: datetime
    observations: tuple[LegacySplitObservation, ...] = Field(min_length=3, max_length=3)
    unsupported_boundaries: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_common(self) -> "_LegacySplitReportCommon":
        expected = (
            "minimal_transport_control",
            "frozen_short_nonstream",
            "frozen_stream_first_chunk",
        )
        if tuple(row.variant for row in self.observations) != expected:
            raise ValueError("probe variants must use canonical order")
        if self.calls_attempted != sum(row.external_calls for row in self.observations):
            raise ValueError("call count mismatch")
        if self.resources.calls_used != self.calls_attempted:
            raise ValueError("resource call count mismatch")
        if self.resources.input_tokens != sum(row.input_tokens or 0 for row in self.observations):
            raise ValueError("resource input mismatch")
        if self.resources.output_tokens != sum(
            row.output_tokens or 0 for row in self.observations
        ):
            raise ValueError("resource output mismatch")
        if self.resources.cached_input_tokens != sum(
            row.cached_input_tokens or 0 for row in self.observations
        ):
            raise ValueError("resource cache mismatch")
        if self.resources.latency_ms != sum(row.elapsed_ms for row in self.observations):
            raise ValueError("resource latency mismatch")
        identities_match = self.source_identity == self.source_identity_after
        if self.source_identity_stable != identities_match:
            raise ValueError("source identity stability flag must match identities")
        return self


class LegacyTransportGenerationSplitReport(
    _LegacySplitReportCommon
):
    """RQ-188's first control-shape result (producer SHA d7b535e)."""

    experiment_id: Literal[
        "fab7b4f668e2fa992fab206cc9f395b7431d872090e2700c04b850ba378ea41f"
    ]
    diagnostic_code_sha: Literal["d7b535e0c8a02c4b9d55b1ec2b1bdc4f9a0d7d42"]
    verdicts: LegacySplitVerdictsOriginal

    @model_validator(mode="after")
    def validate_source_identity(self) -> "LegacyTransportGenerationSplitReport":
        if self.source_identity.head_sha != "d7b535e4dbfcab758c1bee105087add2c2b4146d":
            raise ValueError("historical source identity drifted")
        return self


class LegacyTransportGenerationSplitReportCorrected(
    _LegacySplitReportCommon
):
    """RQ-188's corrected control result (producer SHA 20331a5)."""

    experiment_id: Literal[
        "791eb51955267cd6da7dc82711863ab4b8bfcaf0e421c932fc71756e4321843b"
    ]
    diagnostic_code_sha: Literal["20331a5d8e040e111b87d934b4a6d5a2b1e4c530"]
    verdicts: LegacySplitVerdictsCorrected

    @model_validator(mode="after")
    def validate_source_identity(
        self,
    ) -> "LegacyTransportGenerationSplitReportCorrected":
        if self.source_identity.head_sha != "20331a580462171331fbae84acf0c8b1ba2e4430":
            raise ValueError("historical source identity drifted")
        return self
