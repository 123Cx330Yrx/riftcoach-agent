import copy

import pytest

from app.evaluation.golden_fact_candidate import fact_pack, FactEvaluation, validate_candidate
from app.evaluation.golden_inference_coverage import report_blocks
from tests.test_golden_compact_coverage import compact


def summary():
    return {"schema_version": "1.0", "player": {}, "request": {}, "recent_summary": {},
            "matches": [
                {"match_id": "TEST_1", "included_in_aggregate": True, "role": "MIDDLE",
                 "win": True, "gold_per_min": 505.29},
                {"match_id": "TEST_2", "included_in_aggregate": True, "role": "MIDDLE",
                 "win": False, "gold_per_min": 432.815},
                {"match_id": "TEST_3", "included_in_aggregate": False, "role": "MIDDLE",
                 "win": False, "gold_per_min": 999},
                {"match_id": "TEST_4", "included_in_aggregate": True, "role": "UTILITY",
                 "win": False, "gold_per_min": 100}]}


def payload(quote="中单经济 505.29 vs 432.82。"):
    canonical, _ = compact()
    value = canonical.model_dump(mode="json")
    value.update(issues=[], verdict="pass")
    claim = value["audits"][1]["claims"][0]
    claim.update(quote=quote, claim_kind="direct_result", scope=None, scope_anchor=None,
                 evidence_refs=["role:MIDDLE:win:gold_per_min", "role:MIDDLE:loss:gold_per_min"],
                 numeric_bindings=[
                     {"evidence_ref": "role:MIDDLE:win:gold_per_min", "path": "/mean", "token": "505.29"},
                     {"evidence_ref": "role:MIDDLE:loss:gold_per_min", "path": "/mean", "token": "432.82"}])
    value["coverage"] = [dict(block_id=report_blocks(quote)[0]["block_id"],
                              metric_to_ability="not_applicable", cohort_comparison="supported", scope_ambiguous=False)]
    return value, quote


def test_correct_numeric_fact_needs_no_invented_scope_anchor():
    value, report = payload()
    assert validate_candidate(FactEvaluation.model_validate(value), report, fact_pack(summary())) == {
        "structural_validation": "passed", "semantic_approval": False}


def test_index_reuses_actual_projection_and_preserves_cohort_identity():
    source = summary()
    before = copy.deepcopy(source)
    pack = fact_pack(source)
    assert source == before
    assert pack["facts"]["facts:recent_match:02"]["included_in_aggregate"] is False
    assert pack["provenance"]["role:MIDDLE:loss:gold_per_min"]["row_indices"] == [1]
    assert pack["facts"]["role:MIDDLE:loss:gold_per_min"]["mean"] == 432.815
    assert pack["provenance"]["facts:recent_match:01"]["match_id"] == "TEST_2"
    source["matches"].reverse()
    assert fact_pack(source)["source_sha256"] != pack["source_sha256"]


@pytest.mark.parametrize("mutation,error", [
    ("wrong_value", "numeric_binding_value_mismatch"),
    ("wrong_role", "numeric_binding_value_mismatch"),
    ("unknown_ref", "inference_audit_anchor_invalid"),
    ("missing_path", "numeric_binding_path_missing"),
    ("unbound_number", "direct_result_unbound_number"),
    ("scope_only", "numeric_binding_unreferenced_source"),
])
def test_numeric_binding_failures(mutation, error):
    value, report = payload()
    claim = value["audits"][1]["claims"][0]
    binding = claim["numeric_bindings"][1]
    if mutation == "wrong_value":
        report = report.replace("432.82", "433.82")
        claim["quote"] = report
        binding["token"] = "433.82"
        value["coverage"][0]["block_id"] = report_blocks(report)[0]["block_id"]
    elif mutation == "wrong_role":
        binding["evidence_ref"] = "role:UTILITY:loss:gold_per_min"
        claim["evidence_refs"][1] = binding["evidence_ref"]
    elif mutation == "unknown_ref": claim["evidence_refs"][1] = "facts:recent_match:99"
    elif mutation == "missing_path": binding["path"] = "/absent"
    elif mutation == "unbound_number": claim["numeric_bindings"].pop()
    else:
        binding["evidence_ref"] = "scope:limits"
        claim["evidence_refs"].append("scope:limits")
    with pytest.raises(ValueError, match=error):
        validate_candidate(FactEvaluation.model_validate(value), report, fact_pack(summary()))


