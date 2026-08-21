"""Fixture/external-client tests for the restricted RiftCoach MCP Server."""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace

import pytest

from app.api.actor import ActorContext
from app.mcp.client import McpClientSession
from app.mcp.errors import (
    McpErrorInfo,
    McpRemoteError,
    McpSessionError,
    McpToolCallError,
)
from app.mcp.models import McpContractLimits, McpImplementation
from app.mcp.server import (
    McpFacadeError,
    McpServerTransport,
    QueryMcpApplicationFacade,
    RiftCoachMcpServer,
    build_riftcoach_mcp_server,
)
from app.rag.models import (
    KnowledgeHit,
    KnowledgeMetadata,
    KnowledgeQuery,
    KnowledgeSearchResult,
)


RUN_ID = "review_20260821T000000Z_abcdef123456"


class FakeFacade:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Mapping[str, object]]] = []

    def recent_summary(self, *, actor: ActorContext, run_id: str):
        self.calls.append(("recent_summary", actor.owner_id, {"run_id": run_id}))
        return {
            "run_id": run_id,
            "skill_name": "recent-form-review",
            "skill_version": "0.2.0",
            "runtime_status": "completed",
            "publication_status": "published",
            "terminal_reason": "published",
            "report_available": True,
            "games_analyzed": 2,
            "wins": 1,
            "losses": 1,
            "win_rate": 50.0,
            "main_role": "MIDDLE",
            "main_champions": ["ChampionA", "ChampionB"],
            "averages": {
                "kda": 3.0,
                "cs_per_min": 8.5,
                "gold_per_min": 430.0,
                "damage_per_min": 700.0,
                "vision_score": 20.0,
                "kill_participation_percent": 50.0,
                "damage_share_percent": 25.0,
                "gold_share_percent": 22.0,
                "deaths_before_15": 0.5,
            },
            "win_loss_comparison": {
                "wins": {
                    "cs_per_min": 9.0,
                    "gold_per_min": 460.0,
                    "damage_per_min": 760.0,
                    "vision_score": 24.0,
                    "deaths_before_15": 0.0,
                },
                "losses": {
                    "cs_per_min": 8.0,
                    "gold_per_min": 400.0,
                    "damage_per_min": 640.0,
                    "vision_score": 16.0,
                    "deaths_before_15": 1.0,
                },
            },
            "player": {"riot_id": "private#id", "puuid": "private"},
            "raw_report": "private report body",
        }

    def single_match_review(self, *, actor: ActorContext, run_id: str):
        self.calls.append(("single_match_review", actor.owner_id, {"run_id": run_id}))
        return {
            "run_id": run_id,
            "skill_name": "single-match-review",
            "skill_version": "0.1.0",
            "runtime_status": "completed",
            "publication_status": "published",
            "terminal_reason": "published",
            "review_available": True,
            "review_sha256": "a" * 64,
        }

    def knowledge_search(
        self,
        *,
        actor: ActorContext,
        query: str,
        top_k: int,
        filters: Mapping[str, object],
    ):
        self.calls.append(
            (
                "knowledge_search",
                actor.owner_id,
                {"query": query, "top_k": top_k, "filters": filters},
            )
        )
        return {
            "provider": "fixture",
            "abstained": False,
            "count": 1,
            "attributions": [
                {
                    "chunk_id": "chunk-1",
                    "source_id": "coach-guide",
                    "title": "Fixture guide",
                    "version": "1.0",
                }
            ],
        }

    def report_evaluation(self, *, actor: ActorContext, run_id: str):
        self.calls.append(("report_evaluation", actor.owner_id, {"run_id": run_id}))
        return {
            "run_id": run_id,
            "publication_status": "published",
            "evaluation_status": "passed",
            "score_available": False,
        }


def _client(server: RiftCoachMcpServer, facade: FakeFacade):
    session = server.new_session()
    transport = McpServerTransport(session)
    client = McpClientSession(
        transport,
        client_info=McpImplementation(name="fixture-client", version="1.0.0"),
        supported_protocol_versions={"2025-06-18"},
        allowed_tools=set(server.tool_names),
    )
    return client, facade


