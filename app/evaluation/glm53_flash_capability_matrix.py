"""A fresh, bounded GLM-5.3-Flash capability matrix.

This is an evaluation-only surface.  It exercises the repaired Zhipu adapter
and a few vendor capabilities without changing the production default, the
Workbench, or the historical G53-4 evidence.  Only allowlisted observations
are serialised; prompts, model text, reasoning text, tool arguments, and raw
request identifiers never cross the result boundary.
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import subprocess
import time
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agent.loop import AgentLoop, AgentRunRequest, AgentRunStatus
from app.evaluation.provider_capability_gate import (
    ExternalCallBudget,
    ExternalCallBudgetExceeded,
)
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    StructuredResponseContract,
    TokenUsage,
    ToolChoiceMode,
)
from app.providers.structured import decode_structured_response
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_MODEL,
    ZHIPU_GLM53_FLASH_THINKING_PROFILE,
)
from app.tools.models import ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


MATRIX_SCHEMA_VERSION = "1.0"
MATRIX_EXPERIMENT_ID = "g53-5-fresh-flash-capability-matrix-v1"
MAX_REAL_CALLS = 11
MAX_OBSERVED_TOKENS = 80_000
MAX_OUTPUT_TOKENS_PER_REQUEST = 512
LONG_CONTEXT_BYTES = 64 * 1024
MATRIX_CASE_IDS = (
    "F1_adapter_text_reasoning",
    "F2_adapter_structured_json",
    "F3_agent_multi_tool_roundtrip",
    "F4_long_context_cache_pair",
    "F5_domain_development_smoke",
    "F6_vendor_stream_text",
    "F7_vendor_tool_stream",
    "F8_vendor_multimodal_image",
)

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
CaseStatus = Literal["passed", "failed", "skipped", "not_observed", "not_supported"]
FieldState = Literal["not_observed", "missing", "empty", "non_empty", "non_string"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MatrixSourceIdentity(_FrozenModel):
    head_sha: GitShaText
    origin_main_sha: GitShaText | None = None
    worktree_dirty: bool
    worktree_patch_sha256: Sha256Text
    public_ci_confirmed: Literal[False] = False


class MatrixBudget(_FrozenModel):
    max_real_calls: Literal[11] = MAX_REAL_CALLS
    max_observed_tokens: Literal[80000] = MAX_OBSERVED_TOKENS
    max_output_tokens_per_request: Literal[512] = (
        MAX_OUTPUT_TOKENS_PER_REQUEST
    )
    sdk_max_retries: Literal[0] = 0


class MatrixCaseResult(_FrozenModel):
    case_id: NonBlankText
    layer: Literal["adapter", "agent", "domain_development", "vendor_raw"]
    capability: NonBlankText
    status: CaseStatus
    error_code: NonBlankText | None = None
    external_calls: int = Field(ge=0, le=MAX_REAL_CALLS)
    response_count: int = Field(ge=0)
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    reasoning_sha256: Sha256Text | None = None
    reasoning_replay_exact: bool | None = None
    tool_call_count: int = Field(ge=0)
    tool_execution_count: int = Field(ge=0)
    tool_order_sha256: Sha256Text | None = None
    output_sha256: Sha256Text | None = None
    request_id_sha256: tuple[Sha256Text, ...] = ()
    resolved_models: tuple[NonBlankText, ...] = ()
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    cache_status: Literal["not_applicable", "unproven", "miss", "hit"] = (
        "not_applicable"
    )
    chunk_count: int = Field(ge=0)
    content_chunk_count: int = Field(ge=0)
    reasoning_chunk_count: int = Field(ge=0)
    tool_call_chunk_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_evidence(self) -> "MatrixCaseResult":
        if self.tool_execution_count > self.tool_call_count:
            raise ValueError("tool executions cannot exceed tool calls")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input tokens")
        if self.reasoning_state == "non_empty" and self.reasoning_sha256 is None:
            raise ValueError("non-empty reasoning needs a digest")
        if self.reasoning_state != "non_empty" and self.reasoning_sha256 is not None:
            raise ValueError("reasoning digest requires non-empty reasoning")
        if self.status == "passed" and self.output_sha256 is None:
            raise ValueError("passed case needs an output digest")
        if self.status != "passed" and self.output_sha256 is not None:
            raise ValueError("non-passed case cannot expose output digest")
        if self.status == "skipped":
            if self.external_calls or self.response_count or self.input_tokens or self.output_tokens:
                raise ValueError("skipped case cannot claim execution")
            if self.content_state != "not_observed" or self.reasoning_state != "not_observed":
                raise ValueError("skipped case cannot claim response state")
        if self.reasoning_replay_exact is True and self.reasoning_state != "non_empty":
            raise ValueError("replay evidence requires reasoning")
        return self


class MatrixResources(_FrozenModel):
    calls_used: int = Field(ge=0, le=MAX_REAL_CALLS)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=MAX_OBSERVED_TOKENS)
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "MatrixResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total must equal input plus output")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        return self


class MatrixVerdicts(_FrozenModel):
    adapter_core_passed: bool
    agent_loop_passed: bool
    domain_development_passed: bool
    vendor_stream_observed: bool
    vendor_multimodal_observed: bool
    production_admitted: Literal[False] = False


class GLM53FlashCapabilityMatrixReport(_FrozenModel):
    schema_version: Literal[MATRIX_SCHEMA_VERSION] = MATRIX_SCHEMA_VERSION
    experiment_id: Sha256Text
    experiment_name: Literal[MATRIX_EXPERIMENT_ID] = MATRIX_EXPERIMENT_ID
    evidence_class: Literal[
        "dirty_worktree_real_api_observation", "preflight_no_io"
    ] = (
        "dirty_worktree_real_api_observation"
    )
    provider_id: Literal["zhipu"] = "zhipu"
    requested_model: Literal[ZHIPU_GLM53_FLASH_MODEL] = ZHIPU_GLM53_FLASH_MODEL
    base_url: NonBlankText
    thinking_profile_id: Literal[ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id] = (
        ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id
    )
    source_identity: MatrixSourceIdentity
    budgets: MatrixBudget
    resources: MatrixResources
    run_timestamp_utc: datetime
    cases: tuple[MatrixCaseResult, ...]
    unsupported_boundaries: tuple[NonBlankText, ...]
    verdicts: MatrixVerdicts

    @model_validator(mode="after")
    def validate_report(self) -> "GLM53FlashCapabilityMatrixReport":
        if tuple(row.case_id for row in self.cases) != MATRIX_CASE_IDS:
            raise ValueError("matrix cases must use canonical order")
        if self.resources.calls_used != sum(row.external_calls for row in self.cases):
            raise ValueError("resource call total mismatch")
        if self.resources.input_tokens != sum(row.input_tokens for row in self.cases):
            raise ValueError("resource input total mismatch")
        if self.resources.output_tokens != sum(row.output_tokens for row in self.cases):
            raise ValueError("resource output total mismatch")
        if self.resources.cached_input_tokens != sum(
            row.cached_input_tokens for row in self.cases
        ):
            raise ValueError("resource cache total mismatch")
        if self.resources.latency_ms != sum(row.latency_ms for row in self.cases):
            raise ValueError("resource latency total mismatch")
        if self.resources.total_tokens > self.budgets.max_observed_tokens:
            raise ValueError("matrix token budget exceeded")
        if self.verdicts.production_admitted is not False:
            raise ValueError("this matrix cannot admit production")
        return self


@dataclass(frozen=True)
class _Observation:
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    reasoning_sha256: str | None = None
    reasoning_replay_exact: bool | None = None
    output_sha256: str | None = None
    request_id_sha256: tuple[str, ...] = ()
    resolved_models: tuple[str, ...] = ()
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    response_count: int = 0
    tool_call_count: int = 0
    tool_execution_count: int = 0
    tool_order_sha256: str | None = None
    chunk_count: int = 0
    content_chunk_count: int = 0
    reasoning_chunk_count: int = 0
    tool_call_chunk_count: int = 0


class _MatrixBudgetExceeded(RuntimeError):
    pass


class _Budget:
    def __init__(self, max_calls: int, max_tokens: int) -> None:
        self.calls = ExternalCallBudget(max_calls=max_calls)
        self.max_tokens = max_tokens
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_input_tokens = 0

    @property
    def calls_used(self) -> int:
        return self.calls.calls_used

    def run(self, operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return self.calls.run(operation, *args, **kwargs)

    def add_usage(self, usage: TokenUsage) -> None:
        next_total = (
            self.input_tokens
            + self.output_tokens
            + usage.input_tokens
            + usage.output_tokens
        )
        if next_total > self.max_tokens:
            raise _MatrixBudgetExceeded("observed_token_budget_exceeded")
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cached_input_tokens += usage.cached_input_tokens


class _RecordingCompletions:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        return self.delegate.create(**kwargs)


class _RecordingClient:
    def __init__(self, delegate: Any) -> None:
        self.completions = _RecordingCompletions(delegate.chat.completions)
        self.chat = SimpleNamespace(completions=self.completions)


class _SamplingProvider:
    """Apply Flash's documented sampling recommendation to AgentLoop calls."""

    def __init__(self, provider: ZhipuProvider, budget: _Budget) -> None:
        self.provider = provider
        self.budget = budget
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities

    def chat(self, request: ChatRequest):
        response = self.budget.run(
            self.provider.chat,
            request.__class__(
                messages=request.messages,
                tools=request.tools,
                tool_choice=request.tool_choice,
                temperature=1.0,
                max_tokens=request.max_tokens,
                timeout_s=request.timeout_s,
                response_contract=request.response_contract,
                metadata=request.metadata,
                top_p=0.95,
            ),
        )
        self.budget.add_usage(response.usage)
        return response


