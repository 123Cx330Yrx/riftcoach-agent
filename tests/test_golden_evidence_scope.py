import json
import pytest

from app.evaluation.golden_evidence_scope import EvidenceEvaluation, expand_evidence, collect_diagnostics
from app.evaluation.golden_numeric_evidence import numeric_support
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_compact_coverage import encode_coverage
from tests.test_golden_fact_candidate import summary, payload


def wire(quote, refs=None):
    value, report = payload(quote)
    claim = value["audits"][1]["claims"][0]
    del claim["numeric_bindings"]
    if refs is not None:
        claim["evidence_refs"] = refs
    canonical = EvidenceEvaluation.model_validate(value)
    value["coverage"] = encode_coverage(canonical.coverage)
    return value, report


@pytest.mark.parametrize("quote", ["中单经济 505.29 vs 432.82。", "中单经济差 72。", "中单经济差 -72.48。", "中单经济比 85.66%。"])
def test_program_computes_values_without_model_numeric_bindings(quote):
    value, report = wire(quote)
    result = expand_evidence(json.dumps(value), report, fact_pack(summary()))
    ledger = numeric_support(result.audits[1].claims[0], fact_pack(summary()))
    assert ledger and all(r["supported"] for r in ledger)
    assert all("numeric_bindings" not in c for a in value["audits"] for c in a["claims"])
    assert collect_diagnostics(json.dumps(value), report, fact_pack(summary())) == []


@pytest.mark.parametrize("quote,refs", [
    ("中单经济 433.82。", None),
    ("跨位置经济差 405.29。", ["role:MIDDLE:win:gold_per_min", "role:UTILITY:loss:gold_per_min"]),
    ("经济百分比 50529%。", ["role:MIDDLE:win:gold_per_min"]),
    ("经济 505.29。", ["scope:limits"]),
    ("经济 505.29。", ["facts:recent_match:99"]),
])
def test_bad_numeric_evidence_still_rejected(quote, refs):
    value, report = wire(quote, refs)
    with pytest.raises(ValueError):
        expand_evidence(json.dumps(value), report, fact_pack(summary()))
    assert collect_diagnostics(json.dumps(value), report, fact_pack(summary()))


def test_percent_conversion_is_computed_only_for_ratio_fields():
    source = summary()
    source["matches"][0]["damage_share"] = 0.2232
    value, report = wire("伤害占比 22.32%。", ["facts:recent_match:00"])
    result = expand_evidence(json.dumps(value), report, fact_pack(source))
    assert any(c["op"] == "percent" for c in numeric_support(result.audits[1].claims[0], fact_pack(source))[0]["candidates"])


def test_reduced_output_does_not_claim_to_prove_semantic_object_or_ability():
    value, report = wire("中单经济 505.29 vs 432.82，证明长期能力更强。")
    result = expand_evidence(json.dumps(value), report, fact_pack(summary()))
    # This remains a required real-model negative control; numeric support only.
    assert result.audits[1].claims[0].claim_kind == "direct_result"


def test_ambiguity_still_requires_exact_issue_and_nonpass():
    value, report = wire("中单经济 505.29 vs 432.82，是稳定差异。")
    value["audits"][1]["claims"][0].update(claim_kind="inference", scope="ambiguous", scope_anchor="稳定差异")
    with pytest.raises(ValueError, match="ambiguous_scope_requires"):
        expand_evidence(json.dumps(value), report, fact_pack(summary()))


def test_duplicate_keys_still_rejected():
    value, report = wire("经济 505.29。")
    with pytest.raises(ValueError, match="duplicate_key"):
        expand_evidence('{"score":0,' + json.dumps(value)[1:], report, fact_pack(summary()))
