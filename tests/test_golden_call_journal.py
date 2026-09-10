import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_journal import GoldenCallJournal, JournaledProvider


def test_reservation_is_create_only_and_attempt_is_durable_before_io(tmp_path):
    directory = tmp_path / "unique"
    ledger = GoldenCallJournal(directory, identity={"run_id": "unique"}, limits={"provider": 1})
    with pytest.raises(FileExistsError):
        GoldenCallJournal(directory, identity={"run_id": "other"}, limits={"provider": 9})
    def fail(request):
        assert json.loads((directory / "provider-001.json").read_text(encoding="utf-8"))["ordinal"] == 1
        raise RuntimeError("private provider payload")
    with pytest.raises(RuntimeError):
        JournaledProvider(SimpleNamespace(chat=fail), ledger).chat(object())
    assert ledger.counts["provider"] == 1
    with pytest.raises(ValueError, match="budget_exceeded"):
        ledger.reserve("provider")
    ledger.finish("failed")
    assert json.loads((directory / "terminal.json").read_text(encoding="utf-8"))["attempt_counts"] == {"provider": 1}
    assert "private" not in "".join(p.read_text(encoding="utf-8") for p in directory.glob("*.json"))


def test_failed_attempt_write_prevents_provider_call(tmp_path, monkeypatch):
    import app.evaluation.golden_journal as module
    ledger = GoldenCallJournal(tmp_path / "unique", identity={}, limits={"provider": 1})
    calls = []
    def fail(*args):
        raise OSError("disk failure")
    monkeypatch.setattr(module, "write_new_json", fail)
    with pytest.raises(OSError):
        JournaledProvider(SimpleNamespace(chat=lambda request: calls.append(request)), ledger).chat(object())
    assert not calls
    assert ledger.counts["provider"] == 0


def test_real_entry_reserves_failure_and_refuses_repeat_before_clients(tmp_path, monkeypatch):
    import app.evaluation.coach_real_data_golden_slice as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    clients = []
    monkeypatch.setattr(module, "RiotClient", lambda **kwargs: clients.append(kwargs))
    config = module.GoldenSliceConfig(riot_id="Offline#TEST", routing_region="asia", run_id="reserved_before_io")
    with pytest.raises(RuntimeError, match="riot_key_missing"):
        module.run_golden_slice(config, environ={})
    with pytest.raises(FileExistsError):
        module.run_golden_slice(config, environ={"RIOT_API_KEY": "offline"})
    assert not clients
    terminal = tmp_path / "data/runs/golden_slice_reservations/reserved_before_io/terminal.json"
    assert json.loads(terminal.read_text(encoding="utf-8"))["state"] == "failed"


def test_riot_attempt_budget_applies_before_session_request(monkeypatch):
    from app.lol.riot_client import RiotClient
    client = RiotClient(api_key="offline-key", region="asia",
                        before_request=lambda: (_ for _ in ()).throw(ValueError("budget_exceeded")))
    calls = []
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="budget_exceeded"):
        client.get_match_detail("OFFLINE_1")
    assert not calls
    client.session.close()


def test_golden_empty_ranked_history_stops_before_unfiltered_or_source_requests(tmp_path, monkeypatch):
    import app.evaluation.coach_real_data_golden_slice as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    queues = []
    class EmptyClient:
        def get_account_by_riot_id(self, game_name, tag_line):
            return {"puuid": "offline", "gameName": game_name, "tagLine": tag_line}
        def get_recent_match_ids(self, puuid, count, queue):
            queues.append(queue)
            assert queue == 420
            return []
    monkeypatch.setattr(module, "RiotClient", lambda **kwargs: EmptyClient())
    monkeypatch.setattr(module, "GoldenMatchStaticData", lambda **kwargs: SimpleNamespace(version=None, language="zh_CN"))
    with pytest.raises(ValueError, match="golden_valid_matches_unavailable"):
        module.run_golden_slice(module.GoldenSliceConfig(
            riot_id="Offline#TEST", routing_region="asia", run_id="empty_ranked_history",
        ), environ={"RIOT_API_KEY": "offline"})
    assert queues == [420]
    state = tmp_path / "data/runs/golden_slice_reservations/empty_ranked_history/terminal.json"
    counts = json.loads(state.read_text(encoding="utf-8"))["attempt_counts"]
    assert counts["official_patch"] == counts["provider"] == counts["opgg_tool"] == 0