class FlashCapabilityMatrixRunner:
    """Run the matrix once; no case retries and no output overwrite."""

    def __init__(
        self,
        *,
        client: Any,
        model: str = ZHIPU_GLM53_FLASH_MODEL,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/",
        code_identity: MatrixSourceIdentity,
        max_calls: int = MAX_REAL_CALLS,
        max_observed_tokens: int = MAX_OBSERVED_TOKENS,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        clock: Callable[[], float] = time.monotonic,
        on_case_complete: Callable[[str, str, int], None] | None = None,
    ) -> None:
        if max_calls != MAX_REAL_CALLS:
            raise ValueError(f"matrix requires exactly {MAX_REAL_CALLS} calls")
        if max_observed_tokens != MAX_OBSERVED_TOKENS:
            raise ValueError(f"matrix requires exactly {MAX_OBSERVED_TOKENS} tokens")
        if model != ZHIPU_GLM53_FLASH_MODEL:
            raise ValueError("matrix requires exact GLM-5.3-Flash model")
        self.client = client
        self.model = model
        self.base_url = base_url
        self.code_identity = code_identity
        self.budget = _Budget(max_calls, max_observed_tokens)
        self.now = now
        self.clock = clock
        self.on_case_complete = on_case_complete
        self.stop_code: str | None = None
        self._cases: list[MatrixCaseResult] = []

    def run(self) -> GLM53FlashCapabilityMatrixReport:
        self._run_case("F1_adapter_text_reasoning", "adapter", "text_reasoning", self._f1)
        self._run_case("F2_adapter_structured_json", "adapter", "structured_output", self._f2)
        self._run_case("F3_agent_multi_tool_roundtrip", "agent", "multi_tool_calling", self._f3)
        self._run_case("F4_long_context_cache_pair", "adapter", "long_context_cache", self._f4)
        self._run_case("F5_domain_development_smoke", "domain_development", "grounded_agent", self._f5)
        self._run_case("F6_vendor_stream_text", "vendor_raw", "streaming", self._f6)
        self._run_case("F7_vendor_tool_stream", "vendor_raw", "tool_streaming", self._f7)
        self._run_case("F8_vendor_multimodal_image", "vendor_raw", "image_input", self._f8)
        resources = MatrixResources(
            calls_used=self.budget.calls_used,
            input_tokens=self.budget.input_tokens,
            output_tokens=self.budget.output_tokens,
            cached_input_tokens=self.budget.cached_input_tokens,
            total_tokens=self.budget.input_tokens + self.budget.output_tokens,
            latency_ms=sum(row.latency_ms for row in self._cases),
        )
        passed = {row.case_id: row.status == "passed" for row in self._cases}
        return GLM53FlashCapabilityMatrixReport(
            experiment_id=_matrix_id(self.code_identity, self.now()),
            base_url=self.base_url,
            source_identity=self.code_identity,
            budgets=MatrixBudget(),
            resources=resources,
            run_timestamp_utc=self.now(),
            cases=tuple(self._cases),
            unsupported_boundaries=(
                "provider-neutral LLMProvider remains synchronous; stream cases are adapter/vendor observations",
                "provider-neutral ChatMessage remains text-only; multimodal is vendor_raw and not production-admitted",
                "parallel_tool_calls remains false; AgentLoop executes a returned batch sequentially",
                "production security/deployment/compliance and public release gates remain open",
            ),
            verdicts=MatrixVerdicts(
                adapter_core_passed=passed["F1_adapter_text_reasoning"] and passed["F2_adapter_structured_json"],
                agent_loop_passed=passed["F3_agent_multi_tool_roundtrip"],
                domain_development_passed=passed["F5_domain_development_smoke"],
                vendor_stream_observed=passed["F6_vendor_stream_text"] or passed["F7_vendor_tool_stream"],
                vendor_multimodal_observed=passed["F8_vendor_multimodal_image"],
            ),
        )

    def _run_case(
        self,
        case_id: str,
        layer: str,
        capability: str,
        operation: Callable[[], _Observation],
    ) -> None:
        if self.stop_code is not None:
            self._cases.append(_skipped_case(case_id, layer, capability, self.stop_code))
            return
        started = self.clock()
        calls_before = self.budget.calls_used
        input_before = self.budget.input_tokens
        output_before = self.budget.output_tokens
        cached_before = self.budget.cached_input_tokens
        try:
            observation = operation()
            if observation.resolved_models and any(
                model != self.model for model in observation.resolved_models
            ):
                raise ProviderResponseError(
                    provider="zhipu",
                    code="resolved_model_mismatch",
                )
            status: CaseStatus = "passed"
            error_code = None
            if observation.output_sha256 is None:
                status = "not_observed"
                error_code = "capability_not_observed"
        except _MatrixBudgetExceeded as error:
            status = "failed"
            error_code = str(error)
            observation = _Observation()
        except ExternalCallBudgetExceeded:
            status = "failed"
            error_code = "external_call_budget_exhausted"
            observation = _Observation()
        except ProviderAuthenticationError as error:
            status = "failed"
            error_code = error.code
            observation = _Observation()
            self.stop_code = error.code
        except (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError) as error:
            status = "failed"
            error_code = error.code
            observation = _Observation()
        except ProviderError as error:
            status = "failed"
            error_code = error.code
            observation = _Observation()
        except Exception:
            status = "failed"
            error_code = "matrix_case_error"
            observation = _Observation()
        calls_used = self.budget.calls_used - calls_before
        observation = replace(
            observation,
            input_tokens=self.budget.input_tokens - input_before,
            output_tokens=self.budget.output_tokens - output_before,
            cached_input_tokens=(
                self.budget.cached_input_tokens - cached_before
            ),
        )
        self._cases.append(
            MatrixCaseResult(
                case_id=case_id,
                layer=layer,  # type: ignore[arg-type]
                capability=capability,
                status=status,
                error_code=error_code,
                external_calls=calls_used,
                response_count=observation.response_count,
                content_state=observation.content_state,
                reasoning_state=observation.reasoning_state,
                reasoning_sha256=observation.reasoning_sha256,
                reasoning_replay_exact=observation.reasoning_replay_exact,
                tool_call_count=observation.tool_call_count,
                tool_execution_count=observation.tool_execution_count,
                tool_order_sha256=observation.tool_order_sha256,
                output_sha256=observation.output_sha256 if status == "passed" else None,
                request_id_sha256=observation.request_id_sha256,
                resolved_models=observation.resolved_models,
                input_tokens=observation.input_tokens,
                output_tokens=observation.output_tokens,
                cached_input_tokens=observation.cached_input_tokens,
                latency_ms=max(0, round((self.clock() - started) * 1000)),
                cache_status=(
                    "hit" if observation.cached_input_tokens > 0 else "unproven"
                    if capability == "long_context_cache"
                    else "not_applicable"
                ),
                chunk_count=observation.chunk_count,
                content_chunk_count=observation.content_chunk_count,
                reasoning_chunk_count=observation.reasoning_chunk_count,
                tool_call_chunk_count=observation.tool_call_chunk_count,
            )
        )
        if self.on_case_complete is not None:
            self.on_case_complete(case_id, status, calls_used)

    def _provider(self, client: Any | None = None) -> ZhipuProvider:
        return ZhipuProvider(
            client=client or self.client,
            model=self.model,
            profile=ZHIPU_GLM53_FLASH_THINKING_PROFILE,
        )

    def _chat(self, provider: ZhipuProvider, request: ChatRequest):
        response = self.budget.run(provider.chat, request)
        self.budget.add_usage(response.usage)
        return response

    def _f1(self) -> _Observation:
        response = self._chat(
            self._provider(),
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "只回复短语 RIFTCOACH_F1_OK，并保持回答简短。"),),
                temperature=1.0,
                top_p=0.95,
                max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
            ),
        )
        if response.content is None or "RIFTCOACH_F1_OK" not in response.content:
            return _response_observation(response, force_output=None)
        return _response_observation(response)

    def _f2(self) -> _Observation:
        contract = StructuredResponseContract(
            name="glm53_flash_matrix",
            version="1.0.0",
            json_schema=_MatrixJSON.model_json_schema(),
        )
        response = self._chat(
            self._provider(),
            ChatRequest(
                messages=(
                    ChatMessage(MessageRole.SYSTEM, "只输出满足给定 JSON 合同的对象，不要 Markdown。"),
                    ChatMessage(MessageRole.USER, "返回 marker=RIFTCOACH_F2_OK、score=100。"),
                ),
                response_contract=contract,
                tool_choice=ToolChoiceMode.NONE,
                temperature=1.0,
                top_p=0.95,
                max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
            ),
        )
        decoded = decode_structured_response(
            response=response,
            contract=contract,
            output_model=_MatrixJSON,
        )
        if decoded.value.marker != "RIFTCOACH_F2_OK":
            raise ProviderResponseError(provider="zhipu", code="matrix_marker_mismatch")
        return _response_observation(response, output_value=decoded.value.model_dump(mode="json"))

    def _f3(self) -> _Observation:
        recording = _RecordingClient(self.client)
        provider = _SamplingProvider(self._provider(recording), self.budget)
        registry = ToolRegistry()
        registry.register(_matrix_tool("matrix.lookup_alpha", "ALPHA_FACT"))
        registry.register(_matrix_tool("matrix.lookup_beta", "BETA_FACT"))
        loop = AgentLoop(
            provider=provider,
            tool_registry=registry,
            tool_runtime=ToolRuntime(registry, call_id_factory=lambda: "matrix-tool-call"),
            clock=self.clock,
        )
        result = loop.run(
            AgentRunRequest(
                messages=(
                    ChatMessage(
                        MessageRole.SYSTEM,
                        "这是一个工具协议测试。必须在同一轮同时调用 matrix.lookup_alpha 和 matrix.lookup_beta，各调用一次；收到两个结果后只回复 RIFTCOACH_F3_OK。",
                    ),
                    ChatMessage(MessageRole.USER, "执行双工具检查。"),
                ),
                allowed_tools=("matrix.lookup_alpha", "matrix.lookup_beta"),
                max_iterations=2,
                max_tool_calls=2,
                timeout_s=90.0,
            )
        )
        responses = result.provider_responses
        tool_calls = tuple(call for response in responses for call in response.tool_calls)
        reasoning = responses[0].reasoning_content if responses else None
        replay_exact = False
        if reasoning is not None and len(recording.completions.calls) >= 2:
            replay_exact = any(
                message.get("reasoning_content") == reasoning
                for message in recording.completions.calls[1].get("messages", [])
                if message.get("role") == "assistant"
            )
        if (
            len(tool_calls) != 2
            or len(result.tool_executions) != 2
            or result.status is not AgentRunStatus.COMPLETED
            or replay_exact is not True
        ):
            return _agent_observation(
                result,
                reasoning_replay_exact=replay_exact,
                output_ok=False,
            )
        final = result.final_response
        if final is None or final.content != "RIFTCOACH_F3_OK":
            raise ProviderResponseError(provider="zhipu", code="matrix_marker_mismatch")
        return _agent_observation(
            result,
            reasoning_replay_exact=replay_exact,
            output_ok=True,
        )

    def _f4(self) -> _Observation:
        body = _long_context_body()
        responses = []
        for suffix in ("FIRST", "SECOND"):
            response = self._chat(
                self._provider(),
                ChatRequest(
                    messages=(
                        ChatMessage(
                            MessageRole.SYSTEM,
                            "从长文本中提取三个哨兵，并只回复三个哨兵，以逗号分隔。",
                        ),
                        ChatMessage(MessageRole.USER, body + f"\n问题批次：{suffix}"),
                    ),
                    temperature=1.0,
                    top_p=0.95,
                    max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
                ),
            )
            responses.append(response)
        if any(response.content is None for response in responses):
            return _response_observation(responses[-1], response_count=2)
        text = responses[-1].content or ""
        if not all(marker in text for marker in ("F4_BEGIN", "F4_MIDDLE", "F4_END")):
            return _response_observation(responses[-1], response_count=2)
        return _response_observation(
            responses[-1],
            response_count=2,
            output_value={"markers": ["F4_BEGIN", "F4_MIDDLE", "F4_END"]},
            input_tokens=sum(row.usage.input_tokens for row in responses),
            output_tokens=sum(row.usage.output_tokens for row in responses),
            cached_input_tokens=sum(row.usage.cached_input_tokens for row in responses),
        )

    def _f5(self) -> _Observation:
        recording = _RecordingClient(self.client)
        provider = _SamplingProvider(self._provider(recording), self.budget)
        registry = ToolRegistry()
        registry.register(_matrix_tool("matrix.game_facts", "PLAYER_FACTS"))
        loop = AgentLoop(
            provider=provider,
            tool_registry=registry,
            tool_runtime=ToolRuntime(registry, call_id_factory=lambda: "matrix-domain-call"),
            clock=self.clock,
        )
        result = loop.run(
            AgentRunRequest(
                messages=(
                    ChatMessage(
                        MessageRole.SYSTEM,
                        "只根据 game_facts 工具返回的事实给出开发集复盘摘要。先调用工具一次，之后必须包含 PLAYER_FACTS 和 RIFTCOACH_F5_OK。不要编造数据。",
                    ),
                    ChatMessage(MessageRole.USER, "请完成一个开发集复盘摘要。"),
                ),
                allowed_tools=("matrix.game_facts",),
                max_iterations=2,
                max_tool_calls=1,
                timeout_s=90.0,
            )
        )
        if result.final_response is None or result.final_response.content is None:
            return _agent_observation(
                result,
                reasoning_replay_exact=None,
                output_ok=False,
            )
        if "RIFTCOACH_F5_OK" not in result.final_response.content or not result.tool_executions:
            return _agent_observation(
                result,
                reasoning_replay_exact=None,
                output_ok=False,
            )
        return _agent_observation(
            result,
            reasoning_replay_exact=None,
            output_ok=True,
        )

    def _f6(self) -> _Observation:
        result = self.budget.run(
            self._provider().chat_stream,
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "只回复 RIFTCOACH_F6_OK。"),),
                temperature=1.0,
                top_p=0.95,
                max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
            ),
        )
        self.budget.add_usage(result.response.usage)
        if result.response.content is None or "RIFTCOACH_F6_OK" not in result.response.content:
            return _response_observation(result.response, stream=result, force_output=None)
        return _response_observation(result.response, stream=result)

    def _f7(self) -> _Observation:
        result = self.budget.run(
            self._provider().chat_stream,
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "必须调用 matrix.lookup_alpha，不要直接回答。"),),
                tools=(
                    _tool_spec("matrix.lookup_alpha"),
                ),
                temperature=1.0,
                top_p=0.95,
                max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
            ),
            tool_stream=True,
        )
        self.budget.add_usage(result.response.usage)
        if not result.response.tool_calls:
            return _response_observation(result.response, stream=result, force_output=None)
        return _response_observation(
            result.response,
            stream=result,
            output_value={"tool_names": [call.name for call in result.response.tool_calls]},
        )

    def _f8(self) -> _Observation:
        try:
            raw = self.budget.run(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": _red_png_data_url()}},
                            {"type": "text", "text": "图像是红色还是蓝色？只回复 RED。"},
                        ],
                    }
                ],
                temperature=1.0,
                top_p=0.95,
                max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST,
                extra_body=ZHIPU_GLM53_FLASH_THINKING_PROFILE.extra_body(),
            )
        except Exception as error:
            raise self._provider()._translate_error(error) from None
        usage = _raw_usage(raw)
        self.budget.add_usage(usage)
        raw_model = getattr(raw, "model", None)
        if not isinstance(raw_model, str) or not raw_model.strip():
            raise ProviderResponseError(
                provider="zhipu",
                code="invalid_chat_response",
            )
        content = getattr(getattr(raw.choices[0], "message", None), "content", None)
        if not isinstance(content, str) or not content.strip():
            return _Observation(
                response_count=1,
                resolved_models=(raw_model,),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
            )
        if "RED" not in content.upper():
            return _Observation(
                content_state="non_empty",
                resolved_models=(raw_model,),
                response_count=1,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
            )
        return _Observation(
            content_state="non_empty",
            output_sha256=_sha(content),
            request_id_sha256=_request_digest(raw),
            resolved_models=(raw_model,),
            response_count=1,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
        )


