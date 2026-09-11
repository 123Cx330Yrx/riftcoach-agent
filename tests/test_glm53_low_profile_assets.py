from __future__ import annotations

from pathlib import Path

import pytest

from app.evaluation.glm53_low_profile_assets import (
    CASE_IDS,
    DATASET_ID,
    admit_low_profile_assets,
)


ROOT = Path(__file__).resolve().parents[1]


def test_fresh_low_profile_assets_are_admitted_without_provider_io() -> None:
    admission = admit_low_profile_assets(
        project_root=ROOT,
        confirm_rules_frozen=True,
    )

    assert admission.admitted is True
    assert admission.external_provider_calls == 0
    assert admission.dataset_id == DATASET_ID
    assert admission.case_ids == CASE_IDS
    assert len(admission.forbidden_marker_sha256) == 2
    assert all(len(value) == 64 for value in admission.forbidden_marker_sha256)


def test_fresh_low_profile_assets_require_frozen_rule_confirmation() -> None:
    with pytest.raises(RuntimeError, match="frozen-rule confirmation"):
        admit_low_profile_assets(project_root=ROOT)
