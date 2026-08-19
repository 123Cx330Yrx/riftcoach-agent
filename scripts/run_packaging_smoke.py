"""Linux/Compose control-plane smoke with zero Riot or Provider calls.

The smoke covers two independent asynchronous paths against real PostgreSQL:
one Review Task deliberately reaches its safe failed terminal without external
I/O, while one Player Link uses an in-process Fake Account Resolver and reaches
succeeded.  Successful Agent/Harness execution remains covered by the existing
offline vertical tests rather than a fake Coach in this package check.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import requests
from sqlalchemy.engine import make_url

from app.api.composition import PostgresReadinessProbe
from app.persistence.config import DatabaseSettings, load_database_settings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.player_repository import PostgresPlayerRepository
from app.persistence.task_repository import PostgresTaskRepository
from app.players.link_worker import (
    PlayerLinkWorker,
    PlayerLinkWorkerError,
    PlayerLinkWorkerIterationStatus,
)
from app.players.models import ResolvedRiotAccount, RoutingRegion
from app.tasks.models import ReviewTask, TaskTerminal
from app.workers.review_worker import (
    ReviewWorker,
    ReviewWorkerError,
    WorkerIterationStatus,
)


PackagingSmokeErrorCode: TypeAlias = Literal[
    "packaging_smoke_disabled",
    "packaging_smoke_profile_invalid",
    "packaging_smoke_configuration_invalid",
    "packaging_smoke_api_not_ready",
    "packaging_smoke_task_create_failed",
    "packaging_smoke_database_not_ready",
    "packaging_smoke_claim_failed",
    "packaging_smoke_claim_invalid",
    "packaging_smoke_terminal_update_failed",
    "packaging_smoke_iteration_invalid",
    "packaging_smoke_task_query_failed",
    "packaging_smoke_worker_failed",
    "packaging_smoke_terminal_invalid",
    "packaging_smoke_link_create_failed",
    "packaging_smoke_link_claim_failed",
    "packaging_smoke_link_terminal_update_failed",
    "packaging_smoke_link_iteration_invalid",
    "packaging_smoke_link_query_failed",
    "packaging_smoke_link_terminal_invalid",
]
_ERROR_CODES = frozenset(
    {
        "packaging_smoke_disabled",
        "packaging_smoke_profile_invalid",
        "packaging_smoke_configuration_invalid",
        "packaging_smoke_api_not_ready",
        "packaging_smoke_task_create_failed",
        "packaging_smoke_database_not_ready",
        "packaging_smoke_claim_failed",
        "packaging_smoke_claim_invalid",
        "packaging_smoke_terminal_update_failed",
        "packaging_smoke_iteration_invalid",
        "packaging_smoke_task_query_failed",
        "packaging_smoke_worker_failed",
        "packaging_smoke_terminal_invalid",
        "packaging_smoke_link_create_failed",
        "packaging_smoke_link_claim_failed",
        "packaging_smoke_link_terminal_update_failed",
        "packaging_smoke_link_iteration_invalid",
        "packaging_smoke_link_query_failed",
        "packaging_smoke_link_terminal_invalid",
    }
)
_LOCAL_SMOKE_API_HOSTS = frozenset({"api", "localhost", "127.0.0.1", "::1"})
_LINK_SMOKE_WORKER_ID = "packaging-link-smoke-worker"
_LOCAL_SMOKE_DATABASE_HOSTS = frozenset(
    {"postgres", "localhost", "127.0.0.1", "::1"}
)


class PackagingSmokeError(RuntimeError):
    def __init__(self, code: PackagingSmokeErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported packaging smoke error")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PackagingSmokeSettings:
    database: DatabaseSettings = field(repr=False)
    base_url: str
    timeout_s: float


@dataclass(frozen=True, slots=True)
class PackagingSmokeResult:
    schema_version: Literal["1.0"]
    task_id: UUID
    run_id: str
    task_status: Literal["failed"]
    link_task_id: UUID
    link_status: Literal["succeeded"]
    external_riot_provider_calls: Literal[0]


class _NoExternalIoExecutor:
    def execute(self, _task: ReviewTask) -> TaskTerminal:
        # ReviewWorker converts this into its allowlisted safe failure reason.
        # No request body, secret or exception text reaches SQL/log/API.
        raise RuntimeError("packaging smoke intentionally performs no external I/O")


class _FakeAccountResolver:
    def resolve(
        self,
        *,
        routing_region: RoutingRegion,
        game_name: str,
        tag_line: str,
    ) -> ResolvedRiotAccount:
        del game_name, tag_line
        return ResolvedRiotAccount(
            routing_region=routing_region,
            puuid="packaging_smoke_fixture_puuid",
            game_name="Packaging Smoke Fixture",
            tag_line="TEST",
        )


def load_packaging_smoke_settings(
    environment: Mapping[str, str],
) -> PackagingSmokeSettings:
    if environment.get("RIFTCOACH_PACKAGING_SMOKE", "").strip().lower() != "true":
        raise PackagingSmokeError("packaging_smoke_disabled")
    if environment.get("RIFTCOACH_API_PROFILE", "").strip().lower() not in {
        "local",
        "test",
    }:
        raise PackagingSmokeError("packaging_smoke_profile_invalid")

    try:
        database = load_database_settings(environment)
        if make_url(database.url).host not in _LOCAL_SMOKE_DATABASE_HOSTS:
            raise ValueError("smoke database must be local or Compose-internal")
        base_url = environment.get(
            "RIFTCOACH_SMOKE_BASE_URL",
            "http://api:8000",
        ).strip().rstrip("/")
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or not parsed.hostname
            or parsed.hostname not in _LOCAL_SMOKE_API_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("smoke base URL must be a plain HTTP origin")
        timeout_s = float(
            environment.get("RIFTCOACH_SMOKE_HTTP_TIMEOUT_SECONDS", "5")
        )
        if not math.isfinite(timeout_s) or not 0 < timeout_s <= 30:
            raise ValueError("smoke timeout is invalid")
        return PackagingSmokeSettings(
            database=database,
            base_url=base_url,
            timeout_s=timeout_s,
        )
    except PackagingSmokeError:
        raise
    except Exception:
        raise PackagingSmokeError(
            "packaging_smoke_configuration_invalid"
        ) from None


def execute_packaging_smoke(
    settings: PackagingSmokeSettings,
    *,
    worker_id: str,
    http: requests.Session | None = None,
) -> PackagingSmokeResult:
    if not isinstance(settings, PackagingSmokeSettings):
        raise TypeError("settings must be PackagingSmokeSettings")
    session = http or requests.Session()
    owns_http = http is None
    engine: Any | None = None
    try:
        try:
            ready = session.get(
                f"{settings.base_url}/health/ready",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_api_not_ready") from None
        if ready.status_code != 200 or _json_object(ready).get("status") != "ready":
            raise PackagingSmokeError("packaging_smoke_api_not_ready")

        try:
            created = session.post(
                f"{settings.base_url}/reviews/recent",
                headers={"Idempotency-Key": f"packaging-smoke-{uuid4().hex}"},
                json={
                    "riot_id": "SyntheticSmoke#TEST",
                    "count": 5,
                    "queue": 420,
                    "focus": "overall",
                },
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_task_create_failed"
            ) from None
        created_body = _json_object(created)
        if created.status_code != 202:
            raise PackagingSmokeError("packaging_smoke_task_create_failed")
        try:
            task_id = UUID(str(created_body["task_id"]))
            run_id = str(created_body["run_id"])
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_task_create_failed"
            ) from None

        try:
            engine = build_engine(settings.database)
            if not PostgresReadinessProbe(engine).check().is_ready:
                raise PackagingSmokeError("packaging_smoke_database_not_ready")
            session_factory = build_session_factory(engine)
            repository = PostgresTaskRepository(session_factory)
            player_repository = PostgresPlayerRepository(session_factory)
        except PackagingSmokeError:
            raise
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_database_not_ready"
            ) from None

        try:
            iteration = ReviewWorker(
                repository=repository,
                executor=_NoExternalIoExecutor(),
                worker_id=worker_id,
            ).run_once()
        except ReviewWorkerError as error:
            worker_codes = {
                "task_claim_failed": "packaging_smoke_claim_failed",
                "task_claim_invalid": "packaging_smoke_claim_invalid",
                "task_terminal_update_failed": (
                    "packaging_smoke_terminal_update_failed"
                ),
            }
            raise PackagingSmokeError(
                worker_codes.get(error.code, "packaging_smoke_worker_failed")
            ) from None
        except Exception:
            raise PackagingSmokeError("packaging_smoke_worker_failed") from None
        if (
            iteration.status is not WorkerIterationStatus.FAILED
            or iteration.task_id != task_id
        ):
            raise PackagingSmokeError("packaging_smoke_iteration_invalid")

        try:
            terminal = session.get(
                f"{settings.base_url}/tasks/{task_id}",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_task_query_failed"
            ) from None
        terminal_body = _json_object(terminal)
        if (
            terminal.status_code != 200
            or terminal_body.get("status") != "failed"
            or terminal_body.get("terminal_reason") != "worker_execution_failed"
            or terminal_body.get("run_id") != run_id
        ):
            raise PackagingSmokeError("packaging_smoke_terminal_invalid")

        try:
            created_link = session.post(
                f"{settings.base_url}/player-links",
                headers={
                    "Idempotency-Key": f"packaging-link-smoke-{uuid4().hex}"
                },
                json={
                    "riot_id": "SyntheticLinkSmoke#TEST",
                    "routing_region": "asia",
                    "relationship_role": "self",
                },
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_link_create_failed"
            ) from None
        created_link_body = _json_object(created_link)
        if created_link.status_code != 202:
            raise PackagingSmokeError("packaging_smoke_link_create_failed")
        try:
            link_task_id = UUID(str(created_link_body["link_task_id"]))
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_link_create_failed"
            ) from None

        try:
            link_iteration = PlayerLinkWorker(
                repository=player_repository,
                resolver=_FakeAccountResolver(),
                worker_id=_LINK_SMOKE_WORKER_ID,
            ).run_once()
        except PlayerLinkWorkerError as error:
            link_worker_codes = {
                "link_claim_failed": "packaging_smoke_link_claim_failed",
                "link_terminal_update_failed": (
                    "packaging_smoke_link_terminal_update_failed"
                ),
            }
            raise PackagingSmokeError(
                link_worker_codes.get(
                    error.code,
                    "packaging_smoke_link_iteration_invalid",
                )
            ) from None
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_link_iteration_invalid"
            ) from None
        if (
            link_iteration.status
            is not PlayerLinkWorkerIterationStatus.SUCCEEDED
            or link_iteration.link_task_id != link_task_id
        ):
            raise PackagingSmokeError(
                "packaging_smoke_link_iteration_invalid"
            )

        try:
            terminal_link = session.get(
                f"{settings.base_url}/player-links/{link_task_id}",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_link_query_failed"
            ) from None
        terminal_link_body = _json_object(terminal_link)
        if (
            terminal_link.status_code != 200
            or terminal_link_body.get("status") != "succeeded"
            or terminal_link_body.get("link_task_id") != str(link_task_id)
            or not terminal_link_body.get("player_subject_id")
            or not terminal_link_body.get("relationship_id")
            or terminal_link_body.get("confirmed_riot_id")
            != "Packaging Smoke Fixture#TEST"
            or terminal_link_body.get("failure") is not None
        ):
            raise PackagingSmokeError(
                "packaging_smoke_link_terminal_invalid"
            )

        return PackagingSmokeResult(
            schema_version="1.0",
            task_id=task_id,
            run_id=run_id,
            task_status="failed",
            link_task_id=link_task_id,
            link_status="succeeded",
            external_riot_provider_calls=0,
        )
    except PackagingSmokeError:
        raise
    except Exception:
        raise PackagingSmokeError("packaging_smoke_worker_failed") from None
    finally:
        if engine is not None:
            engine.dispose()
        if owns_http:
            session.close()


def _json_object(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the no-external-I/O RiftCoach packaging smoke.",
    )
    parser.add_argument("--worker-id", default="packaging-smoke-worker")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    source = dict(os.environ) if environment is None else environment
    try:
        settings = load_packaging_smoke_settings(source)
        result = execute_packaging_smoke(settings, worker_id=args.worker_id)
    except PackagingSmokeError as error:
        print(error.code, file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "schema_version": result.schema_version,
                "task_id": str(result.task_id),
                "run_id": result.run_id,
                "task_status": result.task_status,
                "link_task_id": str(result.link_task_id),
                "link_status": result.link_status,
                "external_riot_provider_calls": result.external_riot_provider_calls,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
