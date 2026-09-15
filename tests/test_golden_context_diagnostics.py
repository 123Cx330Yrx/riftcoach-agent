import copy
import json

import pytest

from app.evaluation.golden_context_diagnostics import collect_diagnostics, context_inspection, feedback
from app.evaluation.golden_context_review import expand_context
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_review_experiment import SourceIndex, compact, index_review
from tests.test_golden_context_review import wire, claim
from tests.test_golden_evidence_v7 import queue_case


@pytest.mark.parametrize("token,found", [(420, True), (421, False)])
@pytest.mark.parametrize("bad_inventory", [False, True])
def test_numeric_location_survives_inventory_failure_without_acceptance(token, found, bad_inventory):
    old, report, summary = queue_case(token)
    old["heading_reviews"] = []
    pack = fact_pack(summary)
    source = SourceIndex.build(report, pack)
    value = index_review(compact(old), source)["evaluation"]
    value["source_digest"] = source.source_digest
    if bad_inventory:
        value["reviewed_blocks"] = [64]
    raw = compact(value)
    rows = collect_diagnostics(raw, report, pack)
    row = next(r for r in rows if "unsupported_numbers" in r)
    assert row["audit_index"] == 1 and row["claim_index"] == 0
    assert source.resolve(row["quote_ref"]) == report
    hint = row["unsupported_numbers"][0]
    assert hint["token"] == str(token) and bool(hint["source_candidates"]) == found
    if found:
        assert all(path == "/queue_id" and ref.startswith("facts:recent_match:")
            for ref, path in hint["source_candidates"][0]["operands"])
    assert compact(value) == raw
    assert feedback(raw, report, pack)["omitted_errors"] == 0
    with pytest.raises(ValueError):
        expand_context(raw, report, pack)


def test_full_context_survives_without_local_anchor_false_positive():
    target = "经济差异较稳定。"
    definition = "下句的较稳定仅指这四场方向一致，不代表未来。"
    value, report, pack = wire(definition + "\n\n" + target + "\n\n建议[K1]")
    source = SourceIndex.build(report, pack)
    row = claim(value, report, pack, quote=target,
        context=dict(quote_ref=source.reference(definition), relation="defines_scope", explanation="下句指代"))
    raw = compact(value)
    assert collect_diagnostics(raw, report, pack) == []
    inspected = context_inspection(raw, report, pack)[0]
    assert inspected["claim_block"] == target and inspected["context_block"] == definition
    assert inspected["semantic_verdict"] == "not_determined_by_program"
    row["scope_anchor"] = "不存在"
    detail = next(r for r in collect_diagnostics(compact(value), report, pack) if "invalid_anchor" in r)
    assert detail["anchor_source_ref"] == source.reference(definition)


@pytest.mark.parametrize("raw,code", [
    ('{"secret":"do not echo"}', "invalid_json_or_context_schema"),
    ('{"score":1,"score":2}', "compact_duplicate_key"),
    ('[]', "invalid_json_or_context_schema"),
    ('not json', "invalid_json_or_context_schema"),
    (None, "invalid_json_or_context_schema"),
])
def test_malformed_response_does_not_echo_exception_text(raw, code):
    _, report, pack = wire()
    rows = collect_diagnostics(raw, report, pack)
    assert rows == [{"codes": [code]}]


def test_feedback_is_bounded_and_stale_source_does_not_generate_hints():
    value, report, pack = wire()
    row = claim(value, report, pack, anchor="错误范围")
    value["audits"][1]["claims"] = [copy.deepcopy(row) for _ in range(24)]
    projected = feedback(compact(value), report, pack)
    assert projected["omitted_errors"] > 0 and len(projected["errors"]) <= 12
    assert len(json.dumps(projected, ensure_ascii=False)) <= 3000
    value["source_digest"] = "0" * 64
    assert collect_diagnostics(compact(value), report, pack) == [{"codes": ["context_source_digest_mismatch"]}]