class _MatrixJSON(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marker: Literal["RIFTCOACH_F2_OK"]
    score: int = Field(ge=0, le=100)


def _agent_observation(
    result: Any,
    *,
    reasoning_replay_exact: bool | None,
    output_ok: bool,
) -> _Observation:
    responses = tuple(result.provider_responses)
    first = responses[0] if responses else None
    final = result.final_response
    content = getattr(final, "content", None)
    reasoning = getattr(first, "reasoning_content", None)
    tool_calls = tuple(
        call for response in responses for call in response.tool_calls
    )
    return _Observation(
        content_state=(
            "non_empty"
            if isinstance(content, str) and content.strip()
            else "empty"
            if isinstance(content, str)
            else "missing"
        ),
        reasoning_state=(
            "non_empty"
            if isinstance(reasoning, str) and reasoning.strip()
            else "empty"
            if isinstance(reasoning, str)
            else "missing"
        ),
        reasoning_sha256=(
            _sha(reasoning)
            if isinstance(reasoning, str) and reasoning.strip()
            else None
        ),
        reasoning_replay_exact=reasoning_replay_exact,
        output_sha256=_sha(content) if output_ok and isinstance(content, str) else None,
        request_id_sha256=tuple(
            _sha(response.request_id)
            for response in responses
            if isinstance(response.request_id, str) and response.request_id
        ),
        resolved_models=tuple(response.model for response in responses),
        input_tokens=sum(response.usage.input_tokens for response in responses),
        output_tokens=sum(response.usage.output_tokens for response in responses),
        cached_input_tokens=sum(
            response.usage.cached_input_tokens for response in responses
        ),
        response_count=len(responses),
        tool_call_count=len(tool_calls),
        tool_execution_count=len(result.tool_executions),
        tool_order_sha256=(
            _sha([call.name for call in tool_calls]) if tool_calls else None
        ),
    )


def _response_observation(
    response: Any,
    *,
    response_count: int | None = None,
    output_value: Any = None,
    force_output: str | None = "auto",
    tool_call_count: int | None = None,
    tool_execution_count: int = 0,
    tool_order: Sequence[str] | None = None,
    reasoning_replay_exact: bool | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    stream: Any = None,
) -> _Observation:
    responses = response if isinstance(response, (list, tuple)) else [response] if response is not None else []
    last = responses[-1] if responses else None
    content = getattr(last, "content", None)
    reasoning = getattr(last, "reasoning_content", None)
    if content is None:
        content_state: FieldState = "missing"
    elif isinstance(content, str) and content.strip():
        content_state = "non_empty"
    elif isinstance(content, str):
        content_state = "empty"
    else:
        content_state = "non_string"
    if reasoning is None:
        reasoning_state: FieldState = "missing"
    elif isinstance(reasoning, str) and reasoning.strip():
        reasoning_state = "non_empty"
    elif isinstance(reasoning, str):
        reasoning_state = "empty"
    else:
        reasoning_state = "non_string"
    if force_output is None:
        digest = None
    elif output_value is not None:
        digest = _sha(output_value)
    elif force_output == "auto" and content_state == "non_empty":
        digest = _sha(content)
    else:
        digest = None
    usage_rows = [getattr(row, "usage", TokenUsage()) for row in responses]
    ids = tuple(
        _sha(getattr(row, "request_id", None))
        for row in responses
        if isinstance(getattr(row, "request_id", None), str)
    )
    tool_count = (
        tool_call_count
        if tool_call_count is not None
        else sum(len(getattr(row, "tool_calls", ()) or ()) for row in responses)
    )
    result = _Observation(
        content_state=content_state,
        reasoning_state=reasoning_state,
        reasoning_sha256=_sha(reasoning) if reasoning_state == "non_empty" else None,
        reasoning_replay_exact=reasoning_replay_exact,
        output_sha256=digest,
        request_id_sha256=ids,
        resolved_models=tuple(
            row.model for row in responses if isinstance(row.model, str)
        ),
        input_tokens=(input_tokens if input_tokens is not None else sum(row.input_tokens for row in usage_rows)),
        output_tokens=(output_tokens if output_tokens is not None else sum(row.output_tokens for row in usage_rows)),
        cached_input_tokens=(cached_input_tokens if cached_input_tokens is not None else sum(row.cached_input_tokens for row in usage_rows)),
        response_count=response_count if response_count is not None else len(responses),
        tool_call_count=tool_count,
        tool_execution_count=tool_execution_count,
        tool_order_sha256=_sha(list(tool_order)) if tool_order else None,
    )
    if stream is not None:
        result = _Observation(
            **{
                **result.__dict__,
                "chunk_count": stream.chunk_count,
                "content_chunk_count": stream.content_chunk_count,
                "reasoning_chunk_count": stream.reasoning_chunk_count,
                "tool_call_chunk_count": stream.tool_call_chunk_count,
            }
        )
    return result


def _raw_usage(raw: Any) -> TokenUsage:
    usage = getattr(raw, "usage", None)
    if usage is None:
        raise ProviderResponseError(provider="zhipu", code="provider_usage_unavailable")
    input_tokens = getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    if not isinstance(input_tokens, int) or isinstance(input_tokens, bool) or input_tokens < 0:
        raise ProviderResponseError(provider="zhipu", code="provider_usage_unavailable")
    if not isinstance(output_tokens, int) or isinstance(output_tokens, bool) or output_tokens < 0:
        raise ProviderResponseError(provider="zhipu", code="provider_usage_unavailable")
    details = getattr(usage, "prompt_tokens_details", None)
    cached = details.get("cached_tokens", 0) if isinstance(details, Mapping) else getattr(details, "cached_tokens", 0) if details is not None else 0
    if cached is None:
        cached = 0
    if not isinstance(cached, int) or isinstance(cached, bool) or cached < 0 or cached > input_tokens:
        raise ProviderResponseError(provider="zhipu", code="provider_usage_unavailable")
    return TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, cached_input_tokens=cached)


