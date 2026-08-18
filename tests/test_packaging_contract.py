from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _compose() -> dict:
    return yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))


def test_runtime_image_contract_is_explicit_and_secret_excluding() -> None:
    dockerfile = ROOT / "Dockerfile"
    dockerignore = ROOT / ".dockerignore"

    assert dockerfile.is_file()
    assert dockerignore.is_file()

    image_contract = dockerfile.read_text(encoding="utf-8")
    ignore_contract = dockerignore.read_text(encoding="utf-8")
    assert "python:3.11" in image_contract
    assert "USER riftcoach" in image_contract
    assert "app.api.composition:create_composed_app" in image_contract
    assert "--factory" in image_contract
    for forbidden in (
        ".env",
        ".git",
        ".venv",
        "data/cache",
        "data/runs",
        "data/static",
        "reports",
        "tests",
        "tmp",
    ):
        assert forbidden in ignore_contract


def test_python_package_declares_the_asgi_server_used_by_the_image() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = tuple(project["project"]["dependencies"])

    assert any(row.startswith("uvicorn") for row in dependencies)


def test_compose_orders_postgres_migration_api_worker_and_smoke() -> None:
    services = _compose()["services"]
    assert {"postgres", "migrate", "api", "worker", "smoke"} <= set(services)

    assert services["postgres"]["healthcheck"]
    assert services["migrate"]["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["worker"]["depends_on"]["api"]["condition"] == (
        "service_healthy"
    )
    assert services["smoke"]["depends_on"]["api"]["condition"] == (
        "service_healthy"
    )
    assert "runtime" in services["worker"]["profiles"]
    assert "smoke" in services["smoke"]["profiles"]


def test_compose_separates_real_worker_from_no_io_smoke() -> None:
    services = _compose()["services"]
    worker_command = " ".join(services["worker"]["command"])
    smoke_command = " ".join(services["smoke"]["command"])

    assert "scripts/run_review_worker.py" in worker_command
    assert "scripts/run_packaging_smoke.py" in smoke_command
    assert services["worker"]["environment"]["RIOT_API_KEY"] is not None
    assert "RIOT_API_KEY" not in services["smoke"].get("environment", {})
    assert "LLM_API_KEY" not in services["smoke"].get("environment", {})
    assert services["api"]["volumes"] == services["worker"]["volumes"][:1]


def test_ci_contains_a_blocking_linux_packaging_smoke_without_secrets() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["packaging-smoke"]
    steps = "\n".join(str(step) for step in job["steps"])

    assert job["runs-on"] == "ubuntu-latest"
    assert job["env"]["COMPOSE_PROJECT_NAME"] == "riftcoach-packaging-smoke"
    assert "docker compose --profile smoke" in steps
    assert "--detach --wait" in steps
    assert "run --rm --no-deps smoke" in steps
    assert "--abort-on-container-exit" not in steps
    assert "RIOT_API_KEY" not in str(job.get("env", {}))
    assert "LLM_API_KEY" not in str(job.get("env", {}))
    assert "docker image" in steps or "docker run" in steps


def test_exit_review_assets_name_evidence_and_deferred_boundaries() -> None:
    matrix = ROOT / "docs/plans/2026-08-18-6a-exit-matrix.md"
    review = ROOT / "docs/plans/2026-08-18-6a-exit-review.md"
    assert matrix.is_file()
    assert review.is_file()

    matrix_text = matrix.read_text(encoding="utf-8")
    review_text = review.read_text(encoding="utf-8")
    for heading in (
        "承诺",
        "实现证据",
        "测试证据",
        "公开证据",
        "限制",
        "退出裁决",
    ):
        assert heading in matrix_text
    for boundary in (
        "Session/Memory",
        "正式 Auth/HTTPS",
        "SSE/前端",
        "lease/heartbeat/reclaim",
        "真实 Provider",
    ):
        assert boundary in review_text
