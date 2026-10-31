"""Offline SDK/HTTP transport-gate precheck for the GLM-5.3 candidate.

This module deliberately sits outside the product provider/runtime path.  It
uses the real OpenAI-compatible SDK object graph with an in-memory ``httpx``
transport, then pauses the response bytes at a known SSE boundary.  The
fixture proves that our observer can see a pending ``next()`` and that the
SDK response close reaches the transport stream.  It does *not* prove
anything about a vendor server or a real network connection.

Only the case projection is suitable for a receipt.  Raw SSE bytes, request
objects, SDK responses and exception text never enter the receipt contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from re import fullmatch
from typing import Any

import httpx
from openai import OpenAI

from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import resolve_zhipu_thinking_profile

from .candidate_provider_close_wakeup_observation import (
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    CloseReportProjection,
    CloseWakeState,
    observe_candidate_session,
)


CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID = (
    "glm-5.3-flash-candidate-close-wakeup-transport-gate"
)
CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION = "1.0.0"
TRANSPORT_GATE_EVIDENCE_ORIGIN = "offline_sdk_transport_fixture"
TRANSPORT_GATE_PROVIDER = "zhipu"
TRANSPORT_GATE_MODEL = "glm-5.3-flash"

_GATE_PHASES = frozenset({"before_first_event", "after_first_event"})
_EVENT_CATEGORIES = frozenset(
    {
        "reasoning_seen",
        "content_seen",
        "terminal_seen",
        "usage_seen",
        "tool_seen",
    }
)
_CLOSE_REPORT_KEYS = frozenset(
    {"iterator_state", "sdk_stream_state", "composite_state", "shared_resource"}
)
_EXPECTED_CASES = (
    ("after-first-event", "after_first_event"),
    ("before-first-event", "before_first_event"),
)
_CONCLUSIONS = frozenset(
    {
        "client_wakeup_clean",
        "client_wakeup_close_race",
        "client_wakeup_not_observed",
        "not_pending",
    }
)
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ID_PATTERN = r"^[a-z][a-z0-9_.-]{0,95}$"

_CASE_KEYS = frozenset(
    {
        "case_id",
        "gate_phase",
        "observation_state",
        "pending_reader_observed",
        "cancel_status",
        "cancel_returned",
        "reader_woke",
        "event_categories",
        "close_report",
        "upstream_event_seen",
        "gate_entered",
        "gate_released",
        "downstream_close_seen",
        "upstream_stream_close_seen",
        "transport_request_count",
        "conclusion",
        "passed",
    }
)
_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "evidence_origin",
        "real_provider_observed",
        "provider_call_count",
        "network_used",
        "implementation_sha",
        "observer_code_sha",
        "input_plan_sha",
        "fixture_sha256",
        "cases",
        "all_cases_passed",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "reasoning",
        "reasoning_content",
        "tool_arguments",
        "tool_results",
        "headers",
        "authorization",
        "api_key",
        "secret",
        "request_id",
        "sdk_response",
        "response_body",
    }
)


class CandidateTransportGateError(ValueError):
    """Machine-safe contract error for the offline gate."""

    def __init__(self, code: str, field_name: str | None = None) -> None:
        if fullmatch(_ID_PATTERN, code) is None:
            code = "transport_gate_contract_error"
        self.code = code
        self.field_name = field_name
        super().__init__(code)


def _safe_sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA_PATTERN, value) is None:
        raise CandidateTransportGateError("invalid_git_sha", field_name)
    return value


def _safe_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA256_PATTERN, value) is None:
        raise CandidateTransportGateError("invalid_sha256", field_name)
    return value


def _safe_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_ID_PATTERN, value) is None:
        raise CandidateTransportGateError("invalid_identifier", field_name)
    return value


def _canonical_json(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise CandidateTransportGateError("json_not_serializable", "serialize") from None


def _assert_no_forbidden_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise CandidateTransportGateError("receipt_field_forbidden", "serialize")
            _assert_no_forbidden_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_no_forbidden_keys(item)


@dataclass(frozen=True, slots=True)
class TransportGateMetrics:
    """Thread-safe snapshot of the gate lifecycle, without response data."""

    upstream_event_seen: bool
    gate_entered: bool
    gate_released: bool
    downstream_close_seen: bool
    upstream_stream_close_seen: bool
    transport_request_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "upstream_event_seen",
            "gate_entered",
            "gate_released",
            "downstream_close_seen",
            "upstream_stream_close_seen",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise CandidateTransportGateError("lifecycle_value_invalid", field_name)
        if (
            isinstance(self.transport_request_count, bool)
            or not isinstance(self.transport_request_count, int)
            or self.transport_request_count < 0
            or self.transport_request_count > 1
        ):
            raise CandidateTransportGateError("request_count_invalid", "transport_request_count")

    def as_dict(self) -> dict[str, object]:
        return {
            "upstream_event_seen": self.upstream_event_seen,
            "gate_entered": self.gate_entered,
            "gate_released": self.gate_released,
            "downstream_close_seen": self.downstream_close_seen,
            "upstream_stream_close_seen": self.upstream_stream_close_seen,
            "transport_request_count": self.transport_request_count,
        }


class _MutableGateMetrics:
    """Private mutable state used by a gate and projected after the run."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._upstream_event_seen = False
        self._gate_entered = False
        self._gate_released = False
        self._downstream_close_seen = False
        self._upstream_stream_close_seen = False
        self._transport_request_count = 0

    def increment_request(self) -> None:
        with self._lock:
            self._transport_request_count += 1

    def mark_upstream_event(self) -> None:
        with self._lock:
            self._upstream_event_seen = True

    def mark_gate_entered(self) -> None:
        with self._lock:
            self._gate_entered = True

    def mark_gate_released(self) -> None:
        with self._lock:
            self._gate_released = True

    def mark_downstream_close(self) -> None:
        with self._lock:
            self._downstream_close_seen = True

    def mark_upstream_stream_close(self) -> None:
        with self._lock:
            self._upstream_stream_close_seen = True

    def snapshot(self) -> TransportGateMetrics:
        with self._lock:
            return TransportGateMetrics(
                upstream_event_seen=self._upstream_event_seen,
                gate_entered=self._gate_entered,
                gate_released=self._gate_released,
                downstream_close_seen=self._downstream_close_seen,
                upstream_stream_close_seen=self._upstream_stream_close_seen,
                transport_request_count=self._transport_request_count,
            )


