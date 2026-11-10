"""Preparation failures keep their category without exposing exception bodies."""
from dataclasses import replace
import socket

import pytest

from app.agent.draft import AgentDraftPreparationError, SkillAgentDraftPreparer
from app.agent.loop import AgentLoop
from app.harness.preparation_errors import DRAFT_PREPARATION_CODES, DraftPreparationError
from app.harness.runtime import ReviewHarness
from app.harness.store import FileRunStore
from app.product.coach_composition import build_coach_application
from tests.test_coach_application_composition import dependencies, product_request


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("diagnostic tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.mark.parametrize("code", sorted(DRAFT_PREPARATION_CODES))
def test_category_survives_agent_skill_harness_and_manifest(tmp_path, monkeypatch, code):
    def fail(self, *args, **kwargs):
        raise AgentDraftPreparationError("PRIVATE_REPORT_AND_REASONING", code=code)
    monkeypatch.setattr(SkillAgentDraftPreparer, "prepare", fail)
    deps = dependencies()
    result = build_coach_application(runs_root=tmp_path, **deps).review(
        product_request(), run_id="safe_preparation_category",
    )
    assert result.publication_status.value == "rejected"
    assert result.terminal_reason == "draft_preparation_failed"
    assert result.output.report is None
    manifest = FileRunStore(tmp_path, result.run_id).read_manifest()
    assert manifest.failure_code == code
    assert not deps["provider"].requests
    for path in tmp_path.rglob("*.json"):
        assert "PRIVATE_REPORT_AND_REASONING" not in path.read_text(encoding="utf-8")


def test_actual_agent_budget_stop_reaches_persistent_category(tmp_path, monkeypatch):
    original = AgentLoop.run
    def constrained(self, request, **kwargs):
        # Exercise the real pre-call guard, not a manually raised diagnostic.
        return original(self, replace(request, max_context_tokens=1), **kwargs)
    monkeypatch.setattr(AgentLoop, "run", constrained)
    deps = dependencies()
    result = build_coach_application(runs_root=tmp_path, **deps).review(
        product_request(), run_id="real_budget_guard",
    )
    assert result.terminal_reason == "draft_preparation_failed"
    assert FileRunStore(tmp_path, result.run_id).read_manifest().failure_code == "agent_context_budget_exceeded"
    assert not deps["provider"].requests


@pytest.mark.parametrize("value", ["private_payload", "a" * 128, {}, [], True, 7])
def test_unknown_or_non_string_code_is_rejected(value):
    with pytest.raises(ValueError, match="unsupported"):
        DraftPreparationError("private", code=value)


def test_legacy_unclassified_failure_and_untyped_spoof_do_not_add_codes():
    original = AgentDraftPreparationError("private")
    assert ReviewHarness._step_failure_reason("draft_preparation", original) == "draft_preparation_failed"
    forged = RuntimeError("private")
    forged.code = "agent_context_budget_exceeded"
    assert ReviewHarness._step_failure_reason("draft_preparation", forged) == "draft_preparation_failed"
    typed = DraftPreparationError("private", code="agent_loop_failed")
    typed.code = "PRIVATE_PAYLOAD"
    assert ReviewHarness._step_failure_reason("draft_preparation", typed) == "draft_preparation_failed"


def test_successful_tools_with_conflicting_identity_get_evidence_category(tmp_path):
    from app.rag.models import KnowledgeQuery
    from app.providers.models import ToolCall
    from tests.test_coach_contract_repair import GroundedProvider
    deps = dependencies()
    base = deps["knowledge_provider"]
    class ConflictingKnowledge:
        provider_name = "offline-conflicting-knowledge"
        calls = 0
        def search(self, query):
            self.calls += 1
            result = base.search(KnowledgeQuery(text="早期死亡", top_k=1))
            assert result.hits
            if self.calls > 1:
                result = replace(result, hits=(replace(result.hits[0], content="CHANGED_PRIVATE_CONTENT"),))
            return result
    class TwoSearches(GroundedProvider):
        def chat(self, request):
            response = super().chat(request)
            if response.tool_calls:
                return replace(response, tool_calls=tuple(
                    ToolCall(id=f"conflict-{i}", name="knowledge.search",
                             arguments={"query": "早期死亡", "top_k": i + 1}) for i in range(2)))
            return response
    deps.update(knowledge_provider=ConflictingKnowledge(),
                provider=TwoSearches(provider_name="zhipu", model_name="glm-5.3-flash"))
    result = build_coach_application(runs_root=tmp_path, **deps).review(product_request(), run_id="attribution_conflict")
    assert result.terminal_reason == "draft_preparation_failed"
    assert FileRunStore(tmp_path, result.run_id).read_manifest().failure_code == "knowledge_evidence_invalid"
    assert result.output.report is None
