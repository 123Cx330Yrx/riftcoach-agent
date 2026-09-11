import copy
import json

import pytest

from app.evaluation.golden_inference_audit import (
    INFERENCE_POLICY, EvaluationResponseModelV13, inference_facts, validate_audit_anchors,
)
from app.runtime.coach_contract import COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT
from scripts.check_golden_quality_counterexamples import DATASET
from scripts.check_coach_golden_replay import _ReplayProvider, probe
from tests.test_coach_application_composition import dependencies


def payload():
    return {"score": 95, "verdict": "pass", "issues": [], "passed_checks": [], "summary": "checked",
            "audits": [{"kind": k, "status": "not_applicable", "claims": []} for k in ("metric_to_ability", "cohort_comparison")]}


def test_role_outcome_projection_preserves_reversal_and_missing_denominators():
    rows = json.loads(DATASET.read_text(encoding="utf-8"))["samples"]
    facts = inference_facts({"matches": rows})
    assert facts["role:MIDDLE:loss:cs_per_min"]["mean"] == 9.01
    assert facts["role:MIDDLE:win:cs_per_min"]["mean"] == 8.805
    rows[0]["cs_per_min"] = None
    rows.append({"included_in_aggregate": False, "role": "MIDDLE", "win": True, "cs_per_min": 999})
    facts = inference_facts({"matches": rows})
    assert facts["role:MIDDLE:win:cs_per_min"] == {"games": 2, "valid": 1, "missing_or_invalid": 1, "mean": 8.66}
    assert facts["scope:limits"]["excluded_count"] == 1


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unsupported_pass", "claim_missing", "issue_missing"])
def test_incomplete_or_contradictory_audits_reject(mutation):
    p = payload()
    if mutation == "missing": p.pop("audits")
    elif mutation == "duplicate": p["audits"][1] = copy.deepcopy(p["audits"][0])
    else:
        p["audits"][0].update(status="unsupported", claims=[{"quote": "claim", "evidence_refs": ["scope:limits"], "explanation": "unsupported"}])
        if mutation == "claim_missing": p["audits"][0]["claims"] = []
        if mutation == "issue_missing": p.update(verdict="fail", score=70)
    with pytest.raises(ValueError): EvaluationResponseModelV13.model_validate(p)


def test_claim_must_anchor_real_text_and_fact_key():
    p = payload(); p["audits"][0].update(status="supported", claims=[{"quote": "single result", "evidence_refs": ["scope:limits"], "explanation": "limited"}])
    parsed = EvaluationResponseModelV13.model_validate(p)
    validate_audit_anchors(parsed, "A single result only.", inference_facts({"matches": []}))
    with pytest.raises(ValueError): validate_audit_anchors(parsed, "Different report", inference_facts({"matches": []}))
    with pytest.raises(ValueError): validate_audit_anchors(parsed, "single result", {})


def test_development_scoring_requires_the_expected_finding(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_inference_development as runner
    p = {"issues": [{"quote": "claim"}], "audits": []}
    monkeypatch.setattr(runner, "_evaluation_payload", lambda _: p)
    result = SimpleNamespace(verdict=SimpleNamespace(value="needs_revision"), score=70)
    case = {"id": "control", "expected": "reject", "claim": "claim", "issue_kind": "mixed_role_deficit"}
    assert not runner.score_case(case, result)["matched"]
    p["audits"] = [{"kind": "cohort_comparison", "status": "unsupported", "claims": [{"quote": "claim"}]}]
    assert runner.score_case(case, result)["matched"]
    p["audits"][0]["claims"][0]["quote"] = "unrelated footer"
    assert not runner.score_case(case, result)["matched"]
    case["expected"] = "accept"
    result.verdict.value = "pass"
    result.score = 95
    assert not runner.score_case(case, result)["matched"]
    p.update(issues=[], audits=[])
    assert runner.score_case(case, result)["matched"]


def test_new_contract_reaches_full_nine_call_path_without_changing_old_identity(monkeypatch):
    captured = []; original = _ReplayProvider.chat
    def record(self, request):
        captured.append(request); return original(self, request)
    monkeypatch.setattr(_ReplayProvider, "chat", record)
    result = probe(dependencies()["summary_builder"].summary, contract=INFERENCE_COACH_CONTRACT, training_positions=())
    assert result["scripted_provider_calls"] == 9
    assert result["revision_count"] == 1
    assert result["report_available"] is False
    assert result["terminal_reason"] == "evaluation_failed"
    for request in captured:
        text = "\n".join(m.content or "" for m in request.messages)
        assert INFERENCE_POLICY in text or json.dumps(INFERENCE_POLICY, ensure_ascii=False)[1:-1] in text
        assert "inference_facts" in text
    assert COMPACT_COACH_CONTRACT.snapshot().sha256 == "d20fc775e7be126d373163a7d72cf71be329e28614aeb1eacaaf5e560b1f59f3"
    old, new = COMPACT_COACH_CONTRACT.descriptor(), INFERENCE_COACH_CONTRACT.descriptor()
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "request_timeout_s", "max_revisions", "minimum_score"):
        assert old[key] == new[key]
