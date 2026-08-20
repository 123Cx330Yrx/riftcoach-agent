"""Production composition for the PostgreSQL recent-review worker process.

Configuration is parsed completely before any database/network dependency is
constructed.  The returned worker has passed PostgreSQL/Alembic readiness and
all local Runtime asset checks, so polling cannot begin with a half-composed
application.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import TypeAdapter, ValidationError

from app.agent.context import ContextBuilderV1
from app.agent.memory_context import MemoryAwareContextBuilder
from app.api.composition import PostgresReadinessProbe
from app.lol.data_dragon import DataDragonService
from app.lol.player_summary import RiotPlayerSummaryBuilder
from app.lol.riot_client import RiotClient
from app.persistence.config import DatabaseSettings, load_database_settings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.task_repository import PostgresTaskRepository
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.product.recent_review import RecentReviewRuntimeRequestCompiler
from app.product.recent_review_service import RecentReviewApplicationService
from app.product.run_receipts import FileRunReceiptStore
from app.providers.config import (
    ProviderRegistrySettings,
    ZhipuSettings,
    create_provider_registry,
    create_zhipu_provider,
    load_provider_registry_settings,
    load_zhipu_settings,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.composition import RuntimeCompositionRoot
from app.tasks.observability import TaskObservability
from app.tasks.models import WorkerId
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier
from app.workers.polling import PollingPolicy
from app.workers.review_worker import ReviewWorker


WorkerCompositionErrorCode: TypeAlias = Literal[
    "worker_configuration_invalid",
    "worker_database_not_ready",
    "worker_dependency_invalid",
]
_ERROR_CODES = frozenset(
    {
        "worker_configuration_invalid",
        "worker_database_not_ready",
        "worker_dependency_invalid",
    }
)
_SAFE_REGION = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
_SAFE_LANGUAGE = re.compile(r"^[a-z]{2}_[A-Z]{2}$")
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)


class WorkerCompositionError(RuntimeError):
    """Allowlisted, body-free worker startup failure."""

    def __init__(self, code: WorkerCompositionErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported worker composition error")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class WorkerCompositionSettings:
    database: DatabaseSettings = field(repr=False)
    zhipu: ZhipuSettings = field(repr=False)
    provider_registry: ProviderRegistrySettings
    riot_api_key: str = field(repr=False)
    riot_region: str
    runs_root: Path
    knowledge_root: Path
    skills_root: Path
    prompt_programs_root: Path
    ddragon_cache_root: Path
    ddragon_language: str
    min_duration_seconds: int
    polling_policy: PollingPolicy


@dataclass(slots=True)
class ReviewWorkerProcess:
    """Own one composed Worker and its process-level SQLAlchemy Engine."""

    worker: ReviewWorker
    _engine: Any = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._engine.dispose()

    def __enter__(self) -> "ReviewWorkerProcess":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def load_worker_composition_settings(
    environment: Mapping[str, str],
) -> WorkerCompositionSettings:
    """Parse every production dependency without performing external I/O."""

    if not isinstance(environment, Mapping):
        raise WorkerCompositionError("worker_configuration_invalid")
    try:
        database = load_database_settings(environment)
        zhipu = load_zhipu_settings(environment)
        registry = load_provider_registry_settings(environment)
        if registry.default_provider_id != "zhipu":
            raise ValueError("only the current product baseline may be selected")

        riot_api_key = _required_secret(environment, "RIOT_API_KEY")
        riot_region = environment.get("RIOT_REGION", "asia").strip().lower()
        if not _SAFE_REGION.fullmatch(riot_region):
            raise ValueError("RIOT_REGION is invalid")

        language = environment.get("RIFTCOACH_DDRAGON_LANGUAGE", "zh_CN").strip()
        if not _SAFE_LANGUAGE.fullmatch(language):
            raise ValueError("RIFTCOACH_DDRAGON_LANGUAGE is invalid")

        min_duration = _read_int(
            environment,
            "RIFTCOACH_MIN_GAME_DURATION_SECONDS",
            default=300,
            minimum=0,
            maximum=3600,
        )
        polling_policy = PollingPolicy(
            initial_delay_s=_read_float(
                environment,
                "RIFTCOACH_WORKER_INITIAL_DELAY_SECONDS",
                default=0.1,
            ),
            maximum_delay_s=_read_float(
                environment,
                "RIFTCOACH_WORKER_MAXIMUM_DELAY_SECONDS",
                default=2.0,
            ),
            multiplier=_read_float(
                environment,
                "RIFTCOACH_WORKER_BACKOFF_MULTIPLIER",
                default=2.0,
            ),
            jitter_ratio=_read_float(
                environment,
                "RIFTCOACH_WORKER_JITTER_RATIO",
                default=0.2,
                allow_zero=True,
            ),
        )
        return WorkerCompositionSettings(
            database=database,
            zhipu=zhipu,
            provider_registry=registry,
            riot_api_key=riot_api_key,
            riot_region=riot_region,
            runs_root=_read_path(
                environment,
                "RIFTCOACH_RUNS_ROOT",
                default="data/runs",
            ),
            knowledge_root=_read_path(
                environment,
                "RIFTCOACH_KNOWLEDGE_ROOT",
                default="data/rag_docs",
            ),
            skills_root=_read_path(
                environment,
                "RIFTCOACH_SKILLS_ROOT",
                default="skills",
            ),
            prompt_programs_root=_read_path(
                environment,
                "RIFTCOACH_PROMPT_PROGRAMS_ROOT",
                default="prompt_programs",
            ),
            ddragon_cache_root=_read_path(
                environment,
                "RIFTCOACH_DDRAGON_CACHE_ROOT",
                default="data/static/ddragon",
            ),
            ddragon_language=language,
            min_duration_seconds=min_duration,
            polling_policy=polling_policy,
        )
    except WorkerCompositionError:
        raise
    except Exception:
        raise WorkerCompositionError("worker_configuration_invalid") from None


def build_review_worker_process(
    settings: WorkerCompositionSettings,
    *,
    worker_id: str,
) -> ReviewWorkerProcess:
    """Build and preflight all dependencies before returning a polling worker."""

    if not isinstance(settings, WorkerCompositionSettings):
        raise TypeError("settings must be WorkerCompositionSettings")
    try:
        normalized_worker_id = _WORKER_ID_ADAPTER.validate_python(
            worker_id,
            strict=True,
        )
    except (TypeError, ValueError, ValidationError):
        raise WorkerCompositionError("worker_configuration_invalid") from None

    engine: Any | None = None
    try:
        _require_directory(settings.knowledge_root)
        _require_directory(settings.skills_root)
        _require_directory(settings.prompt_programs_root)
        settings.runs_root.mkdir(parents=True, exist_ok=True)
        settings.ddragon_cache_root.mkdir(parents=True, exist_ok=True)

        engine = build_engine(settings.database)
        readiness = PostgresReadinessProbe(engine).check()
        if not readiness.is_ready:
            raise WorkerCompositionError("worker_database_not_ready")

        session_factory = build_session_factory(engine)
        repository = PostgresTaskRepository(session_factory)

        riot_client = RiotClient(
            api_key=settings.riot_api_key,
            region=settings.riot_region,
        )
        ddragon = DataDragonService(
            language=settings.ddragon_language,
            cache_dir=str(settings.ddragon_cache_root),
        )
        summary_builder = RiotPlayerSummaryBuilder(
            client=riot_client,
            ddragon=ddragon,
            min_duration_seconds=settings.min_duration_seconds,
        )

        knowledge = LocalHybridKnowledgeProvider.from_directory(
            settings.knowledge_root
        )
        runtime_root = RuntimeCompositionRoot.from_directories(
            skills_root=settings.skills_root,
            prompt_programs_root=settings.prompt_programs_root,
        )
        registry = create_provider_registry(
            {"zhipu": create_zhipu_provider(settings.zhipu)},
            settings.provider_registry,
        )
        runtime = runtime_root.build_runtime(
            runs_root=settings.runs_root,
            provider=registry.resolve(),
            knowledge_provider=knowledge,
            context_builder=MemoryAwareContextBuilder(
                delegate=ContextBuilderV1(),
                repository=PostgresMemoryContextRepository(session_factory),
                manifest_store=FileMemoryContextManifestStore(
                    settings.runs_root
                ),
            ),
        )
        application = RecentReviewApplicationService(
            summary_builder=summary_builder,
            compiler=RecentReviewRuntimeRequestCompiler(
                runtime_root.skill_catalog,
            ),
            runtime=runtime,
            receipt_writer=FileRunReceiptStore(settings.runs_root),
        )
        executor = RecentReviewTaskExecutor(
            application_service=application,
            evidence_verifier=RecentReviewTerminalEvidenceVerifier(
                settings.runs_root
            ),
        )
        worker = ReviewWorker(
            repository=repository,
            executor=executor,
            worker_id=normalized_worker_id,
            polling_policy=settings.polling_policy,
            observability=TaskObservability(logger_name="riftcoach.worker"),
            terminal_turn_writer=PostgresTerminalTurnWriter(session_factory),
        )
        return ReviewWorkerProcess(worker=worker, _engine=engine)
    except WorkerCompositionError:
        if engine is not None:
            engine.dispose()
        raise
    except Exception:
        if engine is not None:
            engine.dispose()
        raise WorkerCompositionError("worker_dependency_invalid") from None


def _required_secret(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "")
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError(f"{name} is required")
    return value.strip()


def _read_path(
    environment: Mapping[str, str],
    name: str,
    *,
    default: str,
) -> Path:
    raw = environment.get(name, default)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{name} must not be blank")
    return Path(raw).expanduser().resolve()


def _read_int(
    environment: Mapping[str, str],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = environment.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside its allowed range")
    return value


def _read_float(
    environment: Mapping[str, str],
    name: str,
    *,
    default: float,
    allow_zero: bool = False,
) -> float:
    raw = environment.get(name, str(default))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name} must be a valid non-negative number")
    return value


def _require_directory(path: Path) -> None:
    if not path.is_dir():
        raise WorkerCompositionError("worker_dependency_invalid")


__all__ = [
    "ReviewWorkerProcess",
    "WorkerCompositionError",
    "WorkerCompositionErrorCode",
    "WorkerCompositionSettings",
    "build_review_worker_process",
    "load_worker_composition_settings",
]