def _sse_frame_end(buffer: bytes) -> int | None:
    candidates = [
        position + len(separator)
        for separator in (b"\r\n\r\n", b"\n\n")
        if (position := buffer.find(separator)) >= 0
    ]
    return min(candidates) if candidates else None


class GatedSyncByteStream(httpx.SyncByteStream):
    """Pass the first complete SSE frame, then wait for close/release."""

    def __init__(
        self,
        inner: httpx.SyncByteStream,
        metrics: _MutableGateMetrics,
        *,
        phase: str,
        hold_timeout_s: float = 5.0,
    ) -> None:
        if phase not in _GATE_PHASES:
            raise CandidateTransportGateError("gate_phase_invalid", "gate_phase")
        if (
            isinstance(hold_timeout_s, bool)
            or not isinstance(hold_timeout_s, (int, float))
            or hold_timeout_s <= 0
            or hold_timeout_s > 30
        ):
            raise CandidateTransportGateError("hold_timeout_invalid", "hold_timeout_s")
        self._inner = inner
        self._metrics = metrics
        self._phase = phase
        self._hold_timeout_s = float(hold_timeout_s)
        self._wake = threading.Event()
        self._closed = threading.Event()
        self._close_lock = threading.Lock()

    def __iter__(self):
        buffer = b""
        first_event_emitted = False
        for chunk in self._inner:
            if self._closed.is_set():
                return
            if not isinstance(chunk, (bytes, bytearray, memoryview)):
                raise TypeError("transport fixture yielded non-bytes")
            buffer += bytes(chunk)
            if first_event_emitted:
                yield bytes(chunk)
                continue

            boundary = _sse_frame_end(buffer)
            if boundary is None:
                # The fixture is tiny and bounded.  This guard prevents an
                # accidental malformed fixture from becoming an unbounded
                # in-memory accumulator.
                if len(buffer) > 64 * 1024:
                    raise RuntimeError("transport_fixture_frame_too_large")
                continue

            first_frame = buffer[:boundary]
            remainder = buffer[boundary:]
            buffer = b""
            self._metrics.mark_upstream_event()
            if self._phase == "before_first_event":
                if not self._wait_at_gate():
                    return
            yield first_frame
            first_event_emitted = True
            if self._phase == "after_first_event":
                if not self._wait_at_gate():
                    return
            if remainder and not self._closed.is_set():
                yield remainder

        if buffer and not self._closed.is_set() and not first_event_emitted:
            # Preserve malformed/incomplete fixture bytes for the SDK to
            # reject; the gate itself must not silently synthesize a frame.
            yield buffer

    def _wait_at_gate(self) -> bool:
        self._metrics.mark_gate_entered()
        self._wake.wait(self._hold_timeout_s)
        return not self._closed.is_set()

    def release(self) -> None:
        """Release the fixture gate explicitly (not used by the probe)."""

        self._metrics.mark_gate_released()
        self._wake.set()

    def close(self) -> None:
        with self._close_lock:
            if self._closed.is_set():
                return
            self._closed.set()
            self._metrics.mark_downstream_close()
            self._wake.set()
            try:
                self._inner.close()
            finally:
                self._metrics.mark_upstream_stream_close()


