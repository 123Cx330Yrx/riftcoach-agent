from copy import deepcopy

import pytest

from scripts import check_golden_scope_contrast_controls as checks


def data():
    return deepcopy(checks.load_source())


def test_source_and_math_pass_without_claiming_semantic_or_model_acceptance():
    result = checks.validate(data())
    assert result["case_count"] == 7
    assert result["expected_math"]["MIDDLE"]["cs_per_min"]["loss_mean"] == "10"
    assert result["expected_math"]["selected"]["gold_per_min"]["loss_mean"] == "1820/3"
    assert result["model_requests_created"] == 0
    assert result["semantic_labels_validated"] is False
    assert result["natural_language_entailment_proven"] is False
    assert result["model_quality_proven"] is False


@pytest.mark.parametrize("field,value,code", [
    ("loss_mean_fraction", "1819/3", "derived_mean_mismatch"),
    ("loss_mean_display_2dp", "606.66", "rounded_mean_mismatch"),
    ("all_pairs", "greater", "derived_relation_mismatch"),
])
def test_raw_values_disprove_tampered_expected_arithmetic(field, value, code):
    value_data = data()
    value_data["derived_checks"]["cohorts"]["selected"]["gold_per_min"][field] = value
    with pytest.raises(ValueError, match=code):
        checks.validate(value_data)


def test_missing_member_is_not_silently_treated_as_complete_cohort():
    value = data()
    value["derived_checks"]["cohorts"]["selected"]["losses"] = [3, 4]
    with pytest.raises(ValueError, match="cohort_members_mismatch"):
        checks.validate(value)


def test_changed_raw_metric_is_detected_even_after_rehashing_fixture():
    value = data()
    value["fixture"]["match_rows"][4]["cs_per_min"] = 10
    value["fixture_sha256"] = checks.fixture_hash(value["fixture"])
    with pytest.raises(ValueError, match="derived_mean_mismatch"):
        checks.validate(value)


def test_boolean_is_not_an_evidence_number():
    value = data()
    value["fixture"]["match_rows"][0]["evidence_ref"] = True
    with pytest.raises(ValueError, match="reference_invalid"):
        checks.validate(value)


def test_wrong_corrected_number_cannot_hide_in_negative_case():
    value = data()
    value["cases"][3]["expected"]["correct_values"]["loss_mean"] = "7"
    with pytest.raises(ValueError, match="corrected_math_mismatch"):
        checks.validate(value)


def test_ambiguity_does_not_allow_cherry_picking_the_supported_group():
    value = data()
    value["cases"][5]["expected"]["cohort"] = "selected"
    with pytest.raises(ValueError, match="ambiguity_preselected"):
        checks.validate(value)


def test_ambiguous_alternative_truth_flags_are_checked_against_raw_math():
    value = data()
    value["cases"][5]["expected"]["alternatives"][0]["supports_target"] = True
    with pytest.raises(ValueError, match="alternative_math_mismatch"):
        checks.validate(value)


def test_nonexistent_context_is_rejected():
    value = data()
    value["cases"][0]["expected"]["scope_evidence"] = ["不存在的范围说明"]
    with pytest.raises(ValueError, match="context_not_unique"):
        checks.validate(value)


def test_real_but_wrong_antecedent_is_label_drift_not_automated_semantic_proof():
    value = data()
    value["cases"][6]["expected"]["scope_evidence"] = ["旁注：四场中单的赢局补刀均值为9/分钟，输局为10/分钟。"]
    with pytest.raises(ValueError, match="analyst_case_changed"):
        checks.validate(value)


def test_report_edit_is_rejected_even_when_its_hash_is_recomputed():
    value = data()
    case = value["cases"][0]
    case["report"] += "\n\n附加新结论。"
    case["report_sha256"] = checks.sha256(case["report"].encode())
    with pytest.raises(ValueError, match="report_source_changed"):
        checks.validate(value)


def test_duplicate_case_id_is_rejected():
    value = data()
    value["cases"][1]["id"] = value["cases"][0]["id"]
    with pytest.raises(ValueError, match="case_inventory_changed"):
        checks.validate(value)


def test_expected_values_cannot_be_declared_model_input():
    value = data()
    value["model_input_boundary"]["allowed"].append("case.expected")
    with pytest.raises(ValueError, match="authority_boundary_changed"):
        checks.validate(value)


def test_source_identity_does_not_alias_booleans_to_numbers():
    value = data()
    value["cases"][0]["expected"]["required_operand_refs"][0] = True
    with pytest.raises(ValueError, match="analyst_case_changed"):
        checks.validate(value)
    value = data()
    value["model_evaluated"] = 0
    with pytest.raises(ValueError, match="authority_boundary_changed"):
        checks.validate(value)


def test_old_frozen_source_pointer_cannot_be_replaced():
    value = data()
    value["frozen_dataset_unchanged"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen_pointer_changed"):
        checks.validate(value)


def test_duplicate_json_keys_fail_instead_of_silently_overwriting(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"expected":1,"expected":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate_json_key"):
        checks.read_json(path)