def test_external_client_can_initialize_discover_and_call_read_only_server():
    facade = FakeFacade()
    server = RiftCoachMcpServer(
        facade=facade,
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    client, _ = _client(server, facade)

    initialization = client.initialize()
    assert initialization.protocol_version == "2025-06-18"
    catalog = client.discover()
    assert tuple(tool.name for tool in catalog.tools) == (
        "riftcoach.knowledge_search",
        "riftcoach.recent_summary",
        "riftcoach.report_evaluation",
        "riftcoach.single_match_review",
    )

    result = client.call("riftcoach.recent_summary", {"run_id": RUN_ID})
    assert result.success is True
    assert result.structured_content is not None
    assert result.structured_content["run_id"] == RUN_ID
    assert result.structured_content["games_analyzed"] == 2
    assert result.structured_content["averages"]["kda"] == 3.0
    assert "owner_id" not in result.structured_content
    assert "player" not in result.structured_content
    assert "raw_report" not in result.structured_content
    assert facade.calls == [("recent_summary", "owner-a", {"run_id": RUN_ID})]


def test_server_injects_actor_and_rejects_client_owned_identity_fields():
    facade = FakeFacade()
    server = RiftCoachMcpServer(
        facade=facade,
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    client, _ = _client(server, facade)
    client.initialize()
    client.discover()

    with pytest.raises(McpToolCallError) as error:
        client.call(
            "riftcoach.recent_summary",
            {"run_id": RUN_ID, "owner_id": "owner-b"},
        )
    assert error.value.code == "mcp_tool_arguments_invalid"
    assert facade.calls == []


def test_all_server_tools_return_bounded_structured_content_without_bodies():
    facade = FakeFacade()
    server = RiftCoachMcpServer(
        facade=facade,
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    client, _ = _client(server, facade)
    client.initialize()
    client.discover()

    outputs = (
        client.call("riftcoach.single_match_review", {"run_id": RUN_ID}),
        client.call("riftcoach.knowledge_search", {"query": "vision", "top_k": 3}),
        client.call("riftcoach.report_evaluation", {"run_id": RUN_ID}),
    )
    assert all(output.success for output in outputs)
    assert all(output.structured_content is not None for output in outputs)
    single = outputs[0].structured_content
    assert single["skill_name"] == "single-match-review"
    assert single["review_sha256"] == "a" * 64
    for output in outputs:
        assert "report" not in output.structured_content
        assert "prompt" not in output.structured_content
        assert "content" not in output.structured_content


def test_facade_failure_is_a_body_free_tool_error():
    class BrokenFacade(FakeFacade):
        def recent_summary(self, *, actor: ActorContext, run_id: str):
            raise McpFacadeError("owner_scope_denied")

    server = RiftCoachMcpServer(
        facade=BrokenFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    session = server.new_session()
    initialize = session.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "fixture", "version": "1.0.0"},
            },
        }
    )
    assert initialize["result"]["protocolVersion"] == "2025-06-18"
    session.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    session.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    failed = session.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "riftcoach.recent_summary", "arguments": {"run_id": RUN_ID}},
        }
    )
    assert failed["result"]["isError"] is True
    assert failed["result"]["_meta"] == {"errorCode": "owner_scope_denied"}
    assert "traceback" not in str(failed).lower()


def test_server_rejects_protocol_and_lifecycle_misuse_without_remote_body():
    server = RiftCoachMcpServer(
        facade=FakeFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    session = server.new_session()
    before_initialize = session.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    assert before_initialize["error"]["code"] == -32001
    unsupported = session.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {
                "protocolVersion": "2020-01-01",
                "capabilities": {},
                "clientInfo": {"name": "fixture", "version": "1.0.0"},
            },
        }
    )
    assert unsupported["error"]["code"] == -32602
    assert "body" not in str(unsupported).lower()


def test_catalog_is_strict_read_only_and_contains_no_identity_or_open_io_fields():
    server = RiftCoachMcpServer(
        facade=FakeFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )

    for descriptor in server.catalog.tools:
        assert descriptor.annotations == {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
        properties = descriptor.input_schema["properties"]
        assert not set(properties).intersection(
            {"owner_id", "puuid", "key", "prompt", "url", "sql", "path"}
        )
        assert descriptor.input_schema["additionalProperties"] is False
        assert descriptor.output_schema["additionalProperties"] is False


def test_initialized_notification_and_exact_request_envelopes_are_required():
    server = RiftCoachMcpServer(
        facade=FakeFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    session = server.new_session()
    session.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "fixture", "version": "1.0.0"},
            },
        }
    )
    too_early = session.handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    assert too_early["error"]["code"] == -32001
    assert session.handle(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    ) is None
    extra = session.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
            "params": {},
            "owner_id": "owner-b",
        }
    )
    assert extra["error"]["code"] == -32600


