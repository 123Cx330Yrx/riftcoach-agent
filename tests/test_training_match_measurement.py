from copy import deepcopy
from datetime import timedelta

import pytest

from app.lol.match_analyzer import analyze_match_detail
from app.memory.training_measurement import match_measurements
from app.memory.models import CandidateKind, MemoryOperation, RelationshipRole, TargetScope
from app.memory.training_models import TrainingContractError, parse_training_progress_write
from uuid import uuid4
from tests.memory_candidate_postgres_support import BASE
from tests.test_run_query_service import PLAYER_SUMMARY
from tests.test_stage1_pipeline import match_detail


def measured_summary():
    summary = deepcopy(PLAYER_SUMMARY)
    summary["metadata"]["generated_at_utc"] = (BASE + timedelta(days=99)).isoformat()
    for index, row in enumerate(summary["matches"]):
        row.update(game_end_timestamp_ms=int((BASE + timedelta(minutes=index + 1)).timestamp() * 1000),
                   queue_id=420, deaths_before_15=index, vision_score=20 + index)
    return summary


def extract(summary, metrics=None):
    return match_measurements(
        summary, metrics=metrics or [{"metric_key": "match.deaths_before_15", "unit": "count"}],
        plan_created_at=BASE, task_created_at=BASE + timedelta(minutes=3), summary_sha256="a" * 64,
    )


def test_measured_zero_uses_match_end_not_generated_time():
    rows = extract(measured_summary())
    assert [item[1] for item in rows] == [0, 1]
    assert rows[0][2].observed_at == BASE + timedelta(minutes=1)
    assert rows[0][2].position == "mid"


@pytest.mark.parametrize("changes", [
    {"game_end_timestamp_ms": None}, {"game_end_timestamp_ms": True},
    {"game_end_timestamp_ms": "123"}, {"game_end_timestamp_ms": -1},
    {"game_end_timestamp_ms": int((BASE - timedelta(seconds=1)).timestamp() * 1000)},
    {"game_end_timestamp_ms": int((BASE + timedelta(days=1)).timestamp() * 1000)},
    {"deaths_before_15": None}, {"deaths_before_15": True},
    {"deaths_before_15": -1}, {"deaths_before_15": 0.5}, {"timeline_status": "unavailable"},
    {"included_in_aggregate": False}, {"role": "UNKNOWN"}, {"queue_id": None},
])
def test_unmeasured_rows_are_skipped_without_inventing_values(changes):
    summary = measured_summary()
    summary["matches"][0].update(changes)
    assert [item[1] for item in extract(summary)] == [1]


def test_legacy_keys_wrong_units_and_missing_timeline_do_not_change_scope():
    summary = measured_summary()
    assert extract(summary, [{"metric_key": "deaths_before_15", "unit": "count"}]) == ()
    assert extract(summary, [{"metric_key": "match.deaths_before_15", "unit": "ratio"}]) == ()
    summary["matches"][0]["timeline_status"] = "unavailable"
    rows = extract(summary, [{"metric_key": "match.vision_score", "unit": "score"}])
    assert [item[1] for item in rows] == [20, 21]  # Detail metric does not require timeline.


def test_duplicate_match_identity_invalidates_source():
    summary = measured_summary()
    summary["matches"].append(deepcopy(summary["matches"][0]))
    with pytest.raises(ValueError, match="match_identity_invalid"):
        extract(summary)


def test_non_finite_json_invalidates_source_before_candidate_generation():
    summary = measured_summary()
    summary["matches"][0]["deaths_before_15"] = float("nan")
    with pytest.raises(ValueError):
        extract(summary)


def test_detail_preserves_only_actual_end_timestamp():
    detail = match_detail("MATCH_NORMAL", 1800)
    puuid = detail["info"]["participants"][0]["puuid"]
    assert analyze_match_detail(detail, puuid)["game_end_timestamp_ms"] is None
    detail["info"]["gameEndTimestamp"] = 1787234460000
    assert analyze_match_detail(detail, puuid)["game_end_timestamp_ms"] == 1787234460000
    detail["info"]["gameEndTimestamp"] = True
    assert analyze_match_detail(detail, puuid)["game_end_timestamp_ms"] is None


@pytest.mark.parametrize("invalid", ["missing", "wrong_time", "legacy_scope", "correction"])
def test_acceptance_parser_cannot_relabel_time_scope_or_correction(invalid):
    key, value, measurement = extract(measured_summary())[0]
    envelope = {"value": {"plan_id": str(uuid4()), "metric_key": key, "metric_value": value,
                           "observed_at": measurement.observed_at.isoformat()},
                "measurement": measurement.model_dump(mode="json")}
    if invalid == "missing":
        envelope.pop("measurement")
    elif invalid == "wrong_time":
        envelope["value"]["observed_at"] = BASE.isoformat()
    elif invalid == "legacy_scope":
        envelope["value"]["metric_key"] = "deaths_before_15"
    else:
        envelope["value"]["supersedes_progress_id"] = str(uuid4())
    with pytest.raises(TrainingContractError):
        parse_training_progress_write(target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.TRAINING_PROGRESS, operation=MemoryOperation.APPEND,
            relationship_role=RelationshipRole.SELF, proposal_payload=envelope)