class GateTransport(httpx.BaseTransport):
    """Wrap one transport response without becoming a network proxy."""

    def __init__(self, inner: httpx.BaseTransport, *, phase: str) -> None:
        if phase not in _GATE_PHASES:
            raise CandidateTransportGateError("gate_phase_invalid", "gate_phase")
        self._inner = inner
        self._phase = phase
        self._metrics = _MutableGateMetrics()

    @property
    def metrics(self) -> TransportGateMetrics:
        return self._metrics.snapshot()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._metrics.increment_request()
        if self._metrics.snapshot().transport_request_count != 1:
            raise RuntimeError("transport_gate_request_budget_exceeded")
        response = self._inner.handle_request(request)
        if not isinstance(response.stream, httpx.SyncByteStream):
            raise RuntimeError("transport_gate_response_not_sync_stream")
        gate = GatedSyncByteStream(
            response.stream,
            self._metrics,
            phase=self._phase,
        )
        response.stream = gate
        return response

    def close(self) -> None:
        self._inner.close()


def _fixture_frame(payload: Mapping[str, object]) -> bytes:
    return (
        b"data: "
        + json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n\n"
    )


_FIXTURE_DESCRIPTOR: tuple[str, ...] = (
    "reasoning_frame",
    "content_frame",
    "terminal_usage_frame",
    "done_frame",
)
_FIXTURE_BYTES = b"".join(
    (
        _fixture_frame(
            {
                "id": "fixture",
                "model": TRANSPORT_GATE_MODEL,
                "choices": [
                    {
                        "delta": {"reasoning_content": "fixture reasoning"},
                        "finish_reason": None,
                    }
                ],
            }
        ),
        _fixture_frame(
            {
                "id": "fixture",
                "model": TRANSPORT_GATE_MODEL,
                "choices": [
                    {"delta": {"content": "fixture answer"}, "finish_reason": None}
                ],
            }
        ),
        _fixture_frame(
            {
                "id": "fixture",
                "model": TRANSPORT_GATE_MODEL,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "prompt_tokens_details": {"cached_tokens": 0},
                },
            }
        ),
        b"data: [DONE]\n\n",
    )
)
_FIXTURE_SHA256 = hashlib.sha256(
    _canonical_json(list(_FIXTURE_DESCRIPTOR))
).hexdigest()


def candidate_transport_gate_fixture_sha256() -> str:
    """Return the stable descriptor digest, never a response-body digest."""

    return _FIXTURE_SHA256