def _request_digest(raw: Any) -> tuple[str, ...]:
    value = getattr(raw, "id", None)
    return (_sha(value),) if isinstance(value, str) and value else ()


def _sha(value: Any) -> str:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    else:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matrix_id(identity: MatrixSourceIdentity, now: datetime) -> str:
    return _sha({"name": MATRIX_EXPERIMENT_ID, "head": identity.head_sha, "patch": identity.worktree_patch_sha256, "timestamp": now.isoformat()})


def _skipped_case(case_id: str, layer: str, capability: str, code: str) -> MatrixCaseResult:
    return MatrixCaseResult(
        case_id=case_id,
        layer=layer,
        capability=capability,
        status="skipped",
        error_code=code,
        external_calls=0,
        response_count=0,
        tool_call_count=0,
        tool_execution_count=0,
        input_tokens=0,
        output_tokens=0,
        cached_input_tokens=0,
        latency_ms=0,
        chunk_count=0,
        content_chunk_count=0,
        reasoning_chunk_count=0,
        tool_call_chunk_count=0,
    )


def _tool_spec(name: str):
    from app.providers.models import ToolSpec

    return ToolSpec(name=name, description="Read-only matrix fixture.", input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "additionalProperties": False})


def _matrix_tool(name: str, marker: str) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        version="1.0.0",
        description="Read-only development fixture for the GLM-5.3-Flash matrix.",
        handler=lambda params, context, marker=marker: {"marker": marker, "query": params.get("query", "")},
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "additionalProperties": False},
        output_schema={"type": "object", "properties": {"marker": {"type": "string"}, "query": {"type": "string"}}, "required": ["marker", "query"], "additionalProperties": False},
        policy=ToolPolicy(),
        idempotent=True,
    )


