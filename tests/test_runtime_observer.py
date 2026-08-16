from __future__ import annotations

import pytest

from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
    observe_runtime_signal,
)
from app.runtime.signals import RunStartedSignal


def _signal() -> RunStartedSignal:
    return RunStartedSignal(
        skill_name="recent-form-review",
        skill_version="0.2.0",
        runtime_policy_version="1.0.0",
    )


class RecordingObserver:
    def __init__(self) -> None:
        self.signals = []

    def observe(self, signal) -> None:
        self.signals.append(signal)


class FailingObserver:
    def observe(self, signal) -> None:
        raise RuntimeError("secret observer detail")


class TypedFailingObserver:
    def observe(self, signal) -> None:
        raise RuntimeObservationError("safe observation failure")


def test_observer_port_is_structural_and_none_is_a_closed_port():
    observer = RecordingObserver()
    signal = _signal()

    assert isinstance(observer, RuntimeSignalObserver)
    assert observe_runtime_signal(None, signal) is None
    assert observe_runtime_signal(observer, signal) is None
    assert observer.signals == [signal]


def test_observer_failure_is_wrapped_without_copying_raw_error_text():
    with pytest.raises(RuntimeObservationError) as captured:
        observe_runtime_signal(FailingObserver(), _signal())

    assert "secret observer detail" not in str(captured.value)
    assert isinstance(captured.value.__cause__, RuntimeError)


def test_typed_observation_error_is_not_wrapped_twice():
    with pytest.raises(RuntimeObservationError) as captured:
        observe_runtime_signal(TypedFailingObserver(), _signal())

    assert str(captured.value) == "safe observation failure"
    assert captured.value.__cause__ is None
