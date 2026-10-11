import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_context_relation_probe as v1
from app.evaluation import golden_context_relation_probe_v2 as v2
from app.evaluation.golden_review_experiment import compact
from scripts import run_golden_context_relation_probe as runner
from tests.test_golden_context_relation_probe import fixture
from tests import test_golden_evidence_runtime as shared


def project(value):
    return {k: v for k, v in value.items() if k not in {"referring_expression", "defined_meaning"}}


def test_v2_preserves_source_but_does_not_make_explanation_a_copying_task():
    _, pack, value, case = fixture()
    value["defined_meaning"] = "A faithful paraphrase is not a literal substring."
    raw = compact(value)
    with pytest.raises(ValueError, match="not_literal"):
        v1.validate_response(raw, case["report"], pack, case["target"])
    projected = project(value)
    projected["explanation"] = "该定义明确指向下一句，并将稳定限定为样本内一致。"
    result = v2.validate_response(compact(projected), case["report"], pack, case["target"])
    assert result.context_ref.block == value["context_ref"]["block"]
    # Old wire output is not silently treated as a new-version result.
    with pytest.raises(ValueError): v2.validate_response(raw, case["report"], pack, case["target"])
    projected["context_ref"] = {"block": 64}
    with pytest.raises(ValueError): v2.validate_response(compact(projected), case["report"], pack, case["target"])


@pytest.mark.parametrize("kind", ["source", "target", "missing_definition", "clarify_with_context", "extra_json"])
def test_v2_still_rejects_reference_and_disposition_errors(kind):
    _, pack, value, case = fixture()
    value = project(value)
    if kind == "source": value["source_digest"] = "0" * 64
    if kind == "target": value["target_ref"] = {"block": 1}
    if kind == "missing_definition": value["context_ref"] = None
    if kind == "clarify_with_context": value["disposition"] = "needs_clarification"
    with pytest.raises(ValueError):
        v2.validate_response(compact(value) + ("{}" if kind == "extra_json" else ""), case["report"], pack, case["target"])


def test_same_complete_data_and_budget_with_explicit_new_identity(monkeypatch):
    req, pack, _, case = fixture()
    args = (req.player_summary, req.deterministic_report, req.knowledge, case["report"], case["target"])
    old, new = v1.build_request(*args), v2.build_request(*args)
    assert old.messages[1].content.split("[UNTRUSTED DATA]")[1] == new.messages[1].content.split("[UNTRUSTED DATA]")[1]
    assert old.max_tokens == new.max_tokens == 32768 and old.timeout_s == new.timeout_s == 300
    assert old.response_contract.version == "1.0.0" and new.response_contract.version == "2.0.0"
    monkeypatch.setattr(runner, "load_inputs", lambda *a:(req.player_summary, req.deterministic_report, req.knowledge, [case]))
    plan = runner.run(SimpleNamespace(source_run=None, base_report=None, execute=False, v2=True))
    assert plan["experiment_id"] == v2.EXPERIMENT_ID and plan["response_contract_version"] == "2.0.0"
    assert plan["max_calls"] == 4 and plan["max_corrections"] == 0


def test_v2_observation_keeps_independent_receipt_and_no_report_acceptance(tmp_path):
    req, pack, value, case = fixture()
    value = project(value)
    state = dict(calls=0, input_tokens=0, output_tokens=0)
    def chat(request):
        state["calls"] += 1
        return shared.ChatResponse(content=compact(value), provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage())
    runner.observe(SimpleNamespace(chat=chat), tmp_path, [case], [None], pack, state,
        validator=v2.validate_response, experiment_id=v2.EXPERIMENT_ID)
    receipt = json.loads((tmp_path/"receipt.json").read_text())
    assert receipt["experiment_id"] == v2.EXPERIMENT_ID and receipt["automatic_target_matches"] == 1
    assert not receipt["whole_report_acceptance"] and receipt["calls"] == 1