def _long_context_body() -> str:
    prefix = "F4_BEGIN\n" + ("context-stable-line-0123456789\n" * 1_000)
    suffix = "F4_MIDDLE\n" + ("context-stable-line-abcdefghij\n" * 1_000) + "F4_END\n"
    body = prefix + suffix
    if len(body.encode("utf-8")) < LONG_CONTEXT_BYTES:
        body += "x" * (LONG_CONTEXT_BYTES - len(body.encode("utf-8")))
    return body[:LONG_CONTEXT_BYTES]


def _red_png_data_url() -> str:
    row = b"\x00" + b"\xff\x00\x00\xff" * 16
    raw = row * 16
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return completed.stdout.strip()


def collect_source_identity(root: Path) -> MatrixSourceIdentity:
    head = _git_output(root, "rev-parse", "HEAD")
    try:
        origin = _git_output(root, "rev-parse", "origin/main")
    except Exception:
        origin = None
    status = _git_output(root, "status", "--short")
    diff = _git_output(root, "diff", "--no-ext-diff", "--binary")
    untracked = _git_output(root, "ls-files", "--others", "--exclude-standard")
    patch_hash = _sha({"status": status, "diff": diff, "untracked_paths": untracked})
    return MatrixSourceIdentity(
        head_sha=head,
        origin_main_sha=origin,
        worktree_dirty=bool(status),
        worktree_patch_sha256=patch_hash,
    )


