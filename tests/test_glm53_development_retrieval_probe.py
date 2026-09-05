import json
from pathlib import Path
import socket

import pytest

from scripts.probe_glm53_development_retrieval import (
    QueryObserver, development_plan, main, observe,
)
from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from tests.test_coaching_retrieval_development_chain import ScriptedCoach
from tests.test_provider_domain_production import ROOT
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1
from app.skills.review_executor import SkillReviewExecutionError


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline probe tests must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_observer_retains_safe_diagnostics_but_does_not_rewrite_model_query():
    provider = ScriptedCoach(query="private-query-5831")
    observer = QueryObserver(provider)
    response = observer.chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "development"),)))
    assert response.tool_calls[0].arguments["query"] == "private-query-5831"
    assert observer.queries[0]["topic"] == "unmapped"
    assert "private-query-5831" not in json.dumps(observer.queries)


def test_development_observation_uses_real_chain_and_no_heldout(tmp_path):
    report = observe(ScriptedCoach(), root=ROOT, runs_root=tmp_path)
    assert report["evidence_origin"] == "offline_fake"
    assert not report["network_used"]
    assert report["resources"]["calls_used"] == 3
    assert report["observation"]["terminal_status"] == "published"
    assert report["observation"]["evidence_source_ids"]
    assert report["queries"][0]["topic"] == "review"
    assert report["production_admitted"] is False
    assert report["retrieval_guidance_id"] is None
    assert report["retrieval_guidance_sha256"] is None
    assert development_plan(ROOT).artifact.dataset_id == "demo-development-not-heldout"
    for forbidden in ('"content"', '"reasoning"', '"api_key"', '"user_utterance"', '"arguments"'):
        assert forbidden not in json.dumps(report)


def test_guidance_is_an_explicit_candidate_context_addendum(tmp_path):
    with pytest.raises(ValueError, match="requires retrieval hardening"):
        ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=development_plan(ROOT),
            runs_root=tmp_path,
            request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
            quality_hardening=True,
            retrieval_guidance=COACHING_QUERY_GUIDANCE_V1,
        )
    report = observe(
        ScriptedCoach(), root=ROOT, runs_root=tmp_path,
        retrieval_guidance=COACHING_QUERY_GUIDANCE_V1,
    )
    assert report["observation"]["terminal_status"] == "published"
    assert report["retrieval_guidance_id"] == "coaching-query-guidance-v1"
    assert report["retrieval_guidance_sha256"]


def test_terminal_projection_failure_retains_safe_diagnostics(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise SkillReviewExecutionError("private model response must not leak")
    monkeypatch.setattr(ProductionDomainCaseExecutor, "execute", broken)
    report = observe(ScriptedCoach(), root=ROOT, runs_root=tmp_path)
    assert report["execution_error"] == "terminal_output_validation_failed"
    assert report["observation"] is None
    assert report["resources"]["calls_used"] == 0
    assert "private model response" not in json.dumps(report)


def test_real_flag_required_before_environment_and_output(tmp_path):
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(SystemExit):
        main(["--implementation-sha", "a" * 40, "--env-file", str(tmp_path / "absent.env"),
              "--output", str(output)])
    assert not output.exists()


def test_persisted_development_observation_has_no_invented_query_or_admission():
    path = ROOT / "data/evaluation/results/development/glm53_autonomous_retrieval_dev_01.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["scope"] == "development_not_admission"
    assert report["resources"]["calls_used"] == 2
    assert len(report["queries"]) == 2
    assert report["observation"]["evidence_source_ids"] == []
    assert report["observation"]["terminal_reason"] == "evidence_required"
    assert not report["production_admitted"]
    for query in report["queries"]:
        assert set(query) == {"shape", "topic", "recognized_topics", "character_count", "term_count", "filter_names"}
    assert report["probe_sha256"]
