"""Opaque server-side session primitives.

The raw cookie and CSRF token are returned only at issuance time. The store
keeps SHA-256 digests, never browser tokens, and is deliberately an explicit
local/test implementation until a PostgreSQL session repository is added.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from typing import Protocol

from app.api.actor import ActorContext


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuthSessionError(ValueError):
    """Safe contract failure; callers map it to an allowlisted auth code."""


@dataclass(frozen=True, slots=True)
class CookiePolicy:
    name: str = "riftcoach_session"
    secure: bool = True
    http_only: bool = True
    same_site: str = "lax"
    path: str = "/"

    def __post_init__(self) -> None:
        if not self.name or any(char in self.name for char in "=;\r\n"):
            raise AuthSessionError("session_cookie_name_invalid")
        if self.same_site not in {"lax", "strict", "none"}:
            raise AuthSessionError("session_cookie_same_site_invalid")
        if not self.path.startswith("/"):
            raise AuthSessionError("session_cookie_path_invalid")


@dataclass(frozen=True, slots=True)
class StoredSession:
    cookie_digest: str
    csrf_digest: str
    owner_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IssuedSession:
    cookie_value: str
    csrf_token: str
    owner_id: str
    expires_at: datetime


class AuthSessionStore(Protocol):
    def issue(
        self,
        *,
        owner_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> IssuedSession: ...

    def resolve(self, *, cookie_value: str, now: datetime) -> ActorContext: ...

    def verify_csrf(
        self,
        *,
        cookie_value: str,
        csrf_token: str,
        now: datetime,
    ) -> bool: ...

    def revoke(self, *, cookie_value: str, now: datetime) -> bool: ...


class AuthSessionService(Protocol):
    """HTTP-facing session boundary; no client-owned owner identity."""

    def issue(self) -> IssuedSession: ...

    def resolve(self, *, cookie_value: str, now: datetime) -> ActorContext: ...

    def verify_csrf(
        self,
        *,
        cookie_value: str,
        csrf_token: str,
        now: datetime,
    ) -> bool: ...

    def revoke(self, *, cookie_value: str, now: datetime) -> bool: ...


class InMemoryAuthSessionStore:
    """Explicitly local/test-only store; production composition must not use it."""

    def __init__(self, *, clock=_utc_now) -> None:
        self._clock = clock
        self._sessions: dict[str, StoredSession] = {}

    def issue(
        self,
        *,
        owner_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> IssuedSession:
        if not owner_id or owner_id.strip() != owner_id:
            raise AuthSessionError("owner_id_invalid")
        if ttl <= timedelta(0) or ttl > timedelta(days=1):
            raise AuthSessionError("session_ttl_invalid")
        cookie_value = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = now + ttl
        self._sessions[_digest(cookie_value)] = StoredSession(
            cookie_digest=_digest(cookie_value),
            csrf_digest=_digest(csrf_token),
            owner_id=owner_id,
            created_at=now,
            expires_at=expires_at,
        )
        return IssuedSession(
            cookie_value=cookie_value,
            csrf_token=csrf_token,
            owner_id=owner_id,
            expires_at=expires_at,
        )

    def _active(self, *, cookie_value: str, now: datetime) -> StoredSession:
        if not cookie_value or any(char in cookie_value for char in "\r\n;="):
            raise AuthSessionError("session_invalid")
        stored = self._sessions.get(_digest(cookie_value))
        if stored is None:
            raise AuthSessionError("session_invalid")
        if stored.revoked_at is not None:
            raise AuthSessionError("session_revoked")
        if now >= stored.expires_at:
            raise AuthSessionError("session_expired")
        return stored

    def resolve(self, *, cookie_value: str, now: datetime) -> ActorContext:
        stored = self._active(cookie_value=cookie_value, now=now)
        return ActorContext(owner_id=stored.owner_id)

    def verify_csrf(
        self,
        *,
        cookie_value: str,
        csrf_token: str,
        now: datetime,
    ) -> bool:
        stored = self._active(cookie_value=cookie_value, now=now)
        if not csrf_token or any(char in csrf_token for char in "\r\n;="):
            return False
        return hmac.compare_digest(stored.csrf_digest, _digest(csrf_token))

    def revoke(self, *, cookie_value: str, now: datetime) -> bool:
        stored = self._active(cookie_value=cookie_value, now=now)
        self._sessions[stored.cookie_digest] = StoredSession(
            cookie_digest=stored.cookie_digest,
            csrf_digest=stored.csrf_digest,
            owner_id=stored.owner_id,
            created_at=stored.created_at,
            expires_at=stored.expires_at,
            revoked_at=now,
        )
        return True


class AuthSessionBoundary:
    """Compose a store with a server-side owner source for local/test use.

    Production must inject an explicitly selected Auth/OIDC adapter instead of
    constructing this boundary from request data. The owner callback is never
    supplied by the browser.
    """

    def __init__(
        self,
        *,
        store: AuthSessionStore,
        owner_provider: Callable[[], str],
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not callable(owner_provider):
            raise TypeError("owner_provider must be callable")
        if ttl <= timedelta(0) or ttl > timedelta(days=1):
            raise AuthSessionError("session_ttl_invalid")
        self._store = store
        self._owner_provider = owner_provider
        self._ttl = ttl
        self._clock = clock

    def issue(self) -> IssuedSession:
        owner_id = self._owner_provider()
        if not isinstance(owner_id, str):
            raise AuthSessionError("owner_id_invalid")
        return self._store.issue(
            owner_id=owner_id,
            now=self._clock(),
            ttl=self._ttl,
        )

    def resolve(self, *, cookie_value: str, now: datetime) -> ActorContext:
        return self._store.resolve(cookie_value=cookie_value, now=now)

    def verify_csrf(
        self,
        *,
        cookie_value: str,
        csrf_token: str,
        now: datetime,
    ) -> bool:
        return self._store.verify_csrf(
            cookie_value=cookie_value,
            csrf_token=csrf_token,
            now=now,
        )

    def revoke(self, *, cookie_value: str, now: datetime) -> bool:
        return self._store.revoke(cookie_value=cookie_value, now=now)


__all__ = [
    "AuthSessionError",
    "AuthSessionBoundary",
    "AuthSessionService",
    "AuthSessionStore",
    "CookiePolicy",
    "InMemoryAuthSessionStore",
    "IssuedSession",
    "StoredSession",
]
