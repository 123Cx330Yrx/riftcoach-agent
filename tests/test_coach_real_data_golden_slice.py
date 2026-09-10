from __future__ import annotations

import pytest

from app.evaluation.coach_real_data_golden_slice import GoldenSliceConfig, preflight


def test_golden_slice_preflight_is_network_free_and_freezes_budget() -> None:
    gate = preflight(
        GoldenSliceConfig(
            riot_id="DK ShowMaker#KR1",
            routing_region="asia",
            count=5,
            position="mid",
            run_id="golden_20260910_showmaker",
        )
    )
    assert gate.network_allowed is False
    assert gate.max_riot_calls == 12
    assert gate.max_ddragon_requests == 5
    assert gate.max_opgg_tool_calls == 1


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("routing_region", "kr", "routing_region_invalid"),
        ("position", "unknown", "position_invalid"),
        ("queue", 430, "queue_not_admitted"),
    ],
)
def test_golden_slice_preflight_rejects_unbounded_or_unadmitted_inputs(field, value, error):
    values = {
        "riot_id": "DK ShowMaker#KR1",
        "routing_region": "asia",
        "count": 5,
        "position": "mid",
        "run_id": "golden_20260910_showmaker",
    }
    values[field] = value
    with pytest.raises(ValueError, match=f"^{error}$"):
        preflight(GoldenSliceConfig(**values))
