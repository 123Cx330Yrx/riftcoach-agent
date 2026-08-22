"""Linux/Compose control-plane smoke with zero Riot or Provider calls.

The smoke covers the durable control plane against real PostgreSQL: one legacy
Review Task deliberately reaches its safe failed terminal without external
I/O; one Player Link uses an in-process Fake Account Resolver and reaches
succeeded; that relationship creates a Conversation, one user Message and one
body-safe Memory Candidate that is rejected without a materializer; a
schema 2.0 Conversation-bound Review Task then passes through the same Worker
and reaches the same safe terminal.  Successful Agent/Harness execution remains
covered by the existing offline vertical tests rather than a fake Coach here.
"""

from __future__ import annotations

import argparse
import hashlib
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
from app.memory.context_models import MemoryContextBinding, MemoryContextRecordKind, MemoryContextSnapshot
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.memory_context_repository import MemoryContextRepositoryError
from app.players.models import RelationshipRole
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
    "packaging_smoke_task_event_query_failed",
    "packaging_smoke_task_event_invalid",
    "packaging_smoke_worker_failed",
    "packaging_smoke_terminal_invalid",
    "packaging_smoke_link_create_failed",
    "packaging_smoke_link_claim_failed",
    "packaging_smoke_link_terminal_update_failed",
    "packaging_smoke_link_iteration_invalid",
    "packaging_smoke_link_query_failed",
    "packaging_smoke_link_terminal_invalid",
    "packaging_smoke_conversation_create_failed",
    "packaging_smoke_conversation_query_failed",
    "packaging_smoke_conversation_invalid",
    "packaging_smoke_message_append_failed",
    "packaging_smoke_message_query_failed",
    "packaging_smoke_message_invalid",
    "packaging_smoke_memory_candidate_create_failed",
    "packaging_smoke_memory_candidate_accept_failed",
    "packaging_smoke_memory_preference_query_failed",
    "packaging_smoke_conversation_review_create_failed",
    "packaging_smoke_conversation_review_iteration_invalid",
    "packaging_smoke_conversation_review_query_failed",
    "packaging_smoke_conversation_review_terminal_invalid",
    "packaging_smoke_memory_context_unavailable",
    "packaging_smoke_memory_context_repository_unavailable",
    "packaging_smoke_memory_context_integrity_failed",
    "packaging_smoke_owner_export_failed",
    "packaging_smoke_owner_export_invalid",
    "packaging_smoke_owner_delete_failed",
    "packaging_smoke_owner_delete_visibility_failed",
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
        "packaging_smoke_task_event_query_failed",
        "packaging_smoke_task_event_invalid",
        "packaging_smoke_worker_failed",
        "packaging_smoke_terminal_invalid",
        "packaging_smoke_link_create_failed",
        "packaging_smoke_link_claim_failed",
        "packaging_smoke_link_terminal_update_failed",
        "packaging_smoke_link_iteration_invalid",
        "packaging_smoke_link_query_failed",
        "packaging_smoke_link_terminal_invalid",
        "packaging_smoke_conversation_create_failed",
        "packaging_smoke_conversation_query_failed",
        "packaging_smoke_conversation_invalid",
        "packaging_smoke_message_append_failed",
        "packaging_smoke_message_query_failed",
        "packaging_smoke_message_invalid",
        "packaging_smoke_memory_candidate_create_failed",
        "packaging_smoke_memory_candidate_accept_failed",
        "packaging_smoke_memory_preference_query_failed",
        "packaging_smoke_conversation_review_create_failed",
        "packaging_smoke_conversation_review_iteration_invalid",
        "packaging_smoke_conversation_review_query_failed",
        "packaging_smoke_conversation_review_terminal_invalid",
        "packaging_smoke_memory_context_unavailable",
        "packaging_smoke_memory_context_repository_unavailable",
        "packaging_smoke_memory_context_integrity_failed",
        "packaging_smoke_owner_export_failed",
        "packaging_smoke_owner_export_invalid",
        "packaging_smoke_owner_delete_failed",
        "packaging_smoke_owner_delete_visibility_failed",
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
    schema_version: Literal["1.6"]
    task_id: UUID
    run_id: str
    task_status: Literal["failed"]
    link_task_id: UUID
    link_status: Literal["succeeded"]
    conversation_id: UUID
    conversation_status: Literal["active"]
    message_id: UUID
    message_sequence_no: Literal[1]
    memory_candidate_id: UUID
    memory_candidate_status: Literal["accepted"]
    memory_preference_version: Literal[1]
    memory_preference_value: Literal["zh-CN"]
    training_candidate_id: UUID
    training_candidate_status: Literal["accepted"]
    training_plan_id: UUID
    training_plan_version: Literal[1]
    conversation_review_task_id: UUID
    conversation_review_run_id: str
    conversation_review_status: Literal["failed"]
    memory_context_record_count: Literal[3]
    memory_context_kinds: tuple[str, ...]
    terminal_assistant_message_count: Literal[0]
    owner_export_schema_version: Literal["1.0"]
    owner_export_record_count: int
    owner_export_record_kinds: tuple[str, ...]
    deletion_scope: Literal["conversation_only"]
    deletion_status: Literal["complete"]
    post_delete_conversation_status: Literal["not_found"]
    post_delete_message_status: Literal["not_found"]
    preference_survives_delete: Literal[1]
    plan_survives_delete: Literal[1]
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
            task_events = session.get(
                f"{settings.base_url}/tasks/{task_id}/events",
                params={"after_cursor": 0, "limit": 100},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_task_event_query_failed"
            ) from None
        task_events_body = _json_object(task_events)
        event_items = task_events_body.get("events")
        if task_events.status_code != 200 or not isinstance(event_items, list):
            print(
                "packaging_smoke_task_event_response_invalid "
                f"status={task_events.status_code} "
                f"code={task_events_body.get('code')} "
                f"keys={sorted(task_events_body)}",
                file=sys.stderr,
            )
            raise PackagingSmokeError("packaging_smoke_task_event_query_failed")
        event_kinds = tuple(
            item.get("event_kind")
            for item in event_items
            if isinstance(item, dict)
        )
        forbidden_event_fields = {
            "owner_id",
            "worker_id",
            "checkpoint_reference",
            "lease_token",
            "operation_identity",
            "request_payload",
            "puuid",
        }
        if (
            len(event_kinds) != len(event_items)
            or task_events_body.get("task_id") != str(task_id)
            or task_events_body.get("after_cursor") != 0
            or task_events_body.get("limit") != 100
            or task_events_body.get("has_more") is not False
            or not event_kinds
            or event_kinds[0] != "created"
            or "claimed" not in event_kinds
            or "execution_started" not in event_kinds
            or event_kinds[-1] != "failed"
            or any(
                forbidden_event_fields.intersection(item)
                for item in event_items
                if isinstance(item, dict)
            )
        ):
            raise PackagingSmokeError("packaging_smoke_task_event_invalid")

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

        try:
            relationship_id = UUID(str(terminal_link_body["relationship_id"]))
            player_subject_id = UUID(str(terminal_link_body["player_subject_id"]))
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_link_terminal_invalid"
            ) from None

        try:
            created_conversation = session.post(
                f"{settings.base_url}/conversations",
                headers={
                    "Idempotency-Key": (
                        f"packaging-conversation-smoke-{uuid4().hex}"
                    )
                },
                json={"relationship_id": str(relationship_id)},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_create_failed"
            ) from None
        created_conversation_body = _json_object(created_conversation)
        if (
            created_conversation.status_code != 201
            or created_conversation_body.get("disposition") != "created"
            or created_conversation_body.get("status") != "active"
            or created_conversation_body.get("relationship_id")
            != str(relationship_id)
        ):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_create_failed"
            )
        try:
            conversation_id = UUID(
                str(created_conversation_body["conversation_id"])
            )
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_create_failed"
            ) from None

        message_content = "Packaging smoke user message"
        expected_digest = hashlib.sha256(
            message_content.encode("utf-8")
        ).hexdigest()
        try:
            appended_message = session.post(
                f"{settings.base_url}/conversations/{conversation_id}/messages",
                json={"content": message_content},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_message_append_failed"
            ) from None
        appended_message_body = _json_object(appended_message)
        if (
            appended_message.status_code != 201
            or appended_message_body.get("conversation_id")
            != str(conversation_id)
            or appended_message_body.get("sequence_no") != 1
            or appended_message_body.get("role") != "user"
            or appended_message_body.get("content") != message_content
            or appended_message_body.get("content_sha256") != expected_digest
        ):
            raise PackagingSmokeError("packaging_smoke_message_invalid")

        try:
            created_memory_candidate = session.post(
                (
                    f"{settings.base_url}/conversations/{conversation_id}"
                    "/memory-candidates"
                ),
                headers={
                    "Idempotency-Key": (
                        f"packaging-memory-candidate-{uuid4().hex}"
                    )
                },
                json={
                    "target_scope": "owner_global",
                    "candidate_kind": "owner_preference",
                    "memory_key": "report_language",
                    "operation": "set",
                    "proposal_payload": {"value": "zh-CN"},
                },
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_memory_candidate_create_failed"
            ) from None
        memory_candidate_body = _json_object(created_memory_candidate)
        if (
            created_memory_candidate.status_code != 201
            or memory_candidate_body.get("conversation_id") != str(conversation_id)
            or memory_candidate_body.get("status") != "pending"
            or any(
                private in memory_candidate_body
                for private in (
                    "proposal_payload",
                    "proposal_confidence",
                    "producer_id",
                    "player_subject_id",
                    "relationship_id",
                    "source_message_id",
                )
            )
        ):
            raise PackagingSmokeError(
                "packaging_smoke_memory_candidate_create_failed"
            )
        try:
            memory_candidate_id = UUID(str(memory_candidate_body["candidate_id"]))
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_memory_candidate_create_failed"
            ) from None

        try:
            accepted_memory_candidate = session.post(
                (
                    f"{settings.base_url}/memory-candidates/"
                    f"{memory_candidate_id}/accept"
                ),
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_memory_candidate_accept_failed"
            ) from None
        accepted_memory_candidate_body = _json_object(accepted_memory_candidate)
        if (
            accepted_memory_candidate.status_code != 200
            or accepted_memory_candidate_body.get("candidate_id")
            != str(memory_candidate_id)
            or accepted_memory_candidate_body.get("status") != "accepted"
            or accepted_memory_candidate_body.get("decision_reason_code")
            != "user_confirmed"
        ):
            raise PackagingSmokeError(
                "packaging_smoke_memory_candidate_accept_failed"
            )
        try:
            memory_preferences = session.get(
                f"{settings.base_url}/memory/preferences",
                params={"include_history": False, "limit": 10},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_memory_preference_query_failed"
            ) from None
        memory_preferences_body = _json_object(memory_preferences)
        records = memory_preferences_body.get("records")
        if (
            memory_preferences.status_code != 200
            or not isinstance(records, list)
            or len(records) != 1
            or records[0].get("target_kind") != "owner_preference"
            or records[0].get("memory_key") != "report_language"
            or records[0].get("version") != 1
            or records[0].get("status") != "active"
            or records[0].get("payload") != {"value": "zh-CN"}
            or any(
                private in records[0]
                for private in ("player_subject_id", "puuid", "source_candidate_id")
            )
        ):
            raise PackagingSmokeError(
                "packaging_smoke_memory_preference_query_failed"
            )

        try:
            created_training_candidate = session.post(
                f"{settings.base_url}/conversations/{conversation_id}/memory-candidates",
                headers={"Idempotency-Key": f"packaging-training-{uuid4().hex}"},
                json={
                    "target_scope": "owner_player",
                    "candidate_kind": "training_plan",
                    "memory_key": "active_plan",
                    "operation": "set",
                    "proposal_payload": {
                        "value": {
                            "action": "activate",
                            "title": "Packaging smoke plan",
                            "objective": "Prove installed Plan materialization",
                            "metrics": [
                                {
                                    "metric_key": "deaths_before_15",
                                    "direction": "decrease",
                                    "unit": "count",
                                }
                            ],
                        }
                    },
                },
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_training_candidate_create_failed") from None
        training_candidate_body = _json_object(created_training_candidate)
        if (
            created_training_candidate.status_code != 201
            or training_candidate_body.get("status") != "pending"
            or training_candidate_body.get("requires_confirmation") is not True
        ):
            raise PackagingSmokeError("packaging_smoke_training_candidate_create_failed")
        try:
            training_candidate_id = UUID(str(training_candidate_body["candidate_id"]))
            accepted_training_candidate = session.post(
                f"{settings.base_url}/memory-candidates/{training_candidate_id}/accept",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_training_candidate_accept_failed") from None
        accepted_training_body = _json_object(accepted_training_candidate)
        if (
            accepted_training_candidate.status_code != 200
            or accepted_training_body.get("status") != "accepted"
            or accepted_training_body.get("candidate_kind") != "training_plan"
        ):
            raise PackagingSmokeError("packaging_smoke_training_candidate_accept_failed")
        try:
            training_plan = session.get(
                f"{settings.base_url}/memory/players/{relationship_id}/training-plan",
                params={"include_history": False, "limit": 10},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_training_plan_query_failed") from None
        training_plan_body = _json_object(training_plan)
        plans = training_plan_body.get("plans")
        if (
            training_plan.status_code != 200
            or not isinstance(plans, list)
            or len(plans) != 1
            or plans[0].get("status") != "active"
            or plans[0].get("version") != 1
            or any(private in plans[0] for private in ("player_subject_id", "source_candidate_id", "puuid"))
        ):
            raise PackagingSmokeError("packaging_smoke_training_plan_query_failed")
        try:
            training_plan_id = UUID(str(plans[0]["plan_id"]))
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError("packaging_smoke_training_plan_query_failed") from None
        try:
            message_id = UUID(str(appended_message_body["message_id"]))
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_message_invalid"
            ) from None

        try:
            conversation = session.get(
                f"{settings.base_url}/conversations/{conversation_id}",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_query_failed"
            ) from None
        conversation_body = _json_object(conversation)
        if (
            conversation.status_code != 200
            or conversation_body.get("conversation_id") != str(conversation_id)
            or conversation_body.get("relationship_id") != str(relationship_id)
            or conversation_body.get("status") != "active"
            or not conversation_body.get("last_message_at")
        ):
            raise PackagingSmokeError("packaging_smoke_conversation_invalid")

        try:
            message_page = session.get(
                f"{settings.base_url}/conversations/{conversation_id}/messages",
                params={"limit": 10, "after_sequence": 0},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_message_query_failed"
            ) from None
        message_page_body = _json_object(message_page)
        items = message_page_body.get("items")
        if (
            message_page.status_code != 200
            or message_page_body.get("conversation_id") != str(conversation_id)
            or message_page_body.get("limit") != 10
            or message_page_body.get("after_sequence") != 0
            or message_page_body.get("has_more") is not False
            or message_page_body.get("next_after_sequence") is not None
            or not isinstance(items, list)
            or len(items) != 1
            or not isinstance(items[0], dict)
            or items[0].get("message_id") != str(message_id)
            or items[0].get("sequence_no") != 1
            or items[0].get("role") != "user"
            or items[0].get("content") != message_content
            or items[0].get("content_sha256") != expected_digest
        ):
            raise PackagingSmokeError("packaging_smoke_message_invalid")

        try:
            created_conversation_review = session.post(
                (
                    f"{settings.base_url}/conversations/{conversation_id}"
                    "/reviews/recent"
                ),
                headers={
                    "Idempotency-Key": (
                        f"packaging-conversation-review-smoke-{uuid4().hex}"
                    )
                },
                json={"count": 5, "queue": 420, "focus": "overall"},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_create_failed"
            ) from None
        conversation_review_body = _json_object(created_conversation_review)
        if (
            created_conversation_review.status_code != 202
            or conversation_review_body.get("schema_version") != "2.0"
            or conversation_review_body.get("conversation_id")
            != str(conversation_id)
            or conversation_review_body.get("status") != "queued"
            or any(
                forbidden in conversation_review_body
                for forbidden in (
                    "puuid",
                    "player_subject_id",
                    "relationship_id",
                    "relationship_role",
                )
            )
        ):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_create_failed"
            )
        try:
            conversation_review_task_id = UUID(
                str(conversation_review_body["task_id"])
            )
            conversation_review_run_id = str(
                conversation_review_body["run_id"]
            )
        except (KeyError, TypeError, ValueError):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_create_failed"
            ) from None

        try:
            conversation_review_iteration = ReviewWorker(
                repository=repository,
                executor=_NoExternalIoExecutor(),
                worker_id=worker_id,
            ).run_once()
        except ReviewWorkerError as error:
            conversation_worker_codes = {
                "task_claim_failed": (
                    "packaging_smoke_conversation_review_iteration_invalid"
                ),
                "task_claim_invalid": (
                    "packaging_smoke_conversation_review_iteration_invalid"
                ),
                "task_terminal_update_failed": (
                    "packaging_smoke_conversation_review_iteration_invalid"
                ),
            }
            raise PackagingSmokeError(
                conversation_worker_codes.get(
                    error.code,
                    "packaging_smoke_conversation_review_iteration_invalid",
                )
            ) from None
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_iteration_invalid"
            ) from None
        if (
            conversation_review_iteration.status
            is not WorkerIterationStatus.FAILED
            or conversation_review_iteration.task_id
            != conversation_review_task_id
        ):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_iteration_invalid"
            )

        try:
            conversation_review_terminal = session.get(
                f"{settings.base_url}/tasks/{conversation_review_task_id}",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_query_failed"
            ) from None
        conversation_review_terminal_body = _json_object(
            conversation_review_terminal
        )
        if (
            conversation_review_terminal.status_code != 200
            or conversation_review_terminal_body.get("schema_version") != "2.0"
            or conversation_review_terminal_body.get("status") != "failed"
            or conversation_review_terminal_body.get("terminal_reason")
            != "worker_execution_failed"
            or conversation_review_terminal_body.get("run_id")
            != conversation_review_run_id
        ):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_terminal_invalid"
            )

        try:
            get_persisted_task = getattr(repository, "get_by_task_id", None)
            persisted_review_task = (
                None
                if not callable(get_persisted_task)
                else get_persisted_task(
                    owner_id="packaging-smoke-owner",
                    task_id=conversation_review_task_id,
                )
            )
            if persisted_review_task is not None:
                if (
                    persisted_review_task.conversation_binding is None
                    or persisted_review_task.run_id != conversation_review_run_id
                ):
                    raise MemoryContextRepositoryError("memory_context_unavailable")
                task_binding = persisted_review_task.conversation_binding
            else:
                task_binding = None
            context_snapshot = PostgresMemoryContextRepository(
                session_factory
            ).load(
                MemoryContextBinding(
                    run_id=conversation_review_run_id,
                    owner_id="packaging-smoke-owner",
                    conversation_id=(
                        conversation_id
                        if task_binding is None
                        else task_binding.conversation_id
                    ),
                    relationship_id=(
                        relationship_id
                        if task_binding is None
                        else task_binding.relationship_id
                    ),
                    player_subject_id=(
                        player_subject_id
                        if task_binding is None
                        else task_binding.player_subject_id
                    ),
                    relationship_role=(
                        RelationshipRole.SELF
                        if task_binding is None
                        else task_binding.relationship_role
                    ),
                )
            )
        except MemoryContextRepositoryError as error:
            context_codes = {
                "memory_context_unavailable": "packaging_smoke_memory_context_unavailable",
                "memory_context_repository_unavailable": "packaging_smoke_memory_context_repository_unavailable",
                "memory_context_integrity_failed": "packaging_smoke_memory_context_integrity_failed",
            }
            raise PackagingSmokeError(
                context_codes.get(
                    str(error), "packaging_smoke_conversation_review_terminal_invalid"
                )
            ) from None
        except Exception:
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_terminal_invalid"
            ) from None
        if not isinstance(context_snapshot, MemoryContextSnapshot):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_terminal_invalid"
            )
        memory_context_kinds = tuple(
            row.kind.value for row in context_snapshot.records
        )
        terminal_assistant_message_count = sum(
            row.kind is MemoryContextRecordKind.MESSAGE
            and json.loads(row.content).get("role") == "assistant"
            for row in context_snapshot.records
        )
        if (
            len(context_snapshot.records) != 3
            or set(memory_context_kinds)
            != {"message", "owner_preference", "training_plan"}
            or terminal_assistant_message_count != 0
        ):
            raise PackagingSmokeError(
                "packaging_smoke_conversation_review_terminal_invalid"
            )

        try:
            owner_export = session.get(
                f"{settings.base_url}/owner-data/export",
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_owner_export_failed") from None
        owner_export_body = _json_object(owner_export)
        export_sections = owner_export_body.get("sections")
        export_records = (
            [record for section in export_sections for record in section.get("records", [])]
            if isinstance(export_sections, list)
            and all(isinstance(section, dict) for section in export_sections)
            else []
        )
        export_kinds = tuple(
            sorted(
                str(record.get("record_kind"))
                for record in export_records
                if isinstance(record, dict) and record.get("record_kind")
            )
        )
        if (
            owner_export.status_code != 200
            or owner_export_body.get("schema_version") != "1.0"
            or owner_export_body.get("owner_id") != "packaging-smoke-owner"
            or not isinstance(export_sections, list)
            or owner_export_body.get("total_record_count") != len(export_records)
            or not {"conversation", "message", "owner_preference", "training_plan"}.issubset(set(export_kinds))
            or any(
                forbidden in repr(owner_export_body).casefold()
                for forbidden in ("puuid", "api_key", "provider_body", "tool_body", "traceback")
            )
        ):
            raise PackagingSmokeError("packaging_smoke_owner_export_invalid")

        try:
            deleted = session.post(
                f"{settings.base_url}/owner-data/deletions",
                headers={"Idempotency-Key": f"packaging-delete-{uuid4().hex}"},
                json={
                    "scope": "conversation_only",
                    "conversation_id": str(conversation_id),
                },
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_owner_delete_failed") from None
        deleted_body = _json_object(deleted)
        if (
            deleted.status_code not in (200, 202)
            or deleted_body.get("scope") != "conversation_only"
            or deleted_body.get("status") != "complete"
            or deleted_body.get("conversation_id") != str(conversation_id)
        ):
            raise PackagingSmokeError("packaging_smoke_owner_delete_failed")

        try:
            hidden_conversation = session.get(
                f"{settings.base_url}/conversations/{conversation_id}",
                timeout=settings.timeout_s,
            )
            hidden_messages = session.get(
                f"{settings.base_url}/conversations/{conversation_id}/messages",
                params={"limit": 10, "after_sequence": 0},
                timeout=settings.timeout_s,
            )
            surviving_preferences = session.get(
                f"{settings.base_url}/memory/preferences",
                params={"include_history": False, "limit": 10},
                timeout=settings.timeout_s,
            )
            surviving_plan = session.get(
                f"{settings.base_url}/memory/players/{relationship_id}/training-plan",
                params={"include_history": False, "limit": 10},
                timeout=settings.timeout_s,
            )
        except Exception:
            raise PackagingSmokeError("packaging_smoke_owner_delete_visibility_failed") from None
        surviving_preferences_body = _json_object(surviving_preferences)
        surviving_plan_body = _json_object(surviving_plan)
        if (
            hidden_conversation.status_code != 404
            or hidden_messages.status_code != 404
            or surviving_preferences.status_code != 200
            or len(surviving_preferences_body.get("records", [])) != 1
            or surviving_plan.status_code != 200
            or len(surviving_plan_body.get("plans", [])) != 1
        ):
            raise PackagingSmokeError("packaging_smoke_owner_delete_visibility_failed")

        return PackagingSmokeResult(
            schema_version="1.6",
            task_id=task_id,
            run_id=run_id,
            task_status="failed",
            link_task_id=link_task_id,
            link_status="succeeded",
            conversation_id=conversation_id,
            conversation_status="active",
            message_id=message_id,
            message_sequence_no=1,
            memory_candidate_id=memory_candidate_id,
            memory_candidate_status="accepted",
            memory_preference_version=1,
            memory_preference_value="zh-CN",
            training_candidate_id=training_candidate_id,
            training_candidate_status="accepted",
            training_plan_id=training_plan_id,
            training_plan_version=1,
            conversation_review_task_id=conversation_review_task_id,
            conversation_review_run_id=conversation_review_run_id,
            conversation_review_status="failed",
            memory_context_record_count=3,
            memory_context_kinds=memory_context_kinds,
            terminal_assistant_message_count=0,
            owner_export_schema_version="1.0",
            owner_export_record_count=len(export_records),
            owner_export_record_kinds=export_kinds,
            deletion_scope="conversation_only",
            deletion_status="complete",
            post_delete_conversation_status="not_found",
            post_delete_message_status="not_found",
            preference_survives_delete=1,
            plan_survives_delete=1,
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
                "conversation_id": str(result.conversation_id),
                "conversation_status": result.conversation_status,
                "message_id": str(result.message_id),
                "message_sequence_no": result.message_sequence_no,
                "memory_candidate_id": str(result.memory_candidate_id),
                "memory_candidate_status": result.memory_candidate_status,
                "memory_preference_version": result.memory_preference_version,
                "memory_preference_value": result.memory_preference_value,
                "training_candidate_id": str(result.training_candidate_id),
                "training_candidate_status": result.training_candidate_status,
                "training_plan_id": str(result.training_plan_id),
                "training_plan_version": result.training_plan_version,
                "conversation_review_task_id": str(
                    result.conversation_review_task_id
                ),
                "conversation_review_run_id": result.conversation_review_run_id,
                "conversation_review_status": result.conversation_review_status,
                "memory_context_record_count": result.memory_context_record_count,
                "memory_context_kinds": list(result.memory_context_kinds),
                "terminal_assistant_message_count": (
                    result.terminal_assistant_message_count
                ),
                "external_riot_provider_calls": result.external_riot_provider_calls,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
