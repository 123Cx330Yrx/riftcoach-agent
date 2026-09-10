"""Verify facts actually sent to every evaluator/reviser, without real I/O."""
import copy
import json

import pytest

from app.evaluation.coach_report import build_fact_pack
from app.runtime.coach_contract import FACT_COACH_CONTRACT, POSITION_COACH_CONTRACT, ADVICE_COACH_CONTRACT
from scripts.check_coach_golden_replay import probe, _ReplayProvider
from tests.test_coach_application_composition import dependencies


@pytest.mark.parametrize("contract,expected", [(FACT_COACH_CONTRACT, True), (POSITION_COACH_CONTRACT, False), (ADVICE_COACH_CONTRACT, True)])
def test_generation_facts_survive_evaluation_correction_revision_and_recheck(monkeypatch, contract, expected):
    value = dependencies()["summary_builder"].summary
    value["metadata"]["generated_at_utc"] = "2026-09-01T12:34:56+00:00"
    value["matches"][0]["damage_share"] = 0.2345
    value["matches"][1]["damage_share"] = 0.2876
    original = copy.deepcopy(value)
    # Document the real projection omission, not an invented model hallucination.
    reduced = build_fact_pack(value)
    assert "metadata" not in reduced
    assert "damage_share" not in reduced["matches"][0]
    requests = []
    original_chat = _ReplayProvider.chat

    def capture(self, request):
        requests.append(request)
        return original_chat(self, request)

    monkeypatch.setattr(_ReplayProvider, "chat", capture)
    result = probe(value, contract=contract, training_positions=())
    review_facts = []
    for request in requests:
        prompt = request.messages[-1].content
        if request.response_contract:
            facts = json.loads(prompt.split("[DETERMINISTIC FACT PACK]\n", 1)[1]
                               .split("[DRAFT REPORT TO REVIEW]", 1)[0])
            review_facts.append(facts.get("generation_facts"))
        elif "[UNTRUSTED REVISION DATA-ONLY]\n" in prompt:
            data = json.loads(prompt.split("[UNTRUSTED REVISION DATA-ONLY]\n", 1)[1])
            review_facts.append(data["knowledge"].get("generation_facts"))
    generation_facts = {}
    for message in requests[0].messages:
        envelope = json.loads(message.content)
        for section in envelope["sections"]:
            if section["section_id"].startswith("facts:") and section["section_id"] != "facts:deterministic_report":
                generation_facts[section["section_id"]] = json.loads(section["content"])
    assert generation_facts["facts:scope"]["metadata"]["generated_at_utc"] == original["metadata"]["generated_at_utc"]
    assert generation_facts["facts:recent_match:00"]["damage_share"] == 0.2345
    assert len(review_facts) == 5  # evaluation + correction, revision, evaluation + correction
    assert review_facts == ([generation_facts] * 5 if expected else [None] * 5)
    assert value == original
    assert result["scripted_provider_calls"] == 9
    assert result["terminal_reason"] == "evaluation_failed"
    assert not result["report_available"]
    assert result["position_policy_present_by_call"] == [True] * 9
    limits = contract.descriptor()
    assert max(result["request_input_ceilings"]) <= limits["max_input_tokens"]
    assert sum(result["request_input_ceilings"]) + result["reserved_output_tokens"] <= limits["total_tokens"]


def test_fact_parity_does_not_rewrite_previous_identity_or_resource_limits():
    assert POSITION_COACH_CONTRACT.snapshot().sha256 == "fb6df08655395d17e85be097b5a4cd859e18c8bee22b98167329892da4d2246f"
    old, new = POSITION_COACH_CONTRACT.descriptor(), FACT_COACH_CONTRACT.descriptor()
    for key in ("request_timeout_s", "agent_timeout_s", "execution_timeout_s", "max_calls", "max_tool_calls",
                "max_context_tokens", "max_input_tokens", "max_output_tokens", "total_tokens", "minimum_score", "max_revisions"):
        assert old[key] == new[key]
