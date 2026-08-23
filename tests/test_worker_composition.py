from __future__ import annotations

from pathlib import Path

import pytest

from app.api.task_models import ReadinessResult
from app.lol.riot_client import RiotClient
from app.workers.composition import (
    WorkerCompositionError,
    ReviewWorkerProcess,
    build_review_worker_process,
    load_worker_composition_settings,
)
from scripts.run_review_worker import main as worker_cli_main


ROOT = Path(__file__).resolve().parents[1]


def valid_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "DATABASE_URL": (
            "postgresql+psycopg://riftcoach:database-secret@localhost/riftcoach"
        ),
        "RIOT_API_KEY": "riot-secret",
        "RIOT_REGION": "asia",
        "LLM_PROVIDER": "zhipu",
        "LLM_DEFAULT_PROVIDER": "zhipu",
        "LLM_API_KEY": "llm-secret",
        "LLM_BASE_URL": "https://provider.invalid/v4/",
        "LLM_MODEL": "glm-test",
        "LLM_TIMEOUT_SECONDS": "30",
        "RIFTCOACH_RUNS_ROOT": str(tmp_path / "runs"),
        "RIFTCOACH_KNOWLEDGE_ROOT": str(ROOT / "data/rag_docs"),
        "RIFTCOACH_SKILLS_ROOT": str(ROOT / "skills"),
        "RIFTCOACH_PROMPT_PROGRAMS_ROOT": str(ROOT / "prompt_programs"),
        "RIFTCOACH_DDRAGON_CACHE_ROOT": str(tmp_path / "ddragon"),
        "RIFTCOACH_WORKER_INITIAL_DELAY_SECONDS": "0.1",
        "RIFTCOACH_WORKER_MAXIMUM_DELAY_SECONDS": "2",
        "RIFTCOACH_WORKER_JITTER_RATIO": "0.2",
    }


@pytest.mark.parametrize(
    "missing",
    ("DATABASE_URL", "RIOT_API_KEY", "LLM_API_KEY"),
)
def test_worker_settings_fail_closed_when_a_required_secret_is_missing(
    tmp_path: Path,
    missing: str,
) -> None:
    environment = valid_environment(tmp_path)
    secret_values = tuple(environment[key] for key in ("RIOT_API_KEY", "LLM_API_KEY"))
    environment.pop(missing)

    with pytest.raises(WorkerCompositionError) as exc_info:
        load_worker_composition_settings(environment)

    assert exc_info.value.code == "worker_configuration_invalid"
    assert str(exc_info.value) == "worker_configuration_invalid"
    for secret in secret_values:
        assert secret not in repr(exc_info.value)


def test_worker_settings_reject_an_unadmitted_product_provider(
    tmp_path: Path,
) -> None:
    environment = valid_environment(tmp_path)
    environment["LLM_DEFAULT_PROVIDER"] = "deepseek"

    with pytest.raises(WorkerCompositionError) as exc_info:
        load_worker_composition_settings(environment)

    assert exc_info.value.code == "worker_configuration_invalid"


def test_worker_settings_hide_secrets_and_resolve_runtime_assets(
    tmp_path: Path,
) -> None:
    settings = load_worker_composition_settings(valid_environment(tmp_path))

    assert not hasattr(settings, "riot_region")
    assert settings.knowledge_root == (ROOT / "data/rag_docs").resolve()
    assert settings.polling_policy.maximum_delay_s == 2
    assert settings.lease_policy.lease_seconds == 120
    assert settings.lease_policy.heartbeat_seconds == 30
    assert "riot-secret" not in repr(settings)
    assert "llm-secret" not in repr(settings)
    assert "database-secret" not in repr(settings)


def test_worker_settings_ignore_legacy_ambient_region_instead_of_using_it(
    tmp_path: Path,
) -> None:
    environment = valid_environment(tmp_path)
    environment["RIOT_REGION"] = "cn"

    settings = load_worker_composition_settings(environment)

    assert not hasattr(settings, "riot_region")


def test_database_readiness_failure_disposes_engine_before_any_riot_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_worker_composition_settings(valid_environment(tmp_path))
    events: list[str] = []

    class Engine:
        def dispose(self) -> None:
            events.append("engine.dispose")

    class Probe:
        def __init__(self, engine: object) -> None:
            assert isinstance(engine, Engine)

        def check(self) -> ReadinessResult:
            events.append("database.readiness")
            return ReadinessResult.not_ready("migration_not_current")

    monkeypatch.setattr(
        "app.workers.composition.build_engine",
        lambda _settings: (events.append("engine.build") or Engine()),
    )
    monkeypatch.setattr("app.workers.composition.PostgresReadinessProbe", Probe)
    monkeypatch.setattr(
        "app.workers.composition.RiotClient",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Riot must not be built after failed DB readiness")
        ),
    )

    with pytest.raises(WorkerCompositionError) as exc_info:
        build_review_worker_process(settings, worker_id="worker-1")

    assert exc_info.value.code == "worker_database_not_ready"
    assert events == ["engine.build", "database.readiness", "engine.dispose"]


