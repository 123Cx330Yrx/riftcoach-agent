import copy
import json

import pytest

from app.evaluation.golden_inference_audit import inference_facts
from app.evaluation.golden_scope_diagnostics import collect_diagnostics, bounded_feedback
from app.evaluation.golden_inference_scope_v5 import expand_response
from tests.test_golden_compact_coverage import compact, REPORT


def diagnose(value):
    return collect_diagnostics(json.dumps(value), REPORT, inference_facts({}))


def codes(rows):
    return {code for row in rows for code in row["codes"]}


def test_valid_payload_is_not_modified_or_misreported():
    _, value = compact()
    before = copy.deepcopy(value)
    assert diagnose(value) == []
    assert value == before
    expand_response(json.dumps(value), REPORT, inference_facts({}))


@pytest.mark.parametrize("mutation,expected", [
    ("substring", "ambiguous_exact_other_issue_missing"),
    ("category", "ambiguous_exact_other_issue_missing"),
    ("pass", "ambiguous_requires_nonpass"),
    ("unsupported", "unsupported_exact_issue_missing"),
    ("aggregate", "audit_claim_aggregate_mismatch"),
    ("inventory", "coverage_inventory_mismatch"),
    ("coverage", "coverage_applicable_claim_mismatch"),
    ("ambiguity", "scope_coverage_claim_mismatch"),
])
def test_relation_faults_are_localized_even_when_old_schema_short_circuits(mutation, expected):
    _, value = compact()
    if mutation == "substring": value["issues"][0]["quote"] = "stable"
    elif mutation == "category": value["issues"][0]["category"] = "fact_error"
    elif mutation == "pass": value["verdict"] = "pass"
    elif mutation == "unsupported":
        value["audits"][1]["claims"][0]["status"] = "unsupported"
        value["issues"] = []
    elif mutation == "aggregate": value["audits"][1]["status"] = "not_applicable"
    elif mutation == "inventory": value["coverage"][0][0] = "b01-00000000"
    elif mutation == "coverage": value["coverage"][0][2] = "N"
    else: value["coverage"][0][3] = False
    rows = diagnose(value)
    assert expected in codes(rows)
    with pytest.raises(ValueError):
        expand_response(json.dumps(value), REPORT, inference_facts({}))
    if mutation in {"substring", "category", "pass", "unsupported"}:
        assert any(r.get("audit_index") == 1 and r.get("claim_index") == 0
                   and expected in r["codes"] for r in rows)


def test_collects_multiple_faults_without_blessing_unknown_refs():
    _, value = compact()
    value["issues"][0]["quote"] = "stable"
    value["audits"][1]["claims"][0]["evidence_refs"] = ["invented"]
    assert {"ambiguous_exact_other_issue_missing", "unknown_evidence_ref"} <= codes(diagnose(value))


@pytest.mark.parametrize("raw", ['{}', '{"x":1,"x":2}', '{"score":NaN}', '[]'])
def test_malformed_input_returns_data_only_error(raw):
    assert codes(collect_diagnostics(raw, REPORT, {})) == {"invalid_json_or_schema"}


def test_feedback_budget_is_enforced_and_omissions_are_exact():
    rows = [{"claim_index": i, "quote_excerpt": "数" * 80,
             "codes": ["unknown_evidence_ref"]} for i in range(48)]
    bounded = bounded_feedback(rows)
    assert len(bounded["errors"]) <= 12
    assert len(json.dumps(bounded, ensure_ascii=False)) <= 3000
    assert len(bounded["errors"]) + bounded["omitted_errors"] == len(rows)
    assert bounded_feedback([]) == {"errors": [], "omitted_errors": 0}


@pytest.mark.parametrize("quote,scope,anchor,status,issue,expected", [
    ("这四场方向一致。", "selected_sample", "这四场", "supported", False, set()),
    ("一次结果不证明长期能力。", "question_or_negation", "不证明", "supported", False, set()),
    ("长期经济能力稳定更强。", "beyond_sample", "长期", "unsupported", True, set()),
    ("中单经济 505.29 vs 432.82。", "selected_sample", "中单", "supported", False,
     {"selected_sample_anchor_missing"}),
])
def test_boundary_labels_are_manual_and_numeric_fact_exposes_existing_rule(quote, scope, anchor, status, issue, expected):
    # This checks representation, NOT the model's ability to choose these labels.
    from app.evaluation.golden_inference_coverage import report_blocks
    _, value = compact()
    value["audits"][1]["claims"][0].update(quote=quote, scope=scope, scope_anchor=anchor, status=status)
    value["audits"][1]["status"] = status
    value["coverage"] = [[report_blocks(quote)[0]["block_id"], "N", "U" if status == "unsupported" else "S", False]]
    if issue:
        value["issues"][0]["quote"] = quote
    else:
        value.update(issues=[], verdict="pass")
    assert codes(collect_diagnostics(json.dumps(value), quote, inference_facts({}))) == expected