def test_invalid_portable_run_id_fails_before_actor_or_facade_call():
    calls = 0

    def actor_provider():
        nonlocal calls
        calls += 1
        return ActorContext(owner_id="owner-a")

    facade = FakeFacade()
    server = RiftCoachMcpServer(facade=facade, actor_provider=actor_provider)
    client, _ = _client(server, facade)
    client.initialize()
    client.discover()

    with pytest.raises(McpRemoteError) as invalid:
        client.call("riftcoach.recent_summary", {"run_id": "CON"})
    assert invalid.value.info.remote_code == -32602
    assert calls == 0
    assert facade.calls == []


def test_actor_failure_and_invalid_facade_output_do_not_leak_private_details():
    def unavailable_actor():
        raise RuntimeError("SECRET owner database path C:/private")

    server = RiftCoachMcpServer(
        facade=FakeFacade(),
        actor_provider=unavailable_actor,
    )
    session = server.new_session()
    transport = McpServerTransport(session)
    client = McpClientSession(
        transport,
        client_info=McpImplementation(name="fixture-client", version="1.0.0"),
        supported_protocol_versions={"2025-06-18"},
        allowed_tools=set(server.tool_names),
    )
    client.initialize()
    client.discover()
    result = client.call("riftcoach.recent_summary", {"run_id": RUN_ID})
    assert result.success is False
    assert "SECRET" not in repr(result)
    assert "private" not in repr(result)

    class InvalidFacade(FakeFacade):
        def knowledge_search(self, **kwargs):
            del kwargs
            return {
                "provider": "fixture",
                "abstained": False,
                "count": 1,
                "attributions": [{
                    "chunk_id": "x" * 129,
                    "source_id": "source",
                    "title": "title",
                    "version": None,
                }],
            }

    invalid_server = RiftCoachMcpServer(
        facade=InvalidFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    invalid_client, _ = _client(invalid_server, InvalidFacade())
    invalid_client.initialize()
    invalid_client.discover()
    invalid = invalid_client.call(
        "riftcoach.knowledge_search",
        {"query": "vision", "top_k": 3},
    )
    assert invalid.success is False

    class WrongSkillFacade(FakeFacade):
        def recent_summary(self, *, actor: ActorContext, run_id: str):
            raw = dict(super().recent_summary(actor=actor, run_id=run_id))
            raw["skill_name"] = "single-match-review"
            return raw

    wrong_skill_server = RiftCoachMcpServer(
        facade=WrongSkillFacade(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    wrong_skill_client, _ = _client(wrong_skill_server, WrongSkillFacade())
    wrong_skill_client.initialize()
    wrong_skill_client.discover()
    wrong_skill = wrong_skill_client.call(
        "riftcoach.recent_summary",
        {"run_id": RUN_ID},
    )
    assert wrong_skill.success is False
    assert wrong_skill.error is not None
    assert wrong_skill.error.code == "mcp_tool_error"


def test_in_process_transport_restart_invalidates_snapshot_and_reinitializes():
    facade = FakeFacade()
    server = RiftCoachMcpServer(
        facade=facade,
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    transport = McpServerTransport(server.new_session())
    client = McpClientSession(
        transport,
        client_info=McpImplementation(name="fixture-client", version="1.0.0"),
        supported_protocol_versions={"2025-06-18"},
        allowed_tools=set(server.tool_names),
    )
    client.initialize()
    client.discover()
    transport.restart()
    with pytest.raises(McpSessionError) as stale:
        client.call("riftcoach.recent_summary", {"run_id": RUN_ID})
    assert getattr(stale.value, "code", None) == "mcp_session_restarted"
    client.initialize()
    client.discover()
    assert client.call("riftcoach.recent_summary", {"run_id": RUN_ID}).success


def test_server_result_budget_fails_closed_before_structured_content_leaves():
    facade = FakeFacade()
    server = RiftCoachMcpServer(
        facade=facade,
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
        limits=McpContractLimits(max_result_bytes=64),
    )
    client, _ = _client(server, facade)
    client.initialize()
    client.discover()

    result = client.call("riftcoach.recent_summary", {"run_id": RUN_ID})

    assert result.success is False
    assert result.structured_content is None
    assert result.error is not None
    assert result.error.code == "mcp_tool_error"


def test_default_query_facade_uses_owner_scoped_services_and_attribution_only():
    calls: list[tuple[str, str]] = []

    class Tasks:
        def get_task_by_run_id(self, *, owner_id: str, run_id: str):
            calls.append((owner_id, run_id))
            return SimpleNamespace(run_id=run_id)

    class Runs:
        def get_run(self, run_id: str):
            return {
                "run_id": run_id,
                "runtime_status": "completed",
                "publication_status": "published",
                "terminal_reason": "published",
                "report_available": True,
            }

        def get_recent_summary(self, run_id: str):
            return FakeFacade().recent_summary(
                actor=ActorContext(owner_id="ignored"),
                run_id=run_id,
            )

        def get_single_match_review(self, run_id: str):
            return FakeFacade().single_match_review(
                actor=ActorContext(owner_id="ignored"),
                run_id=run_id,
            )

    class Knowledge:
        def search(self, query: KnowledgeQuery):
            return KnowledgeSearchResult(
                query=query,
                provider="local-hybrid",
                hits=(
                    KnowledgeHit(
                        chunk_id="chunk-1",
                        parent_id=None,
                        content="private body that must not cross the facade",
                        score=1.0,
                        rank=1,
                        metadata=KnowledgeMetadata(
                            source_id="guide",
                            title="Vision guide",
                            version="1.0",
                        ),
                    ),
                ),
            )

    server = build_riftcoach_mcp_server(
        task_service=Tasks(),
        run_query=Runs(),
        knowledge_provider=Knowledge(),
        actor_provider=lambda: ActorContext(owner_id="owner-a"),
    )
    facade = server.facade
    actor = ActorContext(owner_id="owner-a")
    summary = facade.recent_summary(actor=actor, run_id=RUN_ID)
    single = facade.single_match_review(actor=actor, run_id=RUN_ID)
    knowledge = facade.knowledge_search(
        actor=actor,
        query="vision",
        top_k=3,
        filters={},
    )
    evaluation = facade.report_evaluation(actor=actor, run_id=RUN_ID)

    assert summary["run_id"] == RUN_ID
    assert summary["games_analyzed"] == 2
    assert single["review_sha256"] == "a" * 64
    assert calls == [
        ("owner-a", RUN_ID),
        ("owner-a", RUN_ID),
        ("owner-a", RUN_ID),
    ]
    assert knowledge["attributions"] == [{
        "chunk_id": "chunk-1",
        "source_id": "guide",
        "title": "Vision guide",
        "version": "1.0",
    }]
    assert "private body" not in repr(knowledge)
    assert evaluation == {
        "run_id": RUN_ID,
        "publication_status": "published",
        "evaluation_status": "passed",
        "score_available": False,
    }


def test_default_query_facade_fails_closed_before_query_on_owner_mismatch():
    query_calls: list[str] = []

    class TaskError(RuntimeError):
        code = "task_not_found"

    class Tasks:
        def get_task_by_run_id(self, *, owner_id: str, run_id: str):
            del run_id
            if owner_id != "owner-a":
                raise TaskError("private owner detail")
            return SimpleNamespace(run_id=RUN_ID)

    class Runs:
        def get_run(self, run_id: str):
            query_calls.append(run_id)
            return {}

        get_recent_summary = get_run
        get_single_match_review = get_run

    class Knowledge:
        def search(self, query: KnowledgeQuery):
            raise AssertionError(query)

    facade = QueryMcpApplicationFacade(
        task_service=Tasks(),
        run_query=Runs(),
        knowledge_provider=Knowledge(),
    )

    with pytest.raises(McpFacadeError) as caught:
        facade.recent_summary(
            actor=ActorContext(owner_id="owner-b"),
            run_id=RUN_ID,
        )
    assert caught.value.code == "not_found"
    assert query_calls == []
    assert "private owner detail" not in repr(caught.value)
