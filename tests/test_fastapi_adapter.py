from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.product.recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationResult,
    RecentReviewApplicationService,
)
from app.product.run_query import RunQueryError, RunView
from app.product.run_query import RunQueryService
from app.product.recent_review import (
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.models import RuntimeStatus, RuntimeTraceReference
from app.runtime.models import RuntimeRunResult
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.runtime import RuntimeExecutionFactory
from app.runtime.signals import RuntimePublicationStatus
from app.skills.recent_form_review import RecentFormReviewOutput
from tests.test_agent_draft_preparer import demo_summary
from tests.test_agent_runtime import FactoryProbe, RuntimeProvider


RUN_ID = "review_20260817T000000Z_api00000001"


def _success_result() -> RecentReviewApplicationResult:
    output = RecentFormReviewOutput(
        run_id=RUN_ID,
        status="published",
        report="# reviewed report\n",
        evaluation_score=92,
    )
    return RecentReviewApplicationResult(
        run_id=RUN_ID,
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        terminal_reason="quality_gate_passed",
        output=output,
        trace_reference=RuntimeTraceReference(
            run_id=RUN_ID,
            sha256="a" * 64,
        ),
    )


class FakeReviewService:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.requests: list[RecentReviewProductRequest] = []

    def review(self, request: RecentReviewProductRequest):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


class FakeQueryService:
    def __init__(self) -> None:
        self.run_view = RunView(
            run_id=RUN_ID,
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            skill_name="recent-form-review",
            skill_version="0.2.0",
            prompt_profile_id="recent-form-review-coach",
            prompt_profile_version="1.0.0",
            report_available=True,
        )
        self.report = "# reviewed report\n"
        self.error: RunQueryError | None = None
        self.calls: list[tuple[str, str]] = []

    def get_run(self, run_id: str) -> RunView:
        self.calls.append(("run", run_id))
        if self.error is not None:
            raise self.error
        return self.run_view

    def get_report(self, run_id: str) -> str:
        self.calls.append(("report", run_id))
        if self.error is not None:
            raise self.error
        return self.report


class FixtureSummaryBuilder:
    def build(self, **kwargs) -> dict:
        assert kwargs == {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "count": 10,
            "queue": 420,
        }
        return demo_summary()


def _client(
    *,
    review_service: FakeReviewService | None = None,
    query_service: FakeQueryService | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            review_service=review_service or FakeReviewService(_success_result()),
            query_service=query_service or FakeQueryService(),
        )
    )


def test_openapi_exposes_only_the_frozen_v1_paths() -> None:
    client = _client()
    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == {
        "/reviews/recent",
        "/runs/{run_id}",
        "/runs/{run_id}/report",
        "/health",
    }


def test_adapter_does_not_import_cli_or_internal_orchestrators() -> None:
    tree = ast.parse(Path("app/api/main.py").read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "scripts",
        "app.harness",
        "app.providers",
        "app.runtime.runtime",
        "app.skills.router",
    )
    assert not any(
        module.startswith(forbidden_prefixes)
        for module in imported_modules
    )


def test_app_factory_and_openapi_do_not_read_env_or_send_http(
    monkeypatch,
) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key, default=None):
        if key in {
            "RIOT_API_KEY",
            "ZHIPU_API_KEY",
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        }:
            raise AssertionError("app factory must not read API keys")
        return original_getenv(key, default)

    def forbidden_http(*args, **kwargs):
        raise AssertionError("app factory must not send HTTP requests")

    monkeypatch.setattr("os.getenv", guarded_getenv)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden_http)

    app = create_app(
        review_service=FakeReviewService(_success_result()),
        query_service=FakeQueryService(),
    )

    assert set(app.openapi()["paths"]) == {
        "/reviews/recent",
        "/runs/{run_id}",
        "/runs/{run_id}/report",
        "/health",
    }


def test_health_is_liveness_only() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "1.0",
        "schema_version": "1.0",
    }