def _fixture_request() -> ChatRequest:
    return ChatRequest(
        messages=(
            ChatMessage(
                role=MessageRole.USER,
                content="offline transport gate fixture",
            ),
        ),
        temperature=0.2,
        timeout_s=10.0,
    )


def run_offline_transport_gate_case(
    phase: str,
) -> tuple[CandidateCloseWakeObservation, TransportGateMetrics]:
    """Run one zero-network case through OpenAI SDK → Zhipu adapter."""

    if phase not in _GATE_PHASES:
        raise CandidateTransportGateError("gate_phase_invalid", "gate_phase")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=httpx.ByteStream(_FIXTURE_BYTES),
            request=request,
        )

    transport = GateTransport(httpx.MockTransport(handler), phase=phase)
    http_client = httpx.Client(transport=transport, timeout=10.0)
    sdk_client = OpenAI(
        api_key="offline-fixture-key",
        base_url="https://offline.invalid/v4",
        http_client=http_client,
        max_retries=0,
        timeout=10.0,
    )
    provider = ZhipuProvider(
        client=sdk_client,
        model=TRANSPORT_GATE_MODEL,
        profile=resolve_zhipu_thinking_profile(TRANSPORT_GATE_MODEL),
    )
    adapter = provider.stream_adapter(tool_stream=False)
    request = _fixture_request()
    calls = 0

    def session_factory(
        supplied_request: ChatRequest | None = None,
        *,
        include_usage_tail: bool = False,
    ):
        nonlocal calls
        if calls != 0 or supplied_request is not request:
            raise CandidateTransportGateError("offline_call_budget_exceeded", "session")
        if include_usage_tail is not True:
            raise CandidateTransportGateError("usage_tail_required", "request")
        calls = 1
        return adapter.stream_session(
            supplied_request,
            include_usage_tail=True,
        )

    try:
        observation = observe_candidate_session(
            session_factory,
            request=request,
            initial_read_timeout_s=0.5,
            cancel_timeout_s=2.0,
            reader_grace_s=1.0,
        )
        metrics = transport.metrics
    finally:
        sdk_client.close()
    if calls != 1:
        raise CandidateTransportGateError("offline_call_count_invalid", "provider_call_count")
    return observation, metrics


def _close_report_dict(value: object) -> dict[str, object]:
    try:
        projection = CloseReportProjection.from_value(value)
    except CandidateCloseWakeObservationError:
        raise CandidateTransportGateError("close_report_shape", "close_report") from None
    return projection.as_dict()


def _conclusion(observation: CandidateCloseWakeObservation) -> str:
    if not observation.pending_reader_observed:
        return "not_pending"
    if not observation.reader_woke:
        return "client_wakeup_not_observed"
    try:
        close_report = CloseReportProjection.from_value(observation.close_report)
    except CandidateCloseWakeObservationError:
        raise CandidateTransportGateError("close_report_shape", "close_report") from None
    if observation.cancel_status == "returned" and close_report.composite_state == "closed":
        return "client_wakeup_clean"
    return "client_wakeup_close_race"


