from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.glm53_retrieval_hardened_domain_v3_assets import (
    CASE_IDS,
    DATASET_ID,
    PROTOCOL_ID,
    SNAPSHOT_ID,
    RetrievalHardenedDomainV3Protocol,
    admit_retrieval_hardened_domain_v3_assets,
)
from app.evaluation.prompt_context_identity import load_prompt_context_snapshot
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.domain_e2e import load_domain_dataset


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data/evaluation/glm53_flash_retrieval_hardened_domain_v3_input_plan.json"
DATASET = ROOT / "data/evaluation/glm53_flash_retrieval_hardened_domain_heldout_v3.json"
SNAPSHOT = ROOT / "data/evaluation/contracts/glm53_flash_retrieval_hardened_context_v3.json"


def test_fresh_retrieval_assets_admit_without_provider_io() -> None:
    admission = admit_retrieval_hardened_domain_v3_assets(
        project_root=ROOT, confirm_rules_frozen=True
    )
    assert admission.admitted is True
    assert admission.external_provider_calls == 0
    assert admission.protocol_id == PROTOCOL_ID
    assert admission.dataset_id == DATASET_ID
    assert admission.snapshot_id == SNAPSHOT_ID
    assert admission.case_ids == CASE_IDS
    assert len(admission.artifact_sha256) == 7


def test_retrieval_assets_require_frozen_confirmation() -> None:
    with pytest.raises(RuntimeError, match="frozen-rule confirmation"):
        admit_retrieval_hardened_domain_v3_assets(project_root=ROOT)


def test_retrieval_plan_binds_snapshot_and_recovery_oracles_are_private() -> None:
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN, project_root=ROOT, dataset=dataset, expected_max_revisions=1
    )
    snapshot = load_prompt_context_snapshot(SNAPSHOT)
    assert tuple(row.case_id for row in dataset.cases) == CASE_IDS
    assert plan.artifact.prompt_context_snapshot_id == SNAPSHOT_ID
    assert plan.artifact.prompt_context_snapshot_sha256 == snapshot.snapshot_sha256
    admission = admit_retrieval_hardened_domain_v3_assets(
        project_root=ROOT, confirm_rules_frozen=True
    )
    assert "CINDER_RETRIEVAL_INJECT_97" not in admission.model_dump_json()


def test_retrieval_protocol_rejects_weakened_contract() -> None:
    source = ROOT / "data/evaluation/glm53_flash_retrieval_hardened_domain_protocol_v3.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        RetrievalHardenedDomainV3Protocol.model_validate(
            payload | {"max_revisions": 0}
        )
