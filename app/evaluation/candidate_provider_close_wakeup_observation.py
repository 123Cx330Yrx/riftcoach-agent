"""Body-free close/wakeup observation for the GLM-5.3 candidate.

This module is an evaluation-only seam.  It owns neither the product
provider registry nor an AgentLoop policy.  A caller supplies one explicit
stream-session factory; the seam can open that factory at most once, observe
only normalized event categories, and measure a bounded cancel/read wake
window.  A parent process helper provides the hard boundary needed when a
vendor SDK blocks in a synchronous iterator or close hook.

No provider response body, exception text, request identifier, header, or
credential is retained by the value objects or written to a receipt.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from re import fullmatch
from typing import Any, Literal, Protocol, TypeAlias

from app.providers.stream_adapter_contract import ProviderStreamEvent


CANDIDATE_CLOSE_WAKE_PROTOCOL_ID = (
    "glm-5.3-flash-candidate-close-wakeup-observation"
)
CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION = "1.0.0"

_GIT_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SAFE_CODE_PATTERN = r"^[a-z][a-z0-9_.-]{0,95}$"
_MAX_DURATION_MS = 120_000
_MAX_GRACE_MS = 10_000
_MAX_EVENT_CATEGORIES = 16
_MAX_CHILD_EXIT_CODE = 1_000_000
_MAX_CAPTURE_BYTES = 16 * 1024
_PIPE_CHUNK_BYTES = 4096

_OBSERVATION_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "observation_state",
        "call_count",
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
)
_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "implementation_sha",
        "diagnostic_code_sha",
        "input_plan_sha",
        "observation",
    }
)
_CLOSE_REPORT_KEYS = frozenset(
    {
        "iterator_state",
        "sdk_stream_state",
        "composite_state",
        "shared_resource",
    }
)
_CLOSE_STATES = frozenset({"not_observed", "open", "closed", "failed"})
_EVENT_CATEGORIES = frozenset(
    {
        "reasoning_seen",
        "content_seen",
        "terminal_seen",
        "usage_seen",
        "tool_seen",
    }
)
_CANCEL_STATUSES = frozenset(
    {"not_attempted", "returned", "raised", "timeout"}
)


class CloseWakeState(StrEnum):
    """Safe outcome codes for the finite observation."""

    NOT_PENDING = "not_pending"
    PENDING_CANCEL_RETURNED = "pending_cancel_returned"
    PENDING_CANCEL_TIMEOUT = "pending_cancel_timeout"
    CHILD_TIMEOUT = "child_timeout"
    CHILD_ERROR = "child_error"


CloseWakeCancelStatus: TypeAlias = Literal[
    "not_attempted", "returned", "raised", "timeout"
]


class CandidateCloseWakeObservationError(ValueError):
    """Machine-safe validation error; provider text is never copied."""

    def __init__(self, code: str, field_name: str | None = None) -> None:
        if not isinstance(code, str) or fullmatch(_SAFE_CODE_PATTERN, code) is None:
            code = "observation_contract_error"
        self.code = code
        self.field_name = field_name
        super().__init__(code)


def _safe_code(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SAFE_CODE_PATTERN, value) is None:
        raise CandidateCloseWakeObservationError("unsafe_code", field_name)
    return value


def _sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_GIT_SHA_PATTERN, value) is None:
        raise CandidateCloseWakeObservationError("invalid_git_sha", field_name)
    return value


def _non_negative_ms(value: object, field_name: str, *, maximum: int = _MAX_DURATION_MS) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > maximum
    ):
        raise CandidateCloseWakeObservationError("invalid_duration", field_name)
    return value


def _optional_ms(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    return _non_negative_ms(value, field_name)


def _safe_child_exit(value: object) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < -_MAX_CHILD_EXIT_CODE
        or value > _MAX_CHILD_EXIT_CODE
    ):
        raise CandidateCloseWakeObservationError("invalid_child_exit", "child_exit_code")
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
        raise CandidateCloseWakeObservationError("json_not_serializable", "serialize") from None


def _assert_no_forbidden_keys(value: object) -> None:
    """Reject accidentally supplied body-like keys before serialization."""

    forbidden = {
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
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in forbidden:
                raise CandidateCloseWakeObservationError(
                    "receipt_field_forbidden", "serialize"
                )
            _assert_no_forbidden_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_no_forbidden_keys(item)


@dataclass(frozen=True, slots=True)
class CloseReportProjection:
    """The four safe fields exposed by ``ZhipuStreamCloseReport``."""

    iterator_state: str = "not_observed"
    sdk_stream_state: str = "not_observed"
    composite_state: str = "not_observed"
    shared_resource: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "iterator_state",
            "sdk_stream_state",
            "composite_state",
        ):
            value = getattr(self, field_name)
            if value not in _CLOSE_STATES:
                raise CandidateCloseWakeObservationError("close_state_invalid", field_name)
        if not isinstance(self.shared_resource, bool):
            raise CandidateCloseWakeObservationError("shared_resource_invalid", "close_report")
        if self.composite_state == "failed" and not (
            self.iterator_state == "failed" or self.sdk_stream_state == "failed"
        ):
            raise CandidateCloseWakeObservationError("close_state_invalid", "composite_state")
        if self.composite_state == "closed" and not (
            self.iterator_state == "closed" and self.sdk_stream_state == "closed"
        ):
            raise CandidateCloseWakeObservationError("close_state_invalid", "composite_state")

    @classmethod
    def from_value(cls, value: object) -> "CloseReportProjection":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        as_dict = getattr(value, "as_dict", None)
        if callable(as_dict):
            try:
                value = as_dict()
            except Exception:
                raise CandidateCloseWakeObservationError(
                    "close_report_unavailable", "close_report"
                ) from None
        if not isinstance(value, Mapping) or set(value) != _CLOSE_REPORT_KEYS:
            raise CandidateCloseWakeObservationError("close_report_shape", "close_report")
        return cls(
            iterator_state=value["iterator_state"],
            sdk_stream_state=value["sdk_stream_state"],
            composite_state=value["composite_state"],
            shared_resource=value["shared_resource"],
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "iterator_state": self.iterator_state,
            "sdk_stream_state": self.sdk_stream_state,
            "composite_state": self.composite_state,
            "shared_resource": self.shared_resource,
        }


def _normalize_categories(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise CandidateCloseWakeObservationError("event_categories_invalid", "event_categories")
    try:
        categories = tuple(value)
    except (TypeError, ValueError):
        raise CandidateCloseWakeObservationError("event_categories_invalid", "event_categories") from None
    if len(categories) > _MAX_EVENT_CATEGORIES:
        raise CandidateCloseWakeObservationError("event_categories_limit", "event_categories")
    if any(category not in _EVENT_CATEGORIES for category in categories):
        raise CandidateCloseWakeObservationError("event_category_invalid", "event_categories")
    if len(set(categories)) != len(categories):
        raise CandidateCloseWakeObservationError("event_categories_duplicate", "event_categories")
    return categories


@dataclass(frozen=True, slots=True)
class CandidateCloseWakeObservation:
    """One finite, body-free provider close/wakeup observation."""

    observation_state: str
    call_count: int
    session_opened: bool
    pending_reader_observed: bool
    cancel_status: CloseWakeCancelStatus
    cancel_returned: bool
    reader_woke: bool
    event_categories: tuple[str, ...] = ()
    initial_read_elapsed_ms: int = 0
    cancel_elapsed_ms: int | None = None
    reader_grace_ms: int = 0
    reader_wake_elapsed_ms: int | None = None
    close_report: CloseReportProjection | Mapping[str, object] | None = None
    error_code: str | None = None
    child_exit_code: int | None = None
    child_terminated: bool = False
    schema_version: str = CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION
    protocol_id: str = CANDIDATE_CLOSE_WAKE_PROTOCOL_ID

    def __post_init__(self) -> None:
        try:
            state = CloseWakeState(self.observation_state)
        except (TypeError, ValueError):
            raise CandidateCloseWakeObservationError("observation_state_invalid", "observation_state") from None
        object.__setattr__(self, "observation_state", state.value)
        if self.schema_version != CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION:
            raise CandidateCloseWakeObservationError("schema_version_invalid", "schema_version")
        if self.protocol_id != CANDIDATE_CLOSE_WAKE_PROTOCOL_ID:
            raise CandidateCloseWakeObservationError("protocol_id_invalid", "protocol_id")
        if (
            isinstance(self.call_count, bool)
            or not isinstance(self.call_count, int)
            or self.call_count not in {0, 1}
        ):
            raise CandidateCloseWakeObservationError("call_count_invalid", "call_count")
        for field_name in (
            "session_opened",
            "pending_reader_observed",
            "cancel_returned",
            "reader_woke",
            "child_terminated",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise CandidateCloseWakeObservationError("lifecycle_value_invalid", field_name)
        if self.session_opened and self.call_count != 1:
            raise CandidateCloseWakeObservationError("opened_call_count_mismatch", "call_count")
        if self.call_count == 0 and self.session_opened:
            raise CandidateCloseWakeObservationError("opened_call_count_mismatch", "session_opened")
        if self.cancel_status not in _CANCEL_STATUSES:
            raise CandidateCloseWakeObservationError("cancel_status_invalid", "cancel_status")
        expected_cancel_returned = self.cancel_status in {"returned", "raised"}
        if self.cancel_returned != expected_cancel_returned:
            raise CandidateCloseWakeObservationError("cancel_status_mismatch", "cancel_returned")
        if self.cancel_status == "raised" and self.error_code is None:
            raise CandidateCloseWakeObservationError("cancel_error_code_missing", "error_code")
        if state is CloseWakeState.NOT_PENDING:
            if self.pending_reader_observed or self.cancel_status != "not_attempted":
                raise CandidateCloseWakeObservationError("not_pending_lifecycle_invalid", "observation_state")
            if self.reader_woke:
                raise CandidateCloseWakeObservationError("reader_woke_without_pending", "reader_woke")
        elif state is CloseWakeState.PENDING_CANCEL_RETURNED:
            if not self.pending_reader_observed or not self.cancel_returned:
                raise CandidateCloseWakeObservationError("pending_return_lifecycle_invalid", "observation_state")
        elif state is CloseWakeState.PENDING_CANCEL_TIMEOUT:
            if not self.pending_reader_observed or self.cancel_status != "timeout":
                raise CandidateCloseWakeObservationError("pending_timeout_lifecycle_invalid", "observation_state")
            if self.reader_woke:
                raise CandidateCloseWakeObservationError("reader_woke_on_cancel_timeout", "reader_woke")
            if self.error_code != "cancel_timeout":
                raise CandidateCloseWakeObservationError("pending_timeout_error_invalid", "error_code")
        elif state is CloseWakeState.CHILD_TIMEOUT:
            if not self.child_terminated or self.error_code != "child_timeout":
                raise CandidateCloseWakeObservationError("child_timeout_lifecycle_invalid", "observation_state")
        elif state is CloseWakeState.CHILD_ERROR:
            if self.error_code is None or self.child_terminated:
                raise CandidateCloseWakeObservationError("child_error_lifecycle_invalid", "observation_state")
        if self.reader_woke and not self.pending_reader_observed:
            raise CandidateCloseWakeObservationError("reader_woke_without_pending", "reader_woke")
        _normalize_categories(self.event_categories)
        object.__setattr__(self, "event_categories", tuple(self.event_categories))
        _non_negative_ms(self.initial_read_elapsed_ms, "initial_read_elapsed_ms")
        _optional_ms(self.cancel_elapsed_ms, "cancel_elapsed_ms")
        _non_negative_ms(self.reader_grace_ms, "reader_grace_ms", maximum=_MAX_GRACE_MS)
        _optional_ms(self.reader_wake_elapsed_ms, "reader_wake_elapsed_ms")
        object.__setattr__(self, "close_report", CloseReportProjection.from_value(self.close_report))
        if self.error_code is not None:
            object.__setattr__(self, "error_code", _safe_code(self.error_code, "error_code"))
        object.__setattr__(self, "child_exit_code", _safe_child_exit(self.child_exit_code))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "observation_state": self.observation_state,
            "call_count": self.call_count,
            "session_opened": self.session_opened,
            "pending_reader_observed": self.pending_reader_observed,
            "cancel_status": self.cancel_status,
            "cancel_returned": self.cancel_returned,
            "reader_woke": self.reader_woke,
            "event_categories": list(self.event_categories),
            "initial_read_elapsed_ms": self.initial_read_elapsed_ms,
            "cancel_elapsed_ms": self.cancel_elapsed_ms,
            "reader_grace_ms": self.reader_grace_ms,
            "reader_wake_elapsed_ms": self.reader_wake_elapsed_ms,
            "close_report": self.close_report.as_dict(),  # type: ignore[union-attr]
            "error_code": self.error_code,
            "child_exit_code": self.child_exit_code,
            "child_terminated": self.child_terminated,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateCloseWakeObservation":
        if not isinstance(value, Mapping) or set(value) != _OBSERVATION_KEYS:
            raise CandidateCloseWakeObservationError("observation_fields_invalid", "observation")
        _assert_no_forbidden_keys(value)
        try:
            return cls(**dict(value))
        except CandidateCloseWakeObservationError:
            raise
        except (TypeError, ValueError):
            raise CandidateCloseWakeObservationError("observation_shape_invalid", "observation") from None


@dataclass(frozen=True, slots=True)
class CandidateCloseWakeReceipt:
    """Immutable envelope binding an observation to exact source SHAs."""

    implementation_sha: str
    diagnostic_code_sha: str
    input_plan_sha: str
    observation: CandidateCloseWakeObservation
    schema_version: str = CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION
    protocol_id: str = CANDIDATE_CLOSE_WAKE_PROTOCOL_ID

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION:
            raise CandidateCloseWakeObservationError("schema_version_invalid", "schema_version")
        if self.protocol_id != CANDIDATE_CLOSE_WAKE_PROTOCOL_ID:
            raise CandidateCloseWakeObservationError("protocol_id_invalid", "protocol_id")
        _sha(self.implementation_sha, "implementation_sha")
        _sha(self.diagnostic_code_sha, "diagnostic_code_sha")
        _sha(self.input_plan_sha, "input_plan_sha")
        if not isinstance(self.observation, CandidateCloseWakeObservation):
            raise CandidateCloseWakeObservationError("observation_type_invalid", "observation")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "implementation_sha": self.implementation_sha,
            "diagnostic_code_sha": self.diagnostic_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "observation": self.observation.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateCloseWakeReceipt":
        if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
            raise CandidateCloseWakeObservationError("receipt_fields_invalid", "receipt")
        _assert_no_forbidden_keys(value)
        try:
            observation = CandidateCloseWakeObservation.from_dict(value["observation"])
            return cls(
                implementation_sha=value["implementation_sha"],
                diagnostic_code_sha=value["diagnostic_code_sha"],
                input_plan_sha=value["input_plan_sha"],
                observation=observation,
                schema_version=value["schema_version"],
                protocol_id=value["protocol_id"],
            )
        except CandidateCloseWakeObservationError:
            raise
        except (TypeError, ValueError):
            raise CandidateCloseWakeObservationError("receipt_shape_invalid", "receipt") from None


def write_candidate_close_wakeup_receipt(
    path: str | Path,
    receipt: CandidateCloseWakeReceipt,
) -> Path:
    """Write one canonical receipt without permitting replacement."""

    if not isinstance(receipt, CandidateCloseWakeReceipt):
        raise CandidateCloseWakeObservationError("receipt_type_invalid", "receipt")
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise FileExistsError("candidate close/wakeup evidence is immutable")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = receipt.as_dict()
    _assert_no_forbidden_keys(payload)
    encoded = _canonical_json(payload)
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


def summarize_provider_event(event: ProviderStreamEvent) -> tuple[str, ...]:
    """Return only allow-listed booleans about one normalized event."""

    if not isinstance(event, ProviderStreamEvent):
        raise CandidateCloseWakeObservationError("event_type_invalid", "event")
    categories: list[str] = []
    if event.reasoning_delta is not None or event.reasoning_observed:
        categories.append("reasoning_seen")
    if event.content_delta is not None or event.content_observed:
        categories.append("content_seen")
    if event.finish_reason is not None:
        categories.append("terminal_seen")
    if event.usage is not None:
        categories.append("usage_seen")
    if event.tool_call_deltas:
        categories.append("tool_seen")
    return tuple(categories)


def _elapsed_ms(clock: Callable[[], float], started: float) -> int:
    value = max(0.0, clock() - started)
    # Avoid floating-point noise while retaining a conservative integer.
    return min(_MAX_DURATION_MS, int(round(value * 1000)))


def _validate_timeout(value: float, field_name: str, *, maximum: float = 120.0) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
        or value > maximum
    ):
        raise CandidateCloseWakeObservationError("timeout_invalid", field_name)
    return float(value)


def _safe_error_code(error: BaseException, default: str) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and fullmatch(_SAFE_CODE_PATTERN, code):
        return code
    return default


def _safe_close_report(session: object) -> CloseReportProjection:
    try:
        return CloseReportProjection.from_value(getattr(session, "close_report", None))
    except CandidateCloseWakeObservationError:
        return CloseReportProjection()
    except Exception:
        return CloseReportProjection()


@dataclass(slots=True)
class _ReadResult:
    kind: str
    event: ProviderStreamEvent | None = None
    error_code: str | None = None
    done: threading.Event = field(default_factory=threading.Event)


def _read_once(session: object, result: _ReadResult) -> None:
    try:
        value = next(session)  # type: ignore[arg-type]
    except StopIteration:
        result.kind = "eof"
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        result.error_code = "reader_control"
    except Exception as error:
        result.error_code = _safe_error_code(error, "reader_failed")
    else:
        if isinstance(value, ProviderStreamEvent):
            result.kind = "event"
            result.event = value
        else:
            result.error_code = "event_type_invalid"
    finally:
        result.done.set()
    return None


def _start_reader(session: object) -> tuple[threading.Thread, _ReadResult]:
    result = _ReadResult(kind="error")

    def target() -> None:
        _read_once(session, result)

    # A daemon reader is intentional: a blocked vendor read is contained by
    # the child process boundary rather than force-killed inside this process.
    thread = threading.Thread(target=target, name="candidate-close-reader", daemon=True)
    thread.start()
    return thread, result


def observe_candidate_session(
    session_factory: Callable[..., object],
    request: object | None = None,
    *,
    initial_read_timeout_s: float = 0.5,
    cancel_timeout_s: float = 2.0,
    reader_grace_s: float = 0.5,
    clock: Callable[[], float] = time.monotonic,
) -> CandidateCloseWakeObservation:
    """Open one session and measure a bounded pending-read cancellation.

    If the first read returns an event, one second read is allowed so a
    provider that has already delivered a frame can still expose a pending
    ``next()``.  No second stream/session is opened and no retry is possible.
    """

    if not callable(session_factory):
        raise CandidateCloseWakeObservationError("session_factory_invalid", "session_factory")
    initial_timeout = _validate_timeout(initial_read_timeout_s, "initial_read_timeout_s")
    cancel_timeout = _validate_timeout(cancel_timeout_s, "cancel_timeout_s")
    grace_timeout = _validate_timeout(reader_grace_s, "reader_grace_s", maximum=10.0)
    try:
        if request is None:
            session = session_factory(include_usage_tail=True)
        else:
            session = session_factory(request, include_usage_tail=True)
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        raise
    except Exception as error:
        raise CandidateCloseWakeObservationError(
            _safe_error_code(error, "session_open_failed"), "open"
        ) from None
    if session is None:
        raise CandidateCloseWakeObservationError("session_open_failed", "open")

    categories: list[str] = []
    first_started = clock()
    _thread, first_result = _start_reader(session)
    if not first_result.done.wait(initial_timeout):
        pending_result = first_result
    else:
        pending_result = None
        if first_result.kind == "event" and first_result.event is not None:
            for category in summarize_provider_event(first_result.event):
                if category not in categories:
                    categories.append(category)
            _thread, second_result = _start_reader(session)
            if second_result.done.wait(initial_timeout):
                if second_result.kind == "event" and second_result.event is not None:
                    for category in summarize_provider_event(second_result.event):
                        if category not in categories:
                            categories.append(category)
                elif second_result.error_code is not None:
                    return _finish_not_pending(
                        session,
                        categories,
                        _elapsed_ms(clock, first_started),
                        second_result.error_code,
                    )
            else:
                pending_result = second_result
        elif first_result.error_code is not None:
            return _finish_not_pending(
                session,
                categories,
                _elapsed_ms(clock, first_started),
                first_result.error_code,
            )
        else:
            return _finish_not_pending(
                session,
                categories,
                _elapsed_ms(clock, first_started),
                None,
            )

    if pending_result is None:
        return _finish_not_pending(
            session,
            categories,
            _elapsed_ms(clock, first_started),
            None,
        )

    # The reader has not completed inside the initial window.  Run cancel in
    # its own daemon thread so a blocking SDK close cannot block this worker.
    cancel_done = threading.Event()
    cancel_outcome: dict[str, str] = {}
    cancel_started = clock()

    def cancel_target() -> None:
        try:
            cancel = getattr(session, "cancel")
            cancel("candidate_close_wakeup")
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            cancel_outcome["status"] = "raised"
            cancel_outcome["error_code"] = "cancel_control"
        except Exception as error:
            cancel_outcome["status"] = "raised"
            cancel_outcome["error_code"] = _safe_error_code(error, "cancel_failed")
        else:
            cancel_outcome["status"] = "returned"
        finally:
            cancel_done.set()

    threading.Thread(
        target=cancel_target,
        name="candidate-close-canceller",
        daemon=True,
    ).start()
    if not cancel_done.wait(cancel_timeout):
        return CandidateCloseWakeObservation(
            observation_state=CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
            call_count=1,
            session_opened=True,
            pending_reader_observed=True,
            cancel_status="timeout",
            cancel_returned=False,
            reader_woke=False,
            event_categories=tuple(categories),
            initial_read_elapsed_ms=_elapsed_ms(clock, first_started),
            cancel_elapsed_ms=_elapsed_ms(clock, cancel_started),
            reader_grace_ms=int(round(grace_timeout * 1000)),
            reader_wake_elapsed_ms=None,
            close_report=_safe_close_report(session),
            error_code="cancel_timeout",
        )

    reader_woke = pending_result.done.wait(grace_timeout)
    wake_elapsed = _elapsed_ms(clock, cancel_started) if reader_woke else None
    if reader_woke:
        # Read only the safe category projection from a completed event.
        # ``pending_result`` is never serialized or retained in the receipt.
        result = pending_result
        if result.kind == "event" and result.event is not None:
            for category in summarize_provider_event(result.event):
                if category not in categories:
                    categories.append(category)
        elif result.error_code is not None:
            cancel_outcome.setdefault("error_code", result.error_code)
    error_code = cancel_outcome.get("error_code")
    return CandidateCloseWakeObservation(
        observation_state=CloseWakeState.PENDING_CANCEL_RETURNED.value,
        call_count=1,
        session_opened=True,
        pending_reader_observed=True,
        cancel_status=cancel_outcome.get("status", "raised"),
        cancel_returned=True,
        reader_woke=reader_woke,
        event_categories=tuple(categories),
        initial_read_elapsed_ms=_elapsed_ms(clock, first_started),
        cancel_elapsed_ms=_elapsed_ms(clock, cancel_started),
        reader_grace_ms=int(round(grace_timeout * 1000)),
        reader_wake_elapsed_ms=wake_elapsed,
        close_report=_safe_close_report(session),
        error_code=error_code,
    )


def _finish_not_pending(
    session: object,
    categories: list[str],
    elapsed_ms: int,
    error_code: str | None,
) -> CandidateCloseWakeObservation:
    close_error = error_code
    if error_code is None:
        try:
            close = getattr(session, "close", None)
            if callable(close):
                close()
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            close_error = "session_close_failed"
    return CandidateCloseWakeObservation(
        observation_state=CloseWakeState.NOT_PENDING.value,
        call_count=1,
        session_opened=True,
        pending_reader_observed=False,
        cancel_status="not_attempted",
        cancel_returned=False,
        reader_woke=False,
        event_categories=tuple(categories),
        initial_read_elapsed_ms=elapsed_ms,
        cancel_elapsed_ms=None,
        reader_grace_ms=0,
        reader_wake_elapsed_ms=None,
        close_report=_safe_close_report(session),
        error_code=close_error,
    )


@dataclass(frozen=True, slots=True)
class ParentCloseWakeResult:
    """Result of one child process and its immutable receipt."""

    receipt: CandidateCloseWakeReceipt
    output_path: Path
    stdout_truncated: bool = False

    @property
    def observation(self) -> CandidateCloseWakeObservation:
        return self.receipt.observation


class _ProcessLike(Protocol):
    stdout: Any
    stderr: Any
    returncode: int | None

    def wait(self, timeout: float | None = None) -> int: ...

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


class _BoundedPipe:
    def __init__(self, stream: Any, limit: int = _MAX_CAPTURE_BYTES) -> None:
        self._stream = stream
        self._limit = limit
        self.data = bytearray()
        self.truncated = False
        self._thread = threading.Thread(target=self._drain, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _drain(self) -> None:
        if self._stream is None:
            return
        while True:
            try:
                chunk = self._stream.read(_PIPE_CHUNK_BYTES)
            except Exception:
                return
            if not chunk:
                return
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8", "replace")
            remaining = self._limit - len(self.data)
            if remaining > 0:
                self.data.extend(chunk[:remaining])
            if len(chunk) > remaining:
                self.truncated = True

    def join(self, timeout: float = 1.0) -> None:
        self._thread.join(timeout)
        if self._thread.is_alive() and self._stream is not None:
            # A misbehaving descendant must not keep a pipe handle attached to
            # the parent after the hard boundary.  Closing the read end is a
            # bounded discard operation; the daemon collector may then exit.
            try:
                self._stream.close()
            except Exception:
                pass
            self._thread.join(0.1)
        if not self._thread.is_alive() and self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass


def _started_marker(stdout: bytes) -> tuple[int, bool]:
    """Read only the small safe marker, never return raw child output."""

    latest: tuple[int, bool] = (0, False)
    for line in stdout.decode("utf-8", "replace").splitlines():
        try:
            item = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, Mapping) or item.get("kind") != "probe_started":
            continue
        count = item.get("call_count", 0)
        opened = item.get("session_opened", False)
        if (
            isinstance(count, int)
            and not isinstance(count, bool)
            and count in {0, 1}
            and isinstance(opened, bool)
        ):
            latest = (count, opened)
    return latest


def _child_observation(stdout: bytes) -> CandidateCloseWakeObservation | None:
    for line in reversed(stdout.decode("utf-8", "replace").splitlines()):
        try:
            item = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, Mapping):
            continue
        try:
            return CandidateCloseWakeObservation.from_dict(item)
        except CandidateCloseWakeObservationError:
            continue
    return None


def _child_error_observation(code: str = "child_protocol_error") -> CandidateCloseWakeObservation:
    return CandidateCloseWakeObservation(
        observation_state=CloseWakeState.CHILD_ERROR.value,
        call_count=0,
        session_opened=False,
        pending_reader_observed=False,
        cancel_status="not_attempted",
        cancel_returned=False,
        reader_woke=False,
        event_categories=(),
        initial_read_elapsed_ms=0,
        cancel_elapsed_ms=None,
        reader_grace_ms=0,
        reader_wake_elapsed_ms=None,
        close_report=None,
        error_code=_safe_code(code, "error_code"),
        child_exit_code=None,
        child_terminated=False,
    )


def _child_timeout_observation(stdout: bytes, exit_code: int | None) -> CandidateCloseWakeObservation:
    call_count, opened = _started_marker(stdout)
    return CandidateCloseWakeObservation(
        observation_state=CloseWakeState.CHILD_TIMEOUT.value,
        call_count=call_count,
        session_opened=opened,
        pending_reader_observed=False,
        cancel_status="not_attempted",
        cancel_returned=False,
        reader_woke=False,
        event_categories=(),
        initial_read_elapsed_ms=0,
        cancel_elapsed_ms=None,
        reader_grace_ms=0,
        reader_wake_elapsed_ms=None,
        close_report=None,
        error_code="child_timeout",
        child_exit_code=exit_code,
        child_terminated=True,
    )


def _wait_after_termination(process: _ProcessLike) -> None:
    try:
        process.wait(timeout=0.5)
        return
    except Exception:
        pass
    try:
        process.kill()
    except Exception:
        pass
    try:
        process.wait(timeout=0.5)
    except Exception:
        # The parent has made a bounded best effort; no child output is
        # trusted after this point.
        pass


def run_parent_close_wakeup_observation(
    command: Sequence[str],
    output_path: str | Path,
    *,
    implementation_sha: str,
    diagnostic_code_sha: str,
    input_plan_sha: str,
    confirm_real_call: bool,
    process_deadline_s: float = 30.0,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    popen_factory: Callable[..., _ProcessLike] = subprocess.Popen,
) -> ParentCloseWakeResult:
    """Run one child with a hard wall-clock boundary and write one receipt."""

    if confirm_real_call is not True:
        raise CandidateCloseWakeObservationError("real_call_confirmation_required", "confirmation")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise CandidateCloseWakeObservationError("child_command_invalid", "command")
    deadline = _validate_timeout(process_deadline_s, "process_deadline_s")
    # Validate all immutable identity and output preconditions before Popen.
    _sha(implementation_sha, "implementation_sha")
    _sha(diagnostic_code_sha, "diagnostic_code_sha")
    _sha(input_plan_sha, "input_plan_sha")
    target = Path(output_path)
    if target.exists() or target.is_symlink():
        raise FileExistsError("candidate close/wakeup evidence is immutable")

    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "cwd": str(cwd) if cwd is not None else None,
        "env": dict(env) if env is not None else None,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        process = popen_factory(list(command), **kwargs)
    except Exception:
        raise CandidateCloseWakeObservationError("child_spawn_failed", "process") from None

    stdout_pipe = _BoundedPipe(getattr(process, "stdout", None))
    stderr_pipe = _BoundedPipe(getattr(process, "stderr", None))
    stdout_pipe.start()
    stderr_pipe.start()
    timed_out = False
    try:
        process.wait(timeout=deadline)
    except (TimeoutError, subprocess.TimeoutExpired):
        timed_out = True
        try:
            process.terminate()
        except Exception:
            pass
        _wait_after_termination(process)
    except Exception:
        _wait_after_termination(process)
    stdout_pipe.join()
    stderr_pipe.join()
    exit_code = getattr(process, "returncode", None)
    if timed_out:
        observation = _child_timeout_observation(bytes(stdout_pipe.data), exit_code)
    else:
        observation = _child_observation(bytes(stdout_pipe.data))
        if observation is None:
            observation = _child_error_observation(
                "child_nonzero_exit" if exit_code not in (0, None) else "child_protocol_error"
            )
        if observation.observation_state != CloseWakeState.CHILD_TIMEOUT.value:
            # A child-reported error is still bound to the actual process
            # exit code; the child cannot know that code while it is writing
            # its last safe line.
            if exit_code not in (0, None):
                if observation.observation_state == CloseWakeState.CHILD_ERROR.value:
                    observation = replace(observation, child_exit_code=exit_code)
                else:
                    observation = _child_error_observation("child_nonzero_exit")
            else:
                observation = replace(observation, child_exit_code=exit_code)

    receipt = CandidateCloseWakeReceipt(
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha=input_plan_sha,
        observation=observation,
    )
    written = write_candidate_close_wakeup_receipt(target, receipt)
    return ParentCloseWakeResult(
        receipt=receipt,
        output_path=written,
        stdout_truncated=stdout_pipe.truncated,
    )


def child_observation_line(observation: CandidateCloseWakeObservation) -> str:
    """Serialize one safe child line for the parent parser."""

    if not isinstance(observation, CandidateCloseWakeObservation):
        raise CandidateCloseWakeObservationError("observation_type_invalid", "observation")
    return _canonical_json(observation.as_dict()).decode("utf-8").rstrip("\n")


__all__ = [
    "CANDIDATE_CLOSE_WAKE_PROTOCOL_ID",
    "CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION",
    "CandidateCloseWakeObservation",
    "CandidateCloseWakeObservationError",
    "CandidateCloseWakeReceipt",
    "CloseReportProjection",
    "CloseWakeState",
    "ParentCloseWakeResult",
    "child_observation_line",
    "observe_candidate_session",
    "run_parent_close_wakeup_observation",
    "summarize_provider_event",
    "write_candidate_close_wakeup_receipt",
]
