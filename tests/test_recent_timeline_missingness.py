"""Missing timelines must not become measured zero in downstream summaries."""

from copy import deepcopy

import pytest

from app.api.actor import ActorContext
from app.lol.match_analyzer import aggregate_recent_matches
from app.lol.player_summary import RiotPlayerSummaryBuilder
from app.lol.report_renderer import build_findings, render_deterministic_report
from app.mcp.server import RiftCoachMcpServer
from app.product.run_query import RunQueryService
from tests.test_mcp_server import FakeFacade, _client
from tests.test_run_query_service import _create_terminal_run
from tests.test_stage1_pipeline import FakeClient, FakeDataDragon, match_detail


class TimelineClient(FakeClient):
    def __init__(self, unavailable):
        self.unavailable = unavailable

    def get_match_detail(self, match_id):
        result = match_detail(match_id, 1800)
        result["info"]["participants"][0]["win"] = match_id == "MATCH_NORMAL"
        return result

    def get_match_timeline(self, match_id):
        if match_id in self.unavailable:
            raise RuntimeError("synthetic unavailable timeline")
        result = super().get_match_timeline("MATCH_NORMAL")
        if match_id == "MATCH_SHORT":
            result["info"]["frames"][0]["events"] = [
                {"type": "CHAMPION_KILL", "victimId": 1, "timestamp": 600000}
            ]
        return result


@pytest.mark.parametrize(
    "unavailable, expected, wins, losses",
    [
        ({"MATCH_NORMAL", "MATCH_SHORT"}, None, None, None),
        ({"MATCH_NORMAL"}, None, None, 1.0),
        ({"MATCH_SHORT"}, None, 0.0, None),
        (set(), 0.5, 0.0, 1.0),
    ],
    ids=["all-missing", "winning-timeline-missing", "losing-timeline-missing", "complete"],
)
def test_missingness_survives_summary_report_verified_query_and_mcp(
    tmp_path, unavailable, expected, wins, losses,
):
    summary = RiotPlayerSummaryBuilder(
        client=TimelineClient(unavailable), ddragon=FakeDataDragon(),
    ).build(game_name="Fixture Player", tag_line="TEST", count=2, queue=420)
    recent = summary["recent_summary"]
    assert recent["averages"]["deaths_before_15"] == expected
    assert recent["win_loss_comparison"]["wins"]["deaths_before_15"] == wins
    assert recent["win_loss_comparison"]["losses"]["deaths_before_15"] == losses
    if expected is None:
        assert not any("前 15 分钟平均死亡" in value for value in build_findings(recent))
        assert "| 15分钟前死亡 | N/A |" in render_deterministic_report(summary)

    _, receipt = _create_terminal_run(tmp_path, player_summary=summary)
    view = RunQueryService(tmp_path).get_recent_summary(receipt.run_id)
    assert view.averages.deaths_before_15 == expected
    assert view.win_loss_comparison.wins.deaths_before_15 == wins
    assert view.win_loss_comparison.losses.deaths_before_15 == losses

    class QueryFacade(FakeFacade):
        def recent_summary(self, *, actor, run_id):
            assert run_id == receipt.run_id
            return view.model_dump(mode="json")

    facade = QueryFacade()
    client, _ = _client(RiftCoachMcpServer(
        facade=facade, actor_provider=lambda: ActorContext(owner_id="fixture-owner"),
    ), facade)
    client.initialize()
    client.discover()
    result = client.call("riftcoach.recent_summary", {"run_id": receipt.run_id})
    assert result.success
    assert result.structured_content["averages"]["deaths_before_15"] == expected
    assert result.structured_content["win_loss_comparison"]["wins"]["deaths_before_15"] == wins


def test_unavailable_timeline_cannot_supply_a_stale_numeric_count():
    summary = RiotPlayerSummaryBuilder(
        client=TimelineClient({"MATCH_SHORT"}), ddragon=FakeDataDragon(),
    ).build(game_name="Fixture Player", tag_line="TEST", count=2, queue=420)
    rows = deepcopy(summary["matches"])
    rows[1]["deaths_before_15"] = 0
    assert aggregate_recent_matches(rows)["averages"]["deaths_before_15"] is None


def test_empty_outcome_group_has_no_early_death_measurement():
    summary = RiotPlayerSummaryBuilder(
        client=TimelineClient(set()), ddragon=FakeDataDragon(),
    ).build(game_name="Fixture Player", tag_line="TEST", count=2, queue=420)
    rows = [summary["matches"][0]]
    recent = aggregate_recent_matches(rows)
    assert recent["averages"]["deaths_before_15"] == 0.0
    assert recent["win_loss_comparison"]["losses"]["deaths_before_15"] is None