def test_golden_entry_reads_exact_trace_and_counts_actual_provider_attempts(tmp_path, monkeypatch):
    import copy
    import socket
    import openai
    import app.evaluation.coach_real_data_golden_slice as module
    from app.providers.zhipu import ZhipuProvider
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from tests.test_coach_application_composition import dependencies
    deps = dependencies()
    summary = deps["summary_builder"].summary
    for index, row in enumerate(summary["matches"]):
        row.update(game_version="16.17.100.1", queue_id=420, champion_id=index + 1)
    def forbidden(*args, **kwargs):
        raise AssertionError("golden entry integration is offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    monkeypatch.setattr(module, "RiotClient", lambda **kwargs: object())
    # Protocol/CI validation has its own gate tests; this offline integration
    # exercises the real application, Trace and publication consumers.
    monkeypatch.setattr(module, "verify_real_evidence", lambda *args, **kwargs: SimpleNamespace(model_dump=lambda **kwargs: {}))
    monkeypatch.setattr(module, "GoldenMatchStaticData", lambda **kwargs: object())
    monkeypatch.setattr(module, "build_player_summary", lambda **kwargs: copy.deepcopy(summary))
    monkeypatch.setattr(module, "_official_patch", lambda **kwargs: None)
    monkeypatch.setattr(module, "_ddragon_snapshot", lambda *args: None)
    monkeypatch.setattr(module, "load_zhipu_settings", lambda env: SimpleNamespace(
        api_key="offline", base_url="https://open.bigmodel.cn/api/paas/v4", default_timeout_s=1, model="glm-5.3-flash"))
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: object())
    http_clients = []
    http_factory = openai.DefaultHttpxClient
    def capture_http_client(**kwargs):
        client = http_factory(**kwargs)
        http_clients.append(client)
        return client
    monkeypatch.setattr(openai, "DefaultHttpxClient", capture_http_client)
    monkeypatch.setattr(ZhipuProvider, "from_candidate_profile", lambda **kwargs: deps["provider"])
    monkeypatch.setattr(LocalHybridKnowledgeProvider, "from_directory", lambda directory: deps["knowledge_provider"])
    receipt = module.run_golden_slice(module.GoldenSliceConfig(
        riot_id="Offline#TEST", routing_region="asia", run_id="exact_trace_counter", with_provider=True,
    ), environ={"RIOT_API_KEY": "offline"}, opgg_fetcher=lambda **kwargs: None)
    assert receipt.provider_calls == len(deps["provider"].requests) == 5
    assert len(http_clients) == 1 and http_clients[0].is_closed
    assert receipt.coach_terminal_reason == "quality_gate_passed"
    assert receipt.result == "degraded" and not receipt.production_admitted
    assert receipt.evidence_projection_verified and not receipt.workbench_projection_verified
    assert receipt.coach_contract.version == "1.3.5"
    first_prompt = "\n".join(message.content or "" for message in deps["provider"].requests[0].messages)
    assert "外部来源事实" in first_prompt and receipt.evidence_bundle_digest in first_prompt
    assert "live_workbench_not_verified" in receipt.limitations
    state = tmp_path / "data/runs/golden_slice_reservations/exact_trace_counter"
    assert json.loads((state / "terminal.json").read_text(encoding="utf-8"))["attempt_counts"]["provider"] == 5
    assert len(list(state.glob("http-*.json"))) == 5
    assert all(json.loads(path.read_text())["http_requests"] == 0
               for path in state.glob("http-*.json"))
    from app.evaluation.golden_saved_input import load_saved_summary
    saved_args = dict(run_id=receipt.run_id, expected_digest=receipt.summary_digest,
                      riot_id=summary["player"]["riot_id"], routing_region="asia", count=summary["request"]["count"], queue=420)
    restored, observed = load_saved_summary(tmp_path / "data/runs/golden_slice", **saved_args)
    assert restored == summary and observed.isoformat().startswith(summary["metadata"]["generated_at_utc"][:19])
    with pytest.raises(ValueError, match="digest_mismatch"):
        load_saved_summary(tmp_path / "data/runs/golden_slice", **{**saved_args, "expected_digest": "0" * 64})
    with pytest.raises(ValueError, match="request_mismatch"):
        load_saved_summary(tmp_path / "data/runs/golden_slice", **{**saved_args, "riot_id": "SomeoneElse#TEST"})
    with pytest.raises(ValueError, match="region_mismatch"):
        load_saved_summary(tmp_path / "data/runs/golden_slice", **{**saved_args, "routing_region": "europe"})
    input_path = tmp_path / "data/runs/golden_slice" / receipt.run_id / "inputs/player_summary.json"
    input_path.write_bytes(input_path.read_bytes() + b" ")
    from app.evidence.publication import EvidencePublicationIntegrityError
    with pytest.raises(EvidencePublicationIntegrityError):
        load_saved_summary(tmp_path / "data/runs/golden_slice", **saved_args)
