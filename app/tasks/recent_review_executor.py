"""The 6A-4 bridge from a claimed SQL task to the existing product use case."""

from __future__ import annotations

from typing import Literal, Protocol, TypeAlias

from app.product.recent_review import RecentReviewProductRequest
from app.product.recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationResult,
)
from app.tasks.fingerprint import compute_task_request_fingerprint
from app.tasks.models import ReviewTask, TaskStatus, TaskTerminal

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


class RecentReviewTaskExecutor:
    """Execute exactly one claimed task and return only verified terminal data."""

    def __init__(
        self,
        *,
        application_service: RecentReviewApplicationPort,
        evidence_verifier: TerminalEvidenceVerifier,
    ) -> None:
        if not callable(getattr(application_service, "review", None)):
            raise TypeError("application_service must expose review()")
        if not callable(getattr(evidence_verifier, "terminal_for", None)):
            raise TypeError("evidence_verifier must expose terminal_for()")
        self._application = application_service
        self._evidence = evidence_verifier

    def execute(self, task: ReviewTask) -> TaskTerminal:
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        if task.status is not TaskStatus.RUNNING or task.worker_id is None:
            raise RecentReviewTaskExecutionError("task_not_running")
        if task.task_kind != "recent_review" or task.schema_version != "1.0":
            raise RecentReviewTaskExecutionError("task_contract_invalid")

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
            result = self._application.review(request, run_id=task.run_id)
        except RecentReviewApplicationError:
            raise RecentReviewTaskExecutionError("application_failed") from None
        except Exception:
            raise RecentReviewTaskExecutionError("application_failed") from None
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
        return terminal


__all__ = [
    "RecentReviewApplicationPort",
    "RecentReviewTaskExecutionError",
    "RecentReviewTaskExecutionErrorCode",
    "RecentReviewTaskExecutor",
]
