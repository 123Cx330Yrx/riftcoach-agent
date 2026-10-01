"""Offline tests for the candidate stream hard-deadline seam."""

from __future__ import annotations

from hashlib import sha256
from threading import Event
from time import monotonic

import pytest

from app.evaluation.candidate_stream_contract import (
    CandidateStreamDeadlineError,
    CandidateStreamDeadlineSupervisor,
    CandidateTransportError,
    CandidateZhipuStreamTransport,
    PRIMARY_CANDIDATE_BINDING,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.stream_adapter_contract import ProviderStreamEvent


MODEL = "glm-5.3-flash"
REQUEST_SHA = sha256(b"deadline-test").hexdigest()


def _request() -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline deadline fixture"),)
    )


def _event() -> ProviderStreamEvent:
    return ProviderStreamEvent(
        content_delta="late body must not be yielded",
        model=MODEL,
        request_id_sha256=REQUEST_SHA,
    )


class _BlockingSession:
    """A fake whose cancel operation releases a pending ``next`` call."""

    def __init__(self, *, return_late_event: bool = False, close_error=None):
        self.return_late_event = return_late_event
        self.close_error = close_error
        self.started = Event()
        self.released = Event()
        self.cancel_codes: list[str] = []
        self.close_calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.started.set()
        # The supervisor's watchdog must release this wait; a finite fallback
        # keeps a broken fake from hanging the test process forever.
        self.released.wait(1.0)
        if self.return_late_event:
            self.return_late_event = False
            return _event()
        raise StopIteration

    def cancel(self, code: str = "elapsed_limit") -> None:
        self.cancel_codes.append(code)
        self.released.set()

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


def test_blocked_next_is_cancelled_by_wall_clock_and_closed_once() -> None:
    session = _BlockingSession()
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.03,
        cancel_grace_s=0.5,
    )
    started = monotonic()

    with pytest.raises(CandidateStreamDeadlineError) as caught:
        list(supervisor)

    assert monotonic() - started < 0.8
    assert caught.value.code == "elapsed_limit"
    assert session.cancel_codes == ["elapsed_limit"]
    assert session.close_calls == 1
    assert supervisor.deadline_reached is True
    assert supervisor.cancel_state == "requested"
    assert supervisor.cancel_failed is False
    assert supervisor.close_state == "closed"
    assert supervisor.close_failed is False


def test_event_returned_after_deadline_is_never_yielded() -> None:
    session = _BlockingSession(return_late_event=True)
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.02,
        cancel_grace_s=0.5,
    )

    with pytest.raises(CandidateStreamDeadlineError):
        list(supervisor)

    assert session.close_calls == 1
    assert session.cancel_codes == ["elapsed_limit"]


def test_deadline_error_remains_primary_when_close_also_fails() -> None:
    session = _BlockingSession(close_error=RuntimeError("private close body"))
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.02,
        cancel_grace_s=0.5,
    )

    with pytest.raises(CandidateStreamDeadlineError) as caught:
        list(supervisor)

    assert caught.value.code == "elapsed_limit"
    assert supervisor.close_state == "failed"
    assert supervisor.close_failed is True


def test_cancel_close_failure_is_preserved_as_secondary_evidence() -> None:
    class _CancelClosesBroken(_BlockingSession):
        def __init__(self) -> None:
            super().__init__()
            self._closed = False
            self.close_failed = False

        def cancel(self, code: str = "elapsed_limit") -> None:
            self.cancel_codes.append(code)
            self.released.set()
            self.close()

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            self.close_calls += 1
            self.close_failed = True
            raise RuntimeError("private close body")

    session = _CancelClosesBroken()
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.02,
        cancel_grace_s=0.5,
    )

    with pytest.raises(CandidateStreamDeadlineError):
        list(supervisor)

    assert supervisor.cancel_failed is True
    assert supervisor.close_failed is True
    assert supervisor.close_state == "failed"
    assert session.close_calls == 1


def test_deadline_is_measured_from_attempt_start_not_session_iteration_start() -> None:
    session = _BlockingSession()
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.5,
        started_at=monotonic() - 1.0,
        cancel_grace_s=0.5,
    )
    started = monotonic()

    with pytest.raises(CandidateStreamDeadlineError):
        list(supervisor)

    assert monotonic() - started < 0.3
    assert session.cancel_codes == ["elapsed_limit"]
    assert session.close_calls == 1


def test_caller_checks_absolute_deadline_even_if_watchdog_event_is_late() -> None:
    session = _BlockingSession()
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.5,
        started_at=monotonic() - 1.0,
        cancel_grace_s=0.5,
    )

    # Simulate scheduler lag: the watchdog event has not been set yet, but
    # the absolute timestamp is already in the past.
    assert supervisor.deadline_reached is False
    with pytest.raises(CandidateStreamDeadlineError):
        supervisor._raise_if_deadline()  # type: ignore[attr-defined]

    assert supervisor.deadline_reached is True
    assert session.cancel_codes == ["elapsed_limit"]


def test_supervisor_maps_untrusted_iterator_errors_to_safe_codes() -> None:
    class BrokenSession(_BlockingSession):
        def __next__(self):
            raise RuntimeError("private provider response")

    session = BrokenSession()
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.5,
        cancel_grace_s=0.5,
    )

    with pytest.raises(CandidateTransportError) as caught:
        list(supervisor)

    assert caught.value.code == "stream_read_failed"
    assert str(caught.value) == "stream_read_failed"
    assert "private provider response" not in repr(caught.value)
    assert session.close_calls == 1


def test_normal_eof_surfaces_a_safe_close_failure() -> None:
    class _EmptyCloseBroken(_BlockingSession):
        def __next__(self):
            raise StopIteration

    session = _EmptyCloseBroken(close_error=RuntimeError("private close body"))
    supervisor = CandidateStreamDeadlineSupervisor(
        session,
        deadline_s=0.5,
        cancel_grace_s=0.5,
    )

    with pytest.raises(CandidateTransportError) as caught:
        list(supervisor)

    assert caught.value.code == "stream_close_failed"
    assert str(caught.value) == "stream_close_failed"
    assert supervisor.close_state == "failed"


def test_legacy_iterable_transport_is_rejected_before_opener_io() -> None:
    calls = 0

    def opener(**_kwargs):
        nonlocal calls
        calls += 1
        return []

    transport = CandidateZhipuStreamTransport(opener)
    with pytest.raises(CandidateTransportError) as caught:
        transport.open_stream_session(PRIMARY_CANDIDATE_BINDING, _request())

    assert caught.value.code == "hard_deadline_unsupported"
    assert calls == 0


def test_explicit_session_opener_returning_legacy_iterable_fails_closed_after_open() -> None:
    calls = 0

    def session_opener(**_kwargs):
        nonlocal calls
        calls += 1
        return []

    transport = CandidateZhipuStreamTransport(
        lambda **_kwargs: [],
        session_opener=session_opener,
    )
    with pytest.raises(CandidateTransportError) as caught:
        transport.open_stream_session(PRIMARY_CANDIDATE_BINDING, _request())

    assert caught.value.code == "hard_deadline_unsupported"
    assert calls == 1
