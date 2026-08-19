from __future__ import annotations

import pytest

from app.api.task_models import ReadinessResult
from app.players.composition import (
    PlayerLinkWorkerCompositionError,
    PlayerLinkWorkerProcess,
    build_player_link_worker_process,
    load_player_link_worker_settings,
)
from app.players.link_worker import (
    PlayerLinkWorkerIterationResult,
    PlayerLinkWorkerIterationStatus,
)
from app.players.models import RoutingRegion
from scripts.run_player_link_worker import main as player_link_worker_cli_main


def valid_environment() -> dict[str, str]:
    return {
        "DATABASE_URL": (
            "postgresql+psycopg://riftcoach:database-secret@localhost/riftcoach"
        ),
        "RIOT_API_KEY": "riot-secret",
        "RIFTCOACH_RIOT_ALLOWED_ROUTING_REGIONS": (
            "americas,asia,europe,sea"
        ),
        "RIFTCOACH_RIOT_ACCOUNT_TIMEOUT_SECONDS": "7.5",
        "RIFTCOACH_PLAYER_LINK_WORKER_INITIAL_DELAY_SECONDS": "0.1",
        "RIFTCOACH_PLAYER_LINK_WORKER_MAXIMUM_DELAY_SECONDS": "2",
        "RIFTCOACH_PLAYER_LINK_WORKER_BACKOFF_MULTIPLIER": "2",
        "RIFTCOACH_PLAYER_LINK_WORKER_JITTER_RATIO": "0.2",
    }


@pytest.mark.parametrize("missing", ("DATABASE_URL", "RIOT_API_KEY"))
def test_settings_require_database_and_riot_secret_without_retaining_them(
    missing: str,
) -> None:
    environment = valid_environment()
    secret_values = (
        environment["DATABASE_URL"],
        environment["RIOT_API_KEY"],
    )
    environment.pop(missing)

    with pytest.raises(PlayerLinkWorkerCompositionError) as caught:
        load_player_link_worker_settings(environment)

    assert caught.value.code == "player_link_worker_configuration_invalid"
    assert all(secret not in repr(caught.value) for secret in secret_values)


@pytest.mark.parametrize(
    "regions",
    (
        "",
        "asia",
        "americas,asia,europe",
        "asia,cn",
        "asia,ASIA",
        "asia,asia",
        "asia,unknown",
    ),
)
def test_settings_require_complete_unique_routing_policy(regions: str) -> None:
    environment = valid_environment()
    environment["RIFTCOACH_RIOT_ALLOWED_ROUTING_REGIONS"] = regions

    with pytest.raises(PlayerLinkWorkerCompositionError) as caught:
        load_player_link_worker_settings(environment)

    assert caught.value.code == "player_link_worker_configuration_invalid"


def test_settings_are_bounded_body_free_and_use_shared_polling_policy() -> None:
    settings = load_player_link_worker_settings(valid_environment())

    assert settings.allowed_routing_regions == (
        RoutingRegion.AMERICAS,
        RoutingRegion.ASIA,
        RoutingRegion.EUROPE,
        RoutingRegion.SEA,
    )
    assert settings.account_timeout_s == 7.5
    assert settings.polling_policy.maximum_delay_s == 2
    assert "riot-secret" not in repr(settings)
    assert "database-secret" not in repr(settings)


def test_invalid_worker_id_fails_before_engine_or_riot_client_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_player_link_worker_settings(valid_environment())
    monkeypatch.setattr(
        "app.players.composition.build_engine",
        lambda _settings: (_ for _ in ()).throw(
            AssertionError("invalid worker id must fail before Engine")
        ),
    )
    monkeypatch.setattr(
        "app.players.composition.RiotClient",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("invalid worker id must fail before Riot client")
        ),
    )

    with pytest.raises(PlayerLinkWorkerCompositionError) as caught:
        build_player_link_worker_process(
            settings,
            worker_id="unsafe worker id",
        )

    assert caught.value.code == "player_link_worker_configuration_invalid"


