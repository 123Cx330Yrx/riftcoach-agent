from datetime import datetime, timedelta, timezone

import pytest

from app.api.actor import ActorContext
from app.auth.session import (
    AuthSessionError,
    CookiePolicy,
    InMemoryAuthSessionStore,
)


NOW = datetime(2026, 8, 24, 4, 0, tzinfo=timezone.utc)


def test_issue_stores_only_opaque_digests_and_resolves_owner() -> None:
    store = InMemoryAuthSessionStore()
    issued = store.issue(owner_id="owner-a", now=NOW, ttl=timedelta(minutes=30))

    assert len(issued.cookie_value) >= 32
    assert len(issued.csrf_token) >= 32
    assert store.resolve(cookie_value=issued.cookie_value, now=NOW) == ActorContext(owner_id="owner-a")
    assert issued.cookie_value not in repr(store._sessions)
    assert issued.csrf_token not in repr(store._sessions)


def test_expired_and_revoked_sessions_fail_closed() -> None:
    store = InMemoryAuthSessionStore()
    issued = store.issue(owner_id="owner-a", now=NOW, ttl=timedelta(minutes=5))

    with pytest.raises(AuthSessionError, match="session_expired"):
        store.resolve(cookie_value=issued.cookie_value, now=NOW + timedelta(minutes=5))

    issued_again = store.issue(owner_id="owner-a", now=NOW, ttl=timedelta(minutes=5))
    assert store.revoke(cookie_value=issued_again.cookie_value, now=NOW)
    with pytest.raises(AuthSessionError, match="session_revoked"):
        store.resolve(cookie_value=issued_again.cookie_value, now=NOW)


def test_csrf_is_bound_to_the_same_session_and_owner_is_not_client_supplied() -> None:
    store = InMemoryAuthSessionStore()
    issued = store.issue(owner_id="owner-a", now=NOW, ttl=timedelta(minutes=30))
    other = store.issue(owner_id="owner-b", now=NOW, ttl=timedelta(minutes=30))

    assert store.verify_csrf(
        cookie_value=issued.cookie_value,
        csrf_token=issued.csrf_token,
        now=NOW,
    )
    assert not store.verify_csrf(
        cookie_value=issued.cookie_value,
        csrf_token=other.csrf_token,
        now=NOW,
    )
    assert store.resolve(cookie_value=issued.cookie_value, now=NOW).owner_id == "owner-a"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"owner_id": " owner-a", "now": NOW, "ttl": timedelta(minutes=1)}, "owner_id_invalid"),
        ({"owner_id": "owner-a", "now": NOW, "ttl": timedelta(0)}, "session_ttl_invalid"),
    ],
)
def test_issue_rejects_unsafe_contract_values(kwargs: dict[str, object], error: str) -> None:
    with pytest.raises(AuthSessionError, match=error):
        InMemoryAuthSessionStore().issue(**kwargs)  # type: ignore[arg-type]


def test_cookie_policy_is_explicit_and_rejects_unsafe_flags() -> None:
    assert CookiePolicy().http_only is True
    assert CookiePolicy().same_site == "lax"
    with pytest.raises(AuthSessionError, match="same_site"):
        CookiePolicy(same_site="invalid")
