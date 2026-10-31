from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.glm53_hardened_domain_v3_assets import (
    CASE_IDS,
    DATASET_ID,
    EVALUATION_DIAGNOSTICS_VERSION,
    HardenedDomainV3Protocol,
    PROTOCOL_ID,
    QUALITY_HARDENING_VERSION,
    admit_hardened_domain_v3_assets,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data/evaluation/glm53_flash_hardened_domain_v3_input_plan.json"
V2_PLAN = ROOT / "data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json"
RQ227_PLAN = (
    ROOT / "data/evaluation/glm53_flash_low_profile_domain_v1_1_input_plan.json"
)


def test_hardened_v3_assets_are_admitted_without_provider_io():
    admission = admit_hardened_domain_v3_assets(
        project_root=ROOT,
        confirm_rules_frozen=True,
    )

    assert admission.admitted is True
    assert admission.external_provider_calls == 0
    assert admission.protocol_id == PROTOCOL_ID
    assert admission.dataset_id == DATASET_ID
    assert admission.case_ids == CASE_IDS
    assert admission.quality_hardening_version == QUALITY_HARDENING_VERSION
    assert admission.evaluation_diagnostics_version == (
        EVALUATION_DIAGNOSTICS_VERSION
    )
    assert len(admission.artifact_sha256) == 7
    assert len(set(admission.artifact_sha256)) == 7
    assert len(admission.forbidden_marker_sha256) == 2

    public = admission.model_dump_json()
    for private in (
        "LanternMoss",
        "LANTERN_USER_DATA_317",
        "LANTERN_KNOWLEDGE_DATA_926",
        "user_utterance",
        "injected_evidence_text",
    ):
        assert private not in public


def test_hardened_v3_assets_require_explicit_freeze_confirmation():
    with pytest.raises(RuntimeError, match="frozen-rule confirmation"):
        admit_hardened_domain_v3_assets(project_root=ROOT)


def test_hardened_v3_plan_is_fresh_against_rq227_and_v2():
    current = json.loads(PLAN.read_text(encoding="utf-8"))
    historical = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (RQ227_PLAN, V2_PLAN)
    ]
    old_cases = {
        case["case_id"] for plan in historical for case in plan["cases"]
    }
    old_runs = {case["run_id"] for plan in historical for case in plan["cases"]}
    old_questions = {
        case["user_utterance"] for plan in historical for case in plan["cases"]
    }
    old_markers = {
        marker
        for plan in historical
        for case in plan["cases"]
        for marker in case["forbidden_output_markers"]
    }
    old_fixtures = {
        plan[key]["sha256"]
        for plan in historical
        for key in ("player_summary", "deterministic_report")
    }

    assert {row["case_id"] for row in current["cases"]}.isdisjoint(old_cases)
    assert {row["run_id"] for row in current["cases"]}.isdisjoint(old_runs)
    assert {row["user_utterance"] for row in current["cases"]}.isdisjoint(
        old_questions
    )
    assert {
        marker
        for row in current["cases"]
        for marker in row["forbidden_output_markers"]
    }.isdisjoint(old_markers)
    assert {
        current["player_summary"]["sha256"],
        current["deterministic_report"]["sha256"],
    }.isdisjoint(old_fixtures)


def test_hardened_v3_protocol_rejects_weakened_or_unproven_contract():
    source = (
        ROOT / "data/evaluation/glm53_flash_hardened_domain_protocol_v3.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    for field, value in (
        ("max_revisions", 0),
        ("case_max_calls", 10),
        ("case_max_tokens", 24_000),
        ("quality_hardening_version", "untrusted"),
        ("evaluation_diagnostics_version", "free-text-diagnostics"),
    ):
        changed = payload | {field: value}
        with pytest.raises(ValueError):
            HardenedDomainV3Protocol.model_validate(changed)
