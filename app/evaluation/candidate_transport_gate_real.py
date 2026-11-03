"""Body-free contract for one real candidate transport-gate observation.

The offline transport-gate precheck deliberately has a different receipt
contract.  This module is the small, explicit bridge for a *single* real
request sent through the official HTTPS transport.  It only projects safe
state from the existing close/wakeup observer and the local gate metrics;
provider payloads, request objects, headers, identifiers and credentials are
never retained.

This is evaluation-only code.  It does not register a provider, enable
streaming, change the product runtime, or provide retry/recovery behavior.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from re import fullmatch
from typing import Any

from .candidate_provider_close_wakeup_observation import (
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    CloseReportProjection,
    CloseWakeState,
)
from .candidate_transport_gate import (
    GateTransport,
    TransportGateMetrics,
)


REAL_TRANSPORT_GATE_PROTOCOL_ID = (
    "glm-5.3-flash-candidate-transport-gated-real-observation"
)
REAL_TRANSPORT_GATE_SCHEMA_VERSION = "1.0.0"
REAL_TRANSPORT_GATE_EVIDENCE_ORIGIN = "real_zhipu_https_transport_gate"
REAL_TRANSPORT_GATE_PROVIDER = "zhipu"
REAL_TRANSPORT_GATE_MODEL = "glm-5.3-flash"
REAL_TRANSPORT_GATE_PHASES = frozenset(
    {"before_first_event", "after_first_event"}
)

_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SAFE_CODE_PATTERN = r"^[a-z][a-z0-9_.-]{0,95}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_CLOSE_REPORT_KEYS = frozenset(
    {"iterator_state", "sdk_stream_state", "composite_state", "shared_resource"}
)
_CLOSE_STATES = frozenset({"not_observed", "open", "closed", "failed"})
_EVENT_CATEGORIES = frozenset(
    {"reasoning_seen", "content_seen", "terminal_seen", "usage_seen", "tool_seen"}
)
_OBSERVATION_STATES = frozenset(
    {
        CloseWakeState.NOT_PENDING.value,
        CloseWakeState.PENDING_CANCEL_RETURNED.value,
        CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
        CloseWakeState.CHILD_TIMEOUT.value,
        CloseWakeState.CHILD_ERROR.value,
    }
)
_CANCEL_STATUSES = frozenset(
    {"not_attempted", "returned", "raised", "timeout"}
)
_CONCLUSIONS = frozenset(
    {
        "client_wakeup_clean",
        "client_wakeup_close_race",
        "client_wakeup_not_observed",
        "not_pending",
        "transport_gate_observed",
        "child_timeout",
        "child_error",
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


class CandidateRealTransportGateError(ValueError):
    """Machine-safe validation error for the real observation contract."""

    def __init__(self, code: str, field_name: str | None = None) -> None:
        if not isinstance(code, str) or fullmatch(_SAFE_CODE_PATTERN, code) is None:
            code = "real_transport_gate_contract_error"
        self.code = code
        self.field_name = field_name
        super().__init__(code)


def _safe_code(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SAFE_CODE_PATTERN, value) is None:
        raise CandidateRealTransportGateError("unsafe_code", field_name)
    return value


def _sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA_PATTERN, value) is None:
        raise CandidateRealTransportGateError("invalid_git_sha", field_name)
    return value


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA256_PATTERN, value) is None:
        raise CandidateRealTransportGateError("invalid_sha256", field_name)
    return value


def _bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise CandidateRealTransportGateError("invalid_boolean", field_name)
    return value


def _count(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in {0, 1}:
        raise CandidateRealTransportGateError("invalid_call_count", field_name)
    return value


def _duration(value: object, field_name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > 120_000
    ):
        raise CandidateRealTransportGateError("invalid_duration", field_name)
    return value


def _optional_duration(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    return _duration(value, field_name)


def _optional_exit_code(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < -1_000_000
        or value > 1_000_000
    ):
        raise CandidateRealTransportGateError("invalid_child_exit", field_name)
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
        raise CandidateRealTransportGateError("json_not_serializable", "serialize") from None


def _assert_no_forbidden_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise CandidateRealTransportGateError("receipt_field_forbidden", "serialize")
            _assert_no_forbidden_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_no_forbidden_keys(item)


def _close_report(value: object) -> dict[str, object]:
    try:
        projection = CloseReportProjection.from_value(value)
    except CandidateCloseWakeObservationError:
        raise CandidateRealTransportGateError("close_report_shape", "close_report") from None
    return projection.as_dict()


def _observation_projection(
    observation: Mapping[str, object],
) -> dict[str, object]:
    expected = {
        "observation_state",
        "session_opened",
        "pending_reader_observed",
        "cancel_status",
        "cancel_returned",
        "reader_woke",
        "event_categories",
        "initial_read_elapsed_ms",
        "cancel_elapsed_ms",
        "reader_grace_ms",
        "reader_wake_elapsed_ms",
        "close_report",
        "error_code",
        "child_exit_code",
        "child_terminated",
    }
    if set(observation) != expected:
        raise CandidateRealTransportGateError("observation_fields_invalid", "observation")
    state = observation["observation_state"]
    if state not in _OBSERVATION_STATES:
        raise CandidateRealTransportGateError("observation_state_invalid", "observation_state")
    cancel_status = observation["cancel_status"]
    if cancel_status not in _CANCEL_STATUSES:
        raise CandidateRealTransportGateError("cancel_status_invalid", "cancel_status")
    categories = observation["event_categories"]
    if not isinstance(categories, list) or any(
        not isinstance(item, str) or item not in _EVENT_CATEGORIES for item in categories
    ):
        raise CandidateRealTransportGateError("event_categories_invalid", "event_categories")
    if len(set(categories)) != len(categories):
        raise CandidateRealTransportGateError("event_categories_duplicate", "event_categories")
    error_code = observation["error_code"]
    if error_code is not None:
        _safe_code(error_code, "error_code")
    projected = {
        "observation_state": state,
        "session_opened": _bool(observation["session_opened"], "session_opened"),
        "pending_reader_observed": _bool(
            observation["pending_reader_observed"], "pending_reader_observed"
        ),
        "cancel_status": cancel_status,
        "cancel_returned": _bool(observation["cancel_returned"], "cancel_returned"),
        "reader_woke": _bool(observation["reader_woke"], "reader_woke"),
        "event_categories": list(categories),
        "initial_read_elapsed_ms": _duration(
            observation["initial_read_elapsed_ms"], "initial_read_elapsed_ms"
        ),
        "cancel_elapsed_ms": _optional_duration(
            observation["cancel_elapsed_ms"], "cancel_elapsed_ms"
        ),
        "reader_grace_ms": _duration(observation["reader_grace_ms"], "reader_grace_ms"),
        "reader_wake_elapsed_ms": _optional_duration(
            observation["reader_wake_elapsed_ms"], "reader_wake_elapsed_ms"
        ),
        "close_report": _close_report(observation["close_report"]),
        "error_code": error_code,
        "child_exit_code": _optional_exit_code(
            observation["child_exit_code"], "child_exit_code"
        ),
        "child_terminated": _bool(observation["child_terminated"], "child_terminated"),
    }
    return projected


def _transport_projection(metrics: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "upstream_event_seen",
        "gate_entered",
        "gate_released",
        "downstream_close_seen",
        "upstream_stream_close_seen",
        "transport_request_count",
    }
    if set(metrics) != expected:
        raise CandidateRealTransportGateError("transport_fields_invalid", "transport")
    return {
        "upstream_event_seen": _bool(metrics["upstream_event_seen"], "upstream_event_seen"),
        "gate_entered": _bool(metrics["gate_entered"], "gate_entered"),
        "gate_released": _bool(metrics["gate_released"], "gate_released"),
        "downstream_close_seen": _bool(
            metrics["downstream_close_seen"], "downstream_close_seen"
        ),
        "upstream_stream_close_seen": _bool(
            metrics["upstream_stream_close_seen"], "upstream_stream_close_seen"
        ),
        "transport_request_count": _count(
            metrics["transport_request_count"], "transport_request_count"
        ),
    }


def _conclusion(observation: Mapping[str, object], transport: Mapping[str, object]) -> str:
    state = observation["observation_state"]
    if state == CloseWakeState.CHILD_TIMEOUT.value:
        return "child_timeout"
    if state == CloseWakeState.CHILD_ERROR.value:
        return "child_error"
    if not transport["gate_entered"]:
        return "transport_gate_observed" if transport["upstream_event_seen"] else "client_wakeup_not_observed"
    if not observation["pending_reader_observed"]:
        return "not_pending"
    if not observation["reader_woke"]:
        return "client_wakeup_not_observed"
    report = observation["close_report"]
    if observation["cancel_status"] == "returned" and report["composite_state"] == "closed":
        return "client_wakeup_clean"
    return "client_wakeup_close_race"


@dataclass(frozen=True, slots=True)
class CandidateRealTransportGateReceipt:
    """Canonical, body-free projection of one real gated request."""

    implementation_sha: str
    observer_code_sha: str
    input_plan_sha: str
    gate_phase: str
    process_deadline_ms: int
    observation: Mapping[str, object]
    transport: Mapping[str, object]
    provider_call_count: int
    network_used: bool
    real_provider_observed: bool
    schema_version: str = REAL_TRANSPORT_GATE_SCHEMA_VERSION
    protocol_id: str = REAL_TRANSPORT_GATE_PROTOCOL_ID
    evidence_origin: str = REAL_TRANSPORT_GATE_EVIDENCE_ORIGIN
    provider_id: str = REAL_TRANSPORT_GATE_PROVIDER
    model: str = REAL_TRANSPORT_GATE_MODEL

    def __post_init__(self) -> None:
        _sha(self.implementation_sha, "implementation_sha")
        _sha(self.observer_code_sha, "observer_code_sha")
        _sha(self.input_plan_sha, "input_plan_sha")
        if self.schema_version != REAL_TRANSPORT_GATE_SCHEMA_VERSION:
            raise CandidateRealTransportGateError("schema_version_invalid", "schema_version")
        if self.protocol_id != REAL_TRANSPORT_GATE_PROTOCOL_ID:
            raise CandidateRealTransportGateError("protocol_id_invalid", "protocol_id")
        if self.evidence_origin != REAL_TRANSPORT_GATE_EVIDENCE_ORIGIN:
            raise CandidateRealTransportGateError("evidence_origin_invalid", "evidence_origin")
        if self.provider_id != REAL_TRANSPORT_GATE_PROVIDER:
            raise CandidateRealTransportGateError("provider_id_invalid", "provider_id")
        if self.model != REAL_TRANSPORT_GATE_MODEL:
            raise CandidateRealTransportGateError("model_invalid", "model")
        if self.gate_phase not in REAL_TRANSPORT_GATE_PHASES:
            raise CandidateRealTransportGateError("gate_phase_invalid", "gate_phase")
        if (
            isinstance(self.process_deadline_ms, bool)
            or not isinstance(self.process_deadline_ms, int)
            or self.process_deadline_ms < 1_000
            or self.process_deadline_ms > 30_000
        ):
            raise CandidateRealTransportGateError("deadline_invalid", "process_deadline_ms")
        projected_observation = _observation_projection(self.observation)
        projected_transport = _transport_projection(self.transport)
        object.__setattr__(self, "observation", projected_observation)
        object.__setattr__(self, "transport", projected_transport)
        _count(self.provider_call_count, "provider_call_count")
        _bool(self.network_used, "network_used")
        _bool(self.real_provider_observed, "real_provider_observed")
        if self.network_used is not (projected_transport["transport_request_count"] > 0):
            raise CandidateRealTransportGateError("network_flag_invalid", "network_used")
        if self.real_provider_observed is not (self.provider_call_count > 0):
            raise CandidateRealTransportGateError(
                "provider_observed_flag_invalid", "real_provider_observed"
            )
        if self.provider_call_count != projected_transport["transport_request_count"]:
            raise CandidateRealTransportGateError("call_count_mismatch", "provider_call_count")
        conclusion = _conclusion(projected_observation, projected_transport)
        if conclusion not in _CONCLUSIONS:
            raise CandidateRealTransportGateError("conclusion_invalid", "conclusion")

    @property
    def conclusion(self) -> str:
        return _conclusion(self.observation, self.transport)

    @property
    def gate_observation_valid(self) -> bool:
        transport = self.transport
        return bool(
            self.provider_call_count == 1
            and self.network_used
            and transport["transport_request_count"] == 1
            and transport["upstream_event_seen"]
            and transport["gate_entered"]
            and not transport["gate_released"]
            and transport["downstream_close_seen"]
            and transport["upstream_stream_close_seen"]
        )

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "evidence_origin": self.evidence_origin,
            "real_provider_observed": self.real_provider_observed,
            "provider_id": self.provider_id,
            "model": self.model,
            "gate_phase": self.gate_phase,
            "provider_call_count": self.provider_call_count,
            "network_used": self.network_used,
            "transport_request_count": self.transport["transport_request_count"],
            "implementation_sha": self.implementation_sha,
            "observer_code_sha": self.observer_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "process_deadline_ms": self.process_deadline_ms,
            "observation": dict(self.observation),
            "transport": dict(self.transport),
            "conclusion": self.conclusion,
            "gate_observation_valid": self.gate_observation_valid,
        }
        _assert_no_forbidden_keys(value)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateRealTransportGateReceipt":
        expected = {
            "schema_version",
            "protocol_id",
            "evidence_origin",
            "real_provider_observed",
            "provider_id",
            "model",
            "gate_phase",
            "provider_call_count",
            "network_used",
            "transport_request_count",
            "implementation_sha",
            "observer_code_sha",
            "input_plan_sha",
            "process_deadline_ms",
            "observation",
            "transport",
            "conclusion",
            "gate_observation_valid",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise CandidateRealTransportGateError("receipt_fields_invalid", "receipt")
        _assert_no_forbidden_keys(value)
        observation = value["observation"]
        transport = value["transport"]
        if not isinstance(observation, Mapping) or not isinstance(transport, Mapping):
            raise CandidateRealTransportGateError("nested_shape_invalid", "receipt")
        receipt = cls(
            implementation_sha=value["implementation_sha"],
            observer_code_sha=value["observer_code_sha"],
            input_plan_sha=value["input_plan_sha"],
            gate_phase=value["gate_phase"],
            process_deadline_ms=value["process_deadline_ms"],
            observation=observation,
            transport=transport,
            provider_call_count=value["provider_call_count"],
            network_used=value["network_used"],
            real_provider_observed=value["real_provider_observed"],
            schema_version=value["schema_version"],
            protocol_id=value["protocol_id"],
            evidence_origin=value["evidence_origin"],
            provider_id=value["provider_id"],
            model=value["model"],
        )
        if value["transport_request_count"] != receipt.transport["transport_request_count"]:
            raise CandidateRealTransportGateError("transport_count_mismatch", "transport_request_count")
        if value["conclusion"] != receipt.conclusion:
            raise CandidateRealTransportGateError("conclusion_mismatch", "conclusion")
        if value["gate_observation_valid"] is not receipt.gate_observation_valid:
            raise CandidateRealTransportGateError("validity_mismatch", "gate_observation_valid")
        return receipt


def build_real_transport_gate_receipt(
    *,
    implementation_sha: str,
    observer_code_sha: str,
    input_plan_sha: str,
    gate_phase: str,
    process_deadline_ms: int,
    observation: CandidateCloseWakeObservation | Mapping[str, object],
    metrics: TransportGateMetrics | Mapping[str, object],
    provider_call_count: int,
) -> CandidateRealTransportGateReceipt:
    """Project a child observation and gate metrics into the strict receipt."""

    if isinstance(observation, CandidateCloseWakeObservation):
        raw_observation = observation.as_dict()
    elif isinstance(observation, Mapping):
        raw_observation = dict(observation)
    else:
        raise CandidateRealTransportGateError("observation_type_invalid", "observation")
    if isinstance(metrics, TransportGateMetrics):
        raw_metrics = metrics.as_dict()
    elif isinstance(metrics, Mapping):
        raw_metrics = dict(metrics)
    else:
        raise CandidateRealTransportGateError("transport_type_invalid", "transport")
    # The child protocol may carry the historical observer identity and its
    # local call counter.  They are deliberately not part of this newer
    # transport-gate receipt; the parent records the normalized counters at
    # the top level instead.
    for key in ("schema_version", "protocol_id", "call_count"):
        raw_observation.pop(key, None)
    return CandidateRealTransportGateReceipt(
        implementation_sha=implementation_sha,
        observer_code_sha=observer_code_sha,
        input_plan_sha=input_plan_sha,
        gate_phase=gate_phase,
        process_deadline_ms=process_deadline_ms,
        observation=raw_observation,
        transport=raw_metrics,
        provider_call_count=provider_call_count,
        network_used=raw_metrics.get("transport_request_count") == 1,
        real_provider_observed=provider_call_count == 1,
    )


def write_real_transport_gate_receipt(
    path: str | Path,
    receipt: CandidateRealTransportGateReceipt,
    *,
    results_root: str | Path,
) -> Path:
    """Write one canonical receipt below the explicit capability result root."""

    if not isinstance(receipt, CandidateRealTransportGateReceipt):
        raise CandidateRealTransportGateError("receipt_type_invalid", "receipt")
    target = Path(path)
    allowed = Path(results_root).resolve()
    try:
        resolved = target.resolve()
        resolved.relative_to(allowed)
    except (OSError, ValueError):
        raise CandidateRealTransportGateError("output_path_invalid", "output") from None
    if resolved.suffix.lower() != ".json":
        raise CandidateRealTransportGateError("output_path_invalid", "output")
    if target.exists() or target.is_symlink():
        raise FileExistsError("real transport-gate evidence is immutable")
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


def safe_child_observation(code: str, *, terminated: bool = False) -> dict[str, object]:
    """Return a body-free fallback projection for a child setup/timeout error."""

    _safe_code(code, "error_code")
    return {
        "observation_state": (
            CloseWakeState.CHILD_TIMEOUT.value
            if code == "child_timeout"
            else CloseWakeState.CHILD_ERROR.value
        ),
        "session_opened": False,
        "pending_reader_observed": False,
        "cancel_status": "not_attempted",
        "cancel_returned": False,
        "reader_woke": False,
        "event_categories": [],
        "initial_read_elapsed_ms": 0,
        "cancel_elapsed_ms": None,
        "reader_grace_ms": 0,
        "reader_wake_elapsed_ms": None,
        "close_report": {
            "iterator_state": "not_observed",
            "sdk_stream_state": "not_observed",
            "composite_state": "not_observed",
            "shared_resource": False,
        },
        "error_code": code,
        "child_exit_code": None,
        "child_terminated": terminated,
    }


def default_transport_metrics() -> dict[str, object]:
    """Return a safe zero-call metrics projection for setup failures."""

    return {
        "upstream_event_seen": False,
        "gate_entered": False,
        "gate_released": False,
        "downstream_close_seen": False,
        "upstream_stream_close_seen": False,
        "transport_request_count": 0,
    }


__all__ = [
    "CandidateRealTransportGateError",
    "CandidateRealTransportGateReceipt",
    "REAL_TRANSPORT_GATE_EVIDENCE_ORIGIN",
    "REAL_TRANSPORT_GATE_MODEL",
    "REAL_TRANSPORT_GATE_PHASES",
    "REAL_TRANSPORT_GATE_PROTOCOL_ID",
    "REAL_TRANSPORT_GATE_PROVIDER",
    "REAL_TRANSPORT_GATE_SCHEMA_VERSION",
    "build_real_transport_gate_receipt",
    "default_transport_metrics",
    "safe_child_observation",
    "write_real_transport_gate_receipt",
]