def test_database_readiness_failure_disposes_before_resolver_client_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_player_link_worker_settings(valid_environment())
    events: list[str] = []

    class Engine:
        def dispose(self) -> None:
            events.append("engine.dispose")

    class Probe:
        def __init__(self, _engine: object) -> None:
            pass

        def check(self) -> ReadinessResult:
            events.append("database.readiness")
            return ReadinessResult.not_ready("migration_not_current")

    monkeypatch.setattr(
        "app.players.composition.build_engine",
        lambda _settings: (events.append("engine.build") or Engine()),
    )
    monkeypatch.setattr("app.players.composition.PostgresReadinessProbe", Probe)
    monkeypatch.setattr(
        "app.players.composition.RiotClient",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Riot client must not exist after failed readiness")
        ),
    )

    with pytest.raises(PlayerLinkWorkerCompositionError) as caught:
        build_player_link_worker_process(settings, worker_id="link-worker-1")

    assert caught.value.code == "player_link_worker_database_not_ready"
    assert events == ["engine.build", "database.readiness", "engine.dispose"]


def test_successful_composition_builds_no_client_and_claims_no_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_player_link_worker_settings(valid_environment())
    events: list[str] = []

    class Engine:
        def dispose(self) -> None:
            events.append("engine.dispose")

    class Probe:
        def __init__(self, _engine: object) -> None:
            pass

        def check(self) -> ReadinessResult:
            events.append("database.readiness")
            return ReadinessResult.ready()

    class Repository:
        claim_calls = 0

        def claim_next_link(self, **_kwargs: object) -> None:
            self.claim_calls += 1
            return None

        def resolve_link(self, **_kwargs: object) -> None:
            raise AssertionError("composition must not resolve a link")

        def fail_link(self, **_kwargs: object) -> None:
            raise AssertionError("composition must not fail a link")

    repository = Repository()
    monkeypatch.setattr(
        "app.players.composition.build_engine",
        lambda _settings: (events.append("engine.build") or Engine()),
    )
    monkeypatch.setattr("app.players.composition.PostgresReadinessProbe", Probe)
    monkeypatch.setattr(
        "app.players.composition.build_session_factory",
        lambda _engine: (events.append("session.build") or (lambda: None)),
    )
    monkeypatch.setattr(
        "app.players.composition.PostgresPlayerRepository",
        lambda _factory: (events.append("repository.build") or repository),
    )
    monkeypatch.setattr(
        "app.players.composition.RiotClient",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Resolver construction must not build a Riot client")
        ),
    )

    process = build_player_link_worker_process(
        settings,
        worker_id="link-worker-1",
    )

    assert isinstance(process, PlayerLinkWorkerProcess)
    assert repository.claim_calls == 0
    assert events == [
        "engine.build",
        "database.readiness",
        "session.build",
        "repository.build",
    ]
    process.close()
    process.close()
    assert events.count("engine.dispose") == 1


def test_cli_check_and_once_have_explicit_bounded_control_flow() -> None:
    events: list[str] = []

    class Worker:
        def run_once(self) -> PlayerLinkWorkerIterationResult:
            events.append("once")
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.IDLE,
                link_task_id=None,
            )

    class Process:
        worker = Worker()

        def __enter__(self) -> Process:
            events.append("enter")
            return self

        def __exit__(self, *_args: object) -> None:
            events.append("close")

    factory = lambda _settings, **_kwargs: Process()

    assert player_link_worker_cli_main(
        ["--worker-id", "link-worker-1", "--check"],
        environment=valid_environment(),
        process_factory=factory,
    ) == 0
    assert events == ["enter", "close"]

    events.clear()
    assert player_link_worker_cli_main(
        ["--worker-id", "link-worker-1", "--once"],
        environment=valid_environment(),
        process_factory=factory,
    ) == 0
    assert events == ["enter", "once", "close"]


def test_cli_missing_configuration_is_body_free(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = player_link_worker_cli_main(
        ["--worker-id", "link-worker-1", "--check"],
        environment={},
    )

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert captured.err.strip() == "player_link_worker_configuration_invalid"
