"""Offline policy delivery checks for the opt-in 1.3.6 compact report seam."""

import json

from app.evaluation.golden_compact_report_policy import COMPACT_REPORT_POLICY
from app.evaluation.golden_position_policy import POSITION_POLICY
from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY
from app.runtime.coach_contract import (
    ADVICE_COACH_CONTRACT,
    COMPACT_COACH_CONTRACT,
)
from scripts.check_coach_golden_replay import _ReplayProvider, probe
from tests.test_coach_application_composition import dependencies


def _requests(monkeypatch):
    captured = []
    original = _ReplayProvider.chat

    def capture(self, request):
        captured.append(request)
        return original(self, request)

    monkeypatch.setattr(_ReplayProvider, "chat", capture)
    return captured


def _request_text(request):
    return "\n".join(message.content or "" for message in request.messages)


def test_compact_policy_reaches_generation_evaluation_and_revision_calls(monkeypatch):
    requests = _requests(monkeypatch)
    result = probe(
        dependencies()["summary_builder"].summary,
        contract=COMPACT_COACH_CONTRACT,
        training_positions=(),
    )

    assert len(requests) == 9
    assert result["revision_count"] == 1
    assert result["terminal_reason"] == "evaluation_failed"
    assert result["report_available"] is False

    texts = [_request_text(request) for request in requests]
    envelopes = [json.loads(message.content) for message in requests[0].messages]
    sections = [s for e in envelopes for s in e["sections"]
                if s["section_id"] == "candidate:policy_addendum"]
    assert len(sections) == 1
    for policy in (COMPACT_REPORT_POLICY, SOURCE_USE_POLICY, POSITION_POLICY):
        assert policy in sections[0]["content"]
        encoded = json.dumps(policy, ensure_ascii=False)[1:-1]
        assert all(policy in text or encoded in text for text in texts)
        for request in requests[4:]:
            prompt = request.messages[-1].content
            assert prompt.index(policy) < min(prompt.index(marker) for marker in
                ("[DETERMINISTIC FACT PACK]", "[UNTRUSTED REVISION DATA-ONLY]") if marker in prompt)

    # Evaluation/revision prompts carry the separately named generation and
    # deterministic fact projections.  This checks delivery without exposing
    # their data values or treating the replay as semantic acceptance.
    assert all('"generation_facts"' in text for text in texts[4:])
    assert all('"deterministic_source_facts"' in text for text in texts[4:])


def test_advice_contract_is_frozen_and_compact_changes_only_declared_identity():
    assert ADVICE_COACH_CONTRACT.snapshot().sha256 == (
        "ad83fbff7dd2b49e253d8698a649c632b50bd7062cacc54277eb7c5e7dd26e0d"
    )
    old = ADVICE_COACH_CONTRACT.descriptor()
    new = COMPACT_COACH_CONTRACT.descriptor()
    allowed = {
        "version",
        "skill_version",
        "program_version",
        "context_policy_sha256",
        "compact_report_policy_id",
    }
    changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
    assert changed <= allowed
    assert new["compact_report_policy_id"]
    for key in set(old) & set(new) - allowed:
        assert old[key] == new[key]


def test_compact_replay_keeps_the_existing_resource_budget():
    result = probe(
        dependencies()["summary_builder"].summary,
        contract=COMPACT_COACH_CONTRACT,
        training_positions=(),
    )
    old, new = ADVICE_COACH_CONTRACT.descriptor(), COMPACT_COACH_CONTRACT.descriptor()
    for key in (
        "request_timeout_s",
        "agent_timeout_s",
        "execution_timeout_s",
        "max_calls",
        "max_tool_calls",
        "max_context_tokens",
        "max_input_tokens",
        "max_output_tokens",
        "total_tokens",
        "minimum_score",
        "max_revisions",
    ):
        assert new[key] == old[key]
    assert max(result["request_input_ceilings"]) <= new["max_input_tokens"]
    assert (
        sum(result["request_input_ceilings"]) + result["reserved_output_tokens"]
        <= new["total_tokens"]
    )
