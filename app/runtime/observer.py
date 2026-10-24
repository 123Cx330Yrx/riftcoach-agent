"""Default-closed observation port for body-free Runtime signals."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .signals import ProviderCallStartedSignal, RuntimeSignal


class RuntimeObservationError(RuntimeError):
    """Safe failure raised when the trusted Runtime observer cannot record."""


@runtime_checkable
class RuntimeSignalObserver(Protocol):
    def observe(self, signal: RuntimeSignal) -> None:
        """Record one typed signal or raise an observation failure."""


def observe_runtime_signal(
    observer: RuntimeSignalObserver | None,
    signal: RuntimeSignal,
) -> None:
    """Send one signal through an optional port without leaking raw errors."""

    try:
        if isinstance(signal, ProviderCallStartedSignal):
            # Task ownership is a control-plane precondition, independent of
            # the model request/receipt contract and the selected observer.
            from .dispatch_control import DispatchStopped, require_dispatch_allowed
            try:
                require_dispatch_allowed()
            except DispatchStopped as stop:
                # Only the trusted send guard can bind a recorder for safe
                # terminal persistence. An observer/delegate failure cannot.
                stop.observer = observer
                raise
        if observer is None:
            return
        observer.observe(signal)
    except RuntimeObservationError:
        raise
    except Exception as exc:
        raise RuntimeObservationError("runtime observation failed") from exc
