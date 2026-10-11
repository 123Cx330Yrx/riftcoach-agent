from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from scripts.run_local_observation_api import create_local_observation_app


def test_local_launcher_requires_explicit_profile_and_owner():
    for environment in ({}, {"RIFTCOACH_API_PROFILE": "production"},
                        {"RIFTCOACH_API_PROFILE": "test"},
                        {"RIFTCOACH_API_PROFILE": "local"}):
        with pytest.raises(ValueError):
            create_local_observation_app(environment)


def test_local_session_requires_cookie_and_csrf_without_database_access():
    # Do not enter lifespan: no database is configured or contacted in this test.
    client = TestClient(create_local_observation_app({
        "RIFTCOACH_API_PROFILE": "local", "RIFTCOACH_LOCAL_OWNER_ID": "local-observer",
    }))
    assert client.get("/player-profiles").status_code == 401
    issued = client.post("/auth/session")
    assert issued.status_code == 200
    assert "HttpOnly" in issued.headers["set-cookie"]
    assert "Secure" not in issued.headers["set-cookie"]
    assert client.post("/conversations", json={}).status_code == 403
    assert client.post("/conversations", json={}, headers={
        "X-CSRF-Token": "wrong",
    }).status_code == 403
