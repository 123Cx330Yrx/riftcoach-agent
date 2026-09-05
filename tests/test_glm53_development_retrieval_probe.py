import json
from pathlib import Path
import socket

import pytest

from scripts.probe_glm53_development_retrieval import (
    QueryObserver, development_plan, main, observe,
)
from tests.test_coaching_retrieval_development_chain import ScriptedCoach
from tests.test_provider_domain_production import ROOT
from app.providers.models import ChatMessage, ChatRequest, MessageRole


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
    assert development_plan(ROOT).artifact.dataset_id == "demo-development-not-heldout"
    for forbidden in ('"content"', '"reasoning"', '"api_key"', '"user_utterance"', '"arguments"'):
        assert forbidden not in json.dumps(report)


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
