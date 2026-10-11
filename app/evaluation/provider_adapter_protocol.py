"""Bounded admission slice for a production Provider adapter and AgentLoop."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agent.loop import AgentLoop, AgentRunRequest, AgentRunStatus
from app.evaluation.coach_report import (
    EvaluationResponseModel,
    evaluation_response_contract,
)
from app.model_runtime import (
    CandidateEvaluationRequestPolicy,
    ModelRuntimeProfile,
    require_candidate_evaluation_request_policy,
    require_registered_model_runtime_profile,
)
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    ToolChoiceMode,
)
from app.providers.protocol import LLMProvider
from app.providers.structured import decode_structured_response
from app.tools.models import ToolContext, ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .provider_capability_gate import (
    CodeShaText,
    ExternalCallBudget,
    ExternalCallBudgetExceeded,
    NonBlankText,
    Sha256Text,
)


ADAPTER_PROTOCOL_CASE_IDS = (
    "A1_structured_contract",
    "A2_agent_tool_round_trip",
)
_PROTOCOL_MAX_CALLS = 3
_FINAL_MARKER = "RIFTCOACH_TOOL_ROUNDTRIP_OK"


class AdapterProtocolCaseResult(BaseModel):
    """Sanitized evidence for one production-adapter protocol case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: Literal[
        "A1_structured_contract",
        "A2_agent_tool_round_trip",
    ]
    status: Literal["passed", "failed", "skipped"]
    error_code: NonBlankText | None = None
    external_calls: int = Field(ge=0, le=_PROTOCOL_MAX_CALLS)
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    response_count: int = Field(ge=0, le=2)
    resolved_models: tuple[NonBlankText, ...] = ()
    finish_reasons: tuple[NonBlankText, ...] = ()
    request_id_sha256: tuple[Sha256Text, ...] = ()
    output_sha256: Sha256Text | None = None
    tool_call_count: int = Field(default=0, ge=0)
    tool_execution_count: int = Field(default=0, ge=0, le=1)
    tool_arguments_sha256: Sha256Text | None = None
    tool_result_sha256: Sha256Text | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> "AdapterProtocolCaseResult":
        if self.status == "passed":
            if self.error_code is not None or self.output_sha256 is None:
                raise ValueError("passed case needs an output digest and no error.")
        else:
            if self.error_code is None or self.output_sha256 is not None:
                raise ValueError("non-passed case needs an error and no output digest.")
        if self.status == "skipped" and any(
            (
                self.external_calls,
                self.latency_ms,
                self.input_tokens,
                self.output_tokens,
                self.response_count,
                self.tool_call_count,
                self.tool_execution_count,
            )
        ):
            raise ValueError("skipped case cannot claim execution evidence.")
        if self.status == "skipped" and any(
            (
                self.resolved_models,
                self.finish_reasons,
                self.request_id_sha256,
                self.tool_arguments_sha256,
                self.tool_result_sha256,
            )
        ):
            raise ValueError("skipped case cannot expose response evidence.")
        if len(self.resolved_models) != self.response_count:
            raise ValueError("every response needs one resolved model.")
        if len(self.finish_reasons) > self.response_count:
            raise ValueError("finish reasons cannot outnumber responses.")
        if len(self.request_id_sha256) > self.response_count:
            raise ValueError("request id digests cannot outnumber responses.")
        if self.case_id == "A1_structured_contract" and any(
            (
                self.tool_call_count,
                self.tool_execution_count,
                self.tool_arguments_sha256,
                self.tool_result_sha256,
            )
        ):
            raise ValueError("structured case cannot claim tool evidence.")
        if self.status == "passed" and self.case_id == "A1_structured_contract":
            if self.external_calls != 1 or self.response_count != 1:
                raise ValueError("passed structured case requires exactly one call.")
        if self.status == "passed" and self.case_id == "A2_agent_tool_round_trip":
            if (
                self.external_calls != 2
                or self.response_count != 2
                or self.tool_call_count != 1
                or self.tool_execution_count != 1
                or self.tool_arguments_sha256 is None
                or self.tool_result_sha256 is None
            ):
                raise ValueError(
                    "passed agent case requires one complete two-call tool round trip."
                )
        if self.tool_execution_count > self.tool_call_count:
            raise ValueError("tool executions cannot outnumber tool calls.")
        if self.tool_execution_count == 0 and any(
            (self.tool_arguments_sha256, self.tool_result_sha256)
        ):
            raise ValueError("tool digests require a tool execution.")
        return self