@dataclass(frozen=True, slots=True)
class CandidateTransportGateCase:
    """Stable, body-free projection of one fixture run."""

    case_id: str
    gate_phase: str
    observation_state: str
    pending_reader_observed: bool
    cancel_status: str
    cancel_returned: bool
    reader_woke: bool
    event_categories: tuple[str, ...]
    close_report: Mapping[str, object]
    upstream_event_seen: bool
    gate_entered: bool
    gate_released: bool
    downstream_close_seen: bool
    upstream_stream_close_seen: bool
    transport_request_count: int
    conclusion: str
    passed: bool

    def __post_init__(self) -> None:
        _safe_id(self.case_id, "case_id")
        if self.gate_phase not in _GATE_PHASES:
            raise CandidateTransportGateError("gate_phase_invalid", "gate_phase")
        if self.observation_state not in {
            CloseWakeState.NOT_PENDING.value,
            CloseWakeState.PENDING_CANCEL_RETURNED.value,
            CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
        }:
            raise CandidateTransportGateError("observation_state_invalid", "observation_state")
        for field_name in (
            "pending_reader_observed",
            "cancel_returned",
            "reader_woke",
            "upstream_event_seen",
            "gate_entered",
            "gate_released",
            "downstream_close_seen",
            "upstream_stream_close_seen",
            "passed",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise CandidateTransportGateError("lifecycle_value_invalid", field_name)
        if self.cancel_status not in {"not_attempted", "returned", "raised", "timeout"}:
            raise CandidateTransportGateError("cancel_status_invalid", "cancel_status")
        if not isinstance(self.event_categories, tuple) or any(
            not isinstance(category, str) or category not in _EVENT_CATEGORIES
            for category in self.event_categories
        ):
            raise CandidateTransportGateError("event_categories_invalid", "event_categories")
        if len(set(self.event_categories)) != len(self.event_categories):
            raise CandidateTransportGateError("event_categories_duplicate", "event_categories")
        if not isinstance(self.close_report, Mapping) or set(self.close_report) != _CLOSE_REPORT_KEYS:
            raise CandidateTransportGateError("close_report_shape", "close_report")
        try:
            close_report = CloseReportProjection.from_value(self.close_report)
        except CandidateCloseWakeObservationError:
            raise CandidateTransportGateError("close_report_shape", "close_report") from None
        object.__setattr__(self, "close_report", close_report.as_dict())
        if (
            isinstance(self.transport_request_count, bool)
            or not isinstance(self.transport_request_count, int)
            or self.transport_request_count != 1
        ):
            raise CandidateTransportGateError("request_count_invalid", "transport_request_count")
        if self.conclusion not in _CONCLUSIONS:
            raise CandidateTransportGateError("conclusion_invalid", "conclusion")
        expected_categories = (
            ("reasoning_seen", "content_seen")
            if self.gate_phase == "after_first_event"
            else ()
        )
        expected_pass = (
            self.transport_request_count == 1
            and self.downstream_close_seen
            and self.upstream_stream_close_seen
            and self.gate_entered
            and not self.gate_released
            and self.upstream_event_seen
            and self.pending_reader_observed
            and self.reader_woke
            and self.event_categories == expected_categories
        )
        if self.passed is not expected_pass:
            raise CandidateTransportGateError("pass_projection_invalid", "passed")

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "gate_phase": self.gate_phase,
            "observation_state": self.observation_state,
            "pending_reader_observed": self.pending_reader_observed,
            "cancel_status": self.cancel_status,
            "cancel_returned": self.cancel_returned,
            "reader_woke": self.reader_woke,
            "event_categories": list(self.event_categories),
            "close_report": dict(self.close_report),
            "upstream_event_seen": self.upstream_event_seen,
            "gate_entered": self.gate_entered,
            "gate_released": self.gate_released,
            "downstream_close_seen": self.downstream_close_seen,
            "upstream_stream_close_seen": self.upstream_stream_close_seen,
            "transport_request_count": self.transport_request_count,
            "conclusion": self.conclusion,
            "passed": self.passed,
        }


