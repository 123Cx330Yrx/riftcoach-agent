import json
from pathlib import Path


ADMISSION_PATH = Path(
    "data/evaluation/results/mcp/opgg_meta_admission_v1.json"
)


def load_admission() -> dict:
    return json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))


def test_opgg_admission_fixture_freezes_official_mcp_identity() -> None:
    admission = load_admission()

    assert admission["schema_version"] == "1.0"
    assert admission["candidate"] == {
        "repository": "https://github.com/opgginc/opgg-mcp",
        "repository_head": "039904bf655927402c28717c12bb51fe949e2d61",
        "endpoint": "https://mcp-api.op.gg/mcp",
        "repository_license": "MIT",
    }
    assert admission["initialize"] == {
        "http_status": 200,
        "content_type": "application/json",
        "protocol_version": "2025-06-18",
        "server_name": "OP.GG MCP Server",
        "server_version": "1.0.0",
        "tools_capability": True,
        "session_header_present": True,
    }


def test_lane_meta_snapshot_records_the_observed_contract_without_raw_body() -> None:
    admission = load_admission()
    tool = admission["selected_tool"]

    assert admission["catalog"]["lol_tool_count"] == 18
    assert admission["catalog"]["all_lol_tools_have_output_schema"] is False
    assert tool["name"] == "lol_list_lane_meta_champions"
    assert tool["annotations"] == {
        "read_only": True,
        "destructive": False,
        "idempotent": True,
        "open_world": False,
    }
    assert tool["required_arguments"] == ["desired_output_fields"]
    assert set(tool["argument_names"]) == {
        "lang",
        "position",
        "desired_output_fields",
    }
    assert tool["output_schema_present"] is False
    assert tool["observed_result"] == {
        "content_types": ["text"],
        "structured_content_present": False,
        "current_patch_present": False,
        "source_generated_at_present": False,
        "expires_at_or_ttl_present": False,
        "raw_body_persisted": False,
    }


def test_missing_contracts_force_restricted_partial_provenance() -> None:
    admission = load_admission()
    failed = {
        gate["id"]
        for gate in admission["gates"]
        if gate["status"] == "fail"
    }

    assert {
        "selected_tool_output_schema",
        "structured_result",
        "current_patch_identity",
        "source_freshness",
        "rate_limit_contract",
        "underlying_data_terms",
    }.issubset(failed)
    assert admission["decision"] == {
        "status": "admitted_with_restrictions",
        "reason": "opgg_mcp_reachable_partial_provenance",
        "adapter_implementation_allowed": True,
        "meta_facts_may_enter_context": True,
        "next_checkpoint_blocked": False,
        "allowed_use": ["current_snapshot_recommendation"],
        "forbidden_use": [
            "exact_patch_attribution",
            "historical_patch_comparison",
            "upstream_freshness_claim",
        ],
    }


def test_admission_fixture_is_body_free_and_contains_no_session_or_player_data() -> None:
    admission = load_admission()
    serialized = json.dumps(admission, ensure_ascii=False).lower()

    for forbidden in (
        "mcp-session-id",
        "session_id",
        "raw_response",
        "raw_result",
        "content_text",
        "puuid",
        "api_key",
        "authorization",
    ):
        assert forbidden not in serialized
    assert admission["external_io"] == {
        "initialize_calls": 1,
        "initialized_notifications": 1,
        "tools_list_calls": 3,
        "tools_call_calls": 1,
        "session_delete_attempts": 1,
        "session_delete_http_status": 405,
        "riot_calls": 0,
        "llm_provider_calls": 0,
        "key_reads": 0,
    }
