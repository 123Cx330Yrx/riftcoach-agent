import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.evaluation.golden_evidence_scope_v8 import expand_evidence, heading_blocks
from app.evaluation.golden_evidence_diagnostics_v8 import collect_diagnostics
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_scope_diagnostics import bounded_feedback
from tests.test_golden_evidence_scope import wire
from tests.test_golden_evidence_v4 import current
from tests import test_golden_evidence_runtime as shared


def fixture(report="## 近期概览"):
    value, report = wire(report)
    value = current(value)
    value["audits"][1]["claims"] = []
    value["heading_reviews"] = [dict(block_id=b["block_id"], kind="navigation") for b in heading_blocks(report)]
    return value, report, fact_pack(shared.summary())


def test_plain_heading_can_pass_without_inventing_an_inference():
    value, report, pack = fixture()
    assert expand_evidence(json.dumps(value), report, pack).verdict == "pass"


@pytest.mark.parametrize("change", ["missing", "duplicate", "stale"])
def test_heading_inventory_is_exact(change):
    value, report, pack = fixture()
    if change == "missing": value["heading_reviews"] = []
    elif change == "duplicate": value["heading_reviews"] *= 2
    else: value["heading_reviews"][0]["block_id"] = "b99-stale"
    with pytest.raises(ValueError, match="heading_inventory_mismatch"):
        expand_evidence(json.dumps(value), report, pack)


def test_assertion_heading_requires_exact_inference_claim():
    value, report, pack = fixture("## 长期表现已有改善")
    value["heading_reviews"][0]["kind"] = "assertion"
    with pytest.raises(ValueError, match="heading_assertion_claim_missing"):
        expand_evidence(json.dumps(value), report, pack)
    assert collect_diagnostics(json.dumps(value), report, pack)[0]["codes"] == ["heading_assertion_claim_missing"]


def test_ambiguous_heading_with_real_anchor_and_issue_is_accepted_for_revision():
    value, report, pack = fixture("## 长期表现已有改善")
    value["heading_reviews"][0]["kind"] = "assertion"
    value["audits"][1]["claims"] = [dict(quote=report, evidence_refs=["scope:limits"], explanation="范围需澄清",
        status="unsupported", claim_kind="inference", scope="ambiguous", scope_anchor="长期")]
    value.update(verdict="needs_revision", score=75, issues=[dict(severity="medium", category="other", quote=report,
        evidence="scope:limits", explanation="缺少适用范围", suggested_correction="明确样本范围")])
    assert expand_evidence(json.dumps(value), report, pack).verdict == "needs_revision"
    value["audits"][1]["claims"][0]["scope_anchor"] = None
    with pytest.raises(ValueError, match="inference_literal_scope_required"):
        expand_evidence(json.dumps(value), report, pack)
    errors = collect_diagnostics(json.dumps(value), report, pack)
    assert any("ambiguous仍须非空" in r.get("repair_rule", "") for r in errors)


def test_inventory_failure_does_not_hide_local_anchor_and_never_repairs_input():
    value, report = wire("同位置比较结果。")
    value = current(value)
    value["heading_reviews"] = []
    claim = value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference", scope="selected_sample", scope_anchor="同位置")
    value["reviewed_blocks"] = ["b99-stale"]
    original = copy.deepcopy(value)
    rows = collect_diagnostics(json.dumps(value), report, fact_pack(shared.summary()))
    codes = [c for r in rows for c in r["codes"]]
    assert "reviewed_block_inventory_mismatch" in codes
    assert "selected_sample_anchor_missing" in codes
    assert value == original and bounded_feedback(rows)["omitted_errors"] == 0
    with pytest.raises(ValueError): expand_evidence(json.dumps(value), report, fact_pack(shared.summary()))


def test_duplicate_fields_are_not_flattened_for_diagnostics():
    rows = collect_diagnostics('{"score":95,"score":96}', "report", {})
    assert any("duplicate_json_field" in r["codes"] for r in rows)


@pytest.mark.parametrize("audits", [None, "bad", [None], [{"claims": None}]])
def test_malformed_diagnostic_shapes_do_not_escape_as_runtime_errors(audits):
    rows = collect_diagnostics(json.dumps({"audits": audits, "heading_reviews": [{"block_id": [], "kind": "assertion"}]}), "## 标题", {})
    assert rows


def test_runtime_sends_feedback_and_retains_single_repair_limit(monkeypatch):
    value, report, _ = fixture("## 长期表现已有改善")
    value["heading_reviews"][0]["kind"] = "assertion"
    _, request = shared.request_fixture()
    request = replace(request, report=report)
    calls = []
    def chat(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            assert "heading_assertion_claim_missing" in kwargs["user_prompt"]
        return shared.ChatResponse(content=json.dumps(value), provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage())
    monkeypatch.setattr(shared.module, "_chat_response", chat)
    evaluator = shared.module.GroundedChatEvaluationAdapter(runtime=None, system_prompt="test", fact_pack_builder=lambda _: {}, inference_audit="evidence_v8")
    from app.providers.errors import ProviderResponseError
    with pytest.raises(ProviderResponseError, match="invalid_structured_output"):
        evaluator.evaluate(request)
    assert len(calls) == 2


def test_v8_identity_old_snapshot_and_capacity():
    from app.runtime.coach_contract import EVIDENCE_V8_COACH_CONTRACT as new, EVIDENCE_V7_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256 == "086cf0b4150de5cd1c28f319d37353b06c832e90b57c2efc490af8c4ae769655"
    root = Path("examples/runtime_profiles/flash_v2_golden_evidence_v8")
    runtime = RuntimeCompositionRoot.from_directories(skills_root=root/"skills", prompt_programs_root=root/"prompt_programs", coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version == "1.19.0"
    for key in ("max_output_tokens", "request_timeout_s", "total_tokens", "stream_transport_id"):
        assert new.descriptor()[key] == old.descriptor()[key]
