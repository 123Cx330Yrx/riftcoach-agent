"""Production composition for the dedicated PostgreSQL player-link worker."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from pydantic import TypeAdapter, ValidationError

from app.api.composition import PostgresReadinessProbe
from app.lol.account_resolver import RiotAccountResolver
from app.lol.riot_client import RiotClient
from app.persistence.config import DatabaseSettings, load_database_settings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.player_repository import PostgresPlayerRepository
from app.players.link_worker import PlayerLinkWorker
from app.players.models import RoutingRegion, WorkerId
from app.tasks.observability import TaskObservability
from app.workers.polling import PollingPolicy


PlayerLinkWorkerCompositionErrorCode: TypeAlias = Literal[
    "player_link_worker_configuration_invalid",
    "player_link_worker_database_not_ready",
    "player_link_worker_dependency_invalid",
]
_ERROR_CODES = frozenset(
    {
        "player_link_worker_configuration_invalid",
        "player_link_worker_database_not_ready",
        "player_link_worker_dependency_invalid",
    }
)
_DEFAULT_ROUTING_POLICY = tuple(RoutingRegion)
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)


class PlayerLinkWorkerCompositionError(RuntimeError):
    """Allowlisted, body-free player-link process startup failure."""

    def __init__(self, code: PlayerLinkWorkerCompositionErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported player-link worker composition error")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PlayerLinkWorkerSettings:
    database: DatabaseSettings = field(repr=False)
    riot_api_key: str = field(repr=False)
    allowed_routing_regions: tuple[RoutingRegion, ...]
    account_timeout_s: float
    polling_policy: PollingPolicy


@dataclass(slots=True)
class PlayerLinkWorkerProcess:
    worker: PlayerLinkWorker
    _engine: Any = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._engine.dispose()

    def __enter__(self) -> PlayerLinkWorkerProcess:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def load_player_link_worker_settings(
    environment: Mapping[str, str],
) -> PlayerLinkWorkerSettings:
    if not isinstance(environment, Mapping):
        raise PlayerLinkWorkerCompositionError(
            "player_link_worker_configuration_invalid"
        )
    try:
        database = load_database_settings(environment)
        riot_api_key = _required_secret(environment, "RIOT_API_KEY")
        allowed_routing_regions = _read_routing_policy(environment)
        account_timeout_s = _read_float(
            environment,
            "RIFTCOACH_RIOT_ACCOUNT_TIMEOUT_SECONDS",
            default=15.0,
            minimum=0.001,
            maximum=30.0,
        )
        polling_policy = PollingPolicy(
            initial_delay_s=_read_float(
                environment,
                "RIFTCOACH_PLAYER_LINK_WORKER_INITIAL_DELAY_SECONDS",
                default=0.1,
                minimum=0.001,
                maximum=300.0,
            ),
            maximum_delay_s=_read_float(
                environment,
                "RIFTCOACH_PLAYER_LINK_WORKER_MAXIMUM_DELAY_SECONDS",
                default=2.0,
                minimum=0.001,
                maximum=300.0,
            ),
            multiplier=_read_float(
                environment,
                "RIFTCOACH_PLAYER_LINK_WORKER_BACKOFF_MULTIPLIER",
                default=2.0,
                minimum=1.0,
                maximum=100.0,
            ),
            jitter_ratio=_read_float(
                environment,
                "RIFTCOACH_PLAYER_LINK_WORKER_JITTER_RATIO",
                default=0.2,
                minimum=0.0,
                maximum=0.999999,
            ),
        )
        return PlayerLinkWorkerSettings(
            database=database,
            riot_api_key=riot_api_key,
            allowed_routing_regions=allowed_routing_regions,
            account_timeout_s=account_timeout_s,
            polling_policy=polling_policy,
        )
    except PlayerLinkWorkerCompositionError:
        raise
    except Exception:
        raise PlayerLinkWorkerCompositionError(
            "player_link_worker_configuration_invalid"
        ) from None


def build_player_link_worker_process(
    settings: PlayerLinkWorkerSettings,
    *,
    worker_id: str,
) -> PlayerLinkWorkerProcess:
    if not isinstance(settings, PlayerLinkWorkerSettings):
        raise TypeError("settings must be PlayerLinkWorkerSettings")
    try:
        normalized_worker_id = _WORKER_ID_ADAPTER.validate_python(
            worker_id,
            strict=True,
        )
    except (TypeError, ValueError, ValidationError):
        raise PlayerLinkWorkerCompositionError(
            "player_link_worker_configuration_invalid"
        ) from None

    engine: Any | None = None
    try:
        engine = build_engine(settings.database)
        readiness = PostgresReadinessProbe(engine).check()
        if not readiness.is_ready:
            raise PlayerLinkWorkerCompositionError(
                "player_link_worker_database_not_ready"
            )

        session_factory = build_session_factory(engine)
        repository = PostgresPlayerRepository(session_factory)
        allowed_regions = frozenset(settings.allowed_routing_regions)

        def client_factory(routing_region: str) -> RiotClient:
            try:
                region = RoutingRegion(routing_region)
            except (TypeError, ValueError):
                raise RuntimeError("routing policy rejected") from None
            if region not in allowed_regions:
                raise RuntimeError("routing policy rejected")
            return RiotClient(
                api_key=settings.riot_api_key,
                region=region.value,
            )

        resolver = RiotAccountResolver(
            client_factory=client_factory,
            timeout_s=settings.account_timeout_s,
        )
        worker = PlayerLinkWorker(
            repository=repository,
            resolver=resolver,
            worker_id=normalized_worker_id,
            polling_policy=settings.polling_policy,
            observability=TaskObservability(
                logger_name="riftcoach.player_link_worker"
            ),
        )
        return PlayerLinkWorkerProcess(worker=worker, _engine=engine)
    except PlayerLinkWorkerCompositionError:
        if engine is not None:
            engine.dispose()
        raise
    except Exception:
        if engine is not None:
            engine.dispose()
        raise PlayerLinkWorkerCompositionError(
            "player_link_worker_dependency_invalid"
        ) from None


def _required_secret(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "")
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError(f"{name} is required")
    return value.strip()


def _read_routing_policy(
    environment: Mapping[str, str],
) -> tuple[RoutingRegion, ...]:
    raw = environment.get(
        "RIFTCOACH_RIOT_ALLOWED_ROUTING_REGIONS",
        ",".join(region.value for region in _DEFAULT_ROUTING_POLICY),
    )
    if not isinstance(raw, str) or not raw:
        raise ValueError("routing policy must not be blank")
    values = raw.split(",")
    if any(not value or value != value.strip() or value != value.lower() for value in values):
        raise ValueError("routing policy must use canonical values")
    regions = tuple(RoutingRegion(value) for value in values)
    if not regions or len(set(regions)) != len(regions):
        raise ValueError("routing policy must contain unique values")
    if frozenset(regions) != frozenset(_DEFAULT_ROUTING_POLICY):
        raise ValueError("routing policy must cover every API routing region")
    return regions


def _read_float(
    environment: Mapping[str, str],
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = environment.get(name, str(default))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside its allowed range")
    return value


__all__ = [
    "PlayerLinkWorkerCompositionError",
    "PlayerLinkWorkerCompositionErrorCode",
    "PlayerLinkWorkerProcess",
    "PlayerLinkWorkerSettings",
    "build_player_link_worker_process",
    "load_player_link_worker_settings",
]
