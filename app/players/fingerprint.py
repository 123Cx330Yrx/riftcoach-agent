from __future__ import annotations

import hashlib
import json
import re

from app.players.models import (
    RelationshipRole,
    RoutingRegion,
    normalize_riot_component,
)


_TASK_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SCHEMA_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+$")


def canonical_player_link_request_bytes(
    *,
    task_kind: str,
    schema_version: str,
    routing_region: str,
    game_name: str,
    tag_line: str,
    relationship_role: str,
) -> bytes:
    if not isinstance(task_kind, str) or not _TASK_KIND_PATTERN.fullmatch(task_kind):
        raise ValueError("task_kind must be a safe canonical identifier")
    if (
        not isinstance(schema_version, str)
        or not _SCHEMA_VERSION_PATTERN.fullmatch(schema_version)
    ):
        raise ValueError("schema_version must be a canonical major.minor value")

    envelope = {
        "game_name": normalize_riot_component(
            game_name,
            component_name="game_name",
            max_length=64,
        ),
        "relationship_role": RelationshipRole(relationship_role).value,
        "routing_region": RoutingRegion(routing_region).value,
        "schema_version": schema_version,
        "tag_line": normalize_riot_component(
            tag_line,
            component_name="tag_line",
            max_length=32,
        ),
        "task_kind": task_kind,
    }
    return json.dumps(
        envelope,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_player_link_request_fingerprint(
    *,
    task_kind: str,
    schema_version: str,
    routing_region: str,
    game_name: str,
    tag_line: str,
    relationship_role: str,
) -> str:
    return hashlib.sha256(
        canonical_player_link_request_bytes(
            task_kind=task_kind,
            schema_version=schema_version,
            routing_region=routing_region,
            game_name=game_name,
            tag_line=tag_line,
            relationship_role=relationship_role,
        )
    ).hexdigest()


__all__ = [
    "canonical_player_link_request_bytes",
    "compute_player_link_request_fingerprint",
]
