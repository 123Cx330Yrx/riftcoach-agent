from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.glm53_hardened_domain_assets import (
    CASE_IDS,
    DATASET_ID,
    HardenedDomainProtocol,
    HISTORICAL_MARKERS,
    PROTOCOL_ID,
    QUALITY_HARDENING_VERSION,
    admit_hardened_domain_assets,
)


ROOT = Path(__file__).resolve().parents[1]


def test_hardened_v2_assets_are_admitted_without_provider_io() -> None:
    admission = admit_hardened_domain_assets(
        project_root=ROOT,
        confirm_rules_frozen=True,
    )

    assert admission.admitted is True
    assert admission.external_provider_calls == 0
    assert admission.protocol_id == PROTOCOL_ID
    assert admission.dataset_id == DATASET_ID
    assert admission.quality_hardening_version == QUALITY_HARDENING_VERSION
    assert admission.minimum_evidence_sources == 1
    assert admission.case_ids == CASE_IDS
    assert len(admission.forbidden_marker_sha256) == 2
    assert all(len(value) == 64 for value in admission.forbidden_marker_sha256)
    assert all(len(value) == 64 for value in admission.artifact_sha256)
    public_payload = admission.model_dump_json()
    assert "HARBOR_USER_DATA_592" not in public_payload
    assert "HARBOR_KNOWLEDGE_DATA_841" not in public_payload


def test_hardened_v2_assets_require_frozen_rule_confirmation() -> None:
    with pytest.raises(RuntimeError, match="frozen-rule confirmation"):
        admit_hardened_domain_assets(project_root=ROOT)


def test_hardened_v2_assets_do_not_reuse_historical_markers() -> None:
    plan = json.loads(
        (
            ROOT / "data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json"
        ).read_text(encoding="utf-8")
    )
    markers = {
        marker
        for case in plan["cases"]
        for marker in case["forbidden_output_markers"]
    }

    assert markers
    assert markers.isdisjoint(HISTORICAL_MARKERS)


def test_hardened_v2_assets_reject_quality_contract_drift() -> None:
    source = (
        ROOT / "data/evaluation/glm53_flash_hardened_domain_protocol_v2.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["quality_hardening_version"] = "untrusted-quality-contract"
    with pytest.raises(ValueError):
        HardenedDomainProtocol.model_validate(payload)
