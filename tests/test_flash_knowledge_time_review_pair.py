"""Same-input model comparison and its no-retry execution boundaries."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from scripts import run_flash_knowledge_time_review_pair as runner
from scripts.native_contract_options import body


def test_comparison_preserves_actual_glm_request_and_only_repairs_reference_report(monkeypatch):
    read = Path.read_text
    def offline(path, *args, **kwargs):
        assert "data/runs/" not in path.as_posix() and path.name != ".env"
        return read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", offline)
    frozen = json.loads((runner.ROOT / "data/evaluation/results/golden_flash_knowledge_time_review_preparation_v2.json").read_text(encoding="utf-8"))
    # Replay the closed batch's identity, not the evolving active candidate.
    import scripts.run_knowledge_time_review_pair as source_plan
    monkeypatch.setattr(source_plan, "candidate_identity", lambda: frozen["preparation_plan"]["source_candidate"])
    variants, plan = runner.prepare()
    original, original_plan = runner.prepare_original()
    historical = json.loads(runner.PREDECESSOR.read_text(encoding="utf-8"))
    assert variants[0] == original[0]
    reference = json.loads(runner.REFERENCE_AUDIT.read_text(encoding="utf-8"))
    assert variants[1][1].source.report == reference["reference_report"]
    old_data, new_data = body(original[1][2]), body(variants[1][2])
    for data in (old_data, new_data):
        data["source_index"].pop("blocks")
        data["source_index"].pop("source_digest")
        # Both include the changed report in their source identity; their
        # actual facts/catalog entries must otherwise remain identical.
        data["computed_evidence"].pop("source_digest")
        data["source_roots"].pop("catalog_sha256")
    assert new_data == old_data
    for ((name, inputs, request), (_, _, old_request), cell) in zip(variants, original, plan["cells"], strict=True):
        assert request.messages[0] == old_request.messages[0]
        assert request.messages[2] == old_request.messages[2] and request.tools == old_request.tools
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        assert hashlib.sha256(raw).hexdigest() == cell["request_sha256"]
        assert request.timeout_s == 300 and request.max_tokens == 32768
    actual = validate_request(variants[0][2], transport_id=CAPACITY_TRANSPORT_ID)
    assert hashlib.sha256(actual).hexdigest() == historical["original_file_sha256"]["original-date-error/request.raw.json"]
    assert json.loads(actual) == historical["public_json_contents"]["original-date-error/request.raw.json"]
    assert plan["cells"][0]["request_sha256"] == original_plan["cells"][0]["request_sha256"]
    assert plan["cells"][1]["request_sha256"] != original_plan["cells"][1]["request_sha256"]
    assert plan["model"] == "glm-5.3-flash" and plan["reasoning_effort"] == "high"
    assert not plan["original_glm_reference_call_sent"] and not plan["production_admitted"]
    assert plan["proposed_diagnostic_budget"]["max_calls"] == 2
    assert plan["proposed_diagnostic_budget"]["max_seconds_total"] == 600
    assert frozen == dict(preparation_plan=plan, preparation_plan_sha256=digest(compact(plan)))


@pytest.mark.parametrize("old_source", ["glm", "withdrawn_flash"])
def test_old_plan_hash_cannot_authorize_other_model_or_reference(monkeypatch, tmp_path, old_source):
    import scripts.run_golden_inference_development as ci
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", tmp_path / "not-yet-completed.json")
    monkeypatch.setattr(ci, "verify_public_ci", lambda *_: pytest.fail("mismatch reached CI"))
    _, old_plan = runner.prepare_original()
    old_sha = digest(compact(old_plan))
    if old_source == "withdrawn_flash":
        old = json.loads((runner.ROOT / "data/evaluation/results/golden_flash_knowledge_time_review_preparation_v1.json").read_text(encoding="utf-8"))
        old_sha = old["preparation_plan_sha256"]
    with pytest.raises(ValueError, match="flash_time_review_plan_mismatch"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha=old_sha, ci_run="old", env_file=None))


def test_closed_batch_is_rejected_before_inputs_ci_or_credentials(tmp_path, monkeypatch):
    closed = tmp_path / "result.json"
    closed.write_text("{}")
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", closed)
    monkeypatch.setattr(runner, "RUN_DIRECTORY", tmp_path / "fresh")
    monkeypatch.setattr(runner, "prepare", lambda: pytest.fail("closed batch reached inputs"))
    with pytest.raises(ValueError, match="flash_time_review_batch_closed"):
        runner.run(SimpleNamespace(execute=True))
    assert not runner.RUN_DIRECTORY.exists()


def test_existing_batch_is_not_restarted(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", tmp_path / "uncommitted-result.json")
    monkeypatch.setattr(runner, "RUN_DIRECTORY", tmp_path)
    _, plan = runner.prepare()
    with pytest.raises(ValueError, match="flash_time_review_batch_exists"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha=digest(compact(plan))))


def test_failed_pair_has_nonzero_exit(monkeypatch):
    monkeypatch.setattr(runner, "run", lambda _: {"pair_accepted": False})
    with pytest.raises(SystemExit) as stopped:
        runner.main(["--execute"])
    assert stopped.value.code == 2
