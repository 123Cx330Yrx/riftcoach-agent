import json

import pytest

from app.evaluation.golden_compact_coverage import encode_coverage, expand_response
from app.evaluation.golden_inference_audit import inference_facts
from app.evaluation.golden_inference_scope_v2 import EvaluationResponseModelV17
from tests.test_golden_inference_scope_v2 import anchored_payload

REPORT = "A stable difference. [K1]"


def compact():
    canonical = EvaluationResponseModelV17.model_validate(anchored_payload())
    value = canonical.model_dump(mode="json")
    value["coverage"] = encode_coverage(canonical.coverage)
    return canonical, value


def test_roundtrip_preserves_all_evidence_and_clarification():
    canonical, value = compact()
    restored = expand_response(json.dumps(value), REPORT, inference_facts({}))
    assert restored == canonical
    assert restored.verdict == "needs_revision"
    assert restored.issues == canonical.issues


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "stale", "unknown",
                                     "integer_boolean", "extra_cell", "hidden_ambiguity",
                                     "missing_issue", "bad_anchor", "bad_evidence"])
def test_compaction_never_repairs_or_hides_invalid_evidence(mutation):
    _, value = compact()
    if mutation == "missing": value["coverage"] = []
    elif mutation == "duplicate": value["coverage"] *= 2
    elif mutation == "stale": value["coverage"][0][0] = "b01-00000000"
    elif mutation == "unknown": value["coverage"][0][1] = "X"
    elif mutation == "integer_boolean": value["coverage"][0][3] = 1
    elif mutation == "extra_cell": value["coverage"][0].append("extra")
    elif mutation == "hidden_ambiguity": value["coverage"][0][3] = False
    elif mutation == "missing_issue": value.update(issues=[], verdict="pass")
    elif mutation == "bad_anchor": value["audits"][1]["claims"][0]["scope_anchor"] = "invented"
    else: value["audits"][1]["claims"][0]["evidence_refs"] = ["invented"]
    with pytest.raises(ValueError):
        expand_response(json.dumps(value), REPORT, inference_facts({}))


def test_rejects_duplicate_json_keys():
    _, value = compact()
    raw = json.dumps(value)
    with pytest.raises(ValueError, match="compact_duplicate_key"):
        expand_response('{"score": 0,' + raw[1:], REPORT, inference_facts({}))


def test_reordered_rows_rejected_even_when_ids_and_count_are_valid():
    from app.evaluation.golden_inference_coverage import report_blocks
    _, value = compact()
    report = REPORT + "\n\n## Boundary"
    value["coverage"].append([report_blocks(report)[1]["block_id"], "N", "N", False])
    expand_response(json.dumps(value), report, inference_facts({}))
    value["coverage"].reverse()
    with pytest.raises(ValueError, match="missing_duplicate_or_stale"):
        expand_response(json.dumps(value), report, inference_facts({}))


def test_explicit_sample_support_survives_roundtrip():
    from app.evaluation.golden_inference_coverage import report_blocks
    canonical, _ = compact()
    report = "这四场方向一致。 [K1]"
    value = canonical.model_dump(mode="json")
    value.update(issues=[], verdict="pass")
    value["audits"][1]["claims"][0].update(quote=report, scope="selected_sample", scope_anchor="这四场")
    value["coverage"] = [[report_blocks(report)[0]["block_id"], "N", "S", False]]
    restored = expand_response(json.dumps(value), report, inference_facts({}))
    assert restored.verdict == "pass"
    assert restored.audits[1].claims[0].quote == report
