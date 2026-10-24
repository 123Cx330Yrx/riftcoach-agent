"""The source renderer must not invent ability from mixed-role averages."""
import json
from pathlib import Path

import pytest

from app.lol.report_renderer import build_findings, render_deterministic_report


def sample():
    return dict(games_analyzed=5, wins=2, losses=3, win_rate=40,
        role_summary=[dict(role="MIDDLE", games=4), dict(role="UTILITY", games=1)],
        averages=dict(deaths_before_15=2.6),
        win_loss_comparison=dict(wins=dict(cs_per_min=8.8, gold_per_min=505.29, damage_per_min=1286.76),
            losses=dict(cs_per_min=6.45, gold_per_min=389.41, damage_per_min=591.34)))


def test_mixed_role_gaps_are_descriptive_and_do_not_become_skill_findings():
    findings = build_findings(sample())
    comparisons = [line for line in findings if "赢局均值为" in line]
    assert len(comparisons) == 3
    assert all("混合位置" in line for line in comparisons)
    assert "低 2.35" in comparisons[0] and "低 695.42" in comparisons[2]
    text = "\n".join(findings)
    for obsolete in ("发育稳定性在输局中有所下降", "输出转化能力或参团环境明显变差",
                     "整体表现较好", "不适合下稳定结论"):
        assert obsolete not in text
    assert "均值差异不代表逐局方向一致" in text


def test_same_role_numbers_do_not_establish_cause_and_missing_metrics_stay_missing():
    value = sample()
    value["role_summary"] = [dict(role="MIDDLE", games=4)]
    value["win_loss_comparison"] = dict(wins=dict(cs_per_min=8, vision_score=None),
        losses=dict(cs_per_min=9, vision_score=20))
    comparisons = [line for line in build_findings(value) if "赢局均值为" in line]
    assert len(comparisons) == 1
    assert "本次 MIDDLE 样本" in comparisons[0] and "高 1.00" in comparisons[0]


def test_absent_role_data_is_not_silently_called_same_position():
    value = sample()
    value["role_summary"] = []
    assert all("位置资料缺失" in row for row in build_findings(value) if "赢局均值为" in row)
    value["wins"] = 0
    assert not any("赢局均值为" in row for row in build_findings(value))


def test_report_labels_observed_frequency_without_inventing_training_intent():
    value = json.loads(Path("examples/fixtures/player_summary_demo.json").read_text(encoding="utf-8"))
    before = json.dumps(value, sort_keys=True)
    report = render_deterministic_report(value)
    assert "本样本出现最多的位置：" in report and "- 主要位置：" not in report
    assert "## 6. 样本统计观察" in report
    assert json.dumps(value, sort_keys=True) == before


def test_historical_acceptance_snapshot_is_bound_and_new_renderer_does_not_regrade_it():
    from app.evaluation.coach_product_acceptance import (
        admit_assets, frozen_deterministic_report, summary_from_inputs,
    )
    assets = admit_assets(Path.cwd())  # Original request/context manifest unchanged.
    summary = summary_from_inputs(assets.inputs)
    old = frozen_deterministic_report(summary)
    assert "## 6. 初步问题判断" in old
    assert old != render_deterministic_report(summary)
    summary["recent_summary"]["win_rate"] = 99
    with pytest.raises(ValueError, match="acceptance_asset_drift"):
        frozen_deterministic_report(summary)
