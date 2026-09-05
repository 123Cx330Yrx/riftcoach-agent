from __future__ import annotations

import json
import shutil
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
from app.evaluation import glm53_retrieval_hardened_domain_v3_assets as assets
from app.evaluation import glm53_bounded_revision_budget_reachability as reachability


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


@pytest.fixture
def copied_assets(tmp_path):
    paths = [assets.PROTOCOL_PATH, assets.DATASET_PATH, assets.INPUT_PLAN_PATH,
             assets.SNAPSHOT_PATH, assets.BUDGET_REPORT_PATH]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    for key in ("player_summary", "deterministic_report"):
        path = Path(plan[key]["relative_path"])
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    return tmp_path


@pytest.mark.parametrize("field,value", [
    ("retrieval_hardening", False), ("quality_hardening", False),
    ("request_policy_id", "wrong-policy"), ("request_policy_version", "9.0.0"),
])
def test_input_policy_drift_rejected_before_context_or_io(copied_assets, field, value):
    path = copied_assets / assets.INPUT_PLAN_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="bind candidate retrieval policy"):
        admit_retrieval_hardened_domain_v3_assets(
            project_root=copied_assets, confirm_rules_frozen=True
        )


@pytest.mark.parametrize("field,value", [
    ("minimum_evaluation_score", 84), ("require_fact_check", False),
    ("require_citation_check", False), ("require_injection_check", False),
    ("require_validated_evaluation", False), ("minimum_evidence_sources", 0),
])
def test_dataset_cannot_weaken_quality_gates(copied_assets, field, value):
    path = copied_assets / assets.DATASET_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cases"][0]["requirements"][field] = value
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        admit_retrieval_hardened_domain_v3_assets(
            project_root=copied_assets, confirm_rules_frozen=True
        )


def test_history_includes_consumed_rq235_without_changing_old_files():
    historical = assets._historical_identities(ROOT)
    old = json.loads((ROOT / "data/evaluation/glm53_flash_hardened_domain_v3_input_plan.json").read_text(encoding="utf-8"))
    assert {row["case_id"] for row in old["cases"]} <= historical["case_ids"]
    assert {row["run_id"] for row in old["cases"]} <= historical["run_ids"]
    assert {row["user_utterance"] for row in old["cases"]} <= historical["utterances"]
    assert {marker for row in old["cases"] for marker in row["forbidden_output_markers"]} <= historical["markers"]
    assert {old[key]["sha256"] for key in ("player_summary", "deterministic_report")} <= historical["fixture_sha256"]
    current = json.loads(PLAN.read_text(encoding="utf-8"))
    assert {row["run_id"] for row in current["cases"]}.isdisjoint(historical["run_ids"])
    assert {row["user_utterance"] for row in current["cases"]}.isdisjoint(historical["utterances"])


def test_new_budget_rebuild_uses_retrieval_hardening(monkeypatch):
    calls = []
    original = reachability.ProductionDomainCaseExecutor
    def capture(**kwargs):
        calls.append(kwargs["retrieval_hardening"])
        return original(**kwargs)
    monkeypatch.setattr(reachability, "ProductionDomainCaseExecutor", capture)
    rebuilt = reachability.build_v3_budget_reachability_report(
        project_root=ROOT, input_plan_path=assets.INPUT_PLAN_PATH,
        snapshot_path=assets.SNAPSHOT_PATH, retrieval_hardening=True,
    )
    frozen = reachability.load_v3_budget_reachability_report(ROOT / assets.BUDGET_REPORT_PATH)
    assert rebuilt == frozen
    assert calls == [True, True, True]
    assert (rebuilt.case_token_limit, rebuilt.domain_token_limit) == (205_000, 613_000)
    assert rebuilt.external_provider_calls == 0