def test_invalid_worker_id_fails_before_database_or_network_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_worker_composition_settings(valid_environment(tmp_path))
    monkeypatch.setattr(
        "app.workers.composition.build_engine",
        lambda _settings: (_ for _ in ()).throw(
            AssertionError("invalid process config must fail before Engine build")
        ),
    )

    with pytest.raises(WorkerCompositionError) as exc_info:
        build_review_worker_process(settings, worker_id="unsafe worker id")

    assert exc_info.value.code == "worker_configuration_invalid"


def test_successful_composition_finishes_all_preflight_before_returning_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_worker_composition_settings(valid_environment(tmp_path))
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

        def claim_next(self, **_kwargs):
            self.claim_calls += 1
            return None

        def succeed(self, **_kwargs):
            return True

        def fail(self, **_kwargs):
            return True

        def heartbeat(self, **_kwargs):
            raise AssertionError("composition must not heartbeat a task")

        def save_checkpoint(self, **_kwargs):
            raise AssertionError("composition must not checkpoint a task")

        def cancel_running(self, **_kwargs):
            raise AssertionError("composition must not cancel a task")

        def list_expired_recovery_candidates(self, **_kwargs):
            return ()

        def cancel_expired(self, **_kwargs):
            return False

        def reconcile_expired_success(self, **_kwargs):
            return False

        def requeue_expired(self, **_kwargs):
            return False

        def mark_recovery_required(self, **_kwargs):
            return False

    class Runtime:
        def run(self, _request):
            raise AssertionError("composition must not execute the Runtime")

    class Root:
        skill_catalog = object()

        @classmethod
        def from_directories(cls, **_kwargs):
            events.append("prompt_program.preflight")
            return cls()

        def build_runtime(self, **_kwargs):
            events.append("runtime.build")
            return Runtime()

    class Registry:
        def resolve(self):
            events.append("provider.resolve")
            return object()

    repository = Repository()
    monkeypatch.setattr(
        "app.workers.composition.build_engine",
        lambda _settings: (events.append("engine.build") or Engine()),
    )
    monkeypatch.setattr("app.workers.composition.PostgresReadinessProbe", Probe)
    monkeypatch.setattr(
        "app.workers.composition.build_session_factory",
        lambda _engine: (events.append("session.build") or (lambda: None)),
    )
    monkeypatch.setattr(
        "app.workers.composition.PostgresTaskRepository",
        lambda _factory: (events.append("repository.build") or repository),
    )
    monkeypatch.setattr(
        "app.workers.composition.RiotClient",
        lambda **_kwargs: (events.append("riot.build") or object()),
    )

    class RoutedSummary:
        def __init__(self, **kwargs):
            assert set(kwargs["clients"]) == {
                "americas",
                "asia",
                "europe",
                "sea",
            }
            events.append("riot.router")

        def build(self, **_kwargs):
            return {}

        def build_by_puuid(self, **_kwargs):
            return {}

    monkeypatch.setattr(
        "app.workers.composition.RoutedRiotPlayerSummaryBuilder",
        RoutedSummary,
    )
    monkeypatch.setattr(
        "app.workers.composition.DataDragonService",
        lambda **_kwargs: (events.append("ddragon.preflight") or object()),
    )
    monkeypatch.setattr(
        "app.workers.composition.LocalHybridKnowledgeProvider.from_directory",
        lambda _path: (events.append("knowledge.preflight") or object()),
    )
    monkeypatch.setattr("app.workers.composition.RuntimeCompositionRoot", Root)
    monkeypatch.setattr(
        "app.workers.composition.create_zhipu_provider",
        lambda _settings: (events.append("provider.build") or object()),
    )
    monkeypatch.setattr(
        "app.workers.composition.create_provider_registry",
        lambda _providers, _settings: Registry(),
    )

    process = build_review_worker_process(settings, worker_id="worker-1")

    assert isinstance(process, ReviewWorkerProcess)
    assert repository.claim_calls == 0
    assert events.index("database.readiness") < events.index("riot.build")
    assert events.index("knowledge.preflight") < events.index("runtime.build")
    assert "engine.dispose" not in events
    process.close()
    process.close()
    assert events.count("engine.dispose") == 1


def test_explicit_riot_settings_do_not_implicitly_read_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.lol.riot_client.load_dotenv",
        lambda: (_ for _ in ()).throw(
            AssertionError("explicit deployment config must not read .env")
        ),
    )

    client = RiotClient(api_key="explicit-secret", region="asia")

    assert client.region == "asia"


def test_worker_cli_fails_closed_before_claim_when_configuration_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = worker_cli_main(
        ["--worker-id", "worker-1", "--check"],
        environment={},
    )

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert captured.err.strip() == "worker_configuration_invalid"


def test_worker_cli_check_preflights_and_closes_without_polling(
    tmp_path: Path,
) -> None:
    events: list[str] = []

    class Process:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *_args):
            events.append("close")

        @property
        def worker(self):
            raise AssertionError("--check must not access the polling worker")

    result = worker_cli_main(
        ["--worker-id", "worker-1", "--check"],
        environment=valid_environment(tmp_path),
        process_factory=lambda _settings, **_kwargs: Process(),
    )

    assert result == 0
    assert events == ["enter", "close"]