def reserve_output(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("x", encoding="utf-8", newline="\n")
    handle.close()


def run_real_matrix(
    *,
    repository_root: Path,
    output: Path,
    api_key: str,
    base_url: str,
    model: str,
) -> GLM53FlashCapabilityMatrixReport:
    if not api_key.strip():
        raise ValueError("missing_api_key")
    if base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
        raise ValueError("invalid_base_url")
    if model != ZHIPU_GLM53_FLASH_MODEL:
        raise ValueError("invalid_model")
    reserve_output(output)
    identity = collect_source_identity(repository_root)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=90.0, max_retries=0)
    report = FlashCapabilityMatrixRunner(
        client=client,
        model=model,
        base_url=base_url,
        code_identity=identity,
        on_case_complete=lambda case_id, status, calls: print(
            f"[G53-5] {case_id}: {status} (calls +{calls})", flush=True
        ),
    ).run()
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def build_preflight_report(repository_root: Path) -> GLM53FlashCapabilityMatrixReport:
    identity = collect_source_identity(repository_root)
    cases = tuple(
        _skipped_case(case_id, "adapter" if case_id.startswith("F1") or case_id.startswith("F2") or case_id.startswith("F4") else "agent" if case_id.startswith("F3") else "domain_development" if case_id.startswith("F5") else "vendor_raw", "preflight", "preflight_only")
        for case_id in MATRIX_CASE_IDS
    )
    return GLM53FlashCapabilityMatrixReport(
        experiment_id=_matrix_id(identity, datetime.now(timezone.utc)),
        evidence_class="preflight_no_io",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        source_identity=identity,
        budgets=MatrixBudget(),
        resources=MatrixResources(calls_used=0, input_tokens=0, output_tokens=0, cached_input_tokens=0, total_tokens=0, latency_ms=0),
        run_timestamp_utc=datetime.now(timezone.utc),
        cases=cases,
        unsupported_boundaries=("preflight_only_no_external_io",),
        verdicts=MatrixVerdicts(adapter_core_passed=False, agent_loop_passed=False, domain_development_passed=False, vendor_stream_observed=False, vendor_multimodal_observed=False),
    )


__all__ = [
    "FlashCapabilityMatrixRunner",
    "GLM53FlashCapabilityMatrixReport",
    "MATRIX_CASE_IDS",
    "MAX_OBSERVED_TOKENS",
    "MAX_REAL_CALLS",
    "build_preflight_report",
    "collect_source_identity",
    "reserve_output",
    "run_real_matrix",
]
