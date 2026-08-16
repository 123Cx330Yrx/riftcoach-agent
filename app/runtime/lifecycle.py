"""Version-frozen Runtime 1.1 lifecycle validation.

The reducer is shared by live recording and persisted Trace replay so the two
paths cannot silently acquire different Harness rules.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType

from .signals import (
    AgentRunTerminatedSignal,
    EvaluationCompletedSignal,
    HarnessTransitionedSignal,
    ProviderCallStartedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RuntimeHarnessStatus,
    RuntimeProviderPhase,
    RuntimePublicationStatus,
    RuntimeSignal,
    ToolCallStartedSignal,
)


class RuntimeLifecycleError(ValueError):
    """Raised when a Runtime 1.1 signal violates the frozen lifecycle."""


_TERMINAL_HARNESS_STATUSES = frozenset(
    {
        RuntimeHarnessStatus.PUBLISHED,
        RuntimeHarnessStatus.DEGRADED,
        RuntimeHarnessStatus.REJECTED,
    }
)
_EVALUATION_STATUSES = frozenset(
    {
        RuntimeHarnessStatus.EVALUATING,
        RuntimeHarnessStatus.RE_EVALUATING,
    }
)
_PUBLICATION_BY_HARNESS = MappingProxyType(
    {
        RuntimeHarnessStatus.PUBLISHED: RuntimePublicationStatus.PUBLISHED,
        RuntimeHarnessStatus.DEGRADED: RuntimePublicationStatus.DEGRADED,
        RuntimeHarnessStatus.REJECTED: RuntimePublicationStatus.REJECTED,
    }
)
RUNTIME_V11_HARNESS_TRANSITIONS = MappingProxyType(
    {
        RuntimeHarnessStatus.CREATED: frozenset(
            {
                RuntimeHarnessStatus.FACTS_READY,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.FACTS_READY: frozenset(
            {
                RuntimeHarnessStatus.KNOWLEDGE_READY,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.KNOWLEDGE_READY: frozenset(
            {
                RuntimeHarnessStatus.DRAFT_READY,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.DRAFT_READY: frozenset(
            {
                RuntimeHarnessStatus.EVALUATING,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.EVALUATING: frozenset(
            {
                RuntimeHarnessStatus.PASSED,
                RuntimeHarnessStatus.NEEDS_REVISION,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.NEEDS_REVISION: frozenset(
            {
                RuntimeHarnessStatus.REVISING,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.REVISING: frozenset(
            {
                RuntimeHarnessStatus.RE_EVALUATING,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.RE_EVALUATING: frozenset(
            {
                RuntimeHarnessStatus.PASSED,
                RuntimeHarnessStatus.NEEDS_REVISION,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.PASSED: frozenset(
            {
                RuntimeHarnessStatus.PUBLISHED,
                RuntimeHarnessStatus.DEGRADED,
                RuntimeHarnessStatus.REJECTED,
            }
        ),
        RuntimeHarnessStatus.PUBLISHED: frozenset(),
        RuntimeHarnessStatus.DEGRADED: frozenset(),
        RuntimeHarnessStatus.REJECTED: frozenset(),
    }
)


@dataclass(frozen=True)
class RuntimeHarnessLifecycleV11:
    status: RuntimeHarnessStatus | None = None
    revision_count: int = 0
    evaluation_seen_in_phase: bool = False
    agent_terminal_seen: bool = False
    publication_status: RuntimePublicationStatus | None = None

    def advance(
        self,
        signal: RuntimeSignal,
        *,
        context_seen: bool,
        has_open_calls: bool,
    ) -> "RuntimeHarnessLifecycleV11":
        if self.publication_status is not None and not isinstance(
            signal,
            (RunCompletedSignal, RunFailedSignal),
        ):
            raise RuntimeLifecycleError(
                "publication decision may only be followed by Runtime terminal"
            )

        if isinstance(signal, HarnessTransitionedSignal):
            return self._advance_transition(
                signal,
                context_seen=context_seen,
                has_open_calls=has_open_calls,
            )
        if isinstance(signal, EvaluationCompletedSignal):
            return self._advance_evaluation(signal, has_open_calls=has_open_calls)
        if isinstance(signal, PublicationDecidedSignal):
            return self._advance_publication(
                signal,
                has_open_calls=has_open_calls,
            )
        if isinstance(signal, AgentRunTerminatedSignal):
            if has_open_calls:
                raise RuntimeLifecycleError(
                    "Agent terminal requires closed Provider and Tool calls"
                )
            if self.status is not RuntimeHarnessStatus.FACTS_READY:
                raise RuntimeLifecycleError(
                    "Agent terminal requires Harness facts_ready"
                )
            if self.agent_terminal_seen:
                raise RuntimeLifecycleError("Agent terminal may occur only once")
            return replace(self, agent_terminal_seen=True)
        if isinstance(signal, ProviderCallStartedSignal):
            self._validate_provider_phase(signal)
        elif isinstance(signal, ToolCallStartedSignal):
            if (
                self.status is not RuntimeHarnessStatus.FACTS_READY
                or self.agent_terminal_seen
            ):
                raise RuntimeLifecycleError(
                    "business Tool call requires an active Agent at facts_ready"
                )
        elif isinstance(signal, RunCompletedSignal):
            if self.publication_status is None:
                raise RuntimeLifecycleError(
                    "completed Runtime requires terminal Harness publication"
                )
            if signal.publication_status is not self.publication_status:
                raise RuntimeLifecycleError(
                    "completed Runtime publication does not match Harness"
                )
        elif isinstance(signal, RunFailedSignal):
            self._validate_failed_terminal(signal)
        elif self.status in _TERMINAL_HARNESS_STATUSES:
            raise RuntimeLifecycleError(
                "terminal Harness transition may only be followed by publication"
            )
        return self

    def _advance_transition(
        self,
        signal: HarnessTransitionedSignal,
        *,
        context_seen: bool,
        has_open_calls: bool,
    ) -> "RuntimeHarnessLifecycleV11":
        if not context_seen:
            raise RuntimeLifecycleError(
                "Harness transition requires built context"
            )
        if has_open_calls:
            raise RuntimeLifecycleError(
                "Harness transition requires closed Provider and Tool calls"
            )
        if self.status in _TERMINAL_HARNESS_STATUSES:
            raise RuntimeLifecycleError("Harness terminal status cannot transition")

        expected_source = self.status or RuntimeHarnessStatus.CREATED
        if signal.from_status is not expected_source:
            raise RuntimeLifecycleError(
                "Harness transition source does not match previous status"
            )
        if signal.to_status not in RUNTIME_V11_HARNESS_TRANSITIONS[expected_source]:
            raise RuntimeLifecycleError("Harness transition edge is not allowed")

        expected_revision = self.revision_count + (
            1 if signal.to_status is RuntimeHarnessStatus.REVISING else 0
        )
        if signal.revision_count != expected_revision:
            raise RuntimeLifecycleError(
                "Harness transition revision_count is inconsistent"
            )
        return replace(
            self,
            status=signal.to_status,
            revision_count=expected_revision,
            evaluation_seen_in_phase=False,
        )

    def _advance_evaluation(
        self,
        signal: EvaluationCompletedSignal,
        *,
        has_open_calls: bool,
    ) -> "RuntimeHarnessLifecycleV11":
        if has_open_calls:
            raise RuntimeLifecycleError(
                "Evaluation completion requires closed Provider and Tool calls"
            )
        if self.status not in _EVALUATION_STATUSES:
            raise RuntimeLifecycleError(
                "Evaluation completion requires evaluating or re_evaluating"
            )
        if self.evaluation_seen_in_phase:
            raise RuntimeLifecycleError(
                "Evaluation completion may occur only once per Harness phase"
            )
        if signal.attempt != self.revision_count:
            raise RuntimeLifecycleError(
                "Evaluation attempt must match zero-based Harness revision"
            )
        return replace(self, evaluation_seen_in_phase=True)

    def _advance_publication(
        self,
        signal: PublicationDecidedSignal,
        *,
        has_open_calls: bool,
    ) -> "RuntimeHarnessLifecycleV11":
        if has_open_calls:
            raise RuntimeLifecycleError(
                "publication requires closed Provider and Tool calls"
            )
        expected = _PUBLICATION_BY_HARNESS.get(self.status)
        if expected is None:
            raise RuntimeLifecycleError(
                "publication requires terminal Harness transition"
            )
        if signal.publication_status is not expected:
            raise RuntimeLifecycleError(
                "publication status does not match terminal Harness status"
            )
        return replace(self, publication_status=signal.publication_status)

    def _validate_provider_phase(self, signal: ProviderCallStartedSignal) -> None:
        if signal.phase is RuntimeProviderPhase.AGENT:
            if (
                self.status is not RuntimeHarnessStatus.FACTS_READY
                or self.agent_terminal_seen
            ):
                raise RuntimeLifecycleError(
                    "Agent Provider call requires active facts_ready phase"
                )
        elif signal.phase in {
            RuntimeProviderPhase.EVALUATION,
            RuntimeProviderPhase.EVALUATION_REPAIR,
        }:
            if self.status not in _EVALUATION_STATUSES:
                raise RuntimeLifecycleError(
                    "Evaluation Provider call requires evaluation Harness phase"
                )
        elif self.status is not RuntimeHarnessStatus.REVISING:
            raise RuntimeLifecycleError(
                "Revision Provider call requires revising Harness phase"
            )

    def _validate_failed_terminal(self, signal: RunFailedSignal) -> None:
        if self.publication_status is not None:
            if signal.publication_status is not self.publication_status:
                raise RuntimeLifecycleError(
                    "failed Runtime publication does not match observed publication"
                )
            return
        expected = _PUBLICATION_BY_HARNESS.get(self.status)
        if signal.publication_status is not expected:
            raise RuntimeLifecycleError(
                "failed Runtime publication does not match terminal Harness"
            )
