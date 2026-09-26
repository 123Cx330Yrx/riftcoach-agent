"""Task-specific edits on the existing bounded observation/receipt runner."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation import source_patch_editor as editor
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE as PROFILE
from scripts import run_source_patch_pair as runner
from scripts.run_review_model_comparison import observe
from tests.test_review_model_comparison import decision
from tests.test_independent_edit_pair import provider_for


def response(edits):
    return ChatResponse(provider="zhipu", model=PROFILE.model, content=None, finish_reason="tool_calls",
        tool_calls=(ToolCall(id="call_1", name=editor.SUBMIT_TOOL, arguments={"edits": edits}),), usage=TokenUsage(10, 10))


def test_wrong_keep_stops_before_positive_control_and_preserves_raw_receipt(tmp_path):
    variants, plan = runner.prepare()
    provider = provider_for([response([])])
    result = observe(provider, tmp_path, variants, plan, adjudicate=decision(False),
        reviewer_profile=PROFILE, transport_id=CAPACITY_TRANSPORT_ID, inspect_response=editor.inspect_exchange)
    assert result["error_code"] == "model_comparison_semantic_failure"
    assert result["reserved_calls"] == 1 and not result["pair_accepted"]
    journal = json.loads((tmp_path / variants[0][0] / "journal.json").read_text(encoding="utf-8"))
    assert journal["original_report"] == journal["assembled_report"]
    assert not (tmp_path / variants[1][0]).exists()
    assert (tmp_path / variants[0][0] / "response.json").exists()


def test_offline_edit_and_keep_are_observed_without_becoming_qualification(tmp_path):
    from scripts.check_source_patch_editor import audit
    witness = audit()
    variants, plan = runner.prepare()
    edits = [{k: row[k] for k in ("block", "before", "after", "source_ids", "reason")}
             for row in witness["analyst_authored_patch"]["operations"]]
    provider = provider_for([response(edits), response([])])
    result = observe(provider, tmp_path, variants, plan, adjudicate=decision(True),
        reviewer_profile=PROFILE, transport_id=CAPACITY_TRANSPORT_ID, inspect_response=editor.inspect_exchange)
    assert result["pair_accepted"] and result["reserved_calls"] == 2
    assert [c["edit_changed"] for c in result["cases"]] == [True, False]
    assert not result["production_admitted"]
    assert witness["five_call_capacity_sample"]["within_input_caps"]


def test_preparation_offline_bound_to_complete_controls_and_frozen_hash(monkeypatch):
    import socket
    original = Path.read_text
    def read(path, *args, **kwargs):
        assert "data/runs/" not in path.as_posix() and path.name != ".env"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("network"))
    frozen = json.loads((runner.ROOT / "data/evaluation/results/golden_source_patch_preparation_v1.json").read_text(encoding="utf-8"))
    # This batch is closed. Rebuild its historical candidate identity instead
    # of silently relabelling it when the active product manifest evolves.
    import scripts.run_knowledge_time_review_pair as source_plan
    monkeypatch.setattr(source_plan, "candidate_identity", lambda: frozen["preparation_plan"]["source_candidate"])
    _, plan = runner.prepare()
    assert frozen == dict(preparation_plan=plan, preparation_plan_sha256=digest(compact(plan)))
    assert plan["proposed_diagnostic_budget"]["max_calls"] == 2
    assert not plan["labels_sent_to_model"] and not plan["prior_reviews_sent_to_model"]


def test_closed_result_rejects_before_any_input_or_credentials(monkeypatch, tmp_path):
    closed = tmp_path / "closed.json"
    closed.write_text("{}")
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", closed)
    monkeypatch.setattr(runner, "prepare", lambda: pytest.fail("read inputs"))
    with pytest.raises(ValueError, match="source_patch_pair_closed"):
        runner.run(SimpleNamespace(execute=True))


def test_mismatched_plan_and_existing_batch_cannot_start(monkeypatch, tmp_path):
    import scripts.run_golden_inference_development as ci
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", tmp_path / "missing.json")
    monkeypatch.setattr(ci, "verify_public_ci", lambda *_: pytest.fail("reached CI"))
    with pytest.raises(ValueError, match="source_patch_plan_mismatch"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha="closed-earlier-plan"))
    monkeypatch.setattr(runner, "RUN_DIRECTORY", tmp_path)
    _, plan = runner.prepare()
    with pytest.raises(ValueError, match="source_patch_pair_exists"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha=digest(compact(plan))))
