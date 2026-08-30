"""Isolated, no-retry P1-P5 capability probe for Zhipu's chat API."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import openai
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from app.evaluation.coach_report import (
    EvaluationResponseModel,
    evaluation_response_contract,
)
from app.evaluation.provider_capability_gate import (
    CapabilityProbeCaseResult,
    CapabilityProbeReport,
    ExternalCallBudget,
    ProbeScope,
    ResponseFieldState,
)
from app.providers.models import ChatResponse, TokenUsage
from app.providers.structured import decode_structured_response
from app.providers.zhipu_profiles import (
    ZhipuThinkingProfile,
    resolve_zhipu_thinking_profile,
    validate_zhipu_profile_for_model,
)


_PROVIDER_TOOL_NAME = "knowledge_search"
_TOOL_ARGUMENTS = {"query": "前15分钟死亡", "top_k": 1}
_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": _PROVIDER_TOOL_NAME,
        "description": "检索英雄联盟赛后复盘知识。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
    },
}
_PASS_PAYLOAD = {
    "score": 100,
    "verdict": "pass",
    "issues": [],
    "passed_checks": ["schema"],
    "summary": "格式通过",
}
_ISSUE_PAYLOAD = {
    "score": 70,
    "verdict": "needs_revision",
    "issues": [
        {
            "severity": "high",
            "category": "fact_error",
            "quote": "错误数字",
            "evidence": "确定性数据",
            "explanation": "数字不一致",
            "suggested_correction": "改用确定性数字",
        }
    ],
    "passed_checks": ["结构完整"],
    "summary": "需要修订",
}


class _ProbeFailure(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class _ObservedResponse:
    resolved_model: str
    request_id: str | None
    finish_reason: str | None
    usage: TokenUsage
    output_value: Any
    tool_call_count: int = 0


@dataclass(frozen=True)
class _SafeResponseObservation:
    """Whitelisted response metadata that never contains model text or raw IDs."""

    response_received: bool
    content_state: ResponseFieldState
    reasoning_content_state: ResponseFieldState
    resolved_model: str | None
    finish_reason: str | None
    usage: TokenUsage
    request_id_sha256: str | None
    tool_call_count: int


class ZhipuCapabilityProbe:
    """Run five bounded raw API cases without Provider retries or raw persistence."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        code_sha: str,
        scope: ProbeScope = "p1_p5",
        max_calls: int = 5,
        profile: ZhipuThinkingProfile | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if client is None:
            raise ValueError("client is required.")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must not be empty.")
        if not isinstance(code_sha, str) or not code_sha.strip():
            raise ValueError("code_sha must not be empty.")
        if scope not in ("p1_p5", "p1_diagnostic"):
            raise ValueError("unsupported capability probe scope.")
        expected_calls = 1 if scope == "p1_diagnostic" else 5
        if max_calls != expected_calls:
            raise ValueError(
                f"{scope} capability probe requires exactly {expected_calls} calls."
            )
        self._client = client
        self._model = model.strip()
        selected_profile = profile or resolve_zhipu_thinking_profile(
            self._model
        )
        try:
            self._profile = validate_zhipu_profile_for_model(
                self._model,
                selected_profile,
            )
        except ValueError as error:
            raise ValueError(str(error)) from error
        self._code_sha = code_sha.strip().lower()
        self._scope = scope
        self._budget = ExternalCallBudget(max_calls=max_calls)
        self._clock = clock
        self._now = now

    def run(self) -> CapabilityProbeReport:
        cases: list[CapabilityProbeCaseResult] = []

        p1, _ = self._run_case(
            case_id="P1_text_baseline",
            capability="text_chat",
            request={
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": "只回复：RIFTCOACH_PROVIDER_OK",
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 128,
                "extra_body": self._profile.extra_body(),
            },
            validator=self._validate_baseline_text,
        )
        cases.append(p1)
        if self._scope == "p1_diagnostic":
            return self._report(cases)
        if p1.status != "passed":
            cases.extend(
                self._skipped(case_id, capability, "p1_baseline_failed")
                for case_id, capability in (
                    ("P2_structured_pass", "structured_output"),
                    ("P3_structured_issue", "structured_output"),
                    ("P4_tool_request", "tool_calling"),
                    ("P5_tool_final", "tool_calling"),
                )
            )
            return self._report(cases)

        for case_id, target in (
            ("P2_structured_pass", _PASS_PAYLOAD),
            ("P3_structured_issue", _ISSUE_PAYLOAD),
        ):
            result, _ = self._run_case(
                case_id=case_id,
                capability="structured_output",
                request=self._structured_request(target),
                validator=lambda raw, expected=target: self._validate_structured(
                    raw,
                    expected,
                ),
            )
            cases.append(result)

        p4, tool_state = self._run_case(
            case_id="P4_tool_request",
            capability="tool_calling",
            request={
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": "必须调用提供的唯一工具，不要直接回答。",
                    },
                    {
                        "role": "user",
                        "content": "检索前15分钟死亡的复盘知识，top_k 使用 1。",
                    },
                ],
                "tools": [_TOOL_SPEC],
                "tool_choice": "auto",
                "temperature": 0.0,
                "max_tokens": 512,
                "extra_body": self._profile.extra_body(),
            },
            validator=self._validate_tool_request,
        )
        cases.append(p4)
        if p4.status != "passed" or tool_state is None:
            cases.append(
                self._skipped(
                    "P5_tool_final",
                    "tool_calling",
                    "p4_tool_request_failed",
                )
            )
            return self._report(cases)

        p5, _ = self._run_case(
            case_id="P5_tool_final",
            capability="tool_calling",
            request=self._tool_final_request(tool_state),
            validator=self._validate_text_without_tool_call,
        )
        cases.append(p5)
        return self._report(cases)

    def _run_case(
        self,
        *,
        case_id: str,
        capability: str,
        request: Mapping[str, Any],
        validator: Callable[[Any], _ObservedResponse],
    ) -> tuple[CapabilityProbeCaseResult, Any | None]:
        started = self._clock()
        safe_observation: _SafeResponseObservation | None = None
        try:
            raw = self._budget.run(
                self._client.chat.completions.create,
                **dict(request),
            )
            safe_observation = _capture_safe_observation(raw)
            observed = validator(raw)
            elapsed_ms = max(0, round((self._clock() - started) * 1000))
            output_digest = _digest(observed.output_value)
            case = CapabilityProbeCaseResult(
                case_id=case_id,
                capability=capability,
                status="passed",
                error_code=None,
                response_received=True,
                content_state=safe_observation.content_state,
                reasoning_content_state=(
                    safe_observation.reasoning_content_state
                ),
                latency_ms=elapsed_ms,
                input_tokens=safe_observation.usage.input_tokens,
                output_tokens=safe_observation.usage.output_tokens,
                finish_reason=safe_observation.finish_reason,
                resolved_model=safe_observation.resolved_model,
                request_id_sha256=safe_observation.request_id_sha256,
                tool_call_count=safe_observation.tool_call_count,
                repair_count=0,
                output_sha256=output_digest,
            )
            return case, observed.output_value
        except Exception as error:
            elapsed_ms = max(0, round((self._clock() - started) * 1000))
            observation = safe_observation or _no_response_observation()
            return (
                CapabilityProbeCaseResult(
                    case_id=case_id,
                    capability=capability,
                    status="failed",
                    error_code=_safe_error_code(error),
                    response_received=observation.response_received,
                    content_state=observation.content_state,
                    reasoning_content_state=(
                        observation.reasoning_content_state
                    ),
                    latency_ms=elapsed_ms,
                    input_tokens=observation.usage.input_tokens,
                    output_tokens=observation.usage.output_tokens,
                    finish_reason=observation.finish_reason,
                    resolved_model=observation.resolved_model,
                    request_id_sha256=observation.request_id_sha256,
                    tool_call_count=observation.tool_call_count,
                    repair_count=0,
                    output_sha256=None,
                ),
                None,
            )

    def _report(
        self,
        cases: list[CapabilityProbeCaseResult],
    ) -> CapabilityProbeReport:
        by_id = {case.case_id: case for case in cases}
        admitted = all(
            by_id.get(case_id) is not None
            and by_id[case_id].status == "passed"
            for case_id in (
                "P1_text_baseline",
                "P2_structured_pass",
                "P3_structured_issue",
                "P4_tool_request",
                "P5_tool_final",
            )
        )
        return CapabilityProbeReport(
            schema_version="1.1",
            probe_scope=self._scope,
            provider_id="zhipu",
            requested_model=self._model,
            code_sha=self._code_sha,
            documentation_snapshot_date="2026-08-12",
            run_timestamp_utc=self._now(),
            max_calls=self._budget.max_calls,
            calls_used=self._budget.calls_used,
            admitted=admitted,
            cases=tuple(cases),
            estimated_cost=None,
            cost_note="Official per-token unit price was not verified for this run.",
        )

    def _structured_request(self, target: Mapping[str, Any]) -> dict[str, Any]:
        schema = evaluation_response_contract().schema_dict()
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "只输出一个 JSON object，不要输出 Markdown 或解释。"
                        "字段必须严格符合给定 JSON Schema。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "JSON Schema:\n"
                        f"{json.dumps(schema, ensure_ascii=False)}\n"
                        "请原样表达下面已经确定的结构化结论：\n"
                        f"{json.dumps(dict(target), ensure_ascii=False)}"
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 1024,
            "extra_body": self._profile.extra_body(),
        }

    def _tool_final_request(self, state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "根据工具结果给出一句简短回答，不要再次调用工具。",
                },
                {
                    "role": "user",
                    "content": "检索前15分钟死亡的复盘知识，top_k 使用 1。",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": state["id"],
                            "type": "function",
                            "function": {
                                "name": state["name"],
                                "arguments": json.dumps(
                                    state["arguments"],
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": state["id"],
                    "content": json.dumps(
                        {
                            "success": True,
                            "data": {
                                "answer": "前15分钟死亡应结合兵线、视野和资源窗口复盘。",
                                "source": "probe_fixture.md",
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "tools": [_TOOL_SPEC],
            "tool_choice": "auto",
            "temperature": 0.0,
            "max_tokens": 512,
            "extra_body": self._profile.extra_body(),
        }

    def _validate_text(self, raw: Any) -> _ObservedResponse:
        observed = _common_observation(raw)
        content = _message(raw).content
        if not isinstance(content, str) or not content.strip():
            raise _ProbeFailure("invalid_text_response")
        self._validate_reasoning_content(raw)
        return _replace_output(observed, content.strip())

    def _validate_baseline_text(self, raw: Any) -> _ObservedResponse:
        observed = self._validate_text(raw)
        if observed.output_value != "RIFTCOACH_PROVIDER_OK":
            raise _ProbeFailure("text_semantic_mismatch")
        return observed

    def _validate_text_without_tool_call(self, raw: Any) -> _ObservedResponse:
        message = _message(raw)
        if getattr(message, "tool_calls", None):
            raise _ProbeFailure("unexpected_additional_tool_call")
        return self._validate_text(raw)

    def _validate_structured(
        self,
        raw: Any,
        expected: Mapping[str, Any],
    ) -> _ObservedResponse:
        try:
            observed = _common_observation(raw)
            self._validate_reasoning_content(raw)
            content = _message(raw).content
            response = ChatResponse(
                content=content,
                model=observed.resolved_model,
                provider="zhipu",
                finish_reason=observed.finish_reason,
                usage=observed.usage,
                request_id=observed.request_id,
            )
            decoded = decode_structured_response(
                response=response,
                contract=evaluation_response_contract(),
                output_model=EvaluationResponseModel,
            )
        except Exception:
            raise _ProbeFailure("invalid_structured_output") from None
        value = decoded.value.model_dump(mode="json")
        if value != dict(expected):
            raise _ProbeFailure("structured_semantic_mismatch")
        return _replace_output(observed, value)

    def _validate_tool_request(self, raw: Any) -> _ObservedResponse:
        observed = _common_observation(raw)
        message = _message(raw)
        tool_calls = list(getattr(message, "tool_calls", None) or [])
        if len(tool_calls) != 1:
            raise _ProbeFailure("tool_call_not_observed")
        self._validate_reasoning_content(raw, tool_roundtrip=True)
        call = tool_calls[0]
        call_id = getattr(call, "id", None)
        function = getattr(call, "function", None)
        name = getattr(function, "name", None)
        arguments_text = getattr(function, "arguments", None)
        if not isinstance(call_id, str) or not call_id.strip():
            raise _ProbeFailure("invalid_tool_call_id")
        if name != _PROVIDER_TOOL_NAME:
            raise _ProbeFailure("unexpected_tool_name")
        if not isinstance(arguments_text, str):
            raise _ProbeFailure("invalid_tool_arguments")
        try:
            arguments = json.loads(arguments_text)
        except (TypeError, ValueError):
            raise _ProbeFailure("invalid_tool_arguments") from None
        if not isinstance(arguments, dict):
            raise _ProbeFailure("invalid_tool_arguments")
        try:
            Draft202012Validator(
                _TOOL_SPEC["function"]["parameters"]
            ).validate(arguments)
        except JsonSchemaValidationError:
            raise _ProbeFailure("invalid_tool_arguments") from None
        query = arguments["query"]
        if "前15分钟" not in query or "死亡" not in query:
            raise _ProbeFailure("invalid_tool_arguments")
        state = {"id": call_id.strip(), "name": name, "arguments": arguments}
        return _ObservedResponse(
            resolved_model=observed.resolved_model,
            request_id=observed.request_id,
            finish_reason=observed.finish_reason,
            usage=observed.usage,
            output_value=state,
            tool_call_count=1,
        )

    def _validate_reasoning_content(
        self,
        raw: Any,
        *,
        tool_roundtrip: bool = False,
    ) -> None:
        """Validate reasoning shape while keeping its body out of evidence."""

        message = _message(raw)
        value = getattr(message, "reasoning_content", None)
        if value is None:
            return
        if not isinstance(value, str):
            raise _ProbeFailure("unexpected_reasoning_content")
        if not value.strip():
            return
        if not self._profile.accepts_reasoning_content or tool_roundtrip:
            raise _ProbeFailure("unexpected_reasoning_content")

    @staticmethod
    def _skipped(
        case_id: str,
        capability: str,
        reason: str,
    ) -> CapabilityProbeCaseResult:
        return CapabilityProbeCaseResult(
            case_id=case_id,
            capability=capability,
            status="skipped",
            error_code=reason,
            response_received=False,
            content_state="not_observed",
            reasoning_content_state="not_observed",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            finish_reason=None,
            resolved_model=None,
            request_id_sha256=None,
            tool_call_count=0,
            repair_count=0,
            output_sha256=None,
        )


def _common_observation(raw: Any) -> _ObservedResponse:
    try:
        choice = raw.choices[0]
        message = choice.message
        resolved_model = getattr(raw, "model", None)
        if not isinstance(resolved_model, str) or not resolved_model.strip():
            raise ValueError
        usage = getattr(raw, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        normalized_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        request_id = getattr(raw, "id", None)
        if request_id is not None and not isinstance(request_id, str):
            raise ValueError
        return _ObservedResponse(
            resolved_model=resolved_model.strip(),
            request_id=request_id,
            finish_reason=getattr(choice, "finish_reason", None),
            usage=normalized_usage,
            output_value=None,
            tool_call_count=len(getattr(message, "tool_calls", None) or []),
        )
    except Exception:
        raise _ProbeFailure("invalid_sdk_response") from None


def _capture_safe_observation(raw: Any) -> _SafeResponseObservation:
    choice = _first_choice(raw)
    message = getattr(choice, "message", _MISSING)
    usage = getattr(raw, "usage", None)
    request_id = getattr(raw, "id", None)
    tool_calls = (
        getattr(message, "tool_calls", None) if message is not _MISSING else None
    )
    return _SafeResponseObservation(
        response_received=True,
        content_state=_classify_field(message, "content"),
        reasoning_content_state=_classify_field(message, "reasoning_content"),
        resolved_model=_safe_optional_text(getattr(raw, "model", None)),
        finish_reason=_safe_optional_text(
            getattr(choice, "finish_reason", None) if choice is not None else None
        ),
        usage=TokenUsage(
            input_tokens=_safe_token_count(
                getattr(usage, "prompt_tokens", 0) if usage is not None else 0
            ),
            output_tokens=_safe_token_count(
                getattr(usage, "completion_tokens", 0) if usage is not None else 0
            ),
        ),
        request_id_sha256=(
            _digest(request_id)
            if isinstance(request_id, str) and request_id
            else None
        ),
        tool_call_count=_safe_collection_length(tool_calls),
    )


def _no_response_observation() -> _SafeResponseObservation:
    return _SafeResponseObservation(
        response_received=False,
        content_state="not_observed",
        reasoning_content_state="not_observed",
        resolved_model=None,
        finish_reason=None,
        usage=TokenUsage(),
        request_id_sha256=None,
        tool_call_count=0,
    )


_MISSING = object()


def _first_choice(raw: Any) -> Any | None:
    try:
        return raw.choices[0]
    except Exception:
        return None


def _classify_field(container: Any, field_name: str) -> ResponseFieldState:
    if container is _MISSING or container is None or not hasattr(container, field_name):
        return "missing"
    value = getattr(container, field_name)
    if value is None:
        return "null"
    if not isinstance(value, str):
        return "non_string"
    return "non_empty" if value.strip() else "empty"


def _safe_optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _safe_token_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _safe_collection_length(value: Any) -> int:
    if value is None or isinstance(value, (str, bytes, bytearray)):
        return 0
    try:
        return max(0, len(value))
    except (TypeError, ValueError):
        return 0


def _message(raw: Any) -> Any:
    try:
        return raw.choices[0].message
    except Exception:
        raise _ProbeFailure("invalid_sdk_response") from None


def _replace_output(
    observed: _ObservedResponse,
    output_value: Any,
) -> _ObservedResponse:
    return _ObservedResponse(
        resolved_model=observed.resolved_model,
        request_id=observed.request_id,
        finish_reason=observed.finish_reason,
        usage=observed.usage,
        output_value=output_value,
        tool_call_count=observed.tool_call_count,
    )


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_error_code(error: Exception) -> str:
    if isinstance(error, _ProbeFailure):
        return error.code
    if isinstance(error, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return "authentication_failed"
    if isinstance(error, openai.RateLimitError):
        return "rate_limited"
    if isinstance(error, openai.APITimeoutError):
        return "timeout"
    if isinstance(error, openai.APIConnectionError):
        return "connection_failed"
    if isinstance(error, openai.APIStatusError):
        return "service_unavailable" if error.status_code >= 500 else "request_rejected"
    return "unexpected_probe_error"
