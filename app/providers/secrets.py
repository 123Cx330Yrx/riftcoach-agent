"""Versioned, redacted Secret source contracts for later deployment wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class SecretConfigurationError(ValueError):
    """Allowlisted Secret configuration failure; never contains the value."""


@dataclass(frozen=True, slots=True)
class SecretMaterial:
    name: str
    version: str
    value: str = field(repr=False)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.version or not self.value:
            raise SecretConfigurationError("secret_invalid")

    def usable_at(self, now: datetime) -> bool:
        return self.revoked_at is None and (
            self.expires_at is None or now < self.expires_at
        )

    def redacted(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "version": self.version,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": "true" if self.revoked_at is not None else "false",
        }


class SecretSource(Protocol):
    def read(self, *, name: str, now: datetime, version: str | None = None) -> SecretMaterial: ...

    def active_versions(self, *, name: str, now: datetime) -> tuple[str, ...]: ...

    def revoke(self, *, name: str, version: str, now: datetime) -> None: ...


class InMemorySecretSource:
    """Local/test source; production must inject a secret-manager adapter."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], SecretMaterial] = {}

    def __repr__(self) -> str:
        versions = tuple(
            f"{name}:{version}"
            for name, version in sorted(self._values)
        )
        return f"InMemorySecretSource(versions={versions!r})"

    def put(
        self,
        *,
        name: str,
        version: str,
        value: str,
        expires_at: datetime | None = None,
    ) -> None:
        material = SecretMaterial(
            name=name,
            version=version,
            value=value,
            expires_at=expires_at,
        )
        self._values[(name, version)] = material

    def read(
        self,
        *,
        name: str,
        now: datetime,
        version: str | None = None,
    ) -> SecretMaterial:
        if version is not None:
            material = self._values.get((name, version))
            if material is None:
                raise SecretConfigurationError("secret_missing")
            if material.revoked_at is not None:
                raise SecretConfigurationError("secret_revoked")
            if material.expires_at is not None and now >= material.expires_at:
                raise SecretConfigurationError("secret_expired")
            return material

        active = [
            material
            for (candidate_name, _), material in self._values.items()
            if candidate_name == name and material.usable_at(now)
        ]
        if not active:
            raise SecretConfigurationError("secret_unavailable")
        return sorted(active, key=lambda material: material.version)[-1]

    def active_versions(self, *, name: str, now: datetime) -> tuple[str, ...]:
        return tuple(
            material.version
            for material in sorted(
                (
                    material
                    for (candidate_name, _), material in self._values.items()
                    if candidate_name == name and material.usable_at(now)
                ),
                key=lambda material: material.version,
            )
        )

    def revoke(self, *, name: str, version: str, now: datetime) -> None:
        material = self._values.get((name, version))
        if material is None:
            raise SecretConfigurationError("secret_missing")
        self._values[(name, version)] = SecretMaterial(
            name=material.name,
            version=material.version,
            value=material.value,
            expires_at=material.expires_at,
            revoked_at=now,
        )


__all__ = [
    "InMemorySecretSource",
    "SecretConfigurationError",
    "SecretMaterial",
    "SecretSource",
]
