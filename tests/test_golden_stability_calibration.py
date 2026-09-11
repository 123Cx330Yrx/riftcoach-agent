import json

import pytest

from scripts.check_golden_stability_calibration import DATASET, SOURCE, check_evidence


def test_sample_local_pairwise_evidence_does_not_claim_semantic_validation():
    result = check_evidence(json.loads(DATASET.read_text(encoding="utf-8")), SOURCE.read_bytes())
    assert result["facts"]["damage_per_min"]["loss_mean"] == "617.52"
    assert result["facts"]["gold_per_min"]["win_mean"] == "505.29"
    assert result["model_evaluated"] is result["semantic_fix_verified"] is False
    assert result["held_out"] is False


@pytest.mark.parametrize("mutation", ["source", "duplicate", "missing_clarify"])
def test_changed_evidence_or_lost_ambiguity_control_rejected(mutation):
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    source = SOURCE.read_bytes()
    if mutation == "source":
        source += b" "
    elif mutation == "duplicate":
        data["cases"][1]["id"] = data["cases"][0]["id"]
    else:
        data["cases"] = [c for c in data["cases"] if c["expected"] != "clarify"]
    with pytest.raises(ValueError):
        check_evidence(data, source)


def test_windows_and_linux_checkouts_bind_the_same_source_content():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    lf = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    assert check_evidence(data, lf) == check_evidence(data, lf.replace(b"\n", b"\r\n"))
    altered = lf.replace(b"1143.4", b"1143.5")
    with pytest.raises(ValueError, match="source evidence changed"):
        check_evidence(data, altered)
