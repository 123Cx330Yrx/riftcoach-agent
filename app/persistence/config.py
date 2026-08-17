from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseConfigurationError(ValueError):
    """A safe, public-detail-free database configuration failure."""


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = field(repr=False)
    pool_size: int = 5
    pool_timeout_s: int = 5

    def __post_init__(self) -> None:
        normalized_url = self.url.strip() if isinstance(self.url, str) else ""
        if not normalized_url:
            raise DatabaseConfigurationError("DATABASE_URL is required")

        try:
            parsed_url = make_url(normalized_url)
        except (ArgumentError, TypeError, ValueError) as exc:
            raise DatabaseConfigurationError(
                "DATABASE_URL must be a valid postgresql+psycopg URL"
            ) from exc

        if parsed_url.drivername != "postgresql+psycopg":
            raise DatabaseConfigurationError(
                "DATABASE_URL must use the postgresql+psycopg driver"
            )
        if not parsed_url.database:
            raise DatabaseConfigurationError(
                "DATABASE_URL must name a PostgreSQL database"
            )

        _validate_positive_int("pool_size", self.pool_size)
        _validate_positive_int("pool_timeout_s", self.pool_timeout_s)
        object.__setattr__(self, "url", normalized_url)


def load_database_settings(
    environment: Mapping[str, str] | None = None,
) -> DatabaseSettings:
    source = os.environ if environment is None else environment
    url = source.get("DATABASE_URL", "")
    pool_size = _read_positive_int(source, "DATABASE_POOL_SIZE", default=5)
    pool_timeout_s = _read_positive_int(
        source,
        "DATABASE_POOL_TIMEOUT_SECONDS",
        default=5,
    )
    return DatabaseSettings(
        url=url,
        pool_size=pool_size,
        pool_timeout_s=pool_timeout_s,
    )


def _read_positive_int(
    environment: Mapping[str, str],
    name: str,
    *,
    default: int,
) -> int:
    raw_value = environment.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise DatabaseConfigurationError(f"{name} must be a positive integer") from exc
    _validate_positive_int(name, value)
    return value


def _validate_positive_int(name: str, value: object) -> None:
    if type(value) is not int or value <= 0:
        raise DatabaseConfigurationError(f"{name} must be a positive integer")