class AdapterProtocolSliceReport(BaseModel):
    """Versioned public evidence for the exact three-call adapter slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    probe_scope: Literal["adapter_protocol"] = "adapter_protocol"
    provider_id: NonBlankText
    requested_model: NonBlankText
    code_sha: CodeShaText
    documentation_snapshot_date: Annotated[
        str,
        StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ] = "2026-08-09"
    run_timestamp_utc: datetime
    max_calls: Literal[3] = _PROTOCOL_MAX_CALLS
    calls_used: int = Field(ge=0, le=_PROTOCOL_MAX_CALLS)
    admitted: bool
    cases: tuple[AdapterProtocolCaseResult, ...]
    estimated_cost: float | None = Field(default=None, ge=0)
    cost_note: NonBlankText = "No verified unit-price snapshot was applied."

    @model_validator(mode="after")
    def validate_report(self) -> "AdapterProtocolSliceReport":
        case_ids = tuple(case.case_id for case in self.cases)
        if case_ids != ADAPTER_PROTOCOL_CASE_IDS:
            raise ValueError("adapter protocol cases must use the canonical order.")
        if self.calls_used != sum(case.external_calls for case in self.cases):
            raise ValueError("calls_used must equal case external calls.")
        expected_admission = (
            self.calls_used == self.max_calls
            and all(case.status == "passed" for case in self.cases)
        )
        if self.admitted is not expected_admission:
            raise ValueError("admitted must match mandatory protocol evidence.")
        return self


class BudgetedProvider:
    """Apply one shared hard call budget before delegating to a Provider."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        budget: ExternalCallBudget,
    ) -> None:
        self._provider = provider
        self._budget = budget
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            return self._budget.run(self._provider.chat, request)
        except ExternalCallBudgetExceeded:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="external_call_budget_exhausted",
            ) from None


