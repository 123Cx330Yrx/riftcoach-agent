"""Central ordering, invariant, and Usage recorder for Runtime signals."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.harness.run_ids import normalize_run_id

from .lifecycle import RuntimeHarnessLifecycleV11, RuntimeLifecycleError
from .models import (
    CostObservation,
    RuntimeArtifactReference,
    RuntimeEvent,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimePricingProfile,
    RuntimeStatus,
    RuntimeTrace,
    RuntimeUsage,
    TokenObservation,
)
from .signals import (
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RunStartedSignal,
    RUNTIME_SIGNAL_TYPES,
    RuntimeSignal,
    TERMINAL_SIGNAL_TYPES,
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)


class RuntimeRecorderError(RuntimeError):
    """Raised when a signal would make the runtime history inconsistent."""


@dataclass(frozen=True)
class PreparedRuntimeTerminal:
    """Opaque, one-use terminal event prepared for prospective persistence."""

    event: RuntimeEvent
    _owner: object = field(repr=False, compare=False)
    _lifecycle_after: RuntimeHarnessLifecycleV11 = field(
        repr=False,
        compare=False,
    )


class RuntimeRecorder:
    def __init__(
        self,
        *,
        run_id: str,
        event_budget: int = 256,
        pricing_profile: RuntimePricingProfile | None = None,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if not 2 <= event_budget <= 1024:
            raise ValueError("event_budget must be between 2 and 1024")
        self._run_id = normalize_run_id(run_id)
        self._event_budget = event_budget
        self._pricing_profile = pricing_profile
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._events: list[RuntimeEvent] = []
        self._started_monotonic: float | None = None
        self._provider_open: dict[int, tuple[str, str]] = {}
        self._provider_calls_started = 0
        self._tool_open: dict[int, tuple[str, str]] = {}
        self._tool_calls_started = 0
        self._publication: PublicationDecidedSignal | None = None
        self._harness_lifecycle = RuntimeHarnessLifecycleV11()
        self._candidate_owner = object()
        self._pending_terminal: PreparedRuntimeTerminal | None = None

    @property
    def events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)

    @property
    def usage(self) -> RuntimeUsage:
        completed_provider_calls = [
            event.signal
            for event in self._events
            if isinstance(event.signal, ProviderCallCompletedSignal)
        ]
        provider_attempts = sum(
            isinstance(event.signal, ProviderCallStartedSignal)
            for event in self._events
        )
        observed_input = sum(
            signal.input_tokens for signal in completed_provider_calls
        )
        observed_output = sum(
            signal.output_tokens for signal in completed_provider_calls
        )
        observed_responses = len(completed_provider_calls)

        if provider_attempts == 0:
            token_observation = TokenObservation.NOT_APPLICABLE
            input_tokens: int | None = 0
            output_tokens: int | None = 0
        elif observed_responses == provider_attempts:
            token_observation = TokenObservation.COMPLETE
            input_tokens = observed_input
            output_tokens = observed_output
        elif observed_responses:
            token_observation = TokenObservation.PARTIAL
            input_tokens = None
            output_tokens = None
        else:
            token_observation = TokenObservation.UNKNOWN
            input_tokens = None
            output_tokens = None

        tool_completions = [
            event.signal
            for event in self._events
            if isinstance(event.signal, ToolCallCompletedSignal)
        ]
        tool_calls = sum(
            isinstance(event.signal, ToolCallStartedSignal)
            for event in self._events
        )

        pricing = self._pricing_profile
        if pricing is None:
            cost = None
            currency = None
            pricing_profile_id = None
            pricing_profile_version = None
            cost_observation = CostObservation.NOT_CONFIGURED
        else:
            currency = pricing.currency
            pricing_profile_id = pricing.profile_id
            pricing_profile_version = pricing.version
            if token_observation in {
                TokenObservation.COMPLETE,
                TokenObservation.NOT_APPLICABLE,
            }:
                cost = (
                    Decimal(input_tokens or 0)
                    * pricing.input_cost_per_million
                    + Decimal(output_tokens or 0)
                    * pricing.output_cost_per_million
                ) / Decimal(1_000_000)
                cost_observation = CostObservation.COMPLETE
            elif token_observation is TokenObservation.PARTIAL:
                cost = None
                cost_observation = CostObservation.PARTIAL
            else:
                cost = None
                cost_observation = CostObservation.UNKNOWN

        return RuntimeUsage(
            provider_calls_attempted=provider_attempts,
            provider_responses_observed=observed_responses,
            observed_input_tokens=observed_input,
            observed_output_tokens=observed_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_observation=token_observation,
            tool_calls=tool_calls,
            tool_attempts=sum(signal.attempts for signal in tool_completions),
            tool_latency_ms=sum(signal.latency_ms for signal in tool_completions),
            cost=cost,
            currency=currency,
            pricing_profile_id=pricing_profile_id,
            pricing_profile_version=pricing_profile_version,
            cost_observation=cost_observation,
        )

    def emit(self, signal: RuntimeSignal) -> RuntimeEvent:
        if isinstance(signal, TERMINAL_SIGNAL_TYPES):
            return self.commit_terminal(self.prepare_terminal(signal))
        if self._pending_terminal is not None:
            raise RuntimeRecorderError(
                "cannot emit while a terminal candidate is pending"
            )
        self._validate_common_signal(signal)
        if len(self._events) >= self._event_budget - 1:
            raise RuntimeRecorderError(
                "runtime terminal slot is reserved by the event budget"
            )
        self._validate_signal(signal)
        lifecycle_after = self._preview_lifecycle(signal)
        event = self._make_event(signal)
        self._events.append(event)
        self._apply_signal(signal, lifecycle_after=lifecycle_after)
        return event

    def prepare_terminal(
        self,
        signal: RunCompletedSignal | RunFailedSignal,
    ) -> PreparedRuntimeTerminal:
        if self._pending_terminal is not None:
            raise RuntimeRecorderError("a terminal candidate is already pending")
        if not isinstance(signal, TERMINAL_SIGNAL_TYPES):
            raise RuntimeRecorderError("terminal candidate requires a terminal signal")
        self._validate_common_signal(signal)
        if len(self._events) >= self._event_budget:
            raise RuntimeRecorderError("runtime event budget exceeded")
        self._validate_signal(signal)
        lifecycle_after = self._preview_lifecycle(signal)
        candidate = PreparedRuntimeTerminal(
            event=self._make_event(signal),
            _owner=self._candidate_owner,
            _lifecycle_after=lifecycle_after,
        )
        self._pending_terminal = candidate
        return candidate

    def commit_terminal(
        self,
        candidate: PreparedRuntimeTerminal,
    ) -> RuntimeEvent:
        self._require_pending_candidate(candidate)
        self._events.append(candidate.event)
        self._apply_signal(
            candidate.event.signal,
            lifecycle_after=candidate._lifecycle_after,
        )
        self._pending_terminal = None
        return candidate.event

    def abort_terminal(self, candidate: PreparedRuntimeTerminal) -> None:
        self._require_pending_candidate(candidate)
        self._pending_terminal = None

    def _require_pending_candidate(
        self,
        candidate: PreparedRuntimeTerminal,
    ) -> None:
        if (
            not isinstance(candidate, PreparedRuntimeTerminal)
            or candidate._owner is not self._candidate_owner
            or self._pending_terminal is not candidate
        ):
            raise RuntimeRecorderError(
                "terminal candidate does not belong to this pending Recorder state"
            )

    def _validate_common_signal(self, signal: RuntimeSignal) -> None:
        if not isinstance(signal, RUNTIME_SIGNAL_TYPES):
            raise RuntimeRecorderError("signal must use a typed runtime contract")
        if self._events and isinstance(
            self._events[-1].signal,
            TERMINAL_SIGNAL_TYPES,
        ):
            raise RuntimeRecorderError("cannot emit after the terminal event")
        if not self._events and not isinstance(signal, RunStartedSignal):
            raise RuntimeRecorderError("first event must be run_started")
        if self._events and isinstance(signal, RunStartedSignal):
            raise RuntimeRecorderError("run_started may only be the first event")

    def _make_event(self, signal: RuntimeSignal) -> RuntimeEvent:
        now = self._utc_now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise RuntimeRecorderError("utc clock must return an aware datetime")
        now = now.astimezone(timezone.utc)
        monotonic_now = self._monotonic()
        if self._started_monotonic is None:
            self._started_monotonic = monotonic_now
        elapsed_ms = max(
            0,
            round((monotonic_now - self._started_monotonic) * 1000),
        )
        if self._events:
            if now < self._events[-1].occurred_at_utc:
                raise RuntimeRecorderError("utc clock moved backwards")
            if elapsed_ms < self._events[-1].elapsed_ms:
                raise RuntimeRecorderError("monotonic clock moved backwards")

        return RuntimeEvent(
            run_id=self._run_id,
            sequence=len(self._events) + 1,
            occurred_at_utc=now,
            elapsed_ms=elapsed_ms,
            signal=signal,
        )

    def _preview_lifecycle(
        self,
        signal: RuntimeSignal,
    ) -> RuntimeHarnessLifecycleV11:
        try:
            return self._harness_lifecycle.advance(
                signal,
                context_seen=any(
                    isinstance(event.signal, ContextBuiltSignal)
                    for event in self._events
                ),
                has_open_calls=bool(self._provider_open or self._tool_open),
            )
        except RuntimeLifecycleError as exc:
            raise RuntimeRecorderError(str(exc)) from exc

    def _validate_signal(self, signal: RuntimeSignal) -> None:
        if isinstance(signal, ExecutionValidatedSignal):
            if any(
                isinstance(event.signal, ExecutionValidatedSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError("execution_validated may occur only once")
        elif isinstance(signal, ContextBuiltSignal):
            if not any(
                isinstance(event.signal, ExecutionValidatedSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError(
                    "context_built requires validated execution"
                )
            if any(
                isinstance(event.signal, ContextBuiltSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError("context_built may occur only once")
        elif isinstance(signal, ProviderCallStartedSignal):
            if not any(
                isinstance(event.signal, ContextBuiltSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError("provider call requires built context")
            expected = self._provider_calls_started + 1
            if signal.ordinal != expected:
                raise RuntimeRecorderError(
                    f"provider call ordinal must be {expected}"
                )
            pricing = self._pricing_profile
            if pricing is not None and (
                signal.provider_id != pricing.provider_id
                or signal.model != pricing.model
            ):
                raise RuntimeRecorderError(
                    "provider call does not match the pricing profile"
                )
        elif isinstance(
            signal,
            (ProviderCallCompletedSignal, ProviderCallFailedSignal),
        ):
            identity = self._provider_open.get(signal.ordinal)
            if identity is None:
                raise RuntimeRecorderError("provider call is not open")
            if identity != (signal.provider_id, signal.model):
                raise RuntimeRecorderError("provider call identity mismatch")
        elif isinstance(signal, ToolCallStartedSignal):
            if not any(
                isinstance(event.signal, ContextBuiltSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError("tool call requires built context")
            expected = self._tool_calls_started + 1
            if signal.ordinal != expected:
                raise RuntimeRecorderError(f"tool call ordinal must be {expected}")
        elif isinstance(signal, ToolCallCompletedSignal):
            identity = self._tool_open.get(signal.ordinal)
            if identity is None:
                raise RuntimeRecorderError("tool call is not open")
            if identity != (signal.tool_name, signal.tool_version):
                raise RuntimeRecorderError("tool call identity mismatch")
        elif isinstance(signal, PublicationDecidedSignal):
            if not any(
                isinstance(event.signal, ContextBuiltSignal)
                for event in self._events
            ):
                raise RuntimeRecorderError(
                    "publication decision requires built context"
                )
            if self._publication is not None:
                raise RuntimeRecorderError("publication may be decided only once")
        elif isinstance(signal, TERMINAL_SIGNAL_TYPES):
            if self._provider_open or self._tool_open:
                raise RuntimeRecorderError("cannot terminate with open calls")
            if isinstance(signal, RunCompletedSignal):
                if self._publication is None:
                    raise RuntimeRecorderError(
                        "completed run requires a publication decision"
                    )
                if (
                    signal.publication_status
                    is not self._publication.publication_status
                    or signal.terminal_reason != self._publication.terminal_reason
                ):
                    raise RuntimeRecorderError(
                        "completed run does not match publication decision"
                    )
            elif self._publication is not None and (
                signal.publication_status is not self._publication.publication_status
            ):
                raise RuntimeRecorderError(
                    "failed run does not match known publication decision"
                )

    def _apply_signal(
        self,
        signal: RuntimeSignal,
        *,
        lifecycle_after: RuntimeHarnessLifecycleV11,
    ) -> None:
        if isinstance(signal, ProviderCallStartedSignal):
            self._provider_calls_started += 1
            self._provider_open[signal.ordinal] = (
                signal.provider_id,
                signal.model,
            )
        elif isinstance(
            signal,
            (ProviderCallCompletedSignal, ProviderCallFailedSignal),
        ):
            del self._provider_open[signal.ordinal]
        elif isinstance(signal, ToolCallStartedSignal):
            self._tool_calls_started += 1
            self._tool_open[signal.ordinal] = (
                signal.tool_name,
                signal.tool_version,
            )
        elif isinstance(signal, ToolCallCompletedSignal):
            del self._tool_open[signal.ordinal]
        elif isinstance(signal, PublicationDecidedSignal):
            self._publication = signal
        self._harness_lifecycle = lifecycle_after

    def build_trace(
        self,
        *,
        identity: RuntimeIdentitySnapshot,
        policy: RuntimePolicySnapshot,
        artifacts: Sequence[RuntimeArtifactReference] = (),
        terminal_candidate: PreparedRuntimeTerminal | None = None,
    ) -> RuntimeTrace:
        if terminal_candidate is None:
            if self._pending_terminal is not None:
                raise RuntimeRecorderError(
                    "pending terminal candidate must be supplied to build Trace"
                )
            if not self._events or not isinstance(
                self._events[-1].signal,
                TERMINAL_SIGNAL_TYPES,
            ):
                raise RuntimeRecorderError("cannot build a trace before terminal")
            trace_events = self.events
        else:
            self._require_pending_candidate(terminal_candidate)
            trace_events = self.events + (terminal_candidate.event,)
        if policy.event_budget != self._event_budget:
            raise RuntimeRecorderError(
                "trace policy event budget does not match recorder budget"
            )
        start = self._events[0].signal
        if not isinstance(start, RunStartedSignal):
            raise RuntimeRecorderError("runtime history has no valid start")
        if (
            identity.skill_name != start.skill_name
            or identity.skill_version != start.skill_version
            or policy.policy_version != start.runtime_policy_version
        ):
            raise RuntimeRecorderError("trace identity or policy mismatch")

        terminal_event = trace_events[-1]
        terminal = terminal_event.signal
        if isinstance(terminal, RunCompletedSignal):
            runtime_status = RuntimeStatus.COMPLETED
            publication_status = terminal.publication_status
            terminal_reason = terminal.terminal_reason
        else:
            runtime_status = RuntimeStatus.FAILED
            publication_status = terminal.publication_status
            terminal_reason = terminal.failure_code

        return RuntimeTrace(
            run_id=self._run_id,
            identity=identity,
            policy=policy,
            events=trace_events,
            usage=self.usage,
            runtime_status=runtime_status,
            publication_status=publication_status,
            terminal_reason=terminal_reason,
            artifacts=tuple(artifacts),
            started_at_utc=trace_events[0].occurred_at_utc,
            completed_at_utc=terminal_event.occurred_at_utc,
            elapsed_ms=terminal_event.elapsed_ms,
        )
