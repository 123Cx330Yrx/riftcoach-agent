from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.run_packaging_smoke import (
    PackagingSmokeError,
    execute_packaging_smoke,
    load_packaging_smoke_settings,
)
from app.api.task_models import ReadinessResult
from app.workers.review_worker import (
    ReviewWorkerError,
    WorkerIterationResult,
    WorkerIterationStatus,
)
from app.players.link_worker import (
    PlayerLinkWorkerIterationResult,
    PlayerLinkWorkerIterationStatus,
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
    conversation_task_id = "90000000-0000-4000-8000-000000000007"
    link_task_id = "90000000-0000-4000-8000-000000000002"
    conversation_id = "90000000-0000-4000-8000-000000000005"
    message_id = "90000000-0000-4000-8000-000000000006"
    memory_candidate_id = "90000000-0000-4000-8000-000000000008"
    message_digest = hashlib.sha256(
        b"Packaging smoke user message"
    ).hexdigest()
    run_id = "packaging_smoke_run"
    conversation_run_id = "packaging_conversation_review_run"
    events: list[str] = []
    requests_seen: list[tuple[str, str, dict[str, object]]] = []

    class Response:
        def __init__(self, status_code: int, body: dict) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return dict(self._body)

    class Http:
        def get(self, url: str, **kwargs):
            requests_seen.append(("GET", url, kwargs))
            if url.endswith("/health/ready"):
                return Response(200, {"status": "ready"})
            if url.endswith(f"/conversations/{conversation_id}/messages"):
                return Response(
                    200,
                    {
                        "schema_version": "1.0",
                        "conversation_id": conversation_id,
                        "items": [
                            {
                                "schema_version": "1.0",
                                "message_id": message_id,
                                "conversation_id": conversation_id,
                                "sequence_no": 1,
                                "role": "user",
                                "content": "Packaging smoke user message",
                                "content_sha256": message_digest,
                                "created_at": "2026-08-20T00:00:00Z",
                            }
                        ],
                        "limit": 10,
                        "after_sequence": 0,
                        "has_more": False,
                        "next_after_sequence": None,
                    },
                )
            if url.endswith("/memory/preferences"):
                return Response(
                    200,
                    {
                        "schema_version": "1.0",
                        "records": [
                            {
                                "schema_version": "1.0",
                                "record_id": "90000000-0000-4000-8000-000000000009",
                                "target_kind": "owner_preference",
                                "relationship_id": None,
                                "relationship_role": None,
                                "memory_key": "report_language",
                                "version": 1,
                                "status": "active",
                                "payload": {"value": "zh-CN"},
                                "supersedes_record_id": None,
                                "created_at": "2026-08-20T00:01:00Z",
                                "updated_at": "2026-08-20T00:01:00Z",
                            }
                        ],
                    },
                )
            if "/memory-candidates/" in url:
                return Response(
                    200,
                    {
                        "schema_version": "1.0",
                        "candidate_id": memory_candidate_id,
                        "conversation_id": conversation_id,
                        "target_scope": "owner_global",
                        "candidate_kind": "owner_preference",
                        "memory_key": "report_language",
                        "operation": "set",
                        "requires_confirmation": False,
                        "status": "accepted",
                        "gate_policy_version": "memory-gate-v1",
                        "created_at": "2026-08-20T00:00:00Z",
                        "expires_at": "2026-09-19T00:00:00Z",
                        "decided_at": "2026-08-20T00:01:00Z",
                        "decision_reason_code": "user_confirmed",
                    },
                )
            if url.endswith(f"/conversations/{conversation_id}"):
                return Response(
                    200,
                    {
                        "schema_version": "1.0",
                        "conversation_id": conversation_id,
                        "relationship_id": (
                            "90000000-0000-4000-8000-000000000004"
                        ),
                        "relationship_role": "self",
                        "status": "active",
                        "created_at": "2026-08-20T00:00:00Z",
                        "updated_at": "2026-08-20T00:00:00Z",
                        "last_message_at": "2026-08-20T00:00:00Z",
                    },
                )
            if "/player-links/" in url:
                return Response(
                    200,
                    {
                        "link_task_id": link_task_id,
                        "status": "succeeded",
                        "player_subject_id": (
                            "90000000-0000-4000-8000-000000000003"
                        ),
                        "relationship_id": (
                            "90000000-0000-4000-8000-000000000004"
                        ),
                        "confirmed_riot_id": "Packaging Smoke Fixture#TEST",
                        "failure": None,
                    },
                )
            if url.endswith(conversation_task_id):
                return Response(
                    200,
                    {
                        "schema_version": "2.0",
                        "task_id": conversation_task_id,
                        "run_id": conversation_run_id,
                        "status": "failed",
                        "terminal_reason": "worker_execution_failed",
                    },
                )
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

        def post(self, url: str, **kwargs):
            requests_seen.append(("POST", url, kwargs))
            if url.endswith("/player-links"):
                return Response(202, {"link_task_id": link_task_id})
            if url.endswith("/conversations"):
                return Response(
                    201,
                    {
                        "schema_version": "1.0",
                        "disposition": "created",
                        "conversation_id": conversation_id,
                        "relationship_id": (
                            "90000000-0000-4000-8000-000000000004"
                        ),
                        "relationship_role": "self",
                        "status": "active",
                        "created_at": "2026-08-20T00:00:00Z",
                        "updated_at": "2026-08-20T00:00:00Z",
                        "last_message_at": None,
                    },
                )
            if url.endswith(f"/conversations/{conversation_id}/messages"):
                return Response(
                    201,
                    {
                        "schema_version": "1.0",
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "sequence_no": 1,
                        "role": "user",
                        "content": "Packaging smoke user message",
                        "content_sha256": message_digest,
                        "created_at": "2026-08-20T00:00:00Z",
                    },
                )
            if url.endswith(f"/conversations/{conversation_id}/memory-candidates"):
                return Response(
                    201,
                    {
                        "schema_version": "1.0",
                        "candidate_id": memory_candidate_id,
                        "conversation_id": conversation_id,
                        "target_scope": "owner_global",
                        "candidate_kind": "owner_preference",
                        "memory_key": "report_language",
                        "operation": "set",
                        "requires_confirmation": False,
                        "status": "pending",
                        "gate_policy_version": "memory-gate-v1",
                        "created_at": "2026-08-20T00:00:00Z",
                        "expires_at": "2026-09-19T00:00:00Z",
                        "decided_at": None,
                        "decision_reason_code": None,
                    },
                )
            if url.endswith(f"/memory-candidates/{memory_candidate_id}/accept"):
                return Response(
                    200,
                    {
                        "schema_version": "1.0",
                        "candidate_id": memory_candidate_id,
                        "conversation_id": conversation_id,
                        "target_scope": "owner_global",
                        "candidate_kind": "owner_preference",
                        "memory_key": "report_language",
                        "operation": "set",
                        "requires_confirmation": False,
                        "status": "accepted",
                        "gate_policy_version": "memory-gate-v1",
                        "created_at": "2026-08-20T00:00:00Z",
                        "expires_at": "2026-09-19T00:00:00Z",
                        "decided_at": "2026-08-20T00:01:00Z",
                        "decision_reason_code": "user_confirmed",
                    },
                )
            if url.endswith(
                f"/conversations/{conversation_id}/reviews/recent"
            ):
                return Response(
                    202,
                    {
                        "schema_version": "2.0",
                        "conversation_id": conversation_id,
                        "task_id": conversation_task_id,
                        "run_id": conversation_run_id,
                        "status": "queued",
                    },
                )
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
        calls = 0

        def __init__(self, **kwargs) -> None:
            assert type(kwargs["executor"]).__name__ == "_NoExternalIoExecutor"

        def run_once(self) -> WorkerIterationResult:
            type(self).calls += 1
            claimed_task_id = (
                task_id if type(self).calls == 1 else conversation_task_id
            )
            return WorkerIterationResult(
                status=WorkerIterationStatus.FAILED,
                task_id=__import__("uuid").UUID(claimed_task_id),
            )

    class LinkWorker:
        def __init__(self, **kwargs) -> None:
            assert type(kwargs["resolver"]).__name__ == "_FakeAccountResolver"
            assert kwargs["worker_id"] == "packaging-link-smoke-worker"

        def run_once(self) -> PlayerLinkWorkerIterationResult:
            return PlayerLinkWorkerIterationResult(
                status=PlayerLinkWorkerIterationStatus.SUCCEEDED,
                link_task_id=__import__("uuid").UUID(link_task_id),
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
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.PostgresPlayerRepository",
        lambda _factory: object(),
    )
    monkeypatch.setattr("scripts.run_packaging_smoke.ReviewWorker", Worker)
    monkeypatch.setattr("scripts.run_packaging_smoke.PlayerLinkWorker", LinkWorker)

    result = execute_packaging_smoke(
        load_packaging_smoke_settings(valid_environment(tmp_path)),
        worker_id="smoke-worker",
        http=Http(),
    )

    assert result.schema_version == "1.3"
    assert result.task_status == "failed"
    assert result.link_status == "succeeded"
    assert str(result.link_task_id) == link_task_id
    assert result.conversation_status == "active"
    assert str(result.conversation_id) == conversation_id
    assert str(result.message_id) == message_id
    assert result.message_sequence_no == 1
    assert str(result.memory_candidate_id) == memory_candidate_id
    assert result.memory_candidate_status == "accepted"
    assert result.memory_preference_version == 1
    assert result.memory_preference_value == "zh-CN"
    assert str(result.conversation_review_task_id) == conversation_task_id
    assert result.conversation_review_run_id == conversation_run_id
    assert result.conversation_review_status == "failed"
    assert result.external_riot_provider_calls == 0
    assert events == ["engine.dispose"]

    conversation_post = next(
        item
        for item in requests_seen
        if item[0] == "POST" and item[1].endswith("/conversations")
    )
    assert conversation_post[2]["json"] == {
        "relationship_id": "90000000-0000-4000-8000-000000000004"
    }
    conversation_headers = conversation_post[2]["headers"]
    assert isinstance(conversation_headers, dict)
    assert set(conversation_headers) == {"Idempotency-Key"}
    assert 1 <= len(conversation_headers["Idempotency-Key"]) <= 128

    message_post = next(
        item
        for item in requests_seen
        if item[0] == "POST" and item[1].endswith("/messages")
    )
    assert message_post[2]["json"] == {
        "content": "Packaging smoke user message"
    }
    message_get = next(
        item
        for item in requests_seen
        if item[0] == "GET" and item[1].endswith("/messages")
    )
    assert message_get[2]["params"] == {
        "limit": 10,
        "after_sequence": 0,
    }
    conversation_review_post = next(
        item
        for item in requests_seen
        if item[0] == "POST"
        and item[1].endswith(
            f"/conversations/{conversation_id}/reviews/recent"
        )
    )
    assert conversation_review_post[2]["json"] == {
        "count": 5,
        "queue": 420,
        "focus": "overall",
    }
    assert set(conversation_review_post[2]["headers"]) == {"Idempotency-Key"}


@pytest.mark.parametrize(
    "code",
    (
        "packaging_smoke_conversation_create_failed",
        "packaging_smoke_conversation_query_failed",
        "packaging_smoke_conversation_invalid",
        "packaging_smoke_message_append_failed",
        "packaging_smoke_message_query_failed",
        "packaging_smoke_message_invalid",
        "packaging_smoke_conversation_review_create_failed",
        "packaging_smoke_conversation_review_iteration_invalid",
        "packaging_smoke_conversation_review_query_failed",
        "packaging_smoke_conversation_review_terminal_invalid",
    ),
)
def test_conversation_packaging_failure_codes_are_allowlisted_and_body_free(
    code: str,
) -> None:
    error = PackagingSmokeError(code)  # type: ignore[arg-type]

    assert str(error) == code
    assert "Packaging smoke user message" not in repr(error)
    assert "secret" not in repr(error)


def test_packaging_smoke_reports_database_preflight_failure_without_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "90000000-0000-4000-8000-000000000001"

    class Response:
        def __init__(self, status_code: int, body: dict) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return dict(self._body)

    class Http:
        def get(self, _url: str, **_kwargs):
            return Response(200, {"status": "ready"})

        def post(self, _url: str, **_kwargs):
            return Response(
                202,
                {"task_id": task_id, "run_id": "packaging_smoke_run"},
            )

    monkeypatch.setattr(
        "scripts.run_packaging_smoke.build_engine",
        lambda _settings: (_ for _ in ()).throw(
            RuntimeError("postgresql://secret@private.example/riftcoach")
        ),
    )

    with pytest.raises(PackagingSmokeError) as exc_info:
        execute_packaging_smoke(
            load_packaging_smoke_settings(valid_environment(tmp_path)),
            worker_id="smoke-worker",
            http=Http(),
        )

    assert exc_info.value.code == "packaging_smoke_database_not_ready"
    assert "private.example" not in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_packaging_smoke_preserves_allowlisted_worker_failure_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "90000000-0000-4000-8000-000000000001"

    class Response:
        def __init__(self, status_code: int, body: dict) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return dict(self._body)

    class Http:
        def get(self, _url: str, **_kwargs):
            return Response(200, {"status": "ready"})

        def post(self, _url: str, **_kwargs):
            return Response(
                202,
                {"task_id": task_id, "run_id": "packaging_smoke_run"},
            )

    class Engine:
        def dispose(self) -> None:
            pass

    class Probe:
        def __init__(self, _engine: object) -> None:
            pass

        def check(self) -> ReadinessResult:
            return ReadinessResult.ready()

    class Worker:
        def __init__(self, **_kwargs) -> None:
            pass

        def run_once(self) -> WorkerIterationResult:
            raise ReviewWorkerError("task_claim_failed")

    monkeypatch.setattr(
        "scripts.run_packaging_smoke.build_engine",
        lambda _settings: Engine(),
    )
    monkeypatch.setattr("scripts.run_packaging_smoke.PostgresReadinessProbe", Probe)
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.build_session_factory",
        lambda _engine: lambda: None,
    )
    monkeypatch.setattr(
        "scripts.run_packaging_smoke.PostgresTaskRepository",
        lambda _factory: object(),
    )
    monkeypatch.setattr("scripts.run_packaging_smoke.ReviewWorker", Worker)

    with pytest.raises(PackagingSmokeError) as exc_info:
        execute_packaging_smoke(
            load_packaging_smoke_settings(valid_environment(tmp_path)),
            worker_id="smoke-worker",
            http=Http(),
        )

    assert exc_info.value.code == "packaging_smoke_claim_failed"
