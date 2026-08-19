from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event
from typing import cast
from uuid import UUID

import pytest

from app.lol.account_resolver import RiotAccountResolutionError
from app.players.link_worker import (
    PlayerLinkResolver,
    PlayerLinkWorker,
    PlayerLinkWorkerError,
    PlayerLinkWorkerIterationStatus,
)
from app.players.models import (
    OwnerPlayerRelationshipRef,
    PlayerLinkFailure,
    PlayerLinkStatus,
    PlayerLinkTask,
    RelationshipRole,
    ResolvedRiotAccount,
    RoutingRegion,
    VerificationStatus,
)
from app.tasks.observability import TaskObservability
from app.workers.polling import PollingPolicy


NOW = datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone.utc)
LINK_TASK_ID = UUID("40000000-0000-4000-8000-000000000001")
SUBJECT_ID = UUID("40000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("40000000-0000-4000-8000-000000000003")


def running_link_task(*, worker_id: str = "link-worker-1") -> PlayerLinkTask:
    claimed_at = NOW + timedelta(seconds=1)
    return PlayerLinkTask(
        link_task_id=LINK_TASK_ID,
        task_kind="player_link",
        schema_version="1.0",
        owner_id="owner-1",
        idempotency_key="link-request-1",
        request_fingerprint="a" * 64,
        routing_region=RoutingRegion.ASIA,
        relationship_role=RelationshipRole.SELF,
        verification_status=VerificationStatus.UNVERIFIED_CLAIM,
        game_name="Private Player",
        tag_line="KR1",
        alias_hash="b" * 64,
        status=PlayerLinkStatus.RUNNING,
        created_at=NOW,
        updated_at=claimed_at,
        claimed_at=claimed_at,
        finished_at=None,
        worker_id=worker_id,
        subject_id=None,
        relationship=None,
        confirmed_game_name=None,
        confirmed_tag_line=None,
        failure=None,
    )


def resolved_account() -> ResolvedRiotAccount:
    return ResolvedRiotAccount(
        routing_region=RoutingRegion.ASIA,
        puuid="private_puuid_123",
        game_name="Confirmed Player",
        tag_line="KR1",
    )


def succeeded_terminal(task: PlayerLinkTask) -> PlayerLinkTask:
    payload = task.model_dump(mode="python")
    payload.update(
        status=PlayerLinkStatus.SUCCEEDED,
        updated_at=NOW + timedelta(seconds=2),
        finished_at=NOW + timedelta(seconds=2),
        subject_id=SUBJECT_ID,
        relationship=OwnerPlayerRelationshipRef(
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
            relationship_role=RelationshipRole.SELF,
            verification_status=VerificationStatus.UNVERIFIED_CLAIM,
        ),
        confirmed_game_name="Confirmed Player",
        confirmed_tag_line="KR1",
        failure=None,
    )
    return PlayerLinkTask.model_validate(payload)


def failed_terminal(
    task: PlayerLinkTask,
    failure: PlayerLinkFailure,
) -> PlayerLinkTask:
    payload = task.model_dump(mode="python")
    payload.update(
        status=PlayerLinkStatus.FAILED,
        updated_at=NOW + timedelta(seconds=2),
        finished_at=NOW + timedelta(seconds=2),
        subject_id=None,
        relationship=None,
        confirmed_game_name=None,
        confirmed_tag_line=None,
        failure=failure,
    )
    return PlayerLinkTask.model_validate(payload)


class FakePlayerRepository:
    def __init__(
        self,
        claims: list[PlayerLinkTask | None] | None = None,
        *,
        sequence: list[str] | None = None,
    ) -> None:
        self.claims = list(claims or [])
        self.sequence = sequence if sequence is not None else []
        self.claim_calls: list[tuple[str, datetime]] = []
        self.resolve_calls: list[tuple[UUID, str, ResolvedRiotAccount]] = []
        self.fail_calls: list[tuple[UUID, str, PlayerLinkFailure]] = []
        self.claim_error: Exception | None = None
        self.resolve_error: Exception | None = None
        self.fail_error: Exception | None = None
        self.resolve_result: object = "auto"
        self.fail_result: object = "auto"
        self.transaction_open = False
        self.last_claimed: PlayerLinkTask | None = None

    def claim_next_link(
        self,
        *,
        worker_id: str,
        now: datetime,
    ) -> PlayerLinkTask | None:
        self.sequence.append("claim_begin")
        self.transaction_open = True
        self.claim_calls.append((worker_id, now))
        if self.claim_error is not None:
            self.transaction_open = False
            raise self.claim_error
        claimed = self.claims.pop(0) if self.claims else None
        self.last_claimed = claimed
        self.transaction_open = False
        self.sequence.append("claim_commit")
        return claimed

    def resolve_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        resolved_account: ResolvedRiotAccount,
    ) -> PlayerLinkTask | None:
        self.sequence.append("resolve_commit")
        self.resolve_calls.append((link_task_id, worker_id, resolved_account))
        if self.resolve_error is not None:
            raise self.resolve_error
        if self.resolve_result is None:
            return None
        if self.resolve_result != "auto":
            return cast(PlayerLinkTask, self.resolve_result)
        assert self.last_claimed is not None
        return succeeded_terminal(self.last_claimed)

    def fail_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        failure: PlayerLinkFailure,
    ) -> PlayerLinkTask | None:
        self.sequence.append("failure_commit")
        self.fail_calls.append((link_task_id, worker_id, failure))
        if self.fail_error is not None:
            raise self.fail_error
        if self.fail_result is None:
            return None
        if self.fail_result != "auto":
            return cast(PlayerLinkTask, self.fail_result)
        assert self.last_claimed is not None
        return failed_terminal(self.last_claimed, failure)