def test_post_recent_validates_at_http_boundary_and_delegates_typed_request() -> None:
    service = FakeReviewService(_success_result())
    response = _client(review_service=service).post(
        "/reviews/recent",
        json={
            "riot_id": "DemoPlayer#TEST",
            "count": 7,
            "queue": 420,
            "focus": "survival",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["run_id"] == RUN_ID
    assert body["publication_status"] == "published"
    assert body["output"]["report"] == "# reviewed report"
    assert body["links"] == {
        "run": f"/runs/{RUN_ID}",
        "report": f"/runs/{RUN_ID}/report",
    }
    assert len(service.requests) == 1
    assert isinstance(service.requests[0], RecentReviewProductRequest)
    assert service.requests[0].focus == "survival"


def test_no_io_vertical_slice_uses_real_runtime_harness_rag_and_query(
    tmp_path: Path,
) -> None:
    provider = RuntimeProvider()
    probe = FactoryProbe()
    composition = RuntimeCompositionRoot.from_directories(
        skills_root="skills",
        prompt_programs_root="prompt_programs",
    )
    execution_factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            Path("data/rag_docs")
        ),
        evaluator_factory=probe.evaluator_factory,
        reviser_factory=probe.reviser_factory,
    )
    runtime = composition.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        execution_factory=execution_factory,
    )
    receipts = FileRunReceiptStore(tmp_path)
    service = RecentReviewApplicationService(
        summary_builder=FixtureSummaryBuilder(),
        compiler=RecentReviewRuntimeRequestCompiler(
            composition.skill_catalog,
            run_id_factory=lambda: "api_no_io_vertical",
        ),
        runtime=runtime,
        receipt_writer=receipts,
    )
    client = TestClient(
        create_app(
            review_service=service,
            query_service=RunQueryService(tmp_path),
        )
    )

    created = client.post(
        "/reviews/recent",
        json={"riot_id": "DemoPlayer#TEST", "focus": "survival"},
    )
    run = client.get("/runs/api_no_io_vertical")
    report = client.get("/runs/api_no_io_vertical/report")

    assert created.status_code == 201
    assert created.json()["run_id"] == "api_no_io_vertical"
    assert created.json()["publication_status"] == "published"
    assert run.status_code == 200
    assert run.json()["skill_name"] == "recent-form-review"
    assert run.json()["prompt_profile_id"] == "recent-form-review-coach"
    assert run.json()["report_available"] is True
    assert report.status_code == 200
    assert report.text.startswith("# Coach draft")
    assert len(provider.requests) == 3


