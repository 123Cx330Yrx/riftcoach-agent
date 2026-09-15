"""Deterministic, offline replay for the candidate close/wakeup observer.

This module is deliberately separate from the real-provider receipt contract.
It exercises the observer with an in-memory scripted session, so the result
can prove that our lifecycle classification is repeatable without implying
anything about a vendor transport.  The fake session opening count and the
external-provider call count are recorded as different fields on purpose.

No network connection, credential read, provider client construction, response
body, exception text, or request identifier is used or retained here. Importing
the existing package may load SDK dependency modules; this replay never
instantiates or calls an SDK client.
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
from typing import Literal

from app.providers.stream_adapter_contract import ProviderStreamEvent

from .candidate_provider_close_wakeup_observation import (
    CANDIDATE_CLOSE_WAKE_PROTOCOL_ID,
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    CloseWakeState,
    observe_candidate_session,
)


CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID = (
    "glm-5.3-flash-candidate-close-wakeup-replay"
)
CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION = "1.0.0"
REPLAY_EVIDENCE_ORIGIN = "offline_fake"

_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SAFE_ID_PATTERN = r"^[a-z][a-z0-9_.-]{0,95}$"
_SCENARIO_MODES = frozenset(
    {
        "not_pending",
        "cancel_wakes",
        "cancel_returns_no_wake",
        "cancel_times_out",
        "cancel_raises",
    }
)
_CORE_STATES = frozenset(
    {
        CloseWakeState.NOT_PENDING.value,
        CloseWakeState.PENDING_CANCEL_RETURNED.value,
        CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
    }
)
_CANCEL_STATUSES = frozenset(
    {"not_attempted", "returned", "raised", "timeout"}
)

_SCENARIO_KEYS = frozenset(
    {
        "scenario_id",
        "session_mode",
        "expected_observation_state",
        "expected_cancel_status",
        "expected_reader_woke",
    }
)
_CASE_KEYS = frozenset(
    {
        "scenario_id",
        "expected_observation_state",
        "observed_observation_state",
        "expected_cancel_status",
        "observed_cancel_status",
        "expected_reader_woke",
        "observed_reader_woke",
        "observer_call_count",
        "fake_session_open_count",
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
        "scenario_sha256",
        "cases",
        "all_cases_passed",
    }
)


class CandidateCloseWakeReplayError(ValueError):
    """Machine-safe replay validation error with no private text."""

    def __init__(self, code: str, field_name: str | None = None) -> None:
        if fullmatch(_SAFE_ID_PATTERN, code) is None:
            code = "replay_contract_error"
        self.code = code
        self.field_name = field_name
        super().__init__(code)


def _safe_sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA_PATTERN, value) is None:
        raise CandidateCloseWakeReplayError("invalid_git_sha", field_name)
    return value


def _safe_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA256_PATTERN, value) is None:
        raise CandidateCloseWakeReplayError("invalid_sha256", field_name)
    return value


def _safe_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SAFE_ID_PATTERN, value) is None:
        raise CandidateCloseWakeReplayError("invalid_identifier", field_name)
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
        raise CandidateCloseWakeReplayError("json_not_serializable", "serialize") from None


def _assert_no_forbidden_keys(value: object) -> None:
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
                raise CandidateCloseWakeReplayError("receipt_field_forbidden", "serialize")
            _assert_no_forbidden_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_no_forbidden_keys(item)


@dataclass(frozen=True, slots=True)
class CandidateCloseWakeReplayScenario:
    """One fixed fake-session schedule and its expected observer outcome."""

    scenario_id: str
    session_mode: Literal[
        "not_pending",
        "cancel_wakes",
        "cancel_returns_no_wake",
        "cancel_times_out",
        "cancel_raises",
    ]
    expected_observation_state: str
    expected_cancel_status: str
    expected_reader_woke: bool

    def __post_init__(self) -> None:
        _safe_id(self.scenario_id, "scenario_id")
        if self.session_mode not in _SCENARIO_MODES:
            raise CandidateCloseWakeReplayError("session_mode_invalid", "session_mode")
        if self.expected_observation_state not in _CORE_STATES:
            raise CandidateCloseWakeReplayError(
                "observation_state_invalid", "expected_observation_state"
            )
        if self.expected_cancel_status not in _CANCEL_STATUSES:
            raise CandidateCloseWakeReplayError("cancel_status_invalid", "expected_cancel_status")
        if not isinstance(self.expected_reader_woke, bool):
            raise CandidateCloseWakeReplayError("reader_woke_invalid", "expected_reader_woke")
        if self.session_mode == "not_pending":
            expected = (
                CloseWakeState.NOT_PENDING.value,
                "not_attempted",
                False,
            )
        elif self.session_mode == "cancel_wakes":
            expected = (
                CloseWakeState.PENDING_CANCEL_RETURNED.value,
                "returned",
                True,
            )
        elif self.session_mode == "cancel_returns_no_wake":
            expected = (
                CloseWakeState.PENDING_CANCEL_RETURNED.value,
                "returned",
                False,
            )
        elif self.session_mode == "cancel_times_out":
            expected = (
                CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
                "timeout",
                False,
            )
        else:
            # The observer intentionally reports a raised cancel control as
            # returned from its bounded control window, with a safe error
            # code.  This is not a successful provider cancellation claim.
            expected = (
                CloseWakeState.PENDING_CANCEL_RETURNED.value,
                "raised",
                False,
            )
        if (
            self.expected_observation_state,
            self.expected_cancel_status,
            self.expected_reader_woke,
        ) != expected:
            raise CandidateCloseWakeReplayError("scenario_expectation_invalid", "scenario")

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "session_mode": self.session_mode,
            "expected_observation_state": self.expected_observation_state,
            "expected_cancel_status": self.expected_cancel_status,
            "expected_reader_woke": self.expected_reader_woke,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateCloseWakeReplayScenario":
        if not isinstance(value, Mapping) or set(value) != _SCENARIO_KEYS:
            raise CandidateCloseWakeReplayError("scenario_fields_invalid", "scenario")
        _assert_no_forbidden_keys(value)
        try:
            return cls(**dict(value))
        except CandidateCloseWakeReplayError:
            raise
        except (TypeError, ValueError):
            raise CandidateCloseWakeReplayError("scenario_shape_invalid", "scenario") from None


REPLAY_SCENARIOS: tuple[CandidateCloseWakeReplayScenario, ...] = (
    CandidateCloseWakeReplayScenario(
        scenario_id="not-pending-eof",
        session_mode="not_pending",
        expected_observation_state=CloseWakeState.NOT_PENDING.value,
        expected_cancel_status="not_attempted",
        expected_reader_woke=False,
    ),
    CandidateCloseWakeReplayScenario(
        scenario_id="pending-cancel-wakes-reader",
        session_mode="cancel_wakes",
        expected_observation_state=CloseWakeState.PENDING_CANCEL_RETURNED.value,
        expected_cancel_status="returned",
        expected_reader_woke=True,
    ),
    CandidateCloseWakeReplayScenario(
        scenario_id="pending-cancel-returns-no-wake",
        session_mode="cancel_returns_no_wake",
        expected_observation_state=CloseWakeState.PENDING_CANCEL_RETURNED.value,
        expected_cancel_status="returned",
        expected_reader_woke=False,
    ),
    CandidateCloseWakeReplayScenario(
        scenario_id="pending-cancel-times-out",
        session_mode="cancel_times_out",
        expected_observation_state=CloseWakeState.PENDING_CANCEL_TIMEOUT.value,
        expected_cancel_status="timeout",
        expected_reader_woke=False,
    ),
    CandidateCloseWakeReplayScenario(
        scenario_id="pending-cancel-raises",
        session_mode="cancel_raises",
        expected_observation_state=CloseWakeState.PENDING_CANCEL_RETURNED.value,
        expected_cancel_status="raised",
        expected_reader_woke=False,
    ),
)


def replay_scenario_sha256(
    scenarios: tuple[CandidateCloseWakeReplayScenario, ...] = REPLAY_SCENARIOS,
) -> str:
    """Return the stable digest of the scenario schedule, not run timings."""

    payload = [scenario.as_dict() for scenario in scenarios]
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256 = replay_scenario_sha256()


@dataclass(frozen=True, slots=True)
class CandidateCloseWakeReplayCase:
    """Body-free comparison of one expected and observed fake outcome."""

    scenario_id: str
    expected_observation_state: str
    observed_observation_state: str
    expected_cancel_status: str
    observed_cancel_status: str
    expected_reader_woke: bool
    observed_reader_woke: bool
    observer_call_count: int
    fake_session_open_count: int
    passed: bool

    def __post_init__(self) -> None:
        _safe_id(self.scenario_id, "scenario_id")
        for field_name in (
            "expected_observation_state",
            "observed_observation_state",
        ):
            if getattr(self, field_name) not in _CORE_STATES:
                raise CandidateCloseWakeReplayError("observation_state_invalid", field_name)
        for field_name in ("expected_cancel_status", "observed_cancel_status"):
            if getattr(self, field_name) not in _CANCEL_STATUSES:
                raise CandidateCloseWakeReplayError("cancel_status_invalid", field_name)
        for field_name in ("expected_reader_woke", "observed_reader_woke", "passed"):
            if not isinstance(getattr(self, field_name), bool):
                raise CandidateCloseWakeReplayError("lifecycle_value_invalid", field_name)
        for field_name in ("observer_call_count", "fake_session_open_count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value != 1:
                raise CandidateCloseWakeReplayError("single_open_invalid", field_name)
        expected_pass = (
            self.expected_observation_state == self.observed_observation_state
            and self.expected_cancel_status == self.observed_cancel_status
            and self.expected_reader_woke == self.observed_reader_woke
        )
        if self.passed is not expected_pass:
            raise CandidateCloseWakeReplayError("pass_projection_invalid", "passed")

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "expected_observation_state": self.expected_observation_state,
            "observed_observation_state": self.observed_observation_state,
            "expected_cancel_status": self.expected_cancel_status,
            "observed_cancel_status": self.observed_cancel_status,
            "expected_reader_woke": self.expected_reader_woke,
            "observed_reader_woke": self.observed_reader_woke,
            "observer_call_count": self.observer_call_count,
            "fake_session_open_count": self.fake_session_open_count,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateCloseWakeReplayCase":
        if not isinstance(value, Mapping) or set(value) != _CASE_KEYS:
            raise CandidateCloseWakeReplayError("case_fields_invalid", "case")
        _assert_no_forbidden_keys(value)
        try:
            return cls(**dict(value))
        except CandidateCloseWakeReplayError:
            raise
        except (TypeError, ValueError):
            raise CandidateCloseWakeReplayError("case_shape_invalid", "case") from None


@dataclass(frozen=True, slots=True)
class CandidateCloseWakeReplayReceipt:
    """Immutable offline evidence, intentionally not a provider capability receipt."""

    implementation_sha: str
    observer_code_sha: str
    input_plan_sha: str
    scenario_sha256: str
    cases: tuple[CandidateCloseWakeReplayCase, ...]
    evidence_origin: Literal["offline_fake"] = REPLAY_EVIDENCE_ORIGIN
    real_provider_observed: bool = False
    provider_call_count: int = 0
    network_used: bool = False
    all_cases_passed: bool = True
    schema_version: str = CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION
    protocol_id: str = CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID

    def __post_init__(self) -> None:
        _safe_sha(self.implementation_sha, "implementation_sha")
        _safe_sha(self.observer_code_sha, "observer_code_sha")
        _safe_sha(self.input_plan_sha, "input_plan_sha")
        _safe_sha256(self.scenario_sha256, "scenario_sha256")
        if self.schema_version != CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION:
            raise CandidateCloseWakeReplayError("schema_version_invalid", "schema_version")
        if self.protocol_id != CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID:
            raise CandidateCloseWakeReplayError("protocol_id_invalid", "protocol_id")
        if self.evidence_origin != REPLAY_EVIDENCE_ORIGIN:
            raise CandidateCloseWakeReplayError("evidence_origin_invalid", "evidence_origin")
        if not isinstance(self.real_provider_observed, bool) or self.real_provider_observed:
            raise CandidateCloseWakeReplayError("real_provider_observed_invalid", "real_provider_observed")
        if isinstance(self.provider_call_count, bool) or self.provider_call_count != 0:
            raise CandidateCloseWakeReplayError("provider_call_count_invalid", "provider_call_count")
        if not isinstance(self.network_used, bool) or self.network_used:
            raise CandidateCloseWakeReplayError("network_used_invalid", "network_used")
        if not isinstance(self.all_cases_passed, bool):
            raise CandidateCloseWakeReplayError("all_cases_passed_invalid", "all_cases_passed")
        if not isinstance(self.cases, tuple) or not self.cases:
            raise CandidateCloseWakeReplayError("cases_invalid", "cases")
        case_ids = tuple(case.scenario_id for case in self.cases)
        expected_ids = tuple(scenario.scenario_id for scenario in REPLAY_SCENARIOS)
        if case_ids != expected_ids:
            raise CandidateCloseWakeReplayError("scenario_order_invalid", "cases")
        if self.scenario_sha256 != CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256:
            raise CandidateCloseWakeReplayError("scenario_digest_mismatch", "scenario_sha256")
        derived_passed = all(case.passed for case in self.cases)
        if self.all_cases_passed is not derived_passed:
            raise CandidateCloseWakeReplayError("all_cases_passed_mismatch", "all_cases_passed")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "evidence_origin": self.evidence_origin,
            "real_provider_observed": self.real_provider_observed,
            "provider_call_count": self.provider_call_count,
            "network_used": self.network_used,
            "implementation_sha": self.implementation_sha,
            "observer_code_sha": self.observer_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "scenario_sha256": self.scenario_sha256,
            "cases": [case.as_dict() for case in self.cases],
            "all_cases_passed": self.all_cases_passed,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateCloseWakeReplayReceipt":
        if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
            raise CandidateCloseWakeReplayError("receipt_fields_invalid", "receipt")
        _assert_no_forbidden_keys(value)
        try:
            raw_cases = value["cases"]
            if isinstance(raw_cases, (str, bytes)) or not isinstance(raw_cases, list):
                raise CandidateCloseWakeReplayError("cases_invalid", "cases")
            cases = tuple(CandidateCloseWakeReplayCase.from_dict(item) for item in raw_cases)
            return cls(
                implementation_sha=value["implementation_sha"],
                observer_code_sha=value["observer_code_sha"],
                input_plan_sha=value["input_plan_sha"],
                scenario_sha256=value["scenario_sha256"],
                cases=cases,
                evidence_origin=value["evidence_origin"],
                real_provider_observed=value["real_provider_observed"],
                provider_call_count=value["provider_call_count"],
                network_used=value["network_used"],
                all_cases_passed=value["all_cases_passed"],
                schema_version=value["schema_version"],
                protocol_id=value["protocol_id"],
            )
        except CandidateCloseWakeReplayError:
            raise
        except (TypeError, ValueError):
            raise CandidateCloseWakeReplayError("receipt_shape_invalid", "receipt") from None


class _ReplaySession:
    """A bounded in-memory session whose gates make pending reads explicit."""

    def __init__(self, mode: str) -> None:
        self._mode = mode
        self._read_release = threading.Event()
        self._cancel_release = threading.Event()
        self._reader_done = threading.Event()
        self._cancel_done = threading.Event()
        self._read_count = 0
        self.cancel_calls = 0
        self.close_calls = 0

    def __next__(self) -> ProviderStreamEvent:
        self._read_count += 1
        if self._mode == "not_pending":
            try:
                if self._read_count == 1:
                    return ProviderStreamEvent(content_delta="offline-fixture")
                raise StopIteration
            finally:
                self._reader_done.set()
        try:
            self._read_release.wait()
            raise StopIteration
        finally:
            self._reader_done.set()

    def cancel(self, _code: str = "candidate_close_wakeup") -> None:
        self.cancel_calls += 1
        try:
            if self._mode == "cancel_wakes":
                self._read_release.set()
            elif self._mode == "cancel_times_out":
                self._cancel_release.wait()
            elif self._mode == "cancel_raises":
                raise RuntimeError("private fixture control text")
            # cancel_returns_no_wake intentionally returns without releasing
            # the reader, so the observer's finite grace window expires.
        finally:
            self._cancel_done.set()

    def close(self) -> None:
        self.close_calls += 1

    @property
    def close_report(self) -> dict[str, object]:
        return {
            "iterator_state": "closed",
            "sdk_stream_state": "closed",
            "composite_state": "closed",
            "shared_resource": False,
        }

    def release(self) -> None:
        """End blocked fake operations after the observer has classified them."""

        self._read_release.set()
        self._cancel_release.set()
        self._reader_done.wait(0.5)
        if self.cancel_calls:
            self._cancel_done.wait(0.5)


def _run_scenario(scenario: CandidateCloseWakeReplayScenario) -> CandidateCloseWakeReplayCase:
    session = _ReplaySession(scenario.session_mode)
    open_count = 0

    def factory(*, include_usage_tail: bool = False) -> _ReplaySession:
        nonlocal open_count
        if include_usage_tail is not True:
            raise CandidateCloseWakeReplayError("usage_tail_required", "factory")
        open_count += 1
        return session

    try:
        observation = observe_candidate_session(
            factory,
            initial_read_timeout_s=0.05,
            cancel_timeout_s=0.05,
            reader_grace_s=0.05,
        )
    except CandidateCloseWakeObservationError:
        raise CandidateCloseWakeReplayError("observer_contract_failed", "observation") from None
    finally:
        session.release()

    return CandidateCloseWakeReplayCase(
        scenario_id=scenario.scenario_id,
        expected_observation_state=scenario.expected_observation_state,
        observed_observation_state=observation.observation_state,
        expected_cancel_status=scenario.expected_cancel_status,
        observed_cancel_status=observation.cancel_status,
        expected_reader_woke=scenario.expected_reader_woke,
        observed_reader_woke=observation.reader_woke,
        observer_call_count=observation.call_count,
        fake_session_open_count=open_count,
        passed=(
            observation.observation_state == scenario.expected_observation_state
            and observation.cancel_status == scenario.expected_cancel_status
            and observation.reader_woke is scenario.expected_reader_woke
            and observation.pending_reader_observed
            is (scenario.expected_observation_state != CloseWakeState.NOT_PENDING.value)
        ),
    )


def run_candidate_close_wakeup_replay(
    *,
    implementation_sha: str,
    observer_code_sha: str,
    input_plan_sha: str,
) -> CandidateCloseWakeReplayReceipt:
    """Run the fixed offline matrix with zero external calls."""

    _safe_sha(implementation_sha, "implementation_sha")
    _safe_sha(observer_code_sha, "observer_code_sha")
    _safe_sha(input_plan_sha, "input_plan_sha")
    cases = tuple(_run_scenario(scenario) for scenario in REPLAY_SCENARIOS)
    return CandidateCloseWakeReplayReceipt(
        implementation_sha=implementation_sha,
        observer_code_sha=observer_code_sha,
        input_plan_sha=input_plan_sha,
        scenario_sha256=CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256,
        cases=cases,
        all_cases_passed=all(case.passed for case in cases),
    )


def write_candidate_close_wakeup_replay_receipt(
    path: str | Path,
    receipt: CandidateCloseWakeReplayReceipt,
    *,
    offline_root: str | Path,
) -> Path:
    """Create one canonical receipt inside an explicit offline evidence root."""

    if not isinstance(receipt, CandidateCloseWakeReplayReceipt):
        raise CandidateCloseWakeReplayError("receipt_type_invalid", "receipt")
    try:
        target = Path(path).resolve()
        allowed_root = Path(offline_root).resolve()
    except OSError:
        raise CandidateCloseWakeReplayError("offline_path_required", "path") from None
    if (
        target.suffix.lower() != ".json"
        or not target.is_relative_to(allowed_root)
        or target == allowed_root
        or any(part.lower() == "provider_capabilities" for part in target.parts)
    ):
        raise CandidateCloseWakeReplayError("offline_path_required", "path")
    if target.exists() or target.is_symlink():
        raise FileExistsError("offline close/wakeup replay evidence is immutable")
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


__all__ = [
    "CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID",
    "CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION",
    "CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256",
    "CandidateCloseWakeReplayCase",
    "CandidateCloseWakeReplayError",
    "CandidateCloseWakeReplayReceipt",
    "CandidateCloseWakeReplayScenario",
    "REPLAY_EVIDENCE_ORIGIN",
    "REPLAY_SCENARIOS",
    "replay_scenario_sha256",
    "run_candidate_close_wakeup_replay",
    "write_candidate_close_wakeup_replay_receipt",
]
