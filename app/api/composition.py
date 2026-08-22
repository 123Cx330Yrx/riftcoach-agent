"""Deployment composition and process lifecycle for the asynchronous API.

Importing this module and generating OpenAPI are deliberately side-effect
free. Environment parsing and process-level Engine/Session construction happen
only inside the FastAPI lifespan.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI

from app.api.actor import (
    ActorContext,
    ActorContextProvider,
    ActorProfile,
    StaticActorContextProvider,
    UnavailableActorContextProvider,
)
from app.api.main import (
    OwnerDataLifecyclePort,
    PlayerLinkServicePort,
    ReadinessPort,
    RunQueryPort,
    TaskDeletionPort,
    TaskServicePort,
    create_app,
)
from app.api.task_models import ReadinessCode, ReadinessResult
from app.conversations.models import (
    AppendUserMessageCommand,
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageView,
    ConversationView,
    CreateConversationCommand,
)
from app.conversations.ports import ConversationServicePort
from app.conversations.service import (
    ConversationService,
    ConversationServiceError,
)
from app.memory.models import CreateMemoryCandidateCommand, MemoryCandidateView
from app.memory.composition import build_typed_memory_materializers
from app.memory.ports import MemoryCandidateServicePort
from app.memory.service import MemoryCandidateService, MemoryCandidateServiceError
from app.memory.typed_models import TypedMemoryPage
from app.memory.typed_ports import TypedMemoryQueryServicePort
from app.memory.typed_service import TypedMemoryQueryService, TypedMemoryQueryServiceError
from app.memory.training_models import TrainingPlanPage, TrainingProgressPage
from app.memory.training_query_ports import TrainingQueryServicePort
from app.memory.training_service import TrainingQueryService, TrainingQueryServiceError
from app.lifecycle.models import OwnerDataDeleteCommand, OwnerDataDeletionMarker, OwnerDataExport
from app.lifecycle.service import (
    NoopOwnerDataCleaner,
    OwnerDataLifecycleError,
    OwnerDataLifecycleService,
)
from app.persistence.config import load_database_settings
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.typed_memory_query_repository import PostgresTypedMemoryQueryRepository
from app.persistence.training_query_repository import PostgresTrainingQueryRepository
from app.persistence.owner_data_lifecycle_repository import PostgresOwnerDataLifecycleRepository
from app.persistence.database import build_engine, build_session_factory
from app.persistence.player_repository import PostgresPlayerRepository
from app.persistence.task_repository import PostgresTaskRepository
from app.players.models import (
    CreatePlayerLinkCommand,
    PlayerLinkCapacityPolicy,
    PlayerLinkCreateResult,
    PlayerLinkTaskView,
)
from app.players.service import PlayerLinkService, PlayerLinkServiceError
from app.product.run_query import RunQueryError, RunQueryService, RunView
from app.tasks.models import (
    CreateConversationReviewTaskCommand,
    CreateReviewTaskCommand,
    ReviewTaskView,
    TaskCapacityPolicy,
    TaskCreateResult,
)
from app.tasks.service import ReviewTaskService, TaskServiceError
from app.tasks.reliable_runtime import TaskCancelResult, TaskEventPage
from app.tasks.deletion import (
    FileRunDataCleaner,
    TaskDeletionError,
    TaskDeletionService,
)
from app.tasks.observability import TaskObservability


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RevisionReader = Callable[[Any], tuple[str | None, str | None]]


@dataclass(frozen=True)
class ApiCompositionSettings:
    profile: ActorProfile
    runs_root: Path
    local_owner_id: str | None = field(repr=False)
    cors_origins: tuple[str, ...] = ()
    cors_allow_credentials: bool = False
    task_capacity: TaskCapacityPolicy = field(
        default_factory=TaskCapacityPolicy,
        repr=False,
    )
    player_link_capacity: PlayerLinkCapacityPolicy = field(
        default_factory=PlayerLinkCapacityPolicy,
        repr=False,
    )


def load_api_composition_settings(
    environment: Mapping[str, str],
) -> ApiCompositionSettings:
    raw_profile = environment.get("RIFTCOACH_API_PROFILE", "production")
    profile = raw_profile.strip().lower()
    if profile not in {"local", "test", "production"}:
        raise ValueError("RIFTCOACH_API_PROFILE must be local, test or production")

    raw_runs_root = environment.get("RIFTCOACH_RUNS_ROOT", "data/runs")
    if not isinstance(raw_runs_root, str) or not raw_runs_root.strip():
        raise ValueError("RIFTCOACH_RUNS_ROOT must not be blank")
    runs_root = Path(raw_runs_root).expanduser().resolve()

    local_owner_id = environment.get("RIFTCOACH_LOCAL_OWNER_ID")
    if profile in {"local", "test"}:
        if not isinstance(local_owner_id, str) or not local_owner_id.strip():
            raise ValueError(
                "RIFTCOACH_LOCAL_OWNER_ID is required in local/test profiles"
            )
        local_owner_id = local_owner_id.strip()
    else:
        local_owner_id = None

    raw_origins = environment.get("RIFTCOACH_CORS_ORIGINS", "")
    if not isinstance(raw_origins, str):
        raise ValueError("RIFTCOACH_CORS_ORIGINS must be a string")
    cors_origins = tuple(
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    )
    raw_credentials = environment.get(
        "RIFTCOACH_CORS_ALLOW_CREDENTIALS",
        "false",
    )
    if not isinstance(raw_credentials, str) or raw_credentials.strip().lower() not in {
        "true",
        "false",
    }:
        raise ValueError(
            "RIFTCOACH_CORS_ALLOW_CREDENTIALS must be true or false"
        )
    cors_allow_credentials = raw_credentials.strip().lower() == "true"
    if profile == "production" and "*" in cors_origins and cors_allow_credentials:
        raise ValueError(
            "production wildcard CORS origins cannot use credentials"
        )

    task_capacity = TaskCapacityPolicy(
        owner_active_limit=_read_positive_int(
            environment,
            "RIFTCOACH_TASK_OWNER_ACTIVE_LIMIT",
            default=3,
        ),
        global_active_limit=_read_positive_int(
            environment,
            "RIFTCOACH_TASK_GLOBAL_ACTIVE_LIMIT",
            default=50,
        ),
    )
    player_link_capacity = PlayerLinkCapacityPolicy(
        owner_active_limit=_read_positive_int(
            environment,
            "RIFTCOACH_PLAYER_LINK_OWNER_ACTIVE_LIMIT",
            default=3,
        ),
        global_active_limit=_read_positive_int(
            environment,
            "RIFTCOACH_PLAYER_LINK_GLOBAL_ACTIVE_LIMIT",
            default=50,
        ),
    )

    return ApiCompositionSettings(
        profile=profile,  # type: ignore[arg-type]
        runs_root=runs_root,
        local_owner_id=local_owner_id,
        cors_origins=cors_origins,
        cors_allow_credentials=cors_allow_credentials,
        task_capacity=task_capacity,
        player_link_capacity=player_link_capacity,
    )


def _read_positive_int(
    environment: Mapping[str, str],
    name: str,
    *,
    default: int,
) -> int:
    raw = environment.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


class PostgresReadinessProbe:
    """Check process connectivity and exact Alembic migration identity."""

    def __init__(
        self,
        engine: Any,
        *,
        revision_reader: RevisionReader | None = None,
    ) -> None:
        if not callable(getattr(engine, "connect", None)):
            raise TypeError("engine must expose connect()")
        if revision_reader is not None and not callable(revision_reader):
            raise TypeError("revision_reader must be callable")
        self._engine = engine
        self._revision_reader = revision_reader or _read_revisions

    def check(self) -> ReadinessResult:
        try:
            with self._engine.connect() as connection:
                result = connection.execute(sa.text("SELECT 1"))
                if result.scalar_one() != 1:
                    return ReadinessResult.not_ready("database_unavailable")
                try:
                    current, head = self._revision_reader(connection)
                except Exception:
                    return ReadinessResult.not_ready("readiness_check_failed")
        except Exception:
            return ReadinessResult.not_ready("database_unavailable")

        if current is None or head is None or current != head:
            return ReadinessResult.not_ready("migration_not_current")
        return ReadinessResult.ready()


class _FixedReadinessProbe:
    def __init__(self, result: ReadinessResult) -> None:
        self._result = result

    def check(self) -> ReadinessResult:
        return self._result


class _TaskServiceProxy:
    def __init__(self) -> None:
        self._target: TaskServicePort | None = None

    def bind(self, target: TaskServicePort | None) -> None:
        self._target = target

    def _service(self) -> TaskServicePort:
        if self._target is None:
            raise TaskServiceError("task_persistence_failed")
        return self._target

    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult:
        return self._service().create(command)

    def create_conversation_review(
        self,
        command: CreateConversationReviewTaskCommand,
    ) -> TaskCreateResult:
        return self._service().create_conversation_review(command)

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        return self._service().get_task(owner_id=owner_id, task_id=task_id)

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        return self._service().get_task_by_run_id(
            owner_id=owner_id,
            run_id=run_id,
        )

    def request_cancel(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        request_id: str,
    ) -> TaskCancelResult:
        return self._service().request_cancel(
            owner_id=owner_id,
            task_id=task_id,
            request_id=request_id,
        )

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int = 0,
        limit: int = 50,
    ) -> TaskEventPage:
        return self._service().read_events(
            owner_id=owner_id,
            task_id=task_id,
            after_cursor=after_cursor,
            limit=limit,
        )


class _RunQueryProxy:
    def __init__(self) -> None:
        self._target: RunQueryPort | None = None

    def bind(self, target: RunQueryPort | None) -> None:
        self._target = target

    def _query(self) -> RunQueryPort:
        if self._target is None:
            raise RunQueryError("run_not_found")
        return self._target

    def get_run(self, run_id: str) -> RunView:
        return self._query().get_run(run_id)

    def get_report(self, run_id: str) -> str:
        return self._query().get_report(run_id)


class _PlayerLinkServiceProxy:
    def __init__(self) -> None:
        self._target: PlayerLinkServicePort | None = None

    def bind(self, target: PlayerLinkServicePort | None) -> None:
        self._target = target

    def _service(self) -> PlayerLinkServicePort:
        if self._target is None:
            raise PlayerLinkServiceError("link_persistence_failed")
        return self._target

    def create(self, command: CreatePlayerLinkCommand) -> PlayerLinkCreateResult:
        return self._service().create(command)

    def get_link(
        self,
        *,
        owner_id: str,
        link_task_id: UUID,
    ) -> PlayerLinkTaskView:
        return self._service().get_link(
            owner_id=owner_id,
            link_task_id=link_task_id,
        )


class _ConversationServiceProxy:
    def __init__(self) -> None:
        self._target: ConversationServicePort | None = None

    def bind(self, target: ConversationServicePort | None) -> None:
        self._target = target

    def _service(self) -> ConversationServicePort:
        if self._target is None:
            raise ConversationServiceError("service_unavailable")
        return self._target

    def create(self, command: CreateConversationCommand) -> ConversationCreateResult:
        return self._service().create(command)

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        return self._service().get_conversation(
            owner_id=owner_id,
            conversation_id=conversation_id,
        )

    def append_user_message(
        self,
        command: AppendUserMessageCommand,
    ) -> ConversationMessageView:
        return self._service().append_user_message(command)

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        limit: int = 50,
        after_sequence: int = 0,
    ) -> ConversationMessagePage:
        return self._service().list_messages(
            owner_id=owner_id,
            conversation_id=conversation_id,
            limit=limit,
            after_sequence=after_sequence,
        )

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        return self._service().archive_conversation(
            owner_id=owner_id,
            conversation_id=conversation_id,
        )

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        return self._service().hide_conversation(
            owner_id=owner_id,
            conversation_id=conversation_id,
        )


class _MemoryCandidateServiceProxy:
    def __init__(self) -> None:
        self._target: MemoryCandidateServicePort | None = None

    def bind(self, target: MemoryCandidateServicePort | None) -> None:
        self._target = target

    def _service(self) -> MemoryCandidateServicePort:
        if self._target is None:
            raise MemoryCandidateServiceError("service_unavailable")
        return self._target

    def create(self, command: CreateMemoryCandidateCommand) -> MemoryCandidateView:
        return self._service().create(command)

    def get(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidateView:
        return self._service().get(owner_id=owner_id, candidate_id=candidate_id)

    def reject(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
    ) -> MemoryCandidateView:
        return self._service().reject(
            owner_id=owner_id,
            candidate_id=candidate_id,
            actor_id=actor_id,
        )

    def accept(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
    ) -> MemoryCandidateView:
        return self._service().accept(
            owner_id=owner_id,
            candidate_id=candidate_id,
            actor_id=actor_id,
        )


class _TypedMemoryQueryServiceProxy:
    def __init__(self) -> None:
        self._target: TypedMemoryQueryServicePort | None = None

    def bind(self, target: TypedMemoryQueryServicePort | None) -> None:
        self._target = target

    def _service(self) -> TypedMemoryQueryServicePort:
        if self._target is None:
            raise TypedMemoryQueryServiceError("service_unavailable")
        return self._target

    def preferences(
        self,
        *,
        owner_id: str,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        return self._service().preferences(
            owner_id=owner_id,
            include_history=include_history,
            limit=limit,
        )

    def profile(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        return self._service().profile(
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )

    def reviews(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        return self._service().reviews(
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )


class _TrainingQueryServiceProxy:
    def __init__(self) -> None:
        self._target: TrainingQueryServicePort | None = None

    def bind(self, target: TrainingQueryServicePort | None) -> None:
        self._target = target

    def _service(self) -> TrainingQueryServicePort:
        if self._target is None:
            raise TrainingQueryServiceError("service_unavailable")
        return self._target

    def plans(self, **kwargs) -> TrainingPlanPage:
        return self._service().plans(**kwargs)

    def progress(self, **kwargs) -> TrainingProgressPage:
        return self._service().progress(**kwargs)


class _OwnerDataLifecycleServiceProxy:
    def __init__(self) -> None:
        self._target: OwnerDataLifecyclePort | None = None

    def bind(self, target: OwnerDataLifecyclePort | None) -> None:
        self._target = target

    def _service(self) -> OwnerDataLifecyclePort:
        if self._target is None:
            raise OwnerDataLifecycleError("lifecycle_unavailable")
        return self._target

    def export(self, *, owner_id: str) -> OwnerDataExport:
        return self._service().export(owner_id=owner_id)

    def delete(self, command: OwnerDataDeleteCommand) -> OwnerDataDeletionMarker:
        return self._service().delete(command)

    def retry(self, *, owner_id: str, marker_id: UUID) -> OwnerDataDeletionMarker:
        return self._service().retry(owner_id=owner_id, marker_id=marker_id)


class _TaskDeletionProxy:
    def __init__(self) -> None:
        self._target: TaskDeletionPort | None = None

    def bind(self, target: TaskDeletionPort | None) -> None:
        self._target = target

    def delete(self, *, owner_id: str, task_id: UUID):
        if self._target is None:
            raise TaskDeletionError("task_persistence_failed")
        return self._target.delete(owner_id=owner_id, task_id=task_id)


class _ActorProviderProxy:
    def __init__(self) -> None:
        self._target: ActorContextProvider = UnavailableActorContextProvider()

    def bind(self, target: ActorContextProvider | None) -> None:
        self._target = target or UnavailableActorContextProvider()

    def __call__(self) -> ActorContext:
        return self._target()


class _ReadinessProxy:
    def __init__(self) -> None:
        self._target: ReadinessPort = _FixedReadinessProbe(
            ReadinessResult.not_ready("service_configuration_invalid")
        )

    def bind(self, target: ReadinessPort | None) -> None:
        self._target = target or _FixedReadinessProbe(
            ReadinessResult.not_ready("service_configuration_invalid")
        )

    def check(self) -> ReadinessResult:
        return self._target.check()


def _read_revisions(connection: Any) -> tuple[str | None, str | None]:
    current_heads = MigrationContext.configure(connection).get_current_heads()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    script_heads = ScriptDirectory.from_config(config).get_heads()
    current = current_heads[0] if len(current_heads) == 1 else None
    head = script_heads[0] if len(script_heads) == 1 else None
    return current, head


def create_composed_app(
    *,
    environment: Mapping[str, str] | None = None,
    actor_provider: ActorContextProvider | None = None,
) -> FastAPI:
    """Create a side-effect-free app whose resources are bound in lifespan."""

    if actor_provider is not None and not callable(actor_provider):
        raise TypeError("actor_provider must be callable")

    source = os.environ if environment is None else environment
    # Configuration parsing has no network/database side effects and is needed
    # to install the static CORS policy before the app can serve a request.
    api_settings = load_api_composition_settings(source)
    task_proxy = _TaskServiceProxy()
    player_link_proxy = _PlayerLinkServiceProxy()
    conversation_proxy = _ConversationServiceProxy()
    memory_candidate_proxy = _MemoryCandidateServiceProxy()
    typed_memory_query_proxy = _TypedMemoryQueryServiceProxy()
    training_query_proxy = _TrainingQueryServiceProxy()
    owner_data_lifecycle_proxy = _OwnerDataLifecycleServiceProxy()
    query_proxy = _RunQueryProxy()
    deletion_proxy = _TaskDeletionProxy()
    actor_proxy = _ActorProviderProxy()
    readiness_proxy = _ReadinessProxy()
    observability = TaskObservability(logger_name="riftcoach.api")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine: Any | None = None
        app.state.database_engine = None
        try:
            database_settings = load_database_settings(source)
            engine = build_engine(database_settings)
            session_factory = build_session_factory(engine)
            repository = PostgresTaskRepository(session_factory)
            player_repository = PostgresPlayerRepository(session_factory)
            conversation_repository = PostgresConversationRepository(
                session_factory
            )
            memory_candidate_repository = PostgresMemoryCandidateRepository(
                session_factory
            )
            typed_memory_query_repository = PostgresTypedMemoryQueryRepository(
                session_factory
            )
            training_query_repository = PostgresTrainingQueryRepository(
                session_factory
            )
            owner_data_lifecycle_repository = PostgresOwnerDataLifecycleRepository(
                session_factory
            )
            task_proxy.bind(
                ReviewTaskService(
                    repository=repository,
                    capacity=api_settings.task_capacity,
                )
            )
            player_link_proxy.bind(
                PlayerLinkService(
                    repository=player_repository,
                    capacity=api_settings.player_link_capacity,
                )
            )
            conversation_proxy.bind(
                ConversationService(repository=conversation_repository)
            )
            memory_candidate_proxy.bind(
                MemoryCandidateService(
                    repository=memory_candidate_repository,
                    materializers=build_typed_memory_materializers(),
                )
            )
            typed_memory_query_proxy.bind(
                TypedMemoryQueryService(repository=typed_memory_query_repository)
            )
            training_query_proxy.bind(
                TrainingQueryService(repository=training_query_repository)
            )
            owner_data_lifecycle_proxy.bind(
                OwnerDataLifecycleService(
                    repository=owner_data_lifecycle_repository,
                    cleaner=NoopOwnerDataCleaner(),
                )
            )
            deletion_proxy.bind(TaskDeletionService(
                repository=repository,
                cleaner=FileRunDataCleaner(
                    api_settings.runs_root,
                    clock=lambda: datetime.now(timezone.utc),
                ),
            ))
            query_proxy.bind(RunQueryService(api_settings.runs_root))

            selected_actor = actor_provider
            if selected_actor is None and api_settings.profile in {"local", "test"}:
                assert api_settings.local_owner_id is not None
                selected_actor = StaticActorContextProvider(
                    owner_id=api_settings.local_owner_id,
                    profile=api_settings.profile,
                )
            actor_proxy.bind(selected_actor)
            if selected_actor is None:
                readiness_proxy.bind(
                    _FixedReadinessProbe(
                        ReadinessResult.not_ready("actor_context_unavailable")
                    )
                )
            else:
                readiness_proxy.bind(PostgresReadinessProbe(engine))
            app.state.database_engine = engine
        except Exception:
            # Keep liveness available while every product operation fails closed.
            readiness_proxy.bind(
                _FixedReadinessProbe(
                    ReadinessResult.not_ready("service_configuration_invalid")
                )
            )
            actor_proxy.bind(None)
            task_proxy.bind(None)
            player_link_proxy.bind(None)
            conversation_proxy.bind(None)
            memory_candidate_proxy.bind(None)
            typed_memory_query_proxy.bind(None)
            training_query_proxy.bind(None)
            owner_data_lifecycle_proxy.bind(None)
            query_proxy.bind(None)
            deletion_proxy.bind(None)
        try:
            yield
        finally:
            task_proxy.bind(None)
            player_link_proxy.bind(None)
            conversation_proxy.bind(None)
            memory_candidate_proxy.bind(None)
            typed_memory_query_proxy.bind(None)
            training_query_proxy.bind(None)
            owner_data_lifecycle_proxy.bind(None)
            query_proxy.bind(None)
            deletion_proxy.bind(None)
            actor_proxy.bind(None)
            readiness_proxy.bind(None)
            if engine is not None:
                engine.dispose()
            app.state.database_engine = None

    app = create_app(
        task_service=task_proxy,
        player_link_service=player_link_proxy,
        query_service=query_proxy,
        actor_provider=actor_proxy,
        readiness_probe=readiness_proxy,
        lifespan=lifespan,
        deletion_service=deletion_proxy,
        cors_origins=api_settings.cors_origins,
        cors_allow_credentials=api_settings.cors_allow_credentials,
        observability=observability,
        conversation_service=conversation_proxy,
        memory_candidate_service=memory_candidate_proxy,
        typed_memory_query_service=typed_memory_query_proxy,
        training_query_service=training_query_proxy,
        owner_data_lifecycle_service=owner_data_lifecycle_proxy,
    )
    app.state.database_engine = None
    return app


__all__ = [
    "ApiCompositionSettings",
    "PostgresReadinessProbe",
    "create_composed_app",
    "load_api_composition_settings",
]
