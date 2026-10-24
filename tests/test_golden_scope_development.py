from types import SimpleNamespace

import pytest

from scripts import run_golden_inference_development as runner


@pytest.mark.parametrize("label,status,scope,expected", [
    ("clarify", "supported", "ambiguous", True),
    ("clarify", "unsupported", "beyond_sample", False),
    ("reject", "supported", "ambiguous", False),
    ("reject", "unsupported", "beyond_sample", True),
])
def test_three_way_scoring_requires_the_matching_claim_finding(monkeypatch, label, status, scope, expected):
    result = SimpleNamespace(verdict=SimpleNamespace(value="needs_revision"), score=80)
    case = dict(id="case", expected=label, scope="ambiguous", claim="whole claim")
    payload = {"issues": [{"quote": "whole claim", "category": "other"}],
        "audits": [{"claims": [{"quote": "whole claim", "status": status, "scope": scope}]}]}
    monkeypatch.setattr(runner, "_evaluation_payload", lambda _: payload)
    assert runner.score_case(case, result)["matched"] is expected
    payload["audits"][0]["claims"][0]["quote"] = "unrelated finding"
    assert runner.score_case(case, result)["matched"] is False


def test_scope_rejects_unbounded_combined_selection_before_io():
    with pytest.raises(ValueError, match="scope_requires_separate"):
        runner.run(SimpleNamespace(scope=True, report_only=False, controls_only=False))