def test_false_numeric_claim_can_be_reported_as_unsupported_with_exact_issue():
    value, report = payload()
    canonical, _ = compact()
    issue = canonical.issues[0].model_dump(mode="json")
    report = report.replace("432.82", "433.82")
    claim = value["audits"][1]["claims"][0]
    claim.update(quote=report, status="unsupported")
    claim["numeric_bindings"][1]["token"] = "433.82"
    issue["quote"] = report
    value.update(issues=[issue], verdict="needs_revision")
    value["audits"][1]["status"] = "unsupported"
    value["coverage"][0].update(block_id=report_blocks(report)[0]["block_id"], cohort_comparison="unsupported")
    assert validate_candidate(FactEvaluation.model_validate(value), report, fact_pack(summary()))["semantic_approval"] is False


def test_disguised_ability_claim_is_explicitly_not_semantically_approved():
    # Document the residual semantic gap; this is NOT a detection success.
    value, report = payload("中单经济 505.29 vs 432.82，证明长期能力更强。")
    result = validate_candidate(FactEvaluation.model_validate(value), report, fact_pack(summary()))
    assert result["structural_validation"] == "passed"
    assert result["semantic_approval"] is False


@pytest.mark.parametrize("value", [None, True, -1])
def test_missing_invalid_metrics_never_become_zero(value):
    source = summary()
    source["matches"][1]["gold_per_min"] = value
    group = fact_pack(source)["facts"]["role:MIDDLE:loss:gold_per_min"]
    assert group["mean"] is None and group["valid"] == 0 and group["missing_or_invalid"] == 1


def test_duplicate_identity_is_rejected():
    source = summary()
    source["matches"][1]["match_id"] = "TEST_1"
    with pytest.raises(ValueError, match="identity_invalid"):
        fact_pack(source)


@pytest.mark.parametrize("scope,anchor,quote", [
    ("selected_sample", "这四场", "这四场中单经济 505.29 vs 432.82。"),
    ("question_or_negation", "不证明", "中单经济 505.29 vs 432.82，不证明长期能力。"),
])
def test_inference_scope_and_negation_remain_representable(scope, anchor, quote):
    value, report = payload(quote)
    claim = value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference", scope=scope, scope_anchor=anchor, numeric_bindings=[])
    assert validate_candidate(FactEvaluation.model_validate(value), report, fact_pack(summary()))["semantic_approval"] is False


def test_ambiguity_cannot_hide_behind_supported_numbers():
    value, report = payload("中单经济 505.29 vs 432.82，是稳定差异。")
    value["audits"][1]["claims"][0].update(claim_kind="inference", scope="ambiguous", scope_anchor="稳定差异")
    with pytest.raises(ValueError, match="ambiguous_scope_requires"):
        FactEvaluation.model_validate(value)


def test_generation_cap_does_not_silently_truncate_role_aggregate():
    source = summary()
    source["matches"] = [dict(source["matches"][0], match_id=f"TEST_{i}") for i in range(11)]
    pack = fact_pack(source)
    assert "facts:recent_match:10" not in pack["facts"]
    assert pack["facts"]["facts:sample_boundaries"]["match_rows_omitted_by_cap"] == 1
    assert pack["facts"]["role:MIDDLE:win:gold_per_min"]["games"] == 11
    assert len(pack["provenance"]["role:MIDDLE:win:gold_per_min"]["row_indices"]) == 11
