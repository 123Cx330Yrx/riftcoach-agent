"""Preserve the actual trace at a trusted send stop, without changing old runs.

The frozen AgentRuntimeV1 core remains unchanged. Product composition uses this
adapter; no request, model, evaluation or publication contract is replaced.
"""
from contextvars import ContextVar
from dataclasses import dataclass

from .dispatch_control import DispatchStopped
from .models import RuntimeIdentitySnapshot, RuntimeRunRequest, RuntimeRunResult
from .observer import RuntimeObservationError
from .runtime import AgentRuntimeV1, RuntimeEventSink, _RecorderObserver
from .signals import RuntimeFailureStage
from .store import RuntimeTraceStore


@dataclass
class _ExecutionIdentity:
    runtime: object
    snapshot: RuntimeIdentitySnapshot | None = None


_identity_capture: ContextVar[_ExecutionIdentity | None] = ContextVar(
    "riftcoach_dispatch_runtime_identity", default=None,
)


class DispatchAwareRuntime(AgentRuntimeV1):
    """Seal only a validated recorder stopped before the next Provider start."""

    @classmethod
    def from_core(cls, core: AgentRuntimeV1) -> "DispatchAwareRuntime":
        """Rebind the exact V1 dependencies; never mutate the frozen instance.

        This is an explicit composition seam, not a generic runtime decorator.
        Reject subclasses so custom execution behavior cannot be silently lost.
        Construction repeats V1's identity/policy checks without Provider IO.
        """
        if type(core) is not AgentRuntimeV1:
            raise TypeError("dispatch adapter requires the exact V1 core")
        return cls(
            runs_root=core._runs_root, catalog=core._catalog,
            provider=core._provider, provider_factory=core._provider_factory,
            execution_factory=core._execution_factory,
            context_builder=core._context_builder,
            prompt_program_resolver=core._prompt_program_resolver,
            runtime_profile=core._runtime_profile,
        )

    def _identity(self, *, skill_name: str, skill_version: str) -> RuntimeIdentitySnapshot:
        identity = super()._identity(skill_name=skill_name, skill_version=skill_version)
        capture = _identity_capture.get()
        if capture is not None and capture.runtime is self:
            capture.snapshot = identity
        return identity

    def _execute(
        self, request: RuntimeRunRequest, *, event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        capture = _ExecutionIdentity(self)
        token = _identity_capture.set(capture)
        try:
            try:
                return super()._execute(request, event_sink=event_sink)
            except DispatchStopped as stop:
                observer = stop.observer
                # These are the frozen core's actual observer/recorder and the
                # identity it resolved at startup, not recreated event history.
                if (capture.snapshot is None or not isinstance(observer, _RecorderObserver)
                        or observer._event_sink is not event_sink
                        or not observer._recorder.events
                        or observer._recorder.events[0].run_id != request.run_id):
                    raise RuntimeObservationError("unbound dispatch stop") from None
                return self._finish_failure(
                    recorder=observer._recorder,
                    trace_store=RuntimeTraceStore(self._runs_root, request.run_id),
                    identity=capture.snapshot,
                    policy=request.policy,
                    stage=RuntimeFailureStage.HARNESS,
                    code="task_dispatch_stopped",
                    artifacts=(),
                    event_sink=event_sink,
                )
        finally:
            _identity_capture.reset(token)
