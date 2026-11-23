import json

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from scripts.check_golden_review_workflow import measure_run
from tests.test_golden_review_experiment import example


@pytest.mark.parametrize("suffix", ["", ' {"score":100}'])
def test_measurement_keeps_interruption_and_does_not_accept_json_prefix(tmp_path, suffix):
    value, report, pack = example()
    (tmp_path / "plan.json").write_text(json.dumps(dict(contract=dict(version="1.3.26"),
        head_sha="a" * 40, selected_case_ids=["one", "two", "three"])), encoding="utf-8")
    pair = tmp_path / "pair-01"
    pair.mkdir()
    for case_id, first_call in [("one", 1), ("two", 2)]:
        (pair / f"{case_id}-input.json").write_text(json.dumps(dict(first_call=first_call, report=report,
            report_sha256=digest(report))), encoding="utf-8")
    (pair / "one-result.json").write_text("{}", encoding="utf-8")
    original = compact(value) + suffix
    response_path = pair / "response-001.json"
    response_path.write_text(json.dumps(dict(content=original, finish_reason="stop")), encoding="utf-8")
    measured = measure_run(tmp_path, pack)
    assert [measured[k] for k in ("started", "finalized", "interrupted", "not_started")] == [2, 1, 1, 1]
    assert measured["responses"] == 1
    assert measured["original_valid_responses"] == measured["projectable_responses"] == (0 if suffix else 1)
    assert json.loads(response_path.read_text(encoding="utf-8"))["content"] == original
    saved = json.loads((pair / "one-input.json").read_text(encoding="utf-8"))
    saved["report"] += "篡改"
    (pair / "one-input.json").write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(ValueError, match="identity_changed"):
        measure_run(tmp_path, pack)
