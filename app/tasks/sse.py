"""Finite, cursor-replayable Server-Sent Events projection for task events."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from typing import Protocol
from uuid import UUID

from app.tasks.models import ReviewTaskView, TaskStatus
from app.tasks.reliable_runtime import TaskEventPage, TaskLifecycleEvent
from app.tasks.service import TaskServiceError


_TERMINAL_STATUSES = frozenset(
    {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)
_STREAM_ERROR_FRAME = 'event: stream.error\ndata: {"code":"service_unavailable"}\n\n'
_KEEPALIVE_FRAME = ": keep-alive\n\n"


class TaskEventSource(Protocol):
    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView: ...

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int,
        limit: int,
    ) -> TaskEventPage: ...


class TaskEventStreamServiceError(RuntimeError):
    _CODES = frozenset({"task_not_found", "service_unavailable"})

    def __init__(self, code: str) -> None:
        if code not in self._CODES:
            raise ValueError("unsupported task event stream error code")
        self.code = code
        super().__init__(code)


def resolve_event_cursor(
    *,
    after_cursor: int | None,
    last_event_id: str | None,
) -> int:
    if after_cursor is not None and (
        isinstance(after_cursor, bool) or not isinstance(after_cursor, int) or after_cursor < 0
    ):
        raise ValueError("event cursor is invalid")
    header_cursor: int | None = None
    if last_event_id is not None:
        if not isinstance(last_event_id, str) or not last_event_id.isascii() or not last_event_id.isdigit():
            raise ValueError("Last-Event-ID is invalid")
        header_cursor = int(last_event_id)
    if (
        after_cursor is not None
        and header_cursor is not None
        and after_cursor != header_cursor
    ):
        raise ValueError("event cursor sources conflict")
    return after_cursor if after_cursor is not None else header_cursor or 0


def encode_task_event_frame(event: TaskLifecycleEvent) -> str:
    if not isinstance(event, TaskLifecycleEvent) or not event.has_valid_identity():
        raise ValueError("event must have a valid lifecycle identity")
    # Keep this projection locally allowlisted so the task/SSE layer does not
    # depend back on the FastAPI package (which would make import order matter).
    payload = json.dumps(
        {
            "event_schema_version": "1.0",
            "event_cursor": event.event_cursor,
            "event_identity": event.event_identity,
            "task_id": str(event.task_id),
            "run_id": event.run_id,
            "task_sequence": event.task_sequence,
            "event_kind": event.event_kind.value,
            "status_after": event.status_after.value,
            "lease_generation": event.lease_generation,
            "reason": event.reason,
            "occurred_at": event.occurred_at.isoformat().replace("+00:00", "Z"),
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return (
        f"id: {event.event_cursor}\n"
        "event: task.lifecycle\n"
        f"data: {payload}\n\n"
    )


class TaskEventStreamService:
    def __init__(
        self,
        *,
        task_service: TaskEventSource,
        max_polls: int = 15,
        page_limit: int = 100,
        poll_interval_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not callable(getattr(task_service, "get_task", None)) or not callable(
            getattr(task_service, "read_events", None)
        ):
            raise TypeError("task_service must expose get_task() and read_events()")
        if not isinstance(max_polls, int) or not 1 <= max_polls <= 300:
            raise ValueError("max_polls must be between 1 and 300")
        if not isinstance(page_limit, int) or not 1 <= page_limit <= 100:
            raise ValueError("page_limit must be between 1 and 100")
        if not isinstance(poll_interval_seconds, (int, float)) or not 0 <= poll_interval_seconds <= 30:
            raise ValueError("poll_interval_seconds must be between 0 and 30")
        if not callable(sleep):
            raise TypeError("sleep must be callable")
        self._task_service = task_service
        self._max_polls = max_polls
        self._page_limit = page_limit
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._sleep = sleep

    def preflight(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        try:
            task = self._task_service.get_task(owner_id=owner_id, task_id=task_id)
        except TaskServiceError as error:
            code = "task_not_found" if error.code == "task_not_found" else "service_unavailable"
            raise TaskEventStreamServiceError(code) from None
        except Exception:
            raise TaskEventStreamServiceError("service_unavailable") from None
        if not isinstance(task, ReviewTaskView) or task.task_id != task_id:
            raise TaskEventStreamServiceError("service_unavailable")
        return task

    def stream(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int,
    ) -> Iterator[str]:
        cursor = after_cursor
        for poll_number in range(self._max_polls):
            try:
                page = self._task_service.read_events(
                    owner_id=owner_id,
                    task_id=task_id,
                    after_cursor=cursor,
                    limit=self._page_limit,
                )
                if not isinstance(page, TaskEventPage) or page.after_cursor != cursor:
                    raise ValueError("event source returned an invalid page")
                if any(event.task_id != task_id for event in page.events):
                    raise ValueError("event source identity drifted")
                if not page.events:
                    yield _KEEPALIVE_FRAME
                for event in page.events:
                    yield encode_task_event_frame(event)
                    cursor = event.event_cursor
                    if event.status_after in _TERMINAL_STATUSES:
                        return
                if page.has_more:
                    continue
            except Exception:
                yield _STREAM_ERROR_FRAME
                return
            if poll_number + 1 < self._max_polls:
                self._sleep(self._poll_interval_seconds)


__all__ = [
    "TaskEventStreamService",
    "TaskEventStreamServiceError",
    "encode_task_event_frame",
    "resolve_event_cursor",
]
