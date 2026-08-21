"""Run one bounded real OP.GG lane-Meta product smoke.

The persisted result is intentionally body-free: it records protocol/catalog/
evidence identities and limits, never the MCP session value or remote text.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.mcp.client import McpClientSession
from app.mcp.models import McpImplementation
from app.mcp.transport import StreamableHttpMcpTransport
from app.meta.context import meta_evidence_context_section
from app.meta.opgg import (
    OPGG_LANE_META_LOCAL_TOOL,
    OPGG_LANE_META_REMOTE_TOOL,
    OPGGLaneMetaAdapter,
)
from app.tools.models import CachePolicy, RetryPolicy, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


ENDPOINT = "https://mcp-api.op.gg/mcp"
PROTOCOL_VERSION = "2025-06-18"


def run_smoke(*, position: str, top_n: int) -> dict[str, Any]:
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
        section = meta_evidence_context_section(
            evidence,
            now=evidence.retrieved_at,
        )
        descriptor = catalog.get(OPGG_LANE_META_REMOTE_TOOL)
        assert descriptor is not None
        return {
            "schema_version": "1.0",
            "result": "passed",
            "body_free": True,
            "endpoint": ENDPOINT,
            "protocol": {
                "version": initialized.protocol_version,
                "server_name": initialized.server_info.name,
                "server_version": initialized.server_info.version,
                "tools_capability": initialized.tools is not None,
            },
            "catalog": {
                "admitted_tool_count": len(catalog.tools),
                "digest": catalog.digest,
                "selected_tool": OPGG_LANE_META_REMOTE_TOOL,
                "selected_tool_schema_digest": descriptor.schema_digest,
                "selected_tool_output_schema_present": (
                    descriptor.output_schema is not None
                ),
            },
            "evidence": {
                "digest": evidence.digest,
                "provenance": evidence.provenance.value,
                "position": evidence.position,
                "fact_count": len(evidence.facts),
                "upstream_patch": evidence.upstream_patch,
                "source_generated_at": None,
                "retrieved_at": evidence.retrieved_at.isoformat(),
                "expires_at": evidence.expires_at.isoformat(),
                "allowed_uses": sorted(
                    item.value for item in evidence.allowed_uses
                ),
            },
            "context": {
                "section_id": section.section_id,
                "trust": section.trust.value,
                "instructional": section.instructional,
                "required": section.required,
                "message_role": section.message_role.value,
            },
            "external_io": {
                "opgg_tools_call_calls": 1,
                "riot_calls": 0,
                "llm_provider_calls": 0,
                "key_reads": 0,
            },
            "limitations": [
                "upstream_patch_unknown",
                "source_generated_at_unknown",
                "upstream_freshness_unknown",
                "exact_patch_attribution_forbidden",
                "historical_patch_comparison_forbidden",
            ],
        }
    finally:
        session.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--position", default="top")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.execute:
        raise SystemExit("refusing external I/O without --execute")
    if args.output.exists():
        raise SystemExit("refusing to overwrite an existing smoke result")
    result = run_smoke(position=args.position, top_n=args.top_n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": result["result"],
                "body_free": result["body_free"],
                "evidence_digest": result["evidence"]["digest"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
