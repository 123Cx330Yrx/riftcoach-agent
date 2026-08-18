from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_packaging_smoke import (
    PackagingSmokeError,
    execute_packaging_smoke,
    load_packaging_smoke_settings,
)
from app.api.task_models import ReadinessResult
from app.workers.review_worker import (
    WorkerIterationResult,
    WorkerIterationStatus,
)


def valid_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "RIFTCOACH_PACKAGING_SMOKE": "true",
        "RIFTCOACH_API_PROFILE": "test",
        "RIFTCOACH_SMOKE_BASE_URL": "http://api:8000",
        "DATABASE_URL": (
            "postgresql+psycopg://riftcoach:smoke-secret@postgres/riftcoach"
        ),
        "RIFTCOACH_RUNS_ROOT": str(tmp_path / "runs"),
    }


def test_packaging_smoke_requires_an_explicit_nonproduction_gate(
    tmp_path: Path,
) -> None:
    environment = valid_environment(tmp_path)
    environment.pop("RIFTCOACH_PACKAGING_SMOKE")

    with pytest.raises(PackagingSmokeError) as exc_info:
        load_packaging_smoke_settings(environment)

    assert exc_info.value.code == "packaging_smoke_disabled"


def test_packaging_smoke_cannot_run_under_the_production_api_profile(
    tmp_path: Path,
) -> None:
    environment = valid_environment(tmp_path)
    environment["RIFTCOACH_API_PROFILE"] = "production"

    with pytest.raises(PackagingSmokeError) as exc_info:
        load_packaging_smoke_settings(environment)

    assert exc_info.value.code == "packaging_smoke_profile_invalid"


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("RIFTCOACH_SMOKE_BASE_URL", "http://public.example.invalid:8000"),
        (
            "DATABASE_URL",
            "postgresql+psycopg://riftcoach:secret@db.example.invalid/riftcoach",
        ),
    ),
)
def test_packaging_smoke_rejects_remote_api_or_database_targets(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    environment = valid_environment(tmp_path)
    environment[name] = value

    with pytest.raises(PackagingSmokeError) as exc_info:
        load_packaging_smoke_settings(environment)

    assert exc_info.value.code == "packaging_smoke_configuration_invalid"


def test_packaging_smoke_settings_need_no_riot_or_provider_secret(
    tmp_path: Path,
) -> None:
    settings = load_packaging_smoke_settings(valid_environment(tmp_path))

    assert settings.base_url == "http://api:8000"
    assert "smoke-secret" not in repr(settings)
    assert not hasattr(settings, "riot_api_key")
    assert not hasattr(settings, "llm_api_key")


def test_packaging_smoke_proves_safe_terminal_without_external_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "90000000-0000-4000-8000-000000000001"
    run_id = "packaging_smoke_run"
    events: list[str] = []

    class Response:
        def __init__(self, status_code: int, body: dict) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return dict(self._body)

    class Http:
        def get(self, url: str, **_kwargs):
            if url.endswith("/health/ready"):
                return Response(200, {"status": "ready"})
            assert url.endswith(task_id)
            return Response(
                200,
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "status": "failed",
                    "terminal_reason": "worker_execution_failed",
                },
            )

        def post(self, _url: str, **_kwargs):
            return Response(202, {"task_id": task_id, "run_id": run_id})

    class Engine:
        def dispose(self) -> None:
            events.append("engine.dispose")

    class Probe:
        def __init__(self, _engine: object) -> None:
            pass

        def check(self) -> ReadinessResult:
            return ReadinessResult.ready()

    class Worker:
        def __init__(self, **kwargs) -> None:
            assert type(kwargs["executor"]).__name__ == "_NoExternalIoExecutor"

        def run_once(self) -> WorkerIterationResult:
            return WorkerIterationResult(
                status=WorkerIterationStatus.FAILED,
                task_id=__import__("uuid").UUID(task_id),
            )

    monkeypatch.setattr(
        "scripts.run_packaging_smoke.build_engine",
        lambda _settings: Engine(),
    )
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.PostgresReadinessProbe",
        Probe,
    )
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.build_session_factory",
        lambda _engine: lambda: None,
    )
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.PostgresTaskRepository",
        lambda _factory: object(),
    )
    monkeypatch.setattr("scripts.run_packaging_smoke.ReviewWorker", Worker)

    result = execute_packaging_smoke(
        load_packaging_smoke_settings(valid_environment(tmp_path)),
        worker_id="smoke-worker",
        http=Http(),
    )

    assert result.task_status == "failed"
    assert result.external_riot_provider_calls == 0
    assert events == ["engine.dispose"]
