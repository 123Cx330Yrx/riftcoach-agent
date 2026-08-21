import json
from datetime import datetime
from pathlib import Path


SCRIPT = Path("scripts/run_opgg_meta_smoke.py")
RESULT = Path("data/evaluation/results/mcp/opgg_meta_product_smoke_v1.json")


def test_opgg_real_smoke_requires_explicit_execute_and_persists_body_free_shape() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "if not args.execute" in source
    assert "refusing external I/O without --execute" in source
    assert '"body_free": True' in source
    assert '"upstream_patch": evidence.upstream_patch' in source
    assert '"riot_calls": 0' in source
    assert '"llm_provider_calls": 0' in source
    assert '"key_reads": 0' in source
    for forbidden in (
        "Mcp-Session-Id",
        "section.content",
        "evidence.facts[",
        "api_key",
        "authorization",
    ):
        assert forbidden not in source


def test_persisted_opgg_product_smoke_is_successful_bounded_and_body_free() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert result["schema_version"] == "1.0"
    assert result["result"] == "passed"
    assert result["body_free"] is True
    assert result["protocol"] == {
        "server_name": "OP.GG MCP Server",
        "server_version": "1.0.0",
        "tools_capability": True,
        "version": "2025-06-18",
    }
    assert result["catalog"]["admitted_tool_count"] == 1
    assert result["catalog"]["selected_tool"] == "lol_list_lane_meta_champions"
    assert result["catalog"]["selected_tool_output_schema_present"] is False
    assert result["evidence"]["provenance"] == "partial"
    assert result["evidence"]["fact_count"] == 3
    assert result["evidence"]["upstream_patch"] is None
    assert result["evidence"]["source_generated_at"] is None
    assert datetime.fromisoformat(result["evidence"]["expires_at"]) > datetime.fromisoformat(
        result["evidence"]["retrieved_at"]
    )
    assert result["context"] == {
        "instructional": False,
        "message_role": "user",
        "required": False,
        "section_id": f"meta:opgg:{result['evidence']['digest'][:16]}",
        "trust": "external_meta_evidence",
    }
    assert result["external_io"] == {
        "key_reads": 0,
        "llm_provider_calls": 0,
        "opgg_tools_call_calls": 1,
        "riot_calls": 0,
    }
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "mcp-session-id",
        "session_id",
        "raw_response",
        "raw_result",
        "content_text",
        "puuid",
        "api_key",
        "authorization",
        "nasus",
        "cho'gath",
    ):
        assert forbidden not in serialized
