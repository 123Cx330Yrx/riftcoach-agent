"""Fuse one body-free Riot validation with one real OP.GG Meta snapshot.

The Riot side is read from a previously persisted body-free validation result;
this command performs exactly one bounded OP.GG read and then calls the pure
8D fusion kernel. It persists only the public bundle projection and source
digests, never the MCP result body or Riot identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evidence import RiotMatchEvidence, fuse_evidence
from app.mcp.client import McpClientSession
from app.mcp.models import McpImplementation
from app.mcp.transport import StreamableHttpMcpTransport
from app.meta.opgg import (
    OPGG_LANE_META_LOCAL_TOOL,
    OPGG_LANE_META_REMOTE_TOOL,
    OPGGMetaError,
    OPGGLaneMetaAdapter,
)
from app.tools.models import CachePolicy, RetryPolicy, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://mcp-api.op.gg/mcp"
PROTOCOL_VERSION = "2025-06-18"
_ROLE_MAP = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "mid",
    "MID": "mid",
    "BOTTOM": "adc",
    "UTILITY": "support",
    "SUPPORT": "support",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_riot_result(path: Path) -> tuple[dict[str, Any], str]:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise ValueError("Riot result must be inside the repository") from error
    raw = resolved.read_bytes()
    result = json.loads(raw.decode("utf-8"))
    if (
        not isinstance(result, dict)
        or result.get("result") != "passed"
        or result.get("body_free") is not True
    ):
        raise ValueError("Riot result is not an admitted body-free success")
    return result, _sha256_bytes(raw)


def _typed_riot_match(result: dict[str, Any]) -> RiotMatchEvidence:
    match = result.get("match")
    target = match.get("target") if isinstance(match, dict) else None
    matches = result.get("matches")
    if not isinstance(match, dict) or not isinstance(target, dict) or not isinstance(matches, dict):
        raise ValueError("Riot result shape is invalid")
    patch_raw = match.get("game_version")
    patch = ".".join(patch_raw.split(".")[:2]) if isinstance(patch_raw, str) else None
    position = _ROLE_MAP.get(str(target.get("role", "")).upper())
    champion_id = target.get("champion_id")
    champion_name = target.get("champion")
    if (
        not isinstance(position, str)
        or not isinstance(champion_id, int)
        or isinstance(champion_id, bool)
        or not isinstance(champion_name, str)
        or not isinstance(result.get("routing_region"), str)
        or not isinstance(match.get("queue_id"), int)
        or not isinstance(match.get("game_duration_seconds"), int)
        or not isinstance(target.get("win"), bool)
        or not isinstance(matches.get("selected_match_id_digest"), str)
    ):
        raise ValueError("Riot result typed facts are invalid")
    observed_at = datetime.fromisoformat(str(result["observed_at"]).replace("Z", "+00:00"))
    source_digest = matches["selected_match_id_digest"]
    return RiotMatchEvidence(
        match_id=f"digest:{source_digest[:32]}",
        routing_region=result["routing_region"],
        queue_id=match["queue_id"],
        champion_id=champion_id,
        champion_name=champion_name,
        position=position,
        patch_version=patch,
        win=target["win"],
        duration_seconds=match["game_duration_seconds"],
        timeline_available=False,
        observed_at=observed_at,
        source_digest=source_digest,
    )


def _fetch_opgg_evidence(*, position: str, top_n: int):
    transport = StreamableHttpMcpTransport(ENDPOINT)
    session = McpClientSession(
        transport,
        client_info=McpImplementation(name="riftcoach", version="0.1.0"),
        supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
        allowed_tools=frozenset({OPGG_LANE_META_REMOTE_TOOL}),
    )
    try:
        initialized = session.initialize(timeout_s=15)
        catalog = session.discover(timeout_s=15)
        registry = ToolRegistry()
        registry.register(
            session.to_tool_definition(
                OPGG_LANE_META_REMOTE_TOOL,
                local_name=OPGG_LANE_META_LOCAL_TOOL,
                description="Fetch one bounded OP.GG lane-meta snapshot.",
                policy=ToolPolicy(
                    timeout_s=15,
                    retry=RetryPolicy(max_attempts=1),
                    cache=CachePolicy(ttl_s=0),
                ),
            )
        )
        evidence = OPGGLaneMetaAdapter(
            session=session,
            runtime=ToolRuntime(registry),
        ).fetch(position=position, top_n=top_n, timeout_s=15)
        descriptor = catalog.get(OPGG_LANE_META_REMOTE_TOOL)
        if descriptor is None:
            raise ValueError("selected OP.GG tool disappeared from catalog")
        return initialized, catalog, descriptor, evidence
    finally:
        session.close()


def run_validation(*, riot_result_path: Path, position: str, top_n: int) -> dict[str, Any]:
    riot_result, riot_file_digest = _read_riot_result(riot_result_path)
    riot_match = _typed_riot_match(riot_result)
    try:
        initialized, catalog, descriptor, opgg = _fetch_opgg_evidence(
            position=position,
            top_n=top_n,
        )
    except OPGGMetaError as error:
        return {
            "schema_version": "1.0",
            "result": "failed",
            "body_free": True,
            "relationship_role": riot_result["relationship_role"],
            "riot": {
                "routing_region": riot_result["routing_region"],
                "source_digest": riot_match.source_digest,
                "result_file_digest": riot_file_digest,
                "riot_calls_in_fusion_run": 0,
            },
            "opgg": {
                "endpoint": ENDPOINT,
                "selected_tool": OPGG_LANE_META_REMOTE_TOOL,
                "position": position,
                "requested_top_n": top_n,
                "error_code": error.code,
                "schema_diagnostic": (
                    error.diagnostic.to_public_projection()
                    if error.diagnostic is not None
                    else None
                ),
            },
            "external_io": {
                "riot_calls": 0,
                "opgg_tools_call_calls": 1,
                "llm_provider_calls": 0,
                "key_reads": 0,
            },
            "limitations": [
                "real_opgg_result_rejected_by_strict_adapter",
                "no_bundle_created",
                "raw_response_not_persisted",
            ],
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    now = max(riot_match.observed_at, opgg.retrieved_at)
    bundle = fuse_evidence(
        riot_matches=[riot_match],
        data_dragon=None,
        official_patch=None,
        meta_evidence=[opgg],
        now=now,
    )
    return {
        "schema_version": "1.0",
        "result": "passed",
        "body_free": True,
        "relationship_role": riot_result["relationship_role"],
        "riot": {
            "routing_region": riot_result["routing_region"],
            "source_digest": riot_match.source_digest,
            "result_file_digest": riot_file_digest,
            "riot_calls_in_fusion_run": 0,
        },
        "opgg": {
            "endpoint": ENDPOINT,
            "protocol_version": initialized.protocol_version,
            "server_name": initialized.server_info.name,
            "server_version": initialized.server_info.version,
            "selected_tool": OPGG_LANE_META_REMOTE_TOOL,
            "catalog_digest": catalog.digest,
            "tool_schema_digest": descriptor.schema_digest,
            "evidence_digest": opgg.digest,
            "position": opgg.position,
            "fact_count": len(opgg.facts),
            "provenance": opgg.provenance.value,
            "retrieved_at": opgg.retrieved_at.isoformat(),
            "expires_at": opgg.expires_at.isoformat(),
        },
        "bundle": bundle.to_public_projection(),
        "external_io": {
            "riot_calls": 0,
            "opgg_tools_call_calls": 1,
            "llm_provider_calls": 0,
            "key_reads": 0,
        },
        "limitations": [
            "Riot input came from a prior body-free validation result",
            "data_dragon_not_included_in_replay",
            "official_patch_not_included_in_replay",
            "opgg_partial_provenance",
            "upstream_patch_unknown",
            "upstream_freshness_unknown",
            "bundle_is_replay_evidence_not_a_production_store",
        ],
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--riot-result", type=Path, required=True)
    parser.add_argument("--position", choices=("top", "mid", "jungle", "adc", "support"), default="mid")
    parser.add_argument("--top-n", type=int, choices=tuple(range(1, 11)), default=10)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.execute:
        raise SystemExit("refusing external I/O without --execute")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError as error:
        raise SystemExit("output must be inside the repository") from error
    if output.exists():
        raise SystemExit("refusing to overwrite an existing fusion result")
    result = run_validation(
        riot_result_path=args.riot_result,
        position=args.position,
        top_n=args.top_n,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": result["result"],
                "body_free": result["body_free"],
                "bundle_digest": (
                    result.get("bundle", {}).get("bundle_digest")
                    if isinstance(result.get("bundle"), dict)
                    else None
                ),
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0 if result["result"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
