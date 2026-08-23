from datetime import datetime, timedelta, timezone

import pytest

from app.providers.secrets import (
    InMemorySecretSource,
    SecretConfigurationError,
)


NOW = datetime(2026, 8, 24, 4, 0, tzinfo=timezone.utc)


def test_secret_value_is_not_in_repr_or_redacted_metadata() -> None:
    source = InMemorySecretSource()
    source.put(name="riot", version="v1", value="super-secret")
    material = source.read(name="riot", now=NOW)

    assert "super-secret" not in repr(material)
    assert "super-secret" not in repr(material.redacted())
    assert material.redacted()["version"] == "v1"


def test_dual_key_overlap_selects_latest_and_supports_revoke() -> None:
    source = InMemorySecretSource()
    source.put(name="riot", version="v1", value="old")
    source.put(name="riot", version="v2", value="new")

    assert source.active_versions(name="riot", now=NOW) == ("v1", "v2")
    assert source.read(name="riot", now=NOW).version == "v2"
    source.revoke(name="riot", version="v2", now=NOW)
    assert source.read(name="riot", now=NOW).version == "v1"


def test_missing_expired_and_revoked_versions_fail_closed() -> None:
    source = InMemorySecretSource()
    source.put(
        name="llm",
        version="v1",
        value="expired",
        expires_at=NOW + timedelta(seconds=1),
    )

    with pytest.raises(SecretConfigurationError, match="secret_expired"):
        source.read(name="llm", version="v1", now=NOW + timedelta(seconds=1))
    with pytest.raises(SecretConfigurationError, match="secret_missing"):
        source.read(name="missing", version="v1", now=NOW)

    source.put(name="riot", version="v1", value="revoked")
    source.revoke(name="riot", version="v1", now=NOW)
    with pytest.raises(SecretConfigurationError, match="secret_revoked"):
        source.read(name="riot", version="v1", now=NOW)