class FakeResolver:
    def __init__(
        self,
        outcome: object,
        *,
        repository: FakePlayerRepository | None = None,
        sequence: list[str] | None = None,
    ) -> None:
        self.outcome = outcome
        self.repository = repository
        self.sequence = sequence if sequence is not None else []
        self.calls: list[tuple[RoutingRegion, str, str]] = []

    def resolve(
        self,
        *,
        routing_region: RoutingRegion,
        game_name: str,
        tag_line: str,
    ) -> object:
        assert self.repository is None or self.repository.transaction_open is False
        self.sequence.append("external_resolve")
        self.calls.append((routing_region, game_name, tag_line))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class StopAfterWaits:
    def __init__(self, count: int) -> None:
        self.remaining = count
        self.stopped = False
        self.waits: list[float] = []

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, timeout: float) -> bool:
        self.waits.append(timeout)
        self.remaining -= 1
        if self.remaining <= 0:
            self.stopped = True
        return self.stopped


def worker(
    repository: FakePlayerRepository,
    resolver: FakeResolver | None = None,
    *,
    policy: PollingPolicy | None = None,
    observability: TaskObservability | None = None,
) -> PlayerLinkWorker:
    return PlayerLinkWorker(
        repository=cast(object, repository),
        resolver=cast(PlayerLinkResolver, resolver or FakeResolver(resolved_account())),
        worker_id="link-worker-1",
        clock=lambda: NOW,
        polling_policy=policy or PollingPolicy(jitter_ratio=0.0),
        random_source=lambda: 0.5,
        observability=observability,
    )


def resolution_error(code: str) -> RiotAccountResolutionError:
    return RiotAccountResolutionError(
        PlayerLinkFailure(
            code=code,
            retryable=code
            in {"riot_rate_limited", "upstream_timeout", "upstream_unavailable"},
        )
    )


def test_run_once_is_idle_without_resolving_or_writing_terminal() -> None:
    repository = FakePlayerRepository([None])
    resolver = FakeResolver(resolved_account())

    result = worker(repository, resolver).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.IDLE
    assert result.link_task_id is None
    assert resolver.calls == []
    assert repository.resolve_calls == []
    assert repository.fail_calls == []


def test_claim_commits_before_external_resolution_and_success_short_transaction() -> None:
    sequence: list[str] = []
    task = running_link_task()
    repository = FakePlayerRepository([task], sequence=sequence)
    resolver = FakeResolver(
        resolved_account(),
        repository=repository,
        sequence=sequence,
    )

    result = worker(repository, resolver).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.SUCCEEDED
    assert result.link_task_id == LINK_TASK_ID
    assert result.reason is None
    assert sequence == [
        "claim_begin",
        "claim_commit",
        "external_resolve",
        "resolve_commit",
    ]
    assert resolver.calls == [
        (RoutingRegion.ASIA, "Private Player", "KR1")
    ]
    assert repository.resolve_calls == [
        (LINK_TASK_ID, "link-worker-1", resolved_account())
    ]
    assert repository.fail_calls == []


@pytest.mark.parametrize(
    "code",
    (
        "player_not_found",
        "riot_authentication_failed",
        "riot_rate_limited",
        "upstream_timeout",
        "upstream_unavailable",
        "account_response_invalid",
    ),
)
def test_safe_resolver_failures_commit_exactly_one_failed_terminal(code: str) -> None:
    task = running_link_task()
    repository = FakePlayerRepository([task])
    resolver = FakeResolver(resolution_error(code))

    result = worker(repository, resolver).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.FAILED
    assert result.reason == code
    assert repository.resolve_calls == []
    assert len(repository.fail_calls) == 1
    assert repository.fail_calls[0][2].code == code


