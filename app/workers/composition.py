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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import TypeAdapter, ValidationError

from app.agent.context import ContextBuilderV1
from app.agent.memory_context import MemoryAwareContextBuilder
from app.api.composition import PostgresReadinessProbe
from app.lol.data_dragon import DataDragonService
from app.lol.player_summary import RoutedRiotPlayerSummaryBuilder
from app.lol.riot_client import RiotClient
from app.persistence.config import DatabaseSettings, load_database_settings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.task_repository import PostgresTaskRepository
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.model_runtime import (
    ModelRuntimeProfile,
    resolve_model_runtime_profile,
)
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
from app.providers.secrets import (
    InMemorySecretSource,
    SecretConfigurationError,
    SecretSource,
)
from app.providers.zhipu_profiles import (
    ZHIPU_GLM52_MODEL,
    ZHIPU_GLM53_FLASH_MODEL,
    ZHIPU_STANDARD_BASE_URL,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.composition import RuntimeCompositionRoot
from app.tasks.observability import TaskObservability
from app.tasks.models import WorkerId
from app.tasks.reliable_runtime import TaskLeasePolicy
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import (
    ExpiredReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
)
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
_SAFE_LANGUAGE = re.compile(r"^[a-z]{2}_[A-Z]{2}$")
_RIOT_ROUTING_REGIONS = ("americas", "asia", "europe", "sea")
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)
_FLASH_MIN_LEASE_SECONDS = 300
_FLASH_DEFAULT_LEASE_SECONDS = 360
_FLASH_DEFAULT_HEARTBEAT_SECONDS = 60
_PRODUCT_ZHIPU_MODELS = frozenset(
    {ZHIPU_GLM52_MODEL, ZHIPU_GLM53_FLASH_MODEL}
)


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
    zhipu: "WorkerZhipuSettings"
    provider_registry: ProviderRegistrySettings
    secret_source: SecretSource = field(repr=False)
    riot_secret_name: str
    llm_secret_name: str
    runs_root: Path
    knowledge_root: Path
    skills_root: Path
    prompt_programs_root: Path
    ddragon_cache_root: Path
    ddragon_language: str
    min_duration_seconds: int
    polling_policy: PollingPolicy
    lease_policy: TaskLeasePolicy
    runtime_profile: ModelRuntimeProfile | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class WorkerZhipuSettings:
    """Non-secret provider configuration retained in the worker plan."""

    base_url: str
    model: str
    default_timeout_s: float


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
    *,
    secret_source: SecretSource | None = None,
) -> WorkerCompositionSettings:
    """Parse every production dependency without performing external I/O."""

    if not isinstance(environment, Mapping):
        raise WorkerCompositionError("worker_configuration_invalid")
    try:
        database = load_database_settings(environment)
        raw_zhipu = load_zhipu_settings(
            {
                **environment,
                "LLM_API_KEY": environment.get("LLM_API_KEY", "secret-source-placeholder"),
            }
        )
        registry = load_provider_registry_settings(environment)
        if registry.default_provider_id != "zhipu":
            raise ValueError("only the current product baseline may be selected")
        runtime_profile = resolve_model_runtime_profile(
            "zhipu",
            raw_zhipu.model,
        )
        if raw_zhipu.model.strip().lower() not in _PRODUCT_ZHIPU_MODELS:
            raise ValueError("worker model is not an admitted product model")
        if (
            runtime_profile is not None
            and raw_zhipu.base_url.rstrip("/")
            != ZHIPU_STANDARD_BASE_URL.rstrip("/")
        ):
            raise ValueError("Flash worker requires the standard Zhipu API base URL")

        selected_secret_source = secret_source or _environment_secret_source(environment)
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
        lease_policy = TaskLeasePolicy(
            lease_seconds=_read_int(
                environment,
                "RIFTCOACH_WORKER_LEASE_SECONDS",
                default=(
                    _FLASH_DEFAULT_LEASE_SECONDS
                    if runtime_profile is not None
                    else 120
                ),
                minimum=15,
                maximum=3600,
            ),
            heartbeat_seconds=_read_int(
                environment,
                "RIFTCOACH_WORKER_HEARTBEAT_SECONDS",
                default=(
                    _FLASH_DEFAULT_HEARTBEAT_SECONDS
                    if runtime_profile is not None
                    else 30
                ),
                minimum=1,
                maximum=1200,
            ),
            recovery_batch_size=_read_int(
                environment,
                "RIFTCOACH_WORKER_RECOVERY_BATCH_SIZE",
                default=25,
                minimum=1,
                maximum=100,
            ),
            max_recoveries=_read_int(
                environment,
                "RIFTCOACH_WORKER_MAX_RECOVERIES",
                default=3,
                minimum=0,
                maximum=25,
            ),
        )
        if (
            runtime_profile is not None
            and lease_policy.lease_seconds < _FLASH_MIN_LEASE_SECONDS
        ):
            raise ValueError(
                "Flash runtime requires a lease window of at least 300 seconds"
            )
        return WorkerCompositionSettings(
            database=database,
            zhipu=WorkerZhipuSettings(
                base_url=raw_zhipu.base_url,
                model=raw_zhipu.model,
                default_timeout_s=raw_zhipu.default_timeout_s,
            ),
            provider_registry=registry,
            secret_source=selected_secret_source,
            riot_secret_name="riot-api",
            llm_secret_name="llm-api",
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
            lease_policy=lease_policy,
            runtime_profile=runtime_profile,
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

        riot_api_key = _read_secret_value(
            settings.secret_source,
            name=settings.riot_secret_name,
        )
        llm_api_key = _read_secret_value(
            settings.secret_source,
            name=settings.llm_secret_name,
        )
        riot_clients = {
            region: RiotClient(api_key=riot_api_key, region=region)
            for region in _RIOT_ROUTING_REGIONS
        }
        ddragon = DataDragonService(
            language=settings.ddragon_language,
            cache_dir=str(settings.ddragon_cache_root),
        )
        summary_builder = RoutedRiotPlayerSummaryBuilder(
            clients=riot_clients,
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
            {
                "zhipu": create_zhipu_provider(
                    ZhipuSettings(
                        api_key=llm_api_key,
                        base_url=settings.zhipu.base_url,
                        model=settings.zhipu.model,
                        default_timeout_s=settings.zhipu.default_timeout_s,
                    )
                )
            },
            settings.provider_registry,
        )
        resolved_provider = registry.resolve()
        if (
            settings.runtime_profile is not None
            and getattr(resolved_provider, "runtime_profile", None)
            != settings.runtime_profile
        ):
            raise WorkerCompositionError("worker_dependency_invalid")
        runtime = runtime_root.build_runtime(
            runs_root=settings.runs_root,
            provider=resolved_provider,
            knowledge_provider=knowledge,
            runtime_profile=settings.runtime_profile,
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
                runtime_profile=settings.runtime_profile,
            ),
            runtime=runtime,
            receipt_writer=FileRunReceiptStore(settings.runs_root),
        )
        evidence_verifier = RecentReviewTerminalEvidenceVerifier(
            settings.runs_root
        )
        executor = RecentReviewTaskExecutor(
            application_service=application,
            evidence_verifier=evidence_verifier,
        )
        worker = ReviewWorker(
            repository=repository,
            executor=executor,
            worker_id=normalized_worker_id,
            polling_policy=settings.polling_policy,
            observability=TaskObservability(logger_name="riftcoach.worker"),
            terminal_turn_writer=PostgresTerminalTurnWriter(session_factory),
            lease_policy=settings.lease_policy,
            recovery=ExpiredReviewTaskRecovery(
                repository=repository,
                verifier=evidence_verifier,
                policy=settings.lease_policy,
            ),
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


def _environment_secret_source(environment: Mapping[str, str]) -> InMemorySecretSource:
    source = InMemorySecretSource()
    try:
        source.put(
            name="riot-api",
            version="environment",
            value=_required_secret(environment, "RIOT_API_KEY"),
        )
        source.put(
            name="llm-api",
            version="environment",
            value=_required_secret(environment, "LLM_API_KEY"),
        )
    except ValueError:
        raise
    return source


def _read_secret_value(source: SecretSource, *, name: str) -> str:
    try:
        material = source.read(
            name=name,
            now=datetime.now(timezone.utc),
        )
    except SecretConfigurationError:
        raise WorkerCompositionError("worker_configuration_invalid") from None
    if not material.value or len(material.value) > 1024:
        raise WorkerCompositionError("worker_configuration_invalid")
    return material.value


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
