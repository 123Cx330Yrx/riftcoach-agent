"""Execution-local preflight for the synchronous Worker -> Runtime call path.

This is a send boundary, not cancellation of an already dispatched request.
Outside a leased Worker execution, the existing Runtime behavior is unchanged.
"""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .observer import RuntimeObservationError


class DispatchStopped(RuntimeObservationError):
    """A trusted execution fence prevents the next Provider-start observation.

    Use the existing terminal observation path so Harness recovery cannot treat
    cancellation as a malformed model response and start another evaluation.
    Worker resolves the actual cancellation/lost-lease/error outcome.
    """


_guard: ContextVar[Callable[[], None] | None] = ContextVar(
    "riftcoach_dispatch_guard", default=None
)


@contextmanager
def bind_dispatch_guard(guard: Callable[[], None]) -> Iterator[None]:
    if not callable(guard):
        raise TypeError("dispatch guard must be callable")
    if _guard.get() is not None:
        raise RuntimeError("dispatch guard already bound")
    token = _guard.set(guard)
    try:
        yield
    finally:
        _guard.reset(token)


def require_dispatch_allowed() -> None:
    guard = _guard.get()
    if guard is not None:
        guard()