class AdapterProtocolSliceRunner:
    """Run the structured request and fixed read-only AgentLoop in order."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        code_sha: str,
        max_calls: int = _PROTOCOL_MAX_CALLS,
        runtime_profile: ModelRuntimeProfile | None = None,
        request_policy: CandidateEvaluationRequestPolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if max_calls != _PROTOCOL_MAX_CALLS:
            raise ValueError("adapter protocol slice requires exactly 3 calls.")
        if runtime_profile is not None and request_policy is not None:
            raise ValueError(
                "runtime_profile and request_policy are mutually exclusive"
            )
        if runtime_profile is not None:
            runtime_profile = require_registered_model_runtime_profile(
                runtime_profile
            )
            if not runtime_profile.matches(
                provider.provider_name,
                provider.model_name,
            ):
                raise ValueError(
                    "runtime_profile does not match the protocol Provider"
                )
        if request_policy is not None:
            request_policy = require_candidate_evaluation_request_policy(
                request_policy,
                provider_id=getattr(provider, "provider_name", None),
                model=getattr(provider, "model_name", None),
            )
        self._budget = ExternalCallBudget(max_calls=max_calls)
        self._provider = BudgetedProvider(provider=provider, budget=self._budget)
        self._code_sha = code_sha
        self._runtime_profile = runtime_profile
        self._request_policy = request_policy
        self._clock = clock
        self._now = now

    @property
    def request_policy(self) -> CandidateEvaluationRequestPolicy | None:
        """Return the explicit candidate policy, if this is an eval run."""

        return self._request_policy

    def run(self) -> AdapterProtocolSliceReport:
        cases: list[AdapterProtocolCaseResult] = []
        structured_case = self._run_structured_case()
        cases.append(structured_case)
        if structured_case.status != "passed":
            cases.append(self._skipped_agent_case())
        else:
            cases.append(self._run_agent_case())
        admitted = (
            self._budget.calls_used == _PROTOCOL_MAX_CALLS
            and all(case.status == "passed" for case in cases)
        )
        return AdapterProtocolSliceReport(
            provider_id=self._provider.provider_name,
            requested_model=self._provider.model_name,
            code_sha=self._code_sha,
            run_timestamp_utc=self._now(),
            calls_used=self._budget.calls_used,
            admitted=admitted,
            cases=tuple(cases),
        )

    def _run_structured_case(self) -> AdapterProtocolCaseResult:
        started = self._clock()
        calls_before = self._budget.calls_used
        response: ChatResponse | None = None
        error_code: str | None = None
        output_digest: str | None = None
        try:
            response = self._provider.chat(
                _structured_request(
                    runtime_profile=self._runtime_profile,
                    request_policy=self._request_policy,
                )
            )
            decoded = decode_structured_response(
                response=response,
                contract=evaluation_response_contract(),
                output_model=EvaluationResponseModel,
            )
            output_digest = _sha256(decoded.value.model_dump(mode="json"))
        except ProviderError as exc:
            error_code = exc.code
        except Exception:
            error_code = "protocol_runner_error"
        status = "passed" if error_code is None else "failed"
        responses = (response,) if response is not None else ()
        return _case_result(
            case_id="A1_structured_contract",
            status=status,
            error_code=error_code,
            external_calls=self._budget.calls_used - calls_before,
            latency_ms=_elapsed_ms(self._clock, started),
            responses=responses,
            output_sha256=output_digest,
        )

    def _run_agent_case(self) -> AdapterProtocolCaseResult:
        started = self._clock()
        calls_before = self._budget.calls_used
        registry = ToolRegistry()
        registry.register(_fixed_knowledge_tool())
        loop = AgentLoop(
            provider=self._provider,
            tool_registry=registry,
            tool_runtime=ToolRuntime(
                registry,
                clock=self._clock,
                call_id_factory=lambda: "adapter-protocol-tool-execution",
            ),
            clock=self._clock,
        )
        try:
            result = loop.run(
                AgentRunRequest(
                    messages=_agent_messages(),
                    allowed_tools=("knowledge.search",),
                    max_iterations=2,
                    max_tool_calls=1,
                    timeout_s=(
                        self._runtime_profile.agent_timeout_s
                        if self._runtime_profile is not None
                        else (
                            self._request_policy.agent_timeout_s
                            if self._request_policy is not None
                            else 30.0
                        )
                    ),
                    temperature=(
                        self._runtime_profile.temperature
                        if self._runtime_profile is not None
                        else (
                            self._request_policy.temperature
                            if self._request_policy is not None
                            else 0.0
                        )
                    ),
                    max_tokens=(
                        self._runtime_profile.max_output_tokens
                        if self._runtime_profile is not None
                        else (
                            self._request_policy.max_output_tokens
                            if self._request_policy is not None
                            else None
                        )
                    ),
                    top_p=(
                        self._runtime_profile.top_p
                        if self._runtime_profile is not None
                        else (
                            self._request_policy.top_p
                            if self._request_policy is not None
                            else None
                        )
                    ),
                    metadata={
                        "probe_scope": "adapter_protocol",
                        **(
                            {
                                "runtime_profile_id": self._runtime_profile.profile_id,
                                "runtime_profile_version": self._runtime_profile.version,
                            }
                            if self._runtime_profile is not None
                            else (
                                self._request_policy.metadata()
                                if self._request_policy is not None
                                else {}
                            )
                        ),
                    },
                )
            )
        except Exception:
            return _case_result(
                case_id="A2_agent_tool_round_trip",
                status="failed",
                error_code="protocol_runner_error",
                external_calls=self._budget.calls_used - calls_before,
                latency_ms=_elapsed_ms(self._clock, started),
                responses=(),
                output_sha256=None,
            )
        error_code = _agent_error_code(result)
        execution = result.tool_executions[0] if result.tool_executions else None
        final_content = (
            result.final_response.content
            if result.final_response is not None
            else None
        )
        return _case_result(
            case_id="A2_agent_tool_round_trip",
            status="passed" if error_code is None else "failed",
            error_code=error_code,
            external_calls=self._budget.calls_used - calls_before,
            latency_ms=_elapsed_ms(self._clock, started),
            responses=result.provider_responses,
            output_sha256=_sha256(final_content) if error_code is None else None,
            tool_call_count=sum(
                len(response.tool_calls) for response in result.provider_responses
            ),
            tool_execution_count=len(result.tool_executions),
            tool_arguments_sha256=(
                _sha256(dict(execution.arguments)) if execution is not None else None
            ),
            tool_result_sha256=(
                _sha256(_safe_tool_result(execution.result))
                if execution is not None
                else None
            ),
        )

    @staticmethod
    def _skipped_agent_case() -> AdapterProtocolCaseResult:
        return AdapterProtocolCaseResult(
            case_id="A2_agent_tool_round_trip",
            status="skipped",
            error_code="structured_contract_failed",
            external_calls=0,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            response_count=0,
        )


def _structured_request(
    *,
    runtime_profile: ModelRuntimeProfile | None = None,
    request_policy: CandidateEvaluationRequestPolicy | None = None,
) -> ChatRequest:
    if runtime_profile is not None and request_policy is not None:
        raise ValueError(
            "runtime_profile and request_policy are mutually exclusive"
        )
    contract = evaluation_response_contract()
    schema_text = json.dumps(
        contract.schema_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return ChatRequest(
        messages=(
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "Return only one JSON object that satisfies this JSON Schema. "
                    f"Do not use Markdown. JSON Schema: {schema_text}"
                ),
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=(
                    "Emit this protocol result: score 100, verdict pass, no "
                    "issues, one passed check, and a non-empty summary."
                ),
            ),
        ),
        tool_choice=ToolChoiceMode.NONE,
        response_contract=contract,
        temperature=(
            runtime_profile.temperature
            if runtime_profile is not None
            else (request_policy.temperature if request_policy is not None else 0.0)
        ),
        max_tokens=(
            runtime_profile.max_output_tokens
            if runtime_profile is not None
            else (
                request_policy.max_output_tokens
                if request_policy is not None
                else 512
            )
        ),
        timeout_s=(
            runtime_profile.llm_tool_timeout_s
            if runtime_profile is not None
            else (
                request_policy.llm_tool_timeout_s
                if request_policy is not None
                else 30.0
            )
        ),
        top_p=(
            runtime_profile.top_p
            if runtime_profile is not None
            else (request_policy.top_p if request_policy is not None else None)
        ),
        metadata={
            "probe_scope": "adapter_protocol",
            **(
                {
                    "runtime_profile_id": runtime_profile.profile_id,
                    "runtime_profile_version": runtime_profile.version,
                }
                if runtime_profile is not None
                else (
                    request_policy.metadata()
                    if request_policy is not None
                    else {}
                )
            ),
        },
    )


def _agent_messages() -> tuple[ChatMessage, ...]:
    return (
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                "This is a protocol admission test. First call knowledge.search "
                "exactly once with top_k=1. After receiving the tool observation, "
                f"reply with exactly {_FINAL_MARKER}. Never call another tool."
            ),
        ),
        ChatMessage(
            role=MessageRole.USER,
            content="Find one coaching note about reducing deaths before 15 minutes.",
        ),
    )


def _fixed_knowledge_tool() -> ToolDefinition:
    def handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        return {
            "provider": "adapter-protocol-fixture",
            "abstained": False,
            "evidence_ids": ["early-death-review-v1"],
            "count": 1,
        }

    return ToolDefinition(
        name="knowledge.search",
        version="1.0.0",
        description=(
            "Read one fixed coaching knowledge fixture for adapter protocol testing."
        ),
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "top_k": {"type": "integer", "const": 1},
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "abstained": {"type": "boolean"},
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "count": {"type": "integer", "const": 1},
            },
            "required": ["provider", "abstained", "evidence_ids", "count"],
            "additionalProperties": False,
        },
        policy=ToolPolicy(),
        idempotent=True,
    )


def _agent_error_code(result) -> str | None:
    if result.status is not AgentRunStatus.COMPLETED:
        return result.error_code or result.stop_reason.value
    if len(result.provider_responses) != 2 or len(result.tool_executions) != 1:
        return "tool_round_trip_incomplete"
    execution = result.tool_executions[0]
    if execution.tool_name != "knowledge.search":
        return "unexpected_tool_name"
    if not execution.result.success:
        return "tool_execution_failed"
    final_content = (
        result.final_response.content
        if result.final_response is not None
        else None
    )
    if final_content != _FINAL_MARKER:
        return "final_marker_mismatch"
    return None


def _case_result(
    *,
    case_id: Literal[
        "A1_structured_contract",
        "A2_agent_tool_round_trip",
    ],
    status: Literal["passed", "failed"],
    error_code: str | None,
    external_calls: int,
    latency_ms: int,
    responses: tuple[ChatResponse, ...],
    output_sha256: str | None,
    tool_call_count: int = 0,
    tool_execution_count: int = 0,
    tool_arguments_sha256: str | None = None,
    tool_result_sha256: str | None = None,
) -> AdapterProtocolCaseResult:
    return AdapterProtocolCaseResult(
        case_id=case_id,
        status=status,
        error_code=error_code,
        external_calls=external_calls,
        latency_ms=latency_ms,
        input_tokens=sum(response.usage.input_tokens for response in responses),
        output_tokens=sum(response.usage.output_tokens for response in responses),
        response_count=len(responses),
        resolved_models=tuple(response.model for response in responses),
        finish_reasons=tuple(
            response.finish_reason
            for response in responses
            if response.finish_reason is not None
        ),
        request_id_sha256=tuple(
            _sha256(response.request_id)
            for response in responses
            if response.request_id is not None
        ),
        output_sha256=output_sha256,
        tool_call_count=tool_call_count,
        tool_execution_count=tool_execution_count,
        tool_arguments_sha256=tool_arguments_sha256,
        tool_result_sha256=tool_result_sha256,
    )


def _safe_tool_result(result) -> dict[str, Any]:
    return {
        "success": result.success,
        "tool_name": result.tool_name,
        "tool_version": result.tool_version,
        "attempts": result.attempts,
        "data": result.data,
        "error_code": result.error.code if result.error is not None else None,
    }


def _sha256(value: Any) -> str:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    else:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _elapsed_ms(clock: Callable[[], float], started: float) -> int:
    return max(0, round((clock() - started) * 1000))
