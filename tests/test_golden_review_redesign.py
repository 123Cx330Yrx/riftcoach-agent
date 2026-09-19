"""Offline correspondence experiment only; no model accuracy claims."""
from copy import deepcopy

import pytest

from app.evaluation.golden_review_experiment import SourceIndex
from scripts.check_golden_review_redesign import handles, join_by_handle


def test_explicit_handles_keep_source_when_responses_are_reordered():
    source = SourceIndex.build("## 持续存在的差距\n\n数字正确。\n\n但已经证明长期能力不足。", {"facts": {}})
    expected = handles(source, [{"block": 1}, {"block": 2}, {"block": 3}])
    rows = [{"target_id": "t003", "finding": "later_conflict"},
            {"target_id": "t001", "finding": "heading_needs_clarification"},
            {"target_id": "t002", "finding": None}]
    before = deepcopy(rows)
    joined = join_by_handle(expected, rows)
    assert [(s["quote"], r["finding"]) for s, r in joined] == [
        ("## 持续存在的差距", "heading_needs_clarification"),
        ("数字正确。", None), ("但已经证明长期能力不足。", "later_conflict")]
    assert rows == before


@pytest.mark.parametrize("rows,code", [
    ([{"target_id": "t002"}], "missing_target_handle"),
    ([{"target_id": "t001"}, {"target_id": "t001"}], "duplicate_target_handle"),
    ([{"target_id": "t003"}], "unknown_target_handle"),
    ([{"explanation": "旧位置式响应不能追补身份"}], "unknown_target_handle"),
])
def test_bad_handles_cannot_be_padded_guessed_or_shifted(rows, code):
    with pytest.raises(ValueError, match=code):
        join_by_handle({"t001": {}, "t002": {}}, rows)
