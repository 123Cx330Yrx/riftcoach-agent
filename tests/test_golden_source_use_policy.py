"""Policy delivery and budget checks, not simulated semantic acceptance."""
import json

import pytest

from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY
from app.runtime.coach_contract import ADVICE_COACH_CONTRACT, FACT_COACH_CONTRACT
from scripts.check_coach_golden_replay import _ReplayProvider, probe
from tests.test_coach_application_composition import dependencies


@pytest.mark.parametrize("contract,expected", [(ADVICE_COACH_CONTRACT, True), (FACT_COACH_CONTRACT, False)])
def test_source_advice_policy_reaches_all_nine_requests_as_trusted_policy(monkeypatch, contract, expected):
    requests = []
    original = _ReplayProvider.chat
    def capture(self, request):
        requests.append(request)
        return original(self, request)
    monkeypatch.setattr(_ReplayProvider, "chat", capture)
    summary = dependencies()["summary_builder"].summary
    result = probe(summary, contract=contract, training_positions=())
    assert len(requests) == 9
    # Inspect the actual Context policy envelope; data is not promoted to policy.
    envelopes = [json.loads(message.content) for message in requests[0].messages]
    policy_sections = [section for item in envelopes for section in item["sections"]
                       if section["section_id"] == "candidate:policy_addendum"]
    assert len(policy_sections) == 1
    assert (SOURCE_USE_POLICY in policy_sections[0]["content"]) is expected
    for request in requests:
        raw = "\n".join(message.content or "" for message in request.messages)
        encoded = json.dumps(SOURCE_USE_POLICY, ensure_ascii=False)[1:-1]
        assert (SOURCE_USE_POLICY in raw or encoded in raw) is expected
    for request in requests[4:]:
        prompt = request.messages[-1].content
        if expected:
            assert prompt.index(SOURCE_USE_POLICY) < min(
                [prompt.index(marker) for marker in ("[DETERMINISTIC FACT PACK]", "[UNTRUSTED REVISION DATA-ONLY]") if marker in prompt])
    assert result["revision_count"] == 1
    assert result["terminal_reason"] == "evaluation_failed"
    assert result["report_available"] is False
    assert result["position_policy_present_by_call"] == [True] * 9
    limits = contract.descriptor()
    assert max(result["request_input_ceilings"]) <= limits["max_input_tokens"]
    assert sum(result["request_input_ceilings"]) + result["reserved_output_tokens"] <= limits["total_tokens"]


def test_previous_contract_and_resource_limits_remain_frozen():
    assert FACT_COACH_CONTRACT.snapshot().sha256 == "2f498babc867a984db82f4777064b2de82c42b40566aa35fea3b593b2c691c47"
    old, new = FACT_COACH_CONTRACT.descriptor(), ADVICE_COACH_CONTRACT.descriptor()
    for key in ("request_timeout_s", "agent_timeout_s", "execution_timeout_s", "max_calls", "max_tool_calls",
                "max_context_tokens", "max_input_tokens", "max_output_tokens", "total_tokens", "minimum_score", "max_revisions"):
        assert old[key] == new[key]
    assert not FACT_COACH_CONTRACT.source_use_policy
    assert ADVICE_COACH_CONTRACT.source_use_policy == SOURCE_USE_POLICY
