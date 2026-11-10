"""Published Summary arithmetic follows the report's decimal rounding rule."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.lol.match_analyzer import aggregate_recent_matches
from app.lol.report_renderer import render_deterministic_report


def summary_with_rows(**columns):
    summary = json.loads((Path(__file__).resolve().parents[1]
        / "examples/fixtures/player_summary_demo.json").read_text(encoding="utf-8"))
    template = summary["matches"][0]
    count = len(next(iter(columns.values())))
    rows = []
    for index in range(count):
        row = deepcopy(template)
        row.update(match_id=f"ROUNDING_{index}", win=True)
        row.update({key: values[index] for key, values in columns.items()})
        rows.append(row)
    summary["matches"] = rows
    summary["recent_summary"] = aggregate_recent_matches(rows)
    return summary


def test_winning_means_and_rendered_evidence_agree_on_decimal_ties():
    # Two measured rows from the failure mechanism, without player identifiers.
    summary = summary_with_rows(cs_per_min=[8.71, 7.56],
                                damage_per_min=[936.73, 1625.10])
    recent = summary["recent_summary"]
    assert recent["win_loss_comparison"]["wins"]["cs_per_min"] == 8.14
    assert recent["win_loss_comparison"]["wins"]["damage_per_min"] == 1280.92
    assert recent["averages"]["cs_per_min"] == 8.14
    report = render_deterministic_report(summary)
    assert "| 补刀/分钟 | 8.14 |" in report
    assert "| 伤害/分钟 | 1280.92 |" in report


@pytest.mark.parametrize("values, expected", [
    ([7.56, 7.56], 7.56),
    ([8.71, 7.55], 8.13),
    ([8.71, 7.54], 8.13),
    ([0.0, 0.0], 0.0),
    ([None, 7.56], 7.56),
    ([None, None], 0.0),
])
def test_correct_values_and_existing_missingness_are_preserved(values, expected):
    summary = summary_with_rows(cs_per_min=values)
    assert summary["recent_summary"]["averages"]["cs_per_min"] == expected


def test_percentage_mean_uses_decimal_before_scaling_and_rounding():
    summary = summary_with_rows(kill_participation=[0.284, 0.285])
    assert summary["recent_summary"]["averages"]["kill_participation_percent"] == 28.5


@pytest.mark.parametrize("values, expected, value_type", [
    ([510, 540], 525, int),
    ([510, 511], 510.5, float),
    ([1, 1, 2], 1.33, float),
    ([525.0, 525.0], 525.0, float),
    ([510, 540.0], 525.0, float),
    ([None, 510, 540], 525, int),
    ([None, None], 0.0, float),
])
def test_json_number_types_remain_stable_when_rounding_does_not_change_value(values, expected, value_type):
    summary = summary_with_rows(damage_per_min=values)
    actual = summary["recent_summary"]["averages"]["damage_per_min"]
    assert actual == expected and type(actual) is value_type
    assert json.dumps({"value": actual}) == json.dumps({"value": expected})


def test_outcome_groups_stay_separate_and_input_rows_are_unchanged():
    summary = summary_with_rows(cs_per_min=[8.71, 7.56, 5.1, 5.3],
                                win=[True, True, False, False])
    rows = deepcopy(summary["matches"])
    result = aggregate_recent_matches(summary["matches"])
    assert result["win_loss_comparison"]["wins"]["cs_per_min"] == 8.14
    assert result["win_loss_comparison"]["losses"]["cs_per_min"] == 5.2
    assert summary["matches"] == rows
