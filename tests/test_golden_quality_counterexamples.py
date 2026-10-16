import copy
import json

import pytest

from scripts.check_golden_quality_counterexamples import DATASET, check_evidence


def test_saved_evidence_reverses_mixed_role_cs_comparison_without_claiming_model_pass():
    result = check_evidence(json.loads(DATASET.read_text(encoding="utf-8")))
    assert result["mid_loss_cs_per_min"] == "9.01"
    assert result["mid_win_cs_per_min"] == "8.805"
    assert result["automatic_quality_fix_verified"] is False
    assert result["model_evaluated"] is False


@pytest.mark.parametrize("mutation", ["role", "outcome", "excluded", "metric", "drop_positive"])
def test_changed_cohort_or_missing_positive_controls_cannot_reuse_frozen_evidence(mutation):
    data = copy.deepcopy(json.loads(DATASET.read_text(encoding="utf-8")))
    if mutation == "role":
        data["samples"][1]["role"] = "MIDDLE"
    elif mutation == "outcome":
        data["samples"][0]["win"] = "true"
    elif mutation == "excluded":
        data["samples"][0]["included_in_aggregate"] = False
    elif mutation == "metric":
        data["samples"][2]["cs_per_min"] = 1
    else:
        data["cases"] = [c for c in data["cases"] if c["expected"] == "reject"]
    with pytest.raises(ValueError):
        check_evidence(data)
