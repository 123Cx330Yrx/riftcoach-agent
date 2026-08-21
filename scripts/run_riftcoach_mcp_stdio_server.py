"""Run the restricted RiftCoach MCP Server over bounded standard stdio.

This 7-5 composition is deliberately no-I/O: it injects a fixed test actor and
a data-only facade so an independent external Client can verify the real MCP
Server/session/schema boundary without database, Provider, Riot, or secrets.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping

from app.api.actor import ActorContext
from app.mcp.server import McpFacadeError, RiftCoachMcpServer
from app.mcp.stdio import serve_stdio


class InteroperabilityFacade:
    """No-I/O facade used only by the immutable Stage 7 protocol proof."""

    @staticmethod
    def recent_summary(*, actor: ActorContext, run_id: str):
        raise McpFacadeError("not_found")

    @staticmethod
    def single_match_review(*, actor: ActorContext, run_id: str):
        raise McpFacadeError("not_found")

    @staticmethod
    def knowledge_search(
        *,
        actor: ActorContext,
        query: str,
        top_k: int,
        filters: Mapping[str, object],
    ):
        return {
            "provider": "interop-fixture",
            "abstained": False,
            "count": 1,
            "attributions": [
                {
                    "chunk_id": "interop-chunk",
                    "source_id": "interop-source",
                    "title": "Interop fixture",
                    "version": "1.0",
                }
            ],
        }

    @staticmethod
    def report_evaluation(*, actor: ActorContext, run_id: str):
        raise McpFacadeError("not_found")


def build_interoperability_server() -> RiftCoachMcpServer:
    return RiftCoachMcpServer(
        facade=InteroperabilityFacade(),
        actor_provider=lambda: ActorContext(owner_id="stage7-interop-owner"),
    )


def main() -> int:
    server = build_interoperability_server()
    serve_stdio(
        server.new_session(),
        reader=sys.stdin.buffer,
        writer=sys.stdout.buffer,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
