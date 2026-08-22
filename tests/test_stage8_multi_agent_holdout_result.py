from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.evaluation.stage8_experiment import StrategyId, load_experiment_record


ROOT = Path(__file__).resolve().parents[1]
RESULT = (
    ROOT
    / "data/evaluation/results/stage8/role_isolated_multi_agent_holdout_v1.json"
)
EXPECTED_SHA256 = (
    "94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8"
)
CODE_SHA = "180bc8b452603572d010b6e25b14ed71f6470ce7"


def test_frozen_holdout_result_is_sha_bound_body_free_and_rejected() -> None:
    raw = RESULT.read_bytes()
    record = load_experiment_record(RESULT)

    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256
    assert record.experiment_id == (
        "0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494"
    )
    assert record.code_sha == CODE_SHA
    assert record.public_ci_sha == CODE_SHA
    assert record.verdict == "reject_multi_agent"
    assert record.reason_codes == (
        "modeled_latency_threshold_missed",
        "no_incremental_benefit_over_parallel",
    )
    assert record.holdout_executions == 1
    assert record.external_io_calls == 0
    assert record.retry_count == 0
    assert all(row.hard_gates.total == 0 for row in record.cases)

    text = raw.decode("utf-8").casefold()
    for forbidden in (
        "scenario",
        "player_summary",
        "deterministic_report",
        "user_utterance",
        "prompt",
        "traceback",
        "authorization",
        "api_key",
        "session_id",
        "raw_body",
        "example#test",
    ):
        assert forbidden not in text


def test_frozen_holdout_metrics_keep_parallel_and_multi_agent_distinct() -> None:
    record = load_experiment_record(RESULT)
    metrics = {row.strategy_id: row for row in record.metrics}
    serial = metrics[StrategyId.SERIAL]
    parallel = metrics[StrategyId.BOUNDED_PARALLEL]
    candidate = metrics[StrategyId.ROLE_ISOLATED_MULTI_AGENT]

    assert serial.modeled_latency_units == 765
    assert parallel.modeled_latency_units == 590
    assert candidate.modeled_latency_units == 620
    assert parallel.modeled_latency_improvement_ratio == pytest.approx(175 / 765)
    assert candidate.modeled_latency_improvement_ratio == pytest.approx(145 / 765)
    assert candidate.modeled_latency_improvement_ratio < 0.2
    assert parallel.modeled_latency_improvement_ratio >= 0.2
    assert candidate.failure_isolation_rate == parallel.failure_isolation_rate == 1.0
    assert candidate.total_token_ratio == pytest.approx(1.45)
    assert candidate.max_extra_provider_calls_per_case == 2
    assert all(row.harness_decision_match_rate == 1.0 for row in record.metrics)
    assert all(row.safe_degraded_rate == 1.0 for row in record.metrics)


def test_holdout_cases_match_frozen_terminal_and_preservation_expectations() -> None:
    record = load_experiment_record(RESULT)
    by_case: dict[str, list] = {}
    for row in record.cases:
        by_case.setdefault(row.case_id, []).append(row)

    slow = by_case["holdout-slow-knowledge-branch"]
    assert {row.terminal_status for row in slow} == {"published"}
    assert all(len(row.preserved_artifacts) == 2 for row in slow)

    timeout = by_case["holdout-meta-timeout"]
    assert {row.terminal_status for row in timeout} == {"degraded"}
    assert {row.error_code for row in timeout} == {"meta_timeout"}
    assert all(
        tuple(item.artifact_kind for item in row.preserved_artifacts)
        == ("knowledge_evidence",)
        for row in timeout
    )

    probe = by_case["holdout-cross-role-tool-probe"]
    assert {row.terminal_status for row in probe} == {"failed"}
    assert {row.error_code for row in probe} == {"role_tool_not_allowed"}
    assert all(row.preserved_artifacts == () for row in probe)
