"""Admission for the fresh, guided GLM-5.3 Flash domain asset bundle.

This module is deliberately an offline boundary: it validates identities,
fixture digests, Context commitments, and the request protocol before a caller
is allowed to construct a Provider runner.  It does not perform network I/O or
change the product default model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.domain_e2e import DomainEvaluationDataset, load_domain_dataset
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.evaluation.glm53_guided_candidate import (
    GUIDANCE_ID,
    GUIDANCE_SHA256,
    GUIDED_DOMAIN_CASES,
    require_guided_candidate,
    validate_guided_domain_case_set,
)
from app.evaluation.prompt_context_identity import load_prompt_context_snapshot
from app.evaluation.provider_domain_plan import (
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)

DATASET_PATH = Path("data/evaluation/glm53_flash_guided_domain_heldout_v4.json")
INPUT_PLAN_PATH = Path("data/evaluation/glm53_flash_guided_domain_v4_input_plan.json")
CONTEXT_PATH = Path("data/evaluation/contracts/glm53_flash_guided_context_v4.json")
BUDGET_PATH = Path("data/evaluation/contracts/glm53_flash_guided_domain_v4_budget.json")
PROTOCOL_PATH = Path("data/evaluation/glm53_flash_guided_domain_protocol_v4.json")
DATASET_ID = "glm53-flash-guided-domain-heldout-v4"
PROTOCOL_ID = "glm53-flash-guided-domain-observation-v4"
PROTOCOL_VERSION = "4.0.0"
CASE_MAX_CALLS = 9
DOMAIN_MAX_CALLS = 36
CASE_MAX_TOKENS = 205_000
DOMAIN_MAX_TOKENS = 820_000


class GuidedDomainProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    protocol_id: Literal[PROTOCOL_ID]
    protocol_version: Literal[PROTOCOL_VERSION]
    retrieval_policy_id: Literal["coaching-query-recovery-v1"]
    retrieval_guidance_id: Literal[GUIDANCE_ID]
    retrieval_guidance_sha256: Literal[GUIDANCE_SHA256]
    quality_hardening: Literal[True]
    retrieval_hardening: Literal[True]
    provider_id: Literal["zhipu"]
    model: Literal["glm-5.3-flash"]
    request_policy_id: Literal[GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.policy_id]
    request_policy_version: Literal[GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.version]
    reasoning_effort: Literal["low"]
    max_output_tokens: Literal[4096]
    sdk_max_retries: Literal[0]
    max_revisions: Literal[1]
    minimum_evidence_sources: int = Field(default=1, ge=1)
    case_max_calls: Literal[CASE_MAX_CALLS]
    domain_max_calls: Literal[DOMAIN_MAX_CALLS]
    case_max_tokens: Literal[CASE_MAX_TOKENS]
    domain_max_tokens: Literal[DOMAIN_MAX_TOKENS]
    stop_on_first_unsafe: Literal[True]
    body_free_receipt: Literal[True]


class GuidedBudgetProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    algorithm_version: Literal["deterministic-full-request-envelope-v1"]
    provider_id: Literal["zhipu"]
    model: Literal["glm-5.3-flash"]
    request_policy_id: Literal[GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.policy_id]
    request_policy_version: Literal[GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.version]
    case_count: Literal[4]
    case_max_calls: Literal[CASE_MAX_CALLS]
    domain_max_calls: Literal[DOMAIN_MAX_CALLS]
    case_max_tokens: Literal[202000]
    domain_max_tokens: Literal[806000]
    external_provider_calls: Literal[0]
    input_plan_sha256: str
    snapshot_sha256: str
    cases: tuple[dict, ...]
    report_sha256: str


class GuidedDomainAssetBundle(BaseModel):
    """Non-sensitive identities returned after a successful admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan
    context_snapshot_sha256: str
    budget: GuidedBudgetProof
    protocol: GuidedDomainProtocol


def admit_guided_domain_assets(
    *, project_root: str | Path
) -> GuidedDomainAssetBundle:
    """Validate the complete V4 bundle without contacting a Provider."""

    root = Path(project_root).resolve()
    dataset_path = _inside(root, DATASET_PATH)
    plan_path = _inside(root, INPUT_PLAN_PATH)
    context_path = _inside(root, CONTEXT_PATH)
    budget_path = _inside(root, BUDGET_PATH)
    protocol_path = _inside(root, PROTOCOL_PATH)
    dataset = load_domain_dataset(dataset_path)
    if dataset.dataset_id != DATASET_ID or dataset.case_count != len(GUIDED_DOMAIN_CASES):
        raise ValueError("guided Dataset identity or case count is not canonical")
    if dataset.role.value != "held_out" or not dataset.calibration_excluded:
        raise ValueError("guided Dataset must be calibration-excluded held-out data")
    validate_guided_domain_case_set(tuple(GUIDED_DOMAIN_CASES))
    if tuple(row.case_id for row in dataset.cases) != tuple(
        row.case_id for row in GUIDED_DOMAIN_CASES
    ):
        raise ValueError("guided Dataset cases do not match the candidate registry")
    plan = load_domain_case_input_plan(
        plan_path,
        project_root=root,
        dataset=dataset,
        expected_max_revisions=1,
    )
    snapshot = load_prompt_context_snapshot(context_path)
    rebuilt = require_guided_candidate(project_root=root, input_plan=plan)
    if snapshot.snapshot_sha256 != rebuilt.snapshot_sha256:
        raise ValueError("guided Context file does not match its rebuilt identity")
    protocol = GuidedDomainProtocol.model_validate_json(protocol_path.read_bytes())
    budget = GuidedBudgetProof.model_validate_json(budget_path.read_bytes())
    if budget.input_plan_sha256 != plan.execution_plan.plan_sha256:
        raise ValueError("guided budget is bound to a different input plan")
    if budget.snapshot_sha256 != rebuilt.snapshot_sha256:
        raise ValueError("guided budget is bound to a different Context snapshot")
    if tuple(row["case_id"] for row in budget.cases) != tuple(
        row.case_id for row in GUIDED_DOMAIN_CASES
    ) or any(row.get("provider_calls") != CASE_MAX_CALLS for row in budget.cases):
        raise ValueError("guided budget does not cover all four worst paths")
    if _canonical_sha256(plan_path) != plan.execution_plan.plan_sha256:
        raise ValueError("guided input plan identity drifted")
    _reject_historical_literals(dataset_path, plan_path, context_path, protocol_path, budget_path)
    return GuidedDomainAssetBundle(
        dataset=dataset,
        input_plan=plan,
        context_snapshot_sha256=rebuilt.snapshot_sha256,
        budget=budget,
        protocol=protocol,
    )


def _inside(root: Path, relative: Path) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FileNotFoundError(f"missing guided asset: {relative.as_posix()}")
    return path


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    ).hexdigest()


def _reject_historical_literals(*paths: Path) -> None:
    historical = (
        "glm53-flash-retrieval-hardened-domain-heldout-v3",
        "glm53-flash-hardened-domain-heldout-v3",
        "retrieval_short_survival_83",
        "retrieval_explicit_economy_89",
        "retrieval_injection_boundary_97",
        "rq227",
        "rq230",
        "rq235",
        "rq237",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if any(token in text.lower() for token in historical):
            raise ValueError("guided assets contain a historical identity")


__all__ = [
    "GuidedDomainAssetBundle",
    "GuidedDomainProtocol",
    "admit_guided_domain_assets",
]
