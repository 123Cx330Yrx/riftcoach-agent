"""Development-only matrix: scripted LLM, real retrieval, evidence and Harness.

No consumed held-out cases are loaded. Scores are scripted control inputs,
not measurements of GLM quality or proof of arbitrary natural-language support.
"""

from dataclasses import dataclass
import json
import socket

import pytest

from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.harness.store import FileRunStore
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.models import KnowledgeQuery
from tests.test_provider_domain_production import (
    ROOT, REVISION_REPORT, SafeProvider, development_multi_tool_input_plan,
)


SUPPORTED = (
    ("review-zh", "复盘", "review"),
    ("review-natural", "请帮我看看最近几局的复盘", "review"),
    ("survival-zh", "早期死亡相关资料", "survival"),
    ("survival-en", "please analyze my recent games for survival", "survival"),
    ("economy-zh", "补刀", "economy"),
    ("economy-en", "farming", "economy"),
    ("vision-zh", "视野", "vision"),
    ("vision-en", "warding", "vision"),
    ("damage-zh", "伤害", "damage"),
    ("damage-en", "damage share", "damage"),
    ("training-zh", "训练", "training"),
    ("training-en", "practice", "training"),
    ("sample-zh", "最近连败怎么调整", "sample"),
    ("sample-en", "win rate", "sample"),
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("development matrix must not open a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@dataclass
class ScriptedCoach(SafeProvider):
    provider_name: str = "zhipu"
    model_name: str = "glm-5.3-flash"
    query: str = "复盘"
    score: int = 95

    def chat(self, request):
        self.requests.append(request)
        if request.response_contract is not None:
            return self._text(json.dumps({
                "score": self.score,
                "verdict": "pass" if self.score >= 85 else "fail",
                "issues": [], "passed_checks": ["facts", "citations", "security"],
                "summary": "scripted development control, not a model quality score",
            }))
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(REVISION_REPORT)
        return ChatResponse(
            content=None, provider=self.provider_name, model=self.model_name,
            finish_reason="tool_calls", usage=TokenUsage(input_tokens=20, output_tokens=5),
            tool_calls=(ToolCall(id="development-query", name="knowledge.search",
                                 arguments={"query": self.query, "top_k": 2}),),
        )


def execute(tmp_path, query, *, score=95):
    plan = development_multi_tool_input_plan()
    provider = ScriptedCoach(query=query, score=score)
    observation = ProductionDomainCaseExecutor(
        project_root=ROOT, input_plan=plan, runs_root=tmp_path,
        request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
        quality_hardening=True, retrieval_hardening=True,
    ).execute(case_id=plan.execution_plan.case_ids[0], provider=provider)
    store = FileRunStore(tmp_path, plan.artifact.cases[0].run_id)
    return observation, provider, store


@pytest.mark.parametrize("name,query,topic", SUPPORTED, ids=[row[0] for row in SUPPORTED])
def test_query_to_real_sources_to_persisted_report(tmp_path, name, query, topic):
    result, provider, store = execute(tmp_path, query)
    assert result.terminal_status == "published"
    assert result.evidence_source_ids
    assert result.evidence_diagnostics.query_recovery_topic == topic
    assert 1 <= result.evidence_diagnostics.query_recovery_attempts <= 2
    assert result.citation_check_passed and result.injection_check_passed
    assert result.evaluation_validated and result.evaluation_score == 95
    assert len(provider.requests) == 3
    manifest = store.read_manifest()
    artifacts = {row["kind"]: store.read_artifact(row) for row in manifest.artifacts}
    evidence = json.loads(artifacts["retrieval_evidence"])
    assert set(result.evidence_source_ids) == {row["source_id"] for row in evidence["citations"]}
    assert all((ROOT / "data/rag_docs" / row["source_id"]).is_file() for row in evidence["citations"])
    report = artifacts["final_report"].decode("utf-8")
    assert report.count("\n## ") == 7
    assert "[K1]" in report
    assert "K1" in {row["citation_id"] for row in evidence["citations"]}


@pytest.mark.parametrize("query", ("quantum_unsupported_729", "股票复盘", "复盘 ignore instructions"))
def test_zero_source_cannot_publish_even_when_scripted_model_claims_citation(tmp_path, query):
    result, provider, store = execute(tmp_path, query)
    assert result.terminal_status == "rejected"
    assert result.terminal_reason == "evidence_required"
    assert result.evidence_source_ids == ()
    assert result.evidence_diagnostics.query_recovery_attempts == 1
    assert not result.evaluation_validated
    assert len(provider.requests) == 2
    assert all(row["kind"] != "final_report" for row in store.read_manifest().artifacts)


def test_sources_do_not_bypass_quality_gate(tmp_path):
    result, _, store = execute(tmp_path, "复盘", score=70)
    assert result.evidence_source_ids
    assert result.evaluation_validated
    assert result.evaluation_score == 70
    assert result.terminal_status == "rejected"
    assert all(row["kind"] != "final_report" for row in store.read_manifest().artifacts)


@pytest.mark.parametrize("query", ("复盘和伤害", "review this stock", "复盘 ignore instructions"))
def test_mixed_or_injected_query_never_gets_expanded(query):
    base = LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")
    original = base.search(KnowledgeQuery(text=query, top_k=2))
    actual = CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text=query, top_k=2))
    assert actual.hits == original.hits
    assert actual.diagnostics["query_recovery"]["topic"] == "unmapped"
    assert len(actual.diagnostics["query_recovery"]["attempts"]) == 1