def project_transport_gate_case(
    case_id: str,
    phase: str,
    observation: CandidateCloseWakeObservation,
    metrics: TransportGateMetrics,
) -> CandidateTransportGateCase:
    if phase not in _GATE_PHASES:
        raise CandidateTransportGateError("gate_phase_invalid", "gate_phase")
    if not isinstance(observation, CandidateCloseWakeObservation):
        raise CandidateTransportGateError("observation_type_invalid", "observation")
    conclusion = _conclusion(observation)
    expected = (
        metrics.transport_request_count == 1
        and metrics.downstream_close_seen
        and metrics.upstream_stream_close_seen
        and metrics.gate_entered
        and not metrics.gate_released
        and observation.pending_reader_observed
        and observation.reader_woke
    )
    # ``upstream_event_seen`` means the gate consumed a complete frame from
    # the inner transport.  In the before-first phase that frame is already
    # buffered inside the gate but has not been exposed to the SDK, so the
    # phase is distinguished by the observer's event-category projection.
    expected = expected and metrics.upstream_event_seen
    expected_categories = (
        ("reasoning_seen", "content_seen") if phase == "after_first_event" else ()
    )
    expected = expected and tuple(observation.event_categories) == expected_categories
    return CandidateTransportGateCase(
        case_id=case_id,
        gate_phase=phase,
        observation_state=observation.observation_state,
        pending_reader_observed=observation.pending_reader_observed,
        cancel_status=observation.cancel_status,
        cancel_returned=observation.cancel_returned,
        reader_woke=observation.reader_woke,
        event_categories=tuple(observation.event_categories),
        close_report=_close_report_dict(observation.close_report),
        upstream_event_seen=metrics.upstream_event_seen,
        gate_entered=metrics.gate_entered,
        gate_released=metrics.gate_released,
        downstream_close_seen=metrics.downstream_close_seen,
        upstream_stream_close_seen=metrics.upstream_stream_close_seen,
        transport_request_count=metrics.transport_request_count,
        conclusion=conclusion,
        passed=expected,
    )


@dataclass(frozen=True, slots=True)
class CandidateTransportGateReceipt:
    """Immutable offline receipt with no provider response material."""

    implementation_sha: str
    observer_code_sha: str
    input_plan_sha: str
    fixture_sha256: str
    cases: tuple[CandidateTransportGateCase, ...]
    evidence_origin: str = TRANSPORT_GATE_EVIDENCE_ORIGIN
    real_provider_observed: bool = False
    provider_call_count: int = 0
    network_used: bool = False
    schema_version: str = CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION
    protocol_id: str = CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION:
            raise CandidateTransportGateError("schema_version_invalid", "schema_version")
        if self.protocol_id != CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID:
            raise CandidateTransportGateError("protocol_id_invalid", "protocol_id")
        if self.evidence_origin != TRANSPORT_GATE_EVIDENCE_ORIGIN:
            raise CandidateTransportGateError("evidence_origin_invalid", "evidence_origin")
        if self.real_provider_observed is not False or self.network_used is not False:
            raise CandidateTransportGateError("offline_flags_invalid", "evidence_origin")
        if (
            isinstance(self.provider_call_count, bool)
            or not isinstance(self.provider_call_count, int)
            or self.provider_call_count != 0
        ):
            raise CandidateTransportGateError("provider_call_count_invalid", "provider_call_count")
        _safe_sha(self.implementation_sha, "implementation_sha")
        _safe_sha(self.observer_code_sha, "observer_code_sha")
        _safe_sha(self.input_plan_sha, "input_plan_sha")
        _safe_sha256(self.fixture_sha256, "fixture_sha256")
        if self.fixture_sha256 != _FIXTURE_SHA256:
            raise CandidateTransportGateError("fixture_digest_mismatch", "fixture_sha256")
        if not isinstance(self.cases, tuple) or any(
            not isinstance(case, CandidateTransportGateCase) for case in self.cases
        ):
            raise CandidateTransportGateError("case_type_invalid", "cases")
        actual_cases = tuple((case.case_id, case.gate_phase) for case in self.cases)
        if actual_cases != _EXPECTED_CASES:
            raise CandidateTransportGateError("case_order_invalid", "cases")

    @property
    def all_cases_passed(self) -> bool:
        return all(case.passed for case in self.cases)

    def as_dict(self) -> dict[str, object]:
        value = {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "evidence_origin": self.evidence_origin,
            "real_provider_observed": self.real_provider_observed,
            "provider_call_count": self.provider_call_count,
            "network_used": self.network_used,
            "implementation_sha": self.implementation_sha,
            "observer_code_sha": self.observer_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "fixture_sha256": self.fixture_sha256,
            "cases": [case.as_dict() for case in self.cases],
            "all_cases_passed": self.all_cases_passed,
        }
        _assert_no_forbidden_keys(value)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateTransportGateReceipt":
        if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
            raise CandidateTransportGateError("receipt_fields_invalid", "receipt")
        _assert_no_forbidden_keys(value)
        raw_cases = value.get("cases")
        if isinstance(raw_cases, (str, bytes)) or not isinstance(raw_cases, list):
            raise CandidateTransportGateError("cases_shape_invalid", "cases")
        cases: list[CandidateTransportGateCase] = []
        for raw in raw_cases:
            if not isinstance(raw, Mapping) or set(raw) != _CASE_KEYS:
                raise CandidateTransportGateError("case_fields_invalid", "case")
            try:
                case_values = dict(raw)
                categories = case_values.get("event_categories")
                if isinstance(categories, list):
                    case_values["event_categories"] = tuple(categories)
                cases.append(CandidateTransportGateCase(**case_values))
            except CandidateTransportGateError:
                raise
            except (TypeError, ValueError):
                raise CandidateTransportGateError("case_shape_invalid", "case") from None
        try:
            receipt = cls(
                implementation_sha=value["implementation_sha"],
                observer_code_sha=value["observer_code_sha"],
                input_plan_sha=value["input_plan_sha"],
                fixture_sha256=value["fixture_sha256"],
                cases=tuple(cases),
                evidence_origin=value["evidence_origin"],
                real_provider_observed=value["real_provider_observed"],
                provider_call_count=value["provider_call_count"],
                network_used=value["network_used"],
                schema_version=value["schema_version"],
                protocol_id=value["protocol_id"],
            )
        except CandidateTransportGateError:
            raise
        except (TypeError, ValueError):
            raise CandidateTransportGateError("receipt_shape_invalid", "receipt") from None
        if value["all_cases_passed"] is not receipt.all_cases_passed:
            raise CandidateTransportGateError("pass_projection_invalid", "all_cases_passed")
        return receipt


