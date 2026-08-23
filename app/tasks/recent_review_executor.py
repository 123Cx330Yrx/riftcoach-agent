"""The 6A-4 bridge from a claimed SQL task to the existing product use case."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Literal, Protocol, TypeAlias

from app.conversations.turns import TerminalAssistantTurn
from app.memory.context_models import MemoryContextBinding
from app.product.recent_review import (
    ConversationRecentReviewRequest,
    RecentReviewProductRequest,
)
from app.product.recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationResult,
)
from app.tasks.fingerprint import (
    compute_conversation_review_task_fingerprint,
    compute_task_request_fingerprint,
)
from app.tasks.models import (
    ConversationReviewExecutionTarget,
    ConversationReviewTaskBinding,
    ReviewTask,
    TaskStatus,
    TaskTerminal,
)
from app.runtime.signals import RuntimePublicationStatus

from .reconciliation import TerminalEvidenceVerifier


RecentReviewTaskExecutionErrorCode: TypeAlias = Literal[
    "task_not_running",
    "task_contract_invalid",
    "task_input_invalid",
    "task_fingerprint_mismatch",
    "application_failed",
    "application_result_invalid",
    "run_id_mismatch",
    "terminal_evidence_invalid",
    "terminal_identity_mismatch",
]
_EXECUTION_ERROR_CODES = frozenset(
    {
        "task_not_running",
        "task_contract_invalid",
        "task_input_invalid",
        "task_fingerprint_mismatch",
        "application_failed",
        "application_result_invalid",
        "run_id_mismatch",
        "terminal_evidence_invalid",
        "terminal_identity_mismatch",
    }
)


class RecentReviewTaskExecutionError(RuntimeError):
    """Safe failure from task input, Application, or terminal evidence."""

    def __init__(self, code: RecentReviewTaskExecutionErrorCode) -> None:
        if code not in _EXECUTION_ERROR_CODES:
            raise ValueError("unsupported recent-review task execution error")
        self.code = code
        super().__init__(code)


class RecentReviewApplicationPort(Protocol):
    def review(
        self,
        request: RecentReviewProductRequest,
        *,
        run_id: str,
    ) -> RecentReviewApplicationResult: ...

    def review_by_puuid(
        self,
        request: ConversationRecentReviewRequest,
        *,
        puuid: str,
        routing_region: str,
        game_name: str,
        tag_line: str,
        run_id: str,
        memory_context_binding: MemoryContextBinding | None = None,
    ) -> RecentReviewApplicationResult: ...


class RecentReviewTaskExecutionResult(TaskTerminal):
    terminal_turn: TerminalAssistantTurn | None = None


class RecentReviewTaskExecutor:
    """Execute exactly one claimed task and return only verified terminal data."""

    def __init__(
        self,
        *,
        application_service: RecentReviewApplicationPort,
        evidence_verifier: TerminalEvidenceVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not callable(getattr(application_service, "review", None)):
            raise TypeError("application_service must expose review()")
        if not callable(getattr(evidence_verifier, "terminal_for", None)):
            raise TypeError("evidence_verifier must expose terminal_for()")
        self._application = application_service
        self._evidence = evidence_verifier
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(self, task: ReviewTask) -> RecentReviewTaskExecutionResult:
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        if task.status is not TaskStatus.RUNNING or task.worker_id is None:
            raise RecentReviewTaskExecutionError("task_not_running")
        if task.task_kind != "recent_review":
            raise RecentReviewTaskExecutionError("task_contract_invalid")

        if task.schema_version == "1.0":
            result = self._execute_legacy(task)
        elif task.schema_version == "2.0":
            result = self._execute_conversation_bound(task)
        else:
            raise RecentReviewTaskExecutionError("task_contract_invalid")
        if not isinstance(result, RecentReviewApplicationResult):
            raise RecentReviewTaskExecutionError("application_result_invalid")
        if (
            result.run_id != task.run_id
            or result.output.run_id != task.run_id
            or result.trace_reference.run_id != task.run_id
        ):
            raise RecentReviewTaskExecutionError("run_id_mismatch")

        try:
            terminal = self._evidence.terminal_for(task)
        except Exception:
            raise RecentReviewTaskExecutionError("terminal_evidence_invalid") from None
        if (
            terminal.run_id != task.run_id
            or terminal.publication_status.value
            != result.publication_status.value
            or terminal.terminal_reason != result.terminal_reason
            or terminal.report_available
            != (result.output.report is not None)
            or terminal.trace_reference != result.trace_reference
        ):
            raise RecentReviewTaskExecutionError("terminal_identity_mismatch")
        terminal_turn = None
        if (
            task.schema_version == "2.0"
            and task.conversation_binding is not None
            and result.output.report is not None
            and terminal.artifact_reference is not None
        ):
            binding = task.conversation_binding
            terminal_turn = TerminalAssistantTurn(
                source_task_id=task.task_id,
                binding=MemoryContextBinding(
                    run_id=task.run_id,
                    owner_id=task.owner_id,
                    conversation_id=binding.conversation_id,
                    relationship_id=binding.relationship_id,
                    player_subject_id=binding.player_subject_id,
                    relationship_role=binding.relationship_role,
                ),
                publication_status=RuntimePublicationStatus(
                    terminal.publication_status.value
                ),
                artifact_reference=terminal.artifact_reference,
                assistant_content=result.output.report,
                candidate_proposals=(),
                created_at=self._clock(),
            )
        return RecentReviewTaskExecutionResult(
            **terminal.model_dump(mode="python"),
            terminal_turn=terminal_turn,
        )

    def _execute_legacy(
        self,
        task: ReviewTask,
    ) -> RecentReviewApplicationResult:
        try:
            request = RecentReviewProductRequest.model_validate(
                task.request_payload
            )
            expected_fingerprint = compute_task_request_fingerprint(
                task_kind=task.task_kind,
                schema_version=task.schema_version,
                request_payload=request.model_dump(mode="json"),
            )
        except Exception:
            raise RecentReviewTaskExecutionError("task_input_invalid") from None
        if expected_fingerprint != task.request_fingerprint:
            raise RecentReviewTaskExecutionError("task_fingerprint_mismatch")
        try:
            return self._application.review(request, run_id=task.run_id)
        except RecentReviewApplicationError:
            raise RecentReviewTaskExecutionError("application_failed") from None
        except Exception:
            raise RecentReviewTaskExecutionError("application_failed") from None

    def _execute_conversation_bound(
        self,
        task: ReviewTask,
    ) -> RecentReviewApplicationResult:
        binding = task.conversation_binding
        target = task.execution_target
        if not isinstance(binding, ConversationReviewTaskBinding) or not isinstance(
            target,
            ConversationReviewExecutionTarget,
        ):
            raise RecentReviewTaskExecutionError("task_contract_invalid")
        try:
            request = ConversationRecentReviewRequest.model_validate(
                task.request_payload
            )
            expected_fingerprint = compute_conversation_review_task_fingerprint(
                owner_id=task.owner_id,
                binding=binding,
                request_payload=request.model_dump(mode="json"),
            )
        except Exception:
            raise RecentReviewTaskExecutionError("task_input_invalid") from None
        if expected_fingerprint != task.request_fingerprint:
            raise RecentReviewTaskExecutionError("task_fingerprint_mismatch")

        review_by_puuid = getattr(self._application, "review_by_puuid", None)
        if not callable(review_by_puuid):
            raise RecentReviewTaskExecutionError("application_failed")
        try:
            memory_context_binding = MemoryContextBinding(
                run_id=task.run_id,
                owner_id=task.owner_id,
                conversation_id=binding.conversation_id,
                relationship_id=binding.relationship_id,
                player_subject_id=binding.player_subject_id,
                relationship_role=binding.relationship_role,
            )
            return review_by_puuid(
                request,
                puuid=target.puuid,
                routing_region=target.routing_region.value,
                game_name=target.game_name,
                tag_line=target.tag_line,
                run_id=task.run_id,
                memory_context_binding=memory_context_binding,
            )
        except RecentReviewApplicationError:
            raise RecentReviewTaskExecutionError("application_failed") from None
        except Exception:
            raise RecentReviewTaskExecutionError("application_failed") from None


__all__ = [
    "RecentReviewApplicationPort",
    "RecentReviewTaskExecutionError",
    "RecentReviewTaskExecutionErrorCode",
    "RecentReviewTaskExecutionResult",
    "RecentReviewTaskExecutor",
]
