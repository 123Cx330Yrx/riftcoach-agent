import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.evaluation.golden_evidence_diagnostics_v7 import collect_diagnostics
from app.evaluation.golden_evidence_scope_v5 import expand_evidence
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_scope_diagnostics import bounded_feedback
from tests.test_golden_evidence_scope import wire
from tests.test_golden_evidence_v4 import current
from tests import test_golden_evidence_runtime as shared


def queue_case(token=420):
    s = shared.summary()
    s["request"]["queue"] = token
    for m in s["matches"]:
        m["queue_id"] = 420
    value, report = wire(f"队列 {token} 的比赛。[K1]", ["facts:recent_aggregate", "facts:scope"])
    return current(value), report, s


@pytest.mark.parametrize("token,has_candidates", [(420, True), (421, False)])
def test_missing_queue_token_and_actual_field_are_reported_without_repair(token, has_candidates):
    value, report, s = queue_case(token)
    original = copy.deepcopy(value)
    raw = json.dumps(value)
    errors = collect_diagnostics(raw, report, fact_pack(s))
    hint = next(e for e in errors if "unsupported_numbers" in e)["unsupported_numbers"][0]
    assert hint["token"] == str(token)
    assert bool(hint["source_candidates"]) == has_candidates
    if has_candidates:
        operands = hint["source_candidates"][0]["operands"]
        assert all(ref.startswith("facts:recent_match:") and path == "/queue_id" for ref, path in operands)
        assert len(operands) == len(s["matches"])
    with pytest.raises(ValueError):
        expand_evidence(raw, report, fact_pack(s))
    assert value == original


def test_table_hint_is_original_block_not_reconstructed_claim():
    report = "| 经济 | 赢局 | 输局 |\n|---|---|---|\n| 每分钟 | 505.29 | 432.82 |"
    value, _ = wire(report)
    value = current(value)
    value["audits"][1]["claims"][0]["quote"] = report.replace("|---|---|---|\n", "")
    raw = json.dumps(value)
    rows = collect_diagnostics(raw, report, fact_pack(shared.summary()))
    hint = next(e for e in rows if "source_block" in e)["source_block"]
    assert hint["text"] == report and not hint["truncated"]
    assert bounded_feedback(rows)["omitted_errors"] == 0
    with pytest.raises(ValueError):
        expand_evidence(raw, report, fact_pack(shared.summary()))


def test_runtime_delivers_source_hint_then_validates_model_correction(monkeypatch):
    value, report, s = queue_case()
    _, req = shared.request_fixture()
    req = replace(req, player_summary=s, report=report)
    valid = copy.deepcopy(value)
    valid["audits"][1]["claims"][0]["evidence_refs"] = [f"facts:recent_match:{i:02d}" for i in range(len(s["matches"]))]
    calls = []

    def chat(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            assert "unsupported_numbers" in kwargs["user_prompt"]
            assert "/queue_id" in kwargs["user_prompt"]
        return shared.ChatResponse(content=json.dumps(value if len(calls) == 1 else valid), provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage())

    monkeypatch.setattr(shared.module, "_chat_response", chat)
    evaluator = shared.module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v7")
    result = evaluator.evaluate(req)
    assert result.verdict.value == "pass" and len(calls) == 2


def test_v7_asset_identity_and_previous_snapshot():
    from app.runtime.coach_contract import EVIDENCE_V7_COACH_CONTRACT as new, EVIDENCE_V6_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256 == "eb17649af753c63bd96ca30a02b4e993f2fc2a287b9cb99040261418bec139d5"
    root = Path("examples/runtime_profiles/flash_v2_golden_evidence_v7")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root / "skills", prompt_programs_root=root / "prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.18.0"