def test_post_rejects_extra_internal_fields_without_calling_service() -> None:
    service = FakeReviewService(_success_result())
    response = _client(review_service=service).post(
        "/reviews/recent",
        json={
            "riot_id": "DemoPlayer#TEST",
            "run_id": "attacker_run",
            "provider": "secret-provider",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.requests == []


@pytest.mark.parametrize(
    ("code", "status"),
    (
        ("player_not_found", 404),
        ("insufficient_match_data", 422),
        ("riot_authentication_failed", 503),
        ("upstream_timeout", 504),
        ("upstream_unavailable", 503),
        ("service_configuration_invalid", 503),
        ("review_runtime_failed", 500),
    ),
)
def test_post_maps_application_errors_to_safe_status_and_body(
    code: str,
    status: int,
) -> None:
    service = FakeReviewService(
        error=RecentReviewApplicationError(
            code,
            run_id=RUN_ID if code == "review_runtime_failed" else None,
            terminal_reason=(
                "harness_execution_failed"
                if code == "review_runtime_failed"
                else None
            ),
        )
    )
    response = _client(review_service=service).post(
        "/reviews/recent",
        json={"riot_id": "DemoPlayer#TEST"},
    )
    assert response.status_code == status
    assert response.json() == {
        key: value
        for key, value in {
            "code": code,
            "run_id": RUN_ID if code == "review_runtime_failed" else None,
            "terminal_reason": (
                "harness_execution_failed"
                if code == "review_runtime_failed"
                else None
            ),
        }.items()
        if value is not None
    }


def test_rate_limit_exposes_only_bounded_retry_after_header() -> None:
    service = FakeReviewService(
        error=RecentReviewApplicationError(
            "riot_rate_limited",
            retry_after_seconds=17,
        )
    )
    response = _client(review_service=service).post(
        "/reviews/recent",
        json={"riot_id": "DemoPlayer#TEST"},
    )
    assert response.status_code == 503
    assert response.headers["retry-after"] == "17"
    assert response.json() == {"code": "riot_rate_limited"}


def test_unexpected_application_exception_is_sanitized() -> None:
    service = FakeReviewService(
        error=RuntimeError("secret-key https://private.example C:\\secret\\.env")
    )
    response = _client(review_service=service).post(
        "/reviews/recent",
        json={"riot_id": "DemoPlayer#TEST"},
    )
    assert response.status_code == 500
    assert response.json() == {"code": "review_runtime_failed"}
    assert "secret-key" not in response.text
    assert "private.example" not in response.text
    assert ".env" not in response.text


def test_get_run_delegates_to_query_projection() -> None:
    query = FakeQueryService()
    response = _client(query_service=query).get(f"/runs/{RUN_ID}")
    assert response.status_code == 200
    assert response.json()["run_id"] == RUN_ID
    assert response.json()["report_available"] is True
    assert query.calls == [("run", RUN_ID)]


def test_get_run_can_use_the_real_file_backed_query_service(
    tmp_path,
) -> None:
    failed_result = RuntimeRunResult(
        run_id=RUN_ID,
        runtime_status=RuntimeStatus.FAILED,
        publication_status=None,
        terminal_reason="context_build_failed",
        output=None,
        trace_reference=None,
    )
    FileRunReceiptStore(tmp_path).write_result(failed_result)
    query = RunQueryService(tmp_path)

    response = _client(query_service=query).get(f"/runs/{RUN_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "1.0",
        "run_id": RUN_ID,
        "runtime_status": "failed",
        "publication_status": None,
        "terminal_reason": "context_build_failed",
        "skill_name": None,
        "skill_version": None,
        "prompt_profile_id": None,
        "prompt_profile_version": None,
        "started_at_utc": None,
        "completed_at_utc": None,
        "elapsed_ms": None,
        "usage": None,
        "report_available": False,
    }


@pytest.mark.parametrize(
    ("code", "status"),
    (
        ("run_not_found", 404),
        ("report_not_available", 409),
        ("run_integrity_failed", 500),
    ),
)
def test_query_errors_have_stable_http_mapping(code: str, status: int) -> None:
    query = FakeQueryService()
    query.error = RunQueryError(code)
    response = _client(query_service=query).get(f"/runs/{RUN_ID}")
    assert response.status_code == status
    assert response.json() == {"code": code}


def test_report_is_utf8_markdown_and_query_service_owns_integrity_checks() -> None:
    query = FakeQueryService()
    response = _client(query_service=query).get(f"/runs/{RUN_ID}/report")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert response.text == "# reviewed report\n"
    assert query.calls == [("report", RUN_ID)]


def test_report_query_error_is_not_returned_as_body() -> None:
    query = FakeQueryService()
    query.error = RunQueryError("report_not_available")
    response = _client(query_service=query).get(f"/runs/{RUN_ID}/report")
    assert response.status_code == 409
    assert response.json() == {"code": "report_not_available"}


def test_deferred_product_endpoints_do_not_exist() -> None:
    client = _client()
    assert client.get(f"/runs/{RUN_ID}/status").status_code == 404
    assert client.post(f"/runs/{RUN_ID}/follow-ups", json={}).status_code == 404
    assert client.get(f"/runs/{RUN_ID}/events").status_code == 404
