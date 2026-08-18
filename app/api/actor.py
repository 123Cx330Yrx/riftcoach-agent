"""Trusted request actor identities for the HTTP boundary.

The product request never owns ``owner_id``.  An authentication adapter (or
an explicitly local/test provider) creates this server-side context instead.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.tasks.models import OwnerId


ActorProfile = Literal["local", "test", "production"]


class ActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    owner_id: OwnerId


class ActorContextUnavailable(RuntimeError):
    """Safe control-plane failure when no trusted actor can be established."""

    def __init__(self) -> None:
        super().__init__("actor_context_unavailable")


class ActorContextProvider(Protocol):
    def __call__(self) -> ActorContext: ...


class StaticActorContextProvider:
    """Fixed actor provider restricted to explicit local/test profiles."""

    def __init__(self, *, owner_id: str, profile: ActorProfile) -> None:
        if profile not in {"local", "test"}:
            raise ValueError(
                "static actor context is restricted to local/test profiles"
            )
        self._context = ActorContext(owner_id=owner_id)

    def __call__(self) -> ActorContext:
        return self._context


class UnavailableActorContextProvider:
    """Fail-closed placeholder used when production Auth is not configured."""

    def __call__(self) -> ActorContext:
        raise ActorContextUnavailable()


__all__ = [
    "ActorContext",
    "ActorContextProvider",
    "ActorContextUnavailable",
    "ActorProfile",
    "StaticActorContextProvider",
    "UnavailableActorContextProvider",
]