def run_offline_transport_gate_replay(
    *,
    implementation_sha: str,
    observer_code_sha: str,
    input_plan_sha: str,
) -> CandidateTransportGateReceipt:
    """Run both deterministic gate phases without network or credentials."""

    cases: list[CandidateTransportGateCase] = []
    for case_id, phase in _EXPECTED_CASES:
        observation, metrics = run_offline_transport_gate_case(phase)
        cases.append(project_transport_gate_case(case_id, phase, observation, metrics))
    return CandidateTransportGateReceipt(
        implementation_sha=implementation_sha,
        observer_code_sha=observer_code_sha,
        input_plan_sha=input_plan_sha,
        fixture_sha256=_FIXTURE_SHA256,
        cases=tuple(cases),
    )


def write_candidate_transport_gate_receipt(
    path: str | Path,
    receipt: CandidateTransportGateReceipt,
    *,
    offline_root: str | Path,
) -> Path:
    """Write one canonical receipt below a dedicated offline directory."""

    if not isinstance(receipt, CandidateTransportGateReceipt):
        raise CandidateTransportGateError("receipt_type_invalid", "receipt")
    target = Path(path)
    allowed = Path(offline_root).resolve()
    try:
        resolved = target.resolve()
        resolved.relative_to(allowed)
    except (OSError, ValueError):
        raise CandidateTransportGateError("output_path_invalid", "output") from None
    if resolved.suffix.lower() != ".json":
        raise CandidateTransportGateError("output_path_invalid", "output")
    if target.exists() or target.is_symlink():
        raise FileExistsError("candidate transport-gate evidence is immutable")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json(receipt.as_dict())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    binary_flag = getattr(os, "O_BINARY", 0)
    fd = os.open(target, flags | binary_flag, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd != -1:
            os.close(fd)
    return target


__all__ = [
    "CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID",
    "CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION",
    "CandidateTransportGateCase",
    "CandidateTransportGateError",
    "CandidateTransportGateReceipt",
    "GateTransport",
    "TRANSPORT_GATE_EVIDENCE_ORIGIN",
    "TRANSPORT_GATE_MODEL",
    "TransportGateMetrics",
    "candidate_transport_gate_fixture_sha256",
    "project_transport_gate_case",
    "run_offline_transport_gate_case",
    "run_offline_transport_gate_replay",
    "write_candidate_transport_gate_receipt",
]
