import json

import pytest

from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_fact_operations import OperationEvaluation, validate_operations, expand_operations
from app.evaluation.golden_compact_coverage import encode_coverage
from app.evaluation.golden_inference_coverage import report_blocks
from tests.test_golden_fact_candidate import payload, summary


def operation_payload(quote, op, operands, token):
    value, report = payload(quote)
    claim = value["audits"][1]["claims"][0]
    claim["evidence_refs"] = list(dict.fromkeys(ref for ref, _ in operands))
    claim["numeric_bindings"] = [{"op": op, "operands": operands, "token": token}]
    return value, report


WIN = ["role:MIDDLE:win:gold_per_min", "/mean"]
LOSS = ["role:MIDDLE:loss:gold_per_min", "/mean"]


@pytest.mark.parametrize("op,operands,token,quote", [
    ("difference", [WIN, LOSS], "72", "中单经济差约 72/分。"),
    ("difference", [LOSS, WIN], "-72.48", "中单经济差 -72.48/分。"),
    ("ratio_percent", [LOSS, WIN], "85.66", "中单输局经济为赢局的 85.66%。"),
    ("value", [WIN], "505.29", "中单赢局经济 505.29/分。"),
])
def test_operations_round_once_and_preserve_order(op, operands, token, quote):
    value, report = operation_payload(quote, op, operands, token)
    canonical = OperationEvaluation.model_validate(value)
    assert validate_operations(canonical, report, fact_pack(summary()))["semantic_approval"] is False
    wire = canonical.model_dump(mode="json")
    wire["coverage"] = encode_coverage(canonical.coverage)
    assert expand_operations(json.dumps(wire), report, fact_pack(summary())) == canonical


def test_fraction_to_percent_uses_actual_ratio_units():
    source = summary()
    source["matches"][0]["damage_share"] = 0.2232
    value, report = operation_payload("单局伤害占比 22.32%。", "percent", [["facts:recent_match:00", "/damage_share"]], "22.32")
    validate_operations(OperationEvaluation.model_validate(value), report, fact_pack(source))


@pytest.mark.parametrize("op,operands,token,error", [
    ("difference", [LOSS, WIN], "72", "value_mismatch"),
    ("difference", [WIN, ["role:UTILITY:loss:gold_per_min", "/mean"]], "405", "role_mismatch"),
    ("difference", [WIN, ["role:MIDDLE:win:vision_score", "/games"]], "504", "metric_mismatch"),
    ("percent", [WIN], "50529", "percent_unit_invalid"),
])
def test_invalid_math_and_units_rejected(op, operands, token, error):
    value, report = operation_payload(f"数值 {token}。", op, operands, token)
    with pytest.raises(ValueError, match=error):
        validate_operations(OperationEvaluation.model_validate(value), report, fact_pack(summary()))


def test_zero_denominator_and_wrong_operand_count():
    source = summary()
    source["matches"][1]["gold_per_min"] = 0
    value, report = operation_payload("经济比 100%。", "ratio_percent", [WIN, LOSS], "100")
    with pytest.raises(ValueError, match="zero_denominator"):
        validate_operations(OperationEvaluation.model_validate(value), report, fact_pack(source))
    value["audits"][1]["claims"][0]["numeric_bindings"][0]["operands"].pop()
    with pytest.raises(ValueError, match="arity_invalid"):
        OperationEvaluation.model_validate(value)


def test_compact_restore_rejects_duplicate_keys_and_stale_coverage():
    value, report = operation_payload("经济 505.29。", "value", [WIN], "505.29")
    canonical = OperationEvaluation.model_validate(value)
    value["coverage"] = encode_coverage(canonical.coverage)
    raw = json.dumps(value)
    with pytest.raises(ValueError, match="duplicate_key"):
        expand_operations('{"score":0,' + raw[1:], report, fact_pack(summary()))
    value["coverage"][0][0] = "b01-00000000"
    with pytest.raises(ValueError, match="missing_duplicate_or_stale"):
        expand_operations(json.dumps(value), report, fact_pack(summary()))
