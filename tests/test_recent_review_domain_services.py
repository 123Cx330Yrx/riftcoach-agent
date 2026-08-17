from __future__ import annotations

import json
from pathlib import Path

from app.lol.player_summary import (
    RiotPlayerSummaryBuilder,
    build_player_summary,
)
from app.lol.report_renderer import render_deterministic_report
from scripts.build_player_summary import build_player_summary as cli_summary_builder
from scripts.generate_markdown_report import build_report as cli_report_renderer
from tests.test_stage1_pipeline import FakeClient, FakeDataDragon


def test_summary_cli_reuses_the_app_level_domain_function() -> None:
    assert cli_summary_builder is build_player_summary


def test_summary_builder_keeps_stage_one_short_match_semantics() -> None:
    summary = RiotPlayerSummaryBuilder(
        client=FakeClient(),
        ddragon=FakeDataDragon(),
        min_duration_seconds=300,
    ).build(
        game_name="Player Name",
        tag_line="CN1",
        count=10,
        queue=420,
    )

    assert summary["recent_summary"]["games_analyzed"] == 1
    assert len(summary["excluded_matches"]) == 1
    assert summary["matches"][1]["timeline_status"] == "unavailable"


def test_report_cli_and_app_renderer_are_byte_identical() -> None:
    summary = json.loads(
        Path("examples/fixtures/player_summary_demo.json").read_text(
            encoding="utf-8"
        )
    )

    app_report = render_deterministic_report(summary)

    assert cli_report_renderer(summary) == app_report
    assert app_report.encode("utf-8") == cli_report_renderer(summary).encode(
        "utf-8"
    )
