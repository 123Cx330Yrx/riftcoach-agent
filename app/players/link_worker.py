from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.lol.account_resolver import RiotAccountResolutionError
from app.players.models import (
    PlayerLinkFailure,
    PlayerLinkStatus,
    PlayerLinkTask,
    ResolvedRiotAccount,
    RoutingRegion,
    WorkerId,
)
from app.players.ports import PlayerRepository
from app.tasks.observability import TaskObservability
from app.workers.polling import PollingPolicy


Clock = Callable[[], datetime]
RandomSource = Callable[[], float]
PlayerLinkWorkerErrorCode: TypeAlias = Literal[
    "link_claim_failed",
    "link_claim_invalid",
    "link_terminal_update_failed",
    "link_terminal_invalid",
    "polling_control_failed",
]
_ERROR_CODES = frozenset(
    {
        "link_claim_failed",
        "link_claim_invalid",
        "link_terminal_update_failed",
        "link_terminal_invalid",
        "polling_control_failed",
    }
)
_FAILURE_CODES = frozenset(
    {
        "player_not_found",
        "riot_authentication_failed",
        "riot_rate_limited",
        "upstream_timeout",
        "upstream_unavailable",
        "account_response_invalid",
        "relationship_role_conflict",
    }
)
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)


class PlayerLinkResolver(Protocol):
    def resolve(
        self,
        *,
        routing_region: RoutingRegion,
        game_name: str,
        tag_line: str,
    ) -> ResolvedRiotAccount: ...


class StopSignal(Protocol):
    def is_set(self) -> bool: ...

    def wait(self, timeout: float) -> bool: ...


