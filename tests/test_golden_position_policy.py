"""Offline integration checks are policy delivery evidence, not model quality."""
import pytest

from app.runtime.coach_contract import LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT
from scripts.check_coach_golden_replay import probe
from tests.test_coach_application_composition import dependencies


@pytest.mark.parametrize("goals", [(), ("mid", "support"), ("jungle",)])
def test_position_rules_reach_draft_evaluation_repair_revision_and_recheck(goals):
    result = probe(dependencies()["summary_builder"].summary,
                   contract=POSITION_COACH_CONTRACT, training_positions=goals)
    assert result["scripted_provider_calls"] == 9
    assert result["position_policy_present_by_call"] == [True] * 9
    assert result["revision_count"] == 1
    assert result["terminal_reason"] == "evaluation_failed"
    assert result["report_available"] is False
    assert result["external_provider_calls"] == 0
    limits = POSITION_COACH_CONTRACT.descriptor()
    assert max(result["request_input_ceilings"]) <= limits["max_input_tokens"]
    assert sum(result["request_input_ceilings"]) + result["reserved_output_tokens"] <= limits["total_tokens"]


def test_previous_latency_contract_remains_reproducible_without_new_policy():
    assert LATENCY_COACH_CONTRACT.snapshot().sha256 == "67ae847819a64dc009e448b518e0fe3564bd395dfc4aed34aff3509cd2b854cc"
    result = probe(dependencies()["summary_builder"].summary, contract=LATENCY_COACH_CONTRACT)
    assert result["position_policy_present_by_call"] == [False] * 9
    old, new = LATENCY_COACH_CONTRACT.descriptor(), POSITION_COACH_CONTRACT.descriptor()
    for key in ("request_timeout_s", "agent_timeout_s", "execution_timeout_s", "max_calls",
                "max_tool_calls", "max_context_tokens", "max_input_tokens", "max_output_tokens",
                "total_tokens", "minimum_score", "max_revisions"):
        assert old[key] == new[key]
