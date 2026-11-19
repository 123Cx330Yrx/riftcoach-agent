from scripts.audit_golden_meaning_first_result import inspect_json
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_meaning_first_review import reading
from tests.test_golden_comparison_reassessment import inputs_for


def test_identical_duplicate_remains_rejected_even_if_other_fields_validate():
    raw = compact(reading(inputs_for())).replace('"block":1', '"block":1,"block":1')
    result = inspect_json(raw)
    assert result["strict_error"] == "compact_duplicate_key"
    assert result["duplicate_keys"] == [{"path": "/readings/0/quote_ref/block", "identical": True}]
    assert result["projected_schema_valid"]
    assert not result["projection_is_live_acceptance"]


def test_conflicting_duplicate_has_no_silent_first_or_last_value_projection():
    raw = compact(reading(inputs_for())).replace('"block":1', '"block":1,"block":2')
    result = inspect_json(raw)
    assert result["projection_skipped"] == "conflicting_duplicate_values"
    assert "projected_schema_valid" not in result


def test_duplicate_in_array_has_precise_path_and_type_sensitive_equality():
    result = inspect_json('{"rows":[{"x":true,"x":1}]}')
    assert result["duplicate_keys"] == [{"path": "/rows/0/x", "identical": False}]
