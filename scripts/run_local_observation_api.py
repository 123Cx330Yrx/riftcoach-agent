"""Explicit single-owner, loopback-only API for local observation consumption."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping

from fastapi import FastAPI

from app.api.composition import create_composed_app, load_api_composition_settings
from app.auth.session import AuthSessionBoundary, CookiePolicy, InMemoryAuthSessionStore


def create_local_observation_app(environment: Mapping[str, str] | None = None) -> FastAPI:
    source = dict(os.environ if environment is None else environment)
    if source.get("RIFTCOACH_API_PROFILE") != "local":
        raise ValueError("local observation requires RIFTCOACH_API_PROFILE=local")
    settings = load_api_composition_settings(source)
    owner_id = settings.local_owner_id
    assert owner_id is not None
    boundary = AuthSessionBoundary(
        store=InMemoryAuthSessionStore(), owner_provider=lambda: owner_id,
    )
    return create_composed_app(
        environment=source,
        auth_session_service=boundary,
        auth_cookie_policy=CookiePolicy(secure=False),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    import uvicorn

    uvicorn.run(create_local_observation_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
