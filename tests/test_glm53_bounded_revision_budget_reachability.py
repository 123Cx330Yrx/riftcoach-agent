from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.glm53_bounded_revision_budget_reachability import (
    CASE_MAX_CALLS,
    DOMAIN_MAX_CALLS,
    REPORT_PATH,
    V3BudgetReachabilityReport,
    build_v3_budget_reachability_report,
    canonical_v3_budget_reachability_bytes,
    load_v3_budget_reachability_report,
)


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_v3_reachability_report_rebuilds_without_provider_io():
    frozen = load_v3_budget_reachability_report(ROOT / REPORT_PATH)
    rebuilt = build_v3_budget_reachability_report(project_root=ROOT)

    assert rebuilt == frozen
    assert canonical_v3_budget_reachability_bytes(rebuilt) == (
        ROOT / REPORT_PATH
    ).read_bytes()
    assert frozen.external_provider_calls == 0
    assert frozen.case_max_calls == CASE_MAX_CALLS == 9
    assert frozen.domain_max_calls == DOMAIN_MAX_CALLS == 27
    assert frozen.case_token_limit == 203_000
    assert frozen.domain_token_limit == 608_000
    assert len(frozen.cases) == 3
    assert all(len(row.requests) == 9 for row in frozen.cases)
    assert all(
        request.output_token_reservation == 4096
        for row in frozen.cases
        for request in row.requests
    )


def test_reachability_report_is_body_free_and_self_identifying():
    payload = json.loads((ROOT / REPORT_PATH).read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for private in (
        "LanternMoss",
        "LANTERN_USER_DATA_317",
        "LANTERN_KNOWLEDGE_DATA_926",
        "bounded synthetic quote",
        "RiftCoach 教练式复盘报告",
    ):
        assert private not in encoded
    assert "messages" not in encoded
    assert "prompt" not in encoded.casefold()
    assert "content" not in encoded.casefold()

    tampered = payload | {"case_token_limit": payload["case_token_limit"] + 1}
    with pytest.raises(ValidationError):
        V3BudgetReachabilityReport.model_validate(tampered)


def test_reachability_binds_all_case_and_context_identities():
    report = load_v3_budget_reachability_report(ROOT / REPORT_PATH)

    assert len(report.input_plan_sha256) == 64
    assert len(report.snapshot_file_sha256) == 64
    assert len(report.snapshot_sha256) == 64
    assert len({row.context_sha256 for row in report.cases}) == 3
    assert all(len(row.context_sha256) == 64 for row in report.cases)
    assert all(
        len({request.request_sha256 for request in row.requests}) == 8
        for row in report.cases
    )
    assert all(
        row.requests[5].request_sha256 == row.requests[8].request_sha256
        for row in report.cases
    )