@pytest.mark.parametrize(
    ("outcome", "expected_code"),
    (
        (object(), "account_response_invalid"),
        (RuntimeError("private resolver secret"), "upstream_unavailable"),
    ),
)
def test_bad_or_unexpected_resolver_result_fails_closed(
    outcome: object,
    expected_code: str,
) -> None:
    repository = FakePlayerRepository([running_link_task()])

    result = worker(repository, FakeResolver(outcome)).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.FAILED
    assert result.reason == expected_code
    assert repository.fail_calls[0][2].code == expected_code
    assert "private" not in repr(result)


def test_role_conflict_is_already_atomic_and_is_not_failed_twice() -> None:
    task = running_link_task()
    repository = FakePlayerRepository([task])
    conflict = PlayerLinkFailure(
        code="relationship_role_conflict",
        retryable=False,
    )
    repository.resolve_result = failed_terminal(task, conflict)

    result = worker(repository).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.FAILED
    assert result.reason == "relationship_role_conflict"
    assert len(repository.resolve_calls) == 1
    assert repository.fail_calls == []


@pytest.mark.parametrize("phase", ("resolve", "failure"))
def test_stale_worker_terminal_cas_reports_ownership_loss(phase: str) -> None:
    repository = FakePlayerRepository([running_link_task()])
    if phase == "resolve":
        repository.resolve_result = None
        resolver = FakeResolver(resolved_account())
    else:
        repository.fail_result = None
        resolver = FakeResolver(resolution_error("player_not_found"))

    result = worker(repository, resolver).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.OWNERSHIP_LOST
    assert result.link_task_id == LINK_TASK_ID


@pytest.mark.parametrize("phase", ("claim", "resolve", "failure"))
def test_repository_failure_exposes_only_allowlisted_worker_error(phase: str) -> None:
    repository = FakePlayerRepository([running_link_task()])
    resolver: FakeResolver
    if phase == "claim":
        repository.claim_error = RuntimeError("postgresql://secret@host")
        resolver = FakeResolver(resolved_account())
    elif phase == "resolve":
        repository.resolve_error = RuntimeError("postgresql://secret@host")
        resolver = FakeResolver(resolved_account())
    else:
        repository.fail_error = RuntimeError("postgresql://secret@host")
        resolver = FakeResolver(resolution_error("player_not_found"))

    with pytest.raises(PlayerLinkWorkerError) as caught:
        worker(repository, resolver).run_once()

    expected = (
        "link_claim_failed"
        if phase == "claim"
        else "link_terminal_update_failed"
    )
    assert caught.value.code == expected
    assert str(caught.value) == expected
    assert "postgresql" not in repr(caught.value)


def test_invalid_claim_or_terminal_fails_closed() -> None:
    wrong_worker = running_link_task(worker_id="other-worker")
    with pytest.raises(PlayerLinkWorkerError, match="link_claim_invalid"):
        worker(FakePlayerRepository([wrong_worker])).run_once()

    repository = FakePlayerRepository([running_link_task()])
    repository.resolve_result = cast(PlayerLinkTask, object())
    with pytest.raises(PlayerLinkWorkerError, match="link_terminal_invalid"):
        worker(repository).run_once()


def test_run_forever_uses_interruptible_backoff_without_busy_polling() -> None:
    repository = FakePlayerRepository()
    stop = StopAfterWaits(3)
    policy = PollingPolicy(
        initial_delay_s=0.1,
        maximum_delay_s=1.0,
        multiplier=2.0,
        jitter_ratio=0.0,
    )

    worker(repository, policy=policy).run_forever(stop)

    assert stop.waits == pytest.approx([0.1, 0.2, 0.4])
    assert len(repository.claim_calls) == 3


def test_graceful_stop_finishes_current_link_and_claims_no_more() -> None:
    stop = Event()
    first = running_link_task()
    second_payload = first.model_dump(mode="python")
    second_payload["link_task_id"] = UUID(
        "40000000-0000-4000-8000-000000000004"
    )
    second = PlayerLinkTask.model_validate(second_payload)
    repository = FakePlayerRepository([first, second])

    class StopResolver(FakeResolver):
        def resolve(self, **kwargs: object) -> object:
            stop.set()
            return super().resolve(**kwargs)  # type: ignore[arg-type]

    worker(repository, StopResolver(resolved_account())).run_forever(stop)

    assert len(repository.resolve_calls) == 1
    assert len(repository.claim_calls) == 1


def test_observability_contains_only_body_free_link_metadata() -> None:
    observer = TaskObservability(logger_name="tests.player_link_worker")
    repository = FakePlayerRepository([running_link_task()])

    result = worker(repository, observability=observer).run_once()

    assert result.status is PlayerLinkWorkerIterationStatus.SUCCEEDED
    assert any(event.name == "player_link.terminal" for event in observer.events)
    serialized = repr(observer.events) + repr(observer.snapshot())
    assert "Private Player" not in serialized
    assert "Confirmed Player" not in serialized
    assert "private_puuid" not in serialized
    assert "KR1" not in serialized
