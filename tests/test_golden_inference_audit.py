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


@pytest.mark.parametrize("version", ["1.3.7", "1.3.8", "1.3.9", "1.3.10"])
def test_new_contract_reaches_full_nine_call_path_without_changing_old_identity(monkeypatch, version):
    from app.runtime.coach_contract import CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT
    contract = {"1.3.7": INFERENCE_COACH_CONTRACT, "1.3.8": CLAIM_COACH_CONTRACT, "1.3.9": ANCHOR_COACH_CONTRACT, "1.3.10": COVERAGE_COACH_CONTRACT}[version]
    from app.evaluation.golden_inference_audit_v2 import INFERENCE_POLICY as V2_POLICY
    policy = INFERENCE_POLICY if version == "1.3.7" else V2_POLICY
    if version == "1.3.9":
        from app.evaluation.golden_inference_audit_v3 import INFERENCE_POLICY as policy
    if version == "1.3.10":
        from app.evaluation.golden_inference_coverage import COVERAGE_POLICY as policy
    captured = []; original = _ReplayProvider.chat
    def record(self, request):
        captured.append(request); return original(self, request)
    monkeypatch.setattr(_ReplayProvider, "chat", record)
    result = probe(dependencies()["summary_builder"].summary, contract=contract, training_positions=())
    assert result["scripted_provider_calls"] == 9
    assert result["revision_count"] == 1
    assert result["report_available"] is False
    assert result["terminal_reason"] == "evaluation_failed"
    for request in captured:
        text = "\n".join(m.content or "" for m in request.messages)
        assert policy in text or json.dumps(policy, ensure_ascii=False)[1:-1] in text
        assert "inference_facts" in text
    assert COMPACT_COACH_CONTRACT.snapshot().sha256 == "d20fc775e7be126d373163a7d72cf71be329e28614aeb1eacaaf5e560b1f59f3"
    assert INFERENCE_COACH_CONTRACT.snapshot().sha256 == "3ca4e014cf870d626e6dcb321b1881a6d4d19db3c854bab2e5c16b6f932445a0"
    assert CLAIM_COACH_CONTRACT.snapshot().sha256 == "17f70cdba761d28359aa00bc17d4a072e65297dfc4a0362dbe97b159e6c5841e"
    assert ANCHOR_COACH_CONTRACT.snapshot().sha256 == "f1c8865e8a11ff765ab547cf76c1aa8a47b9b5b68d49a6b9f22b38adfc05bd1f"
    old, new = COMPACT_COACH_CONTRACT.descriptor(), contract.descriptor()
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "request_timeout_s", "max_revisions", "minimum_score"):
        assert old[key] == new[key]


def test_v2_mixed_claims_require_issues_only_for_unsupported_statements():
    from app.evaluation.golden_inference_audit_v2 import EvaluationResponseModelV14
    p = payload()
    p.update(score=70, verdict="needs_revision", issues=[{"severity": "medium", "category": "other", "quote": "bad claim", "evidence": "metric only", "explanation": "unsupported ability", "suggested_correction": "remove inference"}])
    p["audits"][0].update(status="unsupported", claims=[
        {"status": "unsupported", "quote": "bad claim", "evidence_refs": ["scope:limits"], "explanation": "unsupported"},
        {"status": "supported", "quote": "correct caveat", "evidence_refs": ["scope:limits"], "explanation": "correct"},
    ])
    parsed = EvaluationResponseModelV14.model_validate(p)
    assert len(parsed.issues) == 1
    validate_audit_anchors(parsed, "bad claim; correct caveat", {"scope:limits": {}})
    p["audits"][0]["status"] = "supported"
    with pytest.raises(ValueError): EvaluationResponseModelV14.model_validate(p)

    p["audits"][0]["status"] = "unsupported"
    p["issues"] = []
    with pytest.raises(ValueError): EvaluationResponseModelV14.model_validate(p)


@pytest.mark.parametrize("initial_schema_bad", [False, True])
def test_anchor_validation_shares_one_repair_and_never_weakens_exact_match(initial_schema_bad):
    from app.providers.structured import decode_structured_response
    from app.providers.models import ChatResponse, TokenUsage
    from app.providers.errors import ProviderResponseError
    from app.evaluation.golden_inference_audit_v2 import EvaluationResponseModelV14, inference_response_contract
    p = payload()
    p["audits"][0].update(status="supported", claims=[{"status": "supported", "quote": "**metric**", "evidence_refs": ["scope:limits"], "explanation": "descriptive"}])
    good = ChatResponse(content=json.dumps(p), model="offline", provider="offline", usage=TokenUsage(input_tokens=1, output_tokens=1), finish_reason="stop")
    p["audits"][0]["claims"][0]["quote"] = "metric only"
    bad = ChatResponse(content="{}" if initial_schema_bad else json.dumps(p), model="offline", provider="offline", usage=good.usage, finish_reason="stop")
    fixes=[]
    def repair(request): fixes.append(request); return good
    options = dict(contract=inference_response_contract(), output_model=EvaluationResponseModelV14, validate_context=lambda v: validate_audit_anchors(v, "**metric**", {"scope:limits": {}}))
    assert decode_structured_response(response=bad, repair=repair, **options).repair_attempted
    assert len(fixes) == 1
    fixes.clear()
    def still_bad(request): fixes.append(request); return bad
    with pytest.raises(ProviderResponseError): decode_structured_response(response=bad, repair=still_bad, **options)
    assert len(fixes) == 1
