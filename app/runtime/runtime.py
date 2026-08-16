"""The first framework-neutral synchronous AgentRuntime composition."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from app.agent.context import ContextBuilderV1
from app.agent.draft import SkillAgentDraftPreparer
from app.agent.loop import AgentLoop
from app.harness.models import RunManifest, RunStatus
from app.harness.store import FileRunStore
from app.providers.protocol import LLMProvider
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
    observe_runtime_signal,
)
from app.runtime.recorder import RuntimeRecorder, RuntimeRecorderError
from app.runtime.signals import (
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RunStartedSignal,
    RuntimeFailureStage,
    RuntimePublicationStatus,
    RuntimeSignal,
)
from app.runtime.store import RuntimeTraceStore
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    ValidatedSkillExecution,
)
from app.skills.review_executor import (
    SkillReviewExecutionError,
    SkillReviewExecutor,
)
from app.tools.adapters import build_knowledge_tools, build_llm_tools
from app.tools.adapters.llm import LLM_CHAT_RETRY_MAX_ATTEMPTS
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .models import (
    RuntimeArtifactReference,
    RuntimeEvent,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimeRunRequest,
    RuntimeRunResult,
    RuntimeStreamItem,
    RuntimeStatus,
)


_CONTEXT_CONTRACT_VERSION = "1.0.0"
_PROMPT_PROFILE_VERSION = "1.0.0"
_HARNESS_VERSION = "1.0.0"


class RuntimeCompositionError(RuntimeError):
    """Raised when trusted Runtime dependencies cannot be composed."""


@dataclass(frozen=True)
class RuntimeExecutionBundle:
    """The three business components required by one reviewed Skill run."""

    draft_preparer: SkillAgentDraftPreparer
    evaluator: Any
    reviser: Any


EvaluatorFactory = Callable[[ToolRuntime], Any]
ReviserFactory = Callable[[ToolRuntime], Any]


class RuntimeExecutionFactory:
    """Build one run-scoped Agent/Harness composition from stable dependencies.

    This is dependency injection, not another orchestration framework.  The
    same observed provider is used for AgentLoop and the Harness ``llm.chat``
    tools, while the Agent receives only the knowledge tool registry.
    """

    def __init__(
        self,
        *,
        knowledge_provider: Any,
        evaluator_factory: EvaluatorFactory,
        reviser_factory: ReviserFactory,
    ) -> None:
        if not callable(evaluator_factory):
            raise TypeError("evaluator_factory must be callable")
        if not callable(reviser_factory):
            raise TypeError("reviser_factory must be callable")
        self._knowledge_provider = knowledge_provider
        self._evaluator_factory = evaluator_factory
        self._reviser_factory = reviser_factory

    def build(
        self,
        *,
        provider: ObservedLLMProvider,
        observer: RuntimeSignalObserver,
    ) -> RuntimeExecutionBundle:
        knowledge_registry = ToolRegistry()
        for definition in build_knowledge_tools(self._knowledge_provider):
            knowledge_registry.register(definition)

        agent_loop = AgentLoop(
            provider=provider,
            tool_registry=knowledge_registry,
            tool_runtime=ToolRuntime(knowledge_registry),
        )

        harness_llm_registry = ToolRegistry()
        for definition in build_llm_tools(provider):
            harness_llm_registry.register(definition)
        harness_llm_runtime = ToolRuntime(harness_llm_registry)

        evaluator = self._evaluator_factory(harness_llm_runtime)
        reviser = self._reviser_factory(harness_llm_runtime)
        if not callable(getattr(evaluator, "evaluate", None)):
            raise RuntimeCompositionError(
                "evaluator_factory returned an invalid evaluator"
            )
        if not callable(getattr(reviser, "revise", None)):
            raise RuntimeCompositionError(
                "reviser_factory returned an invalid reviser"
            )

        return RuntimeExecutionBundle(
            draft_preparer=SkillAgentDraftPreparer(
                agent_loop,
                observer=observer,
            ),
            evaluator=evaluator,
            reviser=reviser,
        )


RuntimeEventSink = Callable[[RuntimeEvent], None]


class _RecorderObserver:
    """Adapt the Runtime recorder to the component observer port."""

    def __init__(
        self,
        recorder: RuntimeRecorder,
        event_sink: RuntimeEventSink | None = None,
    ) -> None:
        self._recorder = recorder
        self._event_sink = event_sink

    def observe(self, signal: RuntimeSignal) -> None:
        event = self._recorder.emit(signal)
        if self._event_sink is not None:
            self._event_sink(event)


_STREAM_END = object()


class _RuntimeStreamPublisher:
    """Best-effort queue publisher isolated from the trusted Runtime path."""

    def __init__(
        self,
        items: "queue.Queue[object]",
        closed: threading.Event,
    ) -> None:
        self._items = items
        self._closed = closed
        self._failure: BaseException | None = None

    @property
    def failure(self) -> BaseException | None:
        return self._failure

    def publish_event(self, event: RuntimeEvent) -> None:
        self._put(RuntimeStreamItem(kind="event", event=event))

    def publish_result(self, result: RuntimeRunResult) -> None:
        self._put(RuntimeStreamItem(kind="result", result=result))

    def fail(self, error: BaseException) -> None:
        self._failure = error

    def finish(self) -> None:
        self._put(_STREAM_END)

    def _put(self, item: object) -> None:
        while not self._closed.is_set():
            try:
                self._items.put(item, timeout=0.05)
                return
            except queue.Full:
                continue


class AgentRuntimeV1:
    """Run one selected Skill synchronously and persist one safe Runtime Trace."""

    def __init__(
        self,
        *,
        runs_root: str | Path,
        catalog: SkillCatalog,
        provider: LLMProvider,
        execution_factory: RuntimeExecutionFactory,
        context_builder: ContextBuilderV1 | None = None,
    ) -> None:
        if not isinstance(catalog, SkillCatalog):
            raise TypeError("catalog must be a SkillCatalog")
        if not isinstance(provider, LLMProvider):
            raise TypeError("provider must satisfy LLMProvider")
        if not isinstance(execution_factory, RuntimeExecutionFactory):
            raise TypeError(
                "execution_factory must be a RuntimeExecutionFactory"
            )
        self._runs_root = Path(runs_root).resolve()
        self._catalog = catalog
        self._provider = provider
        self._execution_factory = execution_factory
        self._context_builder = context_builder or ContextBuilderV1()

    def run(self, request: RuntimeRunRequest) -> RuntimeRunResult:
        """Execute one request; all terminal truth comes from the Harness/Trace."""

        if not isinstance(request, RuntimeRunRequest):
            raise TypeError("request must be a RuntimeRunRequest")

        return self._run_with_sink(request, event_sink=None)

    def stream(
        self,
        request: RuntimeRunRequest,
        *,
        queue_size: int = 64,
    ) -> Iterator[RuntimeStreamItem]:
        """Yield live Runtime events followed by one final run result."""

        if not isinstance(request, RuntimeRunRequest):
            raise TypeError("request must be a RuntimeRunRequest")
        if not 1 <= queue_size <= 1024:
            raise ValueError("queue_size must be between 1 and 1024")

        def iterate() -> Iterator[RuntimeStreamItem]:
            items: "queue.Queue[object]" = queue.Queue(maxsize=queue_size)
            closed = threading.Event()
            publisher = _RuntimeStreamPublisher(items, closed)

            def worker() -> None:
                try:
                    result = self._run_with_sink(
                        request,
                        event_sink=publisher.publish_event,
                    )
                    publisher.publish_result(result)
                except BaseException as exc:
                    publisher.fail(exc)
                finally:
                    publisher.finish()

            thread = threading.Thread(
                target=worker,
                name=f"riftcoach-runtime-{request.run_id}",
                daemon=True,
            )
            thread.start()
            try:
                while True:
                    item = items.get()
                    if item is _STREAM_END:
                        if publisher.failure is not None:
                            raise publisher.failure
                        return
                    if not isinstance(item, RuntimeStreamItem):
                        raise RuntimeCompositionError(
                            "runtime stream received an invalid item"
                        )
                    yield item
            finally:
                closed.set()

        return iterate()

    def _run_with_sink(
        self,
        request: RuntimeRunRequest,
        *,
        event_sink: RuntimeEventSink | None,
    ) -> RuntimeRunResult:
        try:
            return self._execute(request, event_sink=event_sink)
        except (RuntimeObservationError, RuntimeRecorderError):
            return RuntimeRunResult(
                run_id=request.run_id,
                runtime_status=RuntimeStatus.FAILED,
                publication_status=self._known_publication_status(
                    request.run_id
                ),
                terminal_reason="observation_failed",
                output=None,
                trace_reference=None,
            )

    def _execute(
        self,
        request: RuntimeRunRequest,
        *,
        event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        """Single synchronous execution core reserved for run/stream parity."""

        selected = request.execution_request.router_decision
        if selected.selected_skill is None or selected.selected_skill_version is None:
            # RuntimeRunRequest rejects this at validation time.  Keep a
            # defensive guard for objects created through unsafe model APIs.
            raise RuntimeCompositionError(
                "Runtime execution requires a selected Skill identity"
            )

        recorder = RuntimeRecorder(
            run_id=request.run_id,
            event_budget=request.policy.event_budget,
        )
        observer = _RecorderObserver(recorder, event_sink)
        identity = self._identity(
            skill_name=selected.selected_skill,
            skill_version=selected.selected_skill_version,
        )
        trace_store = RuntimeTraceStore(self._runs_root, request.run_id)

        observe_runtime_signal(
            observer,
            RunStartedSignal(
                skill_name=identity.skill_name,
                skill_version=identity.skill_version,
                runtime_policy_version=request.policy.policy_version,
            ),
        )

        if self._required_event_budget(request.policy) > request.policy.event_budget:
            return self._finish_failure(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                stage=RuntimeFailureStage.BOUNDARY,
                code="runtime_policy_rejected",
                artifacts=(),
                event_sink=event_sink,
            )

        try:
            execution = SkillExecutionBoundary(self._catalog).validate(
                request.execution_request
            )
            self._validate_policy_against_skill(request.policy, execution)
            observe_runtime_signal(
                observer,
                ExecutionValidatedSignal(
                    input_artifact_sha256s=(
                        execution.input_artifacts.player_summary.sha256,
                        execution.input_artifacts.deterministic_report.sha256,
                    )
                ),
            )
        except RuntimeObservationError:
            raise
        except Exception:
            return self._finish_failure(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                stage=RuntimeFailureStage.BOUNDARY,
                code="execution_validation_failed",
                artifacts=(),
                event_sink=event_sink,
            )

        try:
            context = self._context_builder.build(
                execution,
                max_context_tokens=request.policy.max_context_tokens,
            )
            observe_runtime_signal(
                observer,
                ContextBuiltSignal(
                    context_contract_version=_CONTEXT_CONTRACT_VERSION,
                    estimated_context_units=context.estimated_tokens,
                    omitted_item_ids=context.omitted_section_ids,
                ),
            )
        except RuntimeObservationError:
            raise
        except Exception:
            return self._finish_failure(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                stage=RuntimeFailureStage.CONTEXT,
                code="context_build_failed",
                artifacts=(),
                event_sink=event_sink,
            )

        try:
            observed_provider = ObservedLLMProvider(
                delegate=self._provider,
                observer=observer,
            )
            bundle = self._execution_factory.build(
                provider=observed_provider,
                observer=observer,
            )
            execution_result = SkillReviewExecutor(
                runs_root=self._runs_root,
                draft_preparer=bundle.draft_preparer,
                evaluator=bundle.evaluator,
                reviser=bundle.reviser,
                max_revisions=request.policy.max_revisions,
            ).execute(
                execution=execution,
                context=context,
                observer=observer,
            )
        except RuntimeObservationError:
            raise
        except SkillReviewExecutionError:
            if self._known_publication_status(request.run_id) is None:
                return self._finish_failure(
                    recorder=recorder,
                    trace_store=trace_store,
                    identity=identity,
                    policy=request.policy,
                    stage=RuntimeFailureStage.HARNESS,
                    code="harness_execution_failed",
                    artifacts=(),
                    event_sink=event_sink,
                )
            return self._finish_failure_from_store(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                run_id=request.run_id,
                stage=RuntimeFailureStage.PUBLICATION,
                code="typed_output_build_failed",
                event_sink=event_sink,
            )
        except Exception:
            return self._finish_failure(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                stage=RuntimeFailureStage.HARNESS,
                code="harness_execution_failed",
                artifacts=(),
                event_sink=event_sink,
            )

        try:
            artifacts = self._project_artifacts(request.run_id)
        except RuntimeObservationError:
            raise
        except Exception:
            return self._finish_failure_from_store(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=request.policy,
                run_id=request.run_id,
                stage=RuntimeFailureStage.PUBLICATION,
                code="artifact_integrity_failed",
                event_sink=event_sink,
            )

        return self._finish_success(
            recorder=recorder,
            trace_store=trace_store,
            identity=identity,
            policy=request.policy,
            output=execution_result.output,
            artifacts=artifacts,
            event_sink=event_sink,
        )

    def _finish_success(
        self,
        *,
        recorder: RuntimeRecorder,
        trace_store: RuntimeTraceStore,
        identity: RuntimeIdentitySnapshot,
        policy: RuntimePolicySnapshot,
        output: Any,
        artifacts: tuple[RuntimeArtifactReference, ...],
        event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        publication = _publication_signal(recorder)
        if publication is None:
            return self._finish_failure(
                recorder=recorder,
                trace_store=trace_store,
                identity=identity,
                policy=policy,
                stage=RuntimeFailureStage.HARNESS,
                code="publication_missing",
                artifacts=artifacts,
                event_sink=event_sink,
            )

        candidate = recorder.prepare_terminal(
            RunCompletedSignal(
                publication_status=publication.publication_status,
                terminal_reason=publication.terminal_reason,
            )
        )
        try:
            trace = recorder.build_trace(
                identity=identity,
                policy=policy,
                artifacts=artifacts,
                terminal_candidate=candidate,
            )
        except RuntimeObservationError:
            recorder.abort_terminal(candidate)
            raise
        except Exception:
            recorder.abort_terminal(candidate)
            return self._commit_failed_without_trace(
                recorder=recorder,
                publication_status=publication.publication_status,
                stage=RuntimeFailureStage.OBSERVABILITY,
                code="observation_failed",
                event_sink=event_sink,
            )

        try:
            reference = trace_store.write_trace(trace)
        except Exception:
            recorder.abort_terminal(candidate)
            return self._commit_failed_without_trace(
                recorder=recorder,
                publication_status=publication.publication_status,
                stage=RuntimeFailureStage.OBSERVABILITY,
                code="trace_persistence_failed",
                event_sink=event_sink,
            )

        committed = recorder.commit_terminal(candidate)
        if event_sink is not None:
            event_sink(committed)
        return RuntimeRunResult(
            run_id=recorder.events[0].run_id,
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=publication.publication_status,
            terminal_reason=publication.terminal_reason,
            output=output,
            trace_reference=reference,
        )

    def _finish_failure_from_store(
        self,
        *,
        recorder: RuntimeRecorder,
        trace_store: RuntimeTraceStore,
        identity: RuntimeIdentitySnapshot,
        policy: RuntimePolicySnapshot,
        run_id: str,
        stage: RuntimeFailureStage,
        code: str,
        event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        try:
            artifacts = self._project_artifacts(run_id)
        except RuntimeObservationError:
            raise
        except Exception:
            artifacts = ()
        known_publication = self._known_publication_status(run_id)
        return self._finish_failure(
            recorder=recorder,
            trace_store=trace_store,
            identity=identity,
            policy=policy,
            stage=stage,
            code=code,
            artifacts=artifacts,
            known_publication_status=known_publication,
            event_sink=event_sink,
        )

    def _finish_failure(
        self,
        *,
        recorder: RuntimeRecorder,
        trace_store: RuntimeTraceStore,
        identity: RuntimeIdentitySnapshot,
        policy: RuntimePolicySnapshot,
        stage: RuntimeFailureStage,
        code: str,
        artifacts: tuple[RuntimeArtifactReference, ...],
        known_publication_status: RuntimePublicationStatus | None = None,
        event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        publication = _publication_signal(recorder)
        publication_status = (
            publication.publication_status
            if publication is not None
            else known_publication_status
        )
        candidate = recorder.prepare_terminal(
            RunFailedSignal(
                failure_stage=stage,
                failure_code=code,
                publication_status=publication_status,
            )
        )
        try:
            trace = recorder.build_trace(
                identity=identity,
                policy=policy,
                artifacts=artifacts,
                terminal_candidate=candidate,
            )
        except RuntimeObservationError:
            recorder.abort_terminal(candidate)
            raise
        except Exception:
            recorder.abort_terminal(candidate)
            return self._commit_failed_without_trace(
                recorder=recorder,
                publication_status=publication_status,
                stage=stage,
                code=code,
                event_sink=event_sink,
            )

        try:
            reference = trace_store.write_trace(trace)
        except Exception:
            recorder.abort_terminal(candidate)
            return self._commit_failed_without_trace(
                recorder=recorder,
                publication_status=publication_status,
                stage=RuntimeFailureStage.OBSERVABILITY,
                code="trace_persistence_failed",
                event_sink=event_sink,
            )

        committed = recorder.commit_terminal(candidate)
        if event_sink is not None:
            event_sink(committed)
        return RuntimeRunResult(
            run_id=recorder.events[0].run_id,
            runtime_status=RuntimeStatus.FAILED,
            publication_status=publication_status,
            terminal_reason=code,
            output=None,
            trace_reference=reference,
        )

    @staticmethod
    def _commit_failed_without_trace(
        *,
        recorder: RuntimeRecorder,
        publication_status: RuntimePublicationStatus | None,
        stage: RuntimeFailureStage,
        code: str,
        event_sink: RuntimeEventSink | None = None,
    ) -> RuntimeRunResult:
        committed = recorder.emit(
            RunFailedSignal(
                failure_stage=stage,
                failure_code=code,
                publication_status=publication_status,
            )
        )
        if event_sink is not None:
            event_sink(committed)
        return RuntimeRunResult(
            run_id=recorder.events[0].run_id,
            runtime_status=RuntimeStatus.FAILED,
            publication_status=publication_status,
            terminal_reason=code,
            output=None,
            trace_reference=None,
        )

    def _project_artifacts(
        self,
        run_id: str,
    ) -> tuple[RuntimeArtifactReference, ...]:
        from .artifacts import project_artifact_references

        store = FileRunStore(self._runs_root, run_id)
        manifest: RunManifest = store.read_manifest()
        return project_artifact_references(manifest=manifest, store=store)

    def _known_publication_status(
        self,
        run_id: str,
    ) -> RuntimePublicationStatus | None:
        try:
            status = FileRunStore(self._runs_root, run_id).read_manifest().status
        except Exception:
            return None
        if status not in {
            RunStatus.PUBLISHED,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }:
            return None
        return RuntimePublicationStatus(status.value)

    def _identity(
        self,
        *,
        skill_name: str,
        skill_version: str,
    ) -> RuntimeIdentitySnapshot:
        return RuntimeIdentitySnapshot(
            skill_name=skill_name,
            skill_version=skill_version,
            context_contract_version=_CONTEXT_CONTRACT_VERSION,
            prompt_profile_id=f"{skill_name}-coach",
            prompt_profile_version=_PROMPT_PROFILE_VERSION,
            provider_id=self._provider.provider_name,
            provider_model=self._provider.model_name,
            harness_version=_HARNESS_VERSION,
        )

    @staticmethod
    def _required_event_budget(policy: RuntimePolicySnapshot) -> int:
        # One Evaluation attempt may use the initial structured call plus one
        # bounded repair.  Each Harness llm.chat ToolRuntime call may consume
        # its full retry policy, and each revision may make one more llm.chat
        # call.  This is deliberately a worst-case pre-I/O bound.
        evaluation_rounds = 1 + policy.max_revisions
        provider_events_per_harness_llm_call = (
            2 * LLM_CHAT_RETRY_MAX_ATTEMPTS
        )
        return (
            3  # run_started + execution_validated + context_built
            + (2 * policy.max_iterations)  # Agent Provider start/end
            + (2 * policy.max_tool_calls)  # business Tool start/end
            + 1  # Agent terminal
            + 4  # facts/knowledge/draft/evaluating transitions
            + (
                2
                * provider_events_per_harness_llm_call
                * evaluation_rounds
            )  # Evaluation plus optional repair for every round
            + evaluation_rounds  # evaluation_completed
            + (
                provider_events_per_harness_llm_call
                * policy.max_revisions
            )  # one revision Provider call per revision
            + (3 * policy.max_revisions)  # revision lifecycle transitions
            + 2  # passed + published is the longest final transition path
            + 1  # publication_decided
            + 1  # Runtime terminal
        )

    @staticmethod
    def _validate_policy_against_skill(
        policy: RuntimePolicySnapshot,
        execution: ValidatedSkillExecution,
    ) -> None:
        budgets = execution.skill.manifest.budgets
        gate = execution.skill.manifest.quality_gate
        if policy.max_iterations != budgets.max_iterations:
            raise ValueError("runtime policy max_iterations mismatch")
        if policy.max_tool_calls != budgets.max_tool_calls:
            raise ValueError("runtime policy max_tool_calls mismatch")
        if policy.timeout_s != budgets.timeout_s:
            raise ValueError("runtime policy timeout mismatch")
        if policy.max_context_tokens > budgets.max_context_tokens:
            raise ValueError("runtime policy context ceiling exceeds Skill budget")
        if policy.publish_score_threshold != gate.minimum_score:
            raise ValueError("runtime policy quality threshold mismatch")
        if policy.max_revisions > 1:
            raise ValueError("runtime policy max_revisions exceeds V1 Harness bound")
        if policy.allow_deterministic_fallback != gate.allow_deterministic_fallback:
            raise ValueError("runtime policy fallback setting mismatch")


def _publication_signal(
    recorder: RuntimeRecorder,
) -> PublicationDecidedSignal | None:
    for event in reversed(recorder.events):
        if isinstance(event.signal, PublicationDecidedSignal):
            return event.signal
    return None


__all__ = [
    "AgentRuntimeV1",
    "RuntimeCompositionError",
    "RuntimeExecutionBundle",
    "RuntimeExecutionFactory",
]