class PlayerLinkWorkerError(RuntimeError):
    def __init__(self, code: PlayerLinkWorkerErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported player-link worker error code")
        self.code = code
        super().__init__(code)


class PlayerLinkWorkerIterationStatus(StrEnum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    OWNERSHIP_LOST = "ownership_lost"


@dataclass(frozen=True, slots=True)
class PlayerLinkWorkerIterationResult:
    status: PlayerLinkWorkerIterationStatus
    link_task_id: UUID | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is PlayerLinkWorkerIterationStatus.IDLE:
            if self.link_task_id is not None or self.reason is not None:
                raise ValueError("idle iteration cannot include task data")
            return
        if not isinstance(self.link_task_id, UUID):
            raise ValueError("non-idle iteration requires link_task_id")
        if self.status is PlayerLinkWorkerIterationStatus.FAILED:
            if self.reason not in _FAILURE_CODES:
                raise ValueError("failed iteration requires an allowlisted reason")
        elif self.reason is not None:
            raise ValueError("non-failed iteration cannot include a reason")


class PlayerLinkWorker:
    def __init__(
        self,
        *,
        repository: PlayerRepository,
        resolver: PlayerLinkResolver,
        worker_id: str,
        clock: Clock | None = None,
        polling_policy: PollingPolicy | None = None,
        random_source: RandomSource | None = None,
        observability: TaskObservability | None = None,
    ) -> None:
        for method_name in ("claim_next_link", "resolve_link", "fail_link"):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(getattr(resolver, "resolve", None)):
            raise TypeError("resolver must expose resolve()")
        try:
            normalized_worker_id = _WORKER_ID_ADAPTER.validate_python(
                worker_id,
                strict=True,
            )
        except (TypeError, ValueError, ValidationError):
            raise TypeError("worker_id must be a bounded safe identifier") from None
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        if polling_policy is not None and not isinstance(
            polling_policy,
            PollingPolicy,
        ):
            raise TypeError("polling_policy must be a PollingPolicy")
        if random_source is not None and not callable(random_source):
            raise TypeError("random_source must be callable")
        if observability is not None and not isinstance(
            observability,
            TaskObservability,
        ):
            raise TypeError("observability must be a TaskObservability")

        self._repository = repository
        self._resolver = resolver
        self._worker_id = normalized_worker_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._polling_policy = polling_policy or PollingPolicy()
        self._random_source = random_source or random.random
        self._observability = observability

    def run_once(self) -> PlayerLinkWorkerIterationResult:
        claim_started = time.perf_counter()
        try:
            claimed = self._repository.claim_next_link(
                worker_id=self._worker_id,
                now=self._clock(),
            )
        except Exception:
            self._observe("player_link.claim_failed", {"outcome": "failed"})
            raise PlayerLinkWorkerError("link_claim_failed") from None

        if claimed is None:
            self._observe("player_link.idle", {"status": "idle"})
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.IDLE,
                link_task_id=None,
            )
        if (
            not isinstance(claimed, PlayerLinkTask)
            or claimed.status is not PlayerLinkStatus.RUNNING
            or claimed.worker_id != self._worker_id
        ):
            self._observe("player_link.claim_invalid", {"outcome": "failed"})
            raise PlayerLinkWorkerError("link_claim_invalid")

        self._observe(
            "player_link.claimed",
            {
                "task_id": str(claimed.link_task_id),
                "worker_id": self._worker_id,
                "status": claimed.status.value,
                "queue_delay_ms": max(
                    0.0,
                    (claimed.claimed_at - claimed.created_at).total_seconds() * 1000,
                ),
            },
        )
        self._observe_latency(
            "player_link.claim",
            max(0.0, (time.perf_counter() - claim_started) * 1000),
        )

        resolution_started = time.perf_counter()
        failure: PlayerLinkFailure | None = None
        account: ResolvedRiotAccount | None = None
        try:
            candidate = self._resolver.resolve(
                routing_region=claimed.routing_region,
                game_name=claimed.game_name,
                tag_line=claimed.tag_line,
            )
            if (
                not isinstance(candidate, ResolvedRiotAccount)
                or candidate.routing_region is not claimed.routing_region
            ):
                failure = _failure("account_response_invalid")
            else:
                account = candidate
        except RiotAccountResolutionError as error:
            failure = error.failure
        except Exception:
            failure = _failure("upstream_unavailable")
        self._observe_latency(
            "player_link.resolve",
            max(0.0, (time.perf_counter() - resolution_started) * 1000),
        )

        if account is not None:
            return self._commit_resolution(claimed, account)
        if failure is None:
            failure = _failure("account_response_invalid")
        return self._commit_failure(claimed, failure)

    def run_forever(self, stop_signal: StopSignal) -> None:
        if not callable(getattr(stop_signal, "is_set", None)) or not callable(
            getattr(stop_signal, "wait", None)
        ):
            raise TypeError("stop_signal must expose is_set() and wait()")

        idle_count = 0
        while self._is_stopped(stop_signal) is False:
            result = self.run_once()
            if result.status is not PlayerLinkWorkerIterationStatus.IDLE:
                idle_count = 0
                continue

            idle_count += 1
            try:
                delay = self._polling_policy.delay_for_idle(
                    idle_count=idle_count,
                    jitter_unit=self._random_source(),
                )
                if stop_signal.wait(delay):
                    return
            except Exception:
                raise PlayerLinkWorkerError("polling_control_failed") from None

    def _commit_resolution(
        self,
        claimed: PlayerLinkTask,
        account: ResolvedRiotAccount,
    ) -> PlayerLinkWorkerIterationResult:
        try:
            terminal = self._repository.resolve_link(
                link_task_id=claimed.link_task_id,
                worker_id=self._worker_id,
                resolved_account=account,
            )
        except Exception:
            self._observe(
                "player_link.terminal_update_failed",
                {"task_id": str(claimed.link_task_id), "outcome": "failed"},
            )
            raise PlayerLinkWorkerError("link_terminal_update_failed") from None
        if terminal is None:
            self._observe_terminal(
                claimed.link_task_id,
                status=PlayerLinkWorkerIterationStatus.OWNERSHIP_LOST,
            )
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.OWNERSHIP_LOST,
                link_task_id=claimed.link_task_id,
            )
        if not _matches_terminal_owner(terminal, claimed, self._worker_id):
            raise PlayerLinkWorkerError("link_terminal_invalid")
        if terminal.status is PlayerLinkStatus.SUCCEEDED:
            self._observe_terminal(
                claimed.link_task_id,
                status=PlayerLinkWorkerIterationStatus.SUCCEEDED,
            )
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.SUCCEEDED,
                link_task_id=claimed.link_task_id,
            )
        if (
            terminal.status is PlayerLinkStatus.FAILED
            and terminal.failure is not None
            and terminal.failure.code == "relationship_role_conflict"
        ):
            self._observe_terminal(
                claimed.link_task_id,
                status=PlayerLinkWorkerIterationStatus.FAILED,
                reason=terminal.failure.code,
            )
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.FAILED,
                link_task_id=claimed.link_task_id,
                reason=terminal.failure.code,
            )
        raise PlayerLinkWorkerError("link_terminal_invalid")

    def _commit_failure(
        self,
        claimed: PlayerLinkTask,
        failure: PlayerLinkFailure,
    ) -> PlayerLinkWorkerIterationResult:
        try:
            terminal = self._repository.fail_link(
                link_task_id=claimed.link_task_id,
                worker_id=self._worker_id,
                failure=failure,
            )
        except Exception:
            self._observe(
                "player_link.terminal_update_failed",
                {"task_id": str(claimed.link_task_id), "outcome": "failed"},
            )
            raise PlayerLinkWorkerError("link_terminal_update_failed") from None
        if terminal is None:
            self._observe_terminal(
                claimed.link_task_id,
                status=PlayerLinkWorkerIterationStatus.OWNERSHIP_LOST,
            )
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.OWNERSHIP_LOST,
                link_task_id=claimed.link_task_id,
            )
        if (
            not _matches_terminal_owner(terminal, claimed, self._worker_id)
            or terminal.status is not PlayerLinkStatus.FAILED
            or terminal.failure != failure
        ):
            raise PlayerLinkWorkerError("link_terminal_invalid")
        self._observe_terminal(
            claimed.link_task_id,
            status=PlayerLinkWorkerIterationStatus.FAILED,
            reason=failure.code,
        )
        return PlayerLinkWorkerIterationResult(
            status=PlayerLinkWorkerIterationStatus.FAILED,
            link_task_id=claimed.link_task_id,
            reason=failure.code,
        )

    @staticmethod
    def _is_stopped(stop_signal: StopSignal) -> bool:
        try:
            return bool(stop_signal.is_set())
        except Exception:
            raise PlayerLinkWorkerError("polling_control_failed") from None

    def _observe_terminal(
        self,
        link_task_id: UUID,
        *,
        status: PlayerLinkWorkerIterationStatus,
        reason: str | None = None,
    ) -> None:
        metadata: dict[str, object] = {
            "task_id": str(link_task_id),
            "status": status.value,
        }
        if reason is not None:
            metadata["reason"] = reason
        self._observe("player_link.terminal", metadata)

    def _observe(self, name: str, metadata: dict[str, object]) -> None:
        if self._observability is not None:
            self._observability.emit(name, metadata)

    def _observe_latency(self, name: str, latency_ms: float) -> None:
        if self._observability is not None:
            self._observability.observe_latency(name, latency_ms)


def _failure(code: str) -> PlayerLinkFailure:
    return PlayerLinkFailure(
        code=code,
        retryable=code
        in {"riot_rate_limited", "upstream_timeout", "upstream_unavailable"},
    )


def _matches_terminal_owner(
    terminal: object,
    claimed: PlayerLinkTask,
    worker_id: str,
) -> bool:
    return (
        isinstance(terminal, PlayerLinkTask)
        and terminal.link_task_id == claimed.link_task_id
        and terminal.owner_id == claimed.owner_id
        and terminal.worker_id == worker_id
    )


__all__ = [
    "PlayerLinkResolver",
    "PlayerLinkWorker",
    "PlayerLinkWorkerError",
    "PlayerLinkWorkerIterationResult",
    "PlayerLinkWorkerIterationStatus",
]
