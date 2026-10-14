"""Golden-only context budget, complete RAG, and immutable earlier contracts."""
import json
from dataclasses import replace

import pytest

from app.product.coach_composition import build_coach_application
from app.runtime.coach_contract import BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT
from scripts.check_coach_golden_replay import ROOT, probe
from tests.test_coach_application_composition import dependencies, product_request


def summary():
    return json.loads((ROOT / "examples/fixtures/player_summary_demo.json").read_text(encoding="utf-8"))


def test_full_eight_tool_nine_call_path_remains_bounded_and_low_score_rejected():
    result = probe(summary())
    limits = GOLDEN_COACH_CONTRACT.descriptor()
    assert result["scripted_provider_calls"] == 9
    assert result["revision_count"] == 1
    assert result["terminal_reason"] == "evaluation_failed"
    assert not result["report_available"]
    assert result["agent"][0]["successful_tool_calls"] == 8
    assert result["agent"][0]["agent_stop_reason"] == "final_response"
    assert max(result["request_input_ceilings"]) <= limits["max_input_tokens"]
    assert sum(result["request_input_ceilings"]) + result["reserved_output_tokens"] <= limits["total_tokens"]
    assert result["network_used"] is False and result["external_provider_calls"] == 0


def test_retained_thinking_counts_toward_budget_without_leaking_it():
    result = probe(summary(), reasoning_characters=100000)
    assert result["scripted_provider_calls"] == 1
    assert result["failure_code"] == "agent_context_budget_exceeded"
    assert not result["report_available"]
    assert "x" * 20 not in json.dumps(result)


def test_old_batch_identity_and_total_walls_remain_frozen():
    assert BATCH_COACH_CONTRACT.snapshot().sha256 == "f8fb878e1d94b4251a990db337d0adaf6a354417890ac296dcd9a83e04fd0e66"
    old, new = BATCH_COACH_CONTRACT.descriptor(), GOLDEN_COACH_CONTRACT.descriptor()
    for name in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "max_tool_calls", "minimum_score", "max_revisions"):
        assert old[name] == new[name]
    assert new["max_context_tokens"] == 28000
    assert "max_context_tokens: 16000" in (ROOT / "examples/runtime_profiles/flash_v2_batch/skills/recent-form-review/manifest.yaml").read_text(encoding="utf-8")


def test_new_application_binds_distinct_skill_program_and_trace(tmp_path):
    app = build_coach_application(**dependencies(), runs_root=tmp_path,
                                  compact_context_json=True, coach_contract=GOLDEN_COACH_CONTRACT)
    result = app.review(product_request(), run_id="golden_new_binding")
    assert result.publication_status.value == "published"
    from app.runtime.store import RuntimeTraceStore
    trace = RuntimeTraceStore(tmp_path, result.run_id).read_trace(result.trace_reference)
    assert trace.identity.skill_version == "0.5.0"
    assert trace.identity.prompt_profile_version == "2.3.0"
    assert trace.identity.coach_contract == GOLDEN_COACH_CONTRACT.snapshot()
    assert trace.policy.max_context_tokens == 28000


@pytest.mark.parametrize("contract", [None, replace(GOLDEN_COACH_CONTRACT)])
def test_untrusted_contract_does_not_select_assets(tmp_path, contract):
    deps = dependencies()
    with pytest.raises(ValueError, match="explicit supported"):
        build_coach_application(**deps, runs_root=tmp_path, coach_contract=contract)
    assert not deps["provider"].requests
