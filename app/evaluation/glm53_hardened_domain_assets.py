"""No-I/O admission for the post-RQ-228 hardened domain V2 assets.

This module freezes a new exam rather than rewriting the consumed RQ-227
evidence.  It reads committed bytes, rebuilds the trusted candidate Context,
and returns only public-safe identities.  It never loads credentials or
constructs a Provider.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1

from .domain_e2e import (
    DomainDatasetRole,
    load_domain_dataset,
    validate_domain_dataset_usage,
)
from .glm53_flash_candidate_profile import (
    MAX_OUTPUT_TOKENS,
    MODEL,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
    REQUEST_POLICY_VERSION,
)
from .glm53_low_profile_assets import (
    CASE_IDS as RQ227_CASE_IDS,
    HISTORICAL_CASE_IDS as PRE_RQ227_CASE_IDS,
    HISTORICAL_MARKERS as PRE_RQ227_MARKERS,
)
from .glm53_low_profile_budget import (
    CANDIDATE_CASE_MAX_CALLS,
    CANDIDATE_CASE_MAX_TOKENS,
    CANDIDATE_DOMAIN_MAX_CALLS,
    CANDIDATE_DOMAIN_MAX_TOKENS,
)
from .prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
    load_prompt_context_snapshot,
)
from .provider_domain_plan import load_domain_case_input_plan
from .provider_domain_production import CANDIDATE_QUALITY_HARDENING_VERSION


PROTOCOL_PATH = Path(
    "data/evaluation/glm53_flash_hardened_domain_protocol_v2.json"
)
DATASET_PATH = Path("data/evaluation/glm53_flash_hardened_domain_heldout_v2.json")
INPUT_PLAN_PATH = Path(
    "data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json"
)
SNAPSHOT_PATH = Path("data/evaluation/contracts/glm53_flash_hardened_context_v2.json")
PROTOCOL_ID = "glm53-flash-hardened-domain-observation-v2"
PROTOCOL_VERSION = "2.0.0"
DATASET_ID = "glm53-flash-hardened-domain-heldout-v2"
DATASET_VERSION = "2.0.0"
SNAPSHOT_ID = "glm53-flash-hardened-context-v2"
QUALITY_HARDENING_VERSION = CANDIDATE_QUALITY_HARDENING_VERSION
CASE_IDS = (
    "hardened_form_control_41",
    "hardened_user_data_boundary_47",
    "hardened_knowledge_data_boundary_53",
)
HISTORICAL_CASE_IDS = frozenset(PRE_RQ227_CASE_IDS | set(RQ227_CASE_IDS))
HISTORICAL_MARKERS = frozenset(
    PRE_RQ227_MARKERS
    | {
        "LOW_PROFILE_USER_MARKER_735",
        "LOW_PROFILE_KNOWLEDGE_MARKER_864",
    }
)

Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HardenedDomainProtocol(_FrozenModel):
    """Frozen resource and safety policy for a later, separately authorized run."""

    schema_version: Literal["1.0"] = "1.0"
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = (
        REQUEST_POLICY_VERSION
    )
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    reasoning_effort: Literal["low"] = "low"
    max_output_tokens: Literal[MAX_OUTPUT_TOKENS] = MAX_OUTPUT_TOKENS
    sdk_max_retries: Literal[0] = 0
    max_revisions: Literal[0] = 0
    minimum_evidence_sources: Literal[1] = 1
    case_max_calls: Literal[CANDIDATE_CASE_MAX_CALLS] = CANDIDATE_CASE_MAX_CALLS
    domain_max_calls: Literal[CANDIDATE_DOMAIN_MAX_CALLS] = (
        CANDIDATE_DOMAIN_MAX_CALLS
    )
    case_max_tokens: Literal[CANDIDATE_CASE_MAX_TOKENS] = (
        CANDIDATE_CASE_MAX_TOKENS
    )
    domain_max_tokens: Literal[CANDIDATE_DOMAIN_MAX_TOKENS] = (
        CANDIDATE_DOMAIN_MAX_TOKENS
    )
    stop_on_first_unsafe: Literal[True] = True
    body_free_receipt: Literal[True] = True


class GLM53HardenedDomainAssetAdmission(_FrozenModel):
    """Public-safe identity for the fresh V2 protocol and assets."""

    schema_version: Literal["1.0"] = "1.0"
    admission_id: NonBlankText = "glm53-hardened-domain-v2-assets-admission"
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    dataset_id: Literal[DATASET_ID] = DATASET_ID
    dataset_version: Literal[DATASET_VERSION] = DATASET_VERSION
    snapshot_id: Literal[SNAPSHOT_ID] = SNAPSHOT_ID
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = (
        REQUEST_POLICY_VERSION
    )
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    minimum_evidence_sources: Literal[1] = 1
    case_ids: tuple[NonBlankText, ...]
    forbidden_marker_sha256: tuple[Sha256Text, ...]
    artifact_sha256: tuple[Sha256Text, ...]
    rules_frozen: Literal[True] = True
    external_provider_calls: Literal[0] = 0
    admitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "GLM53HardenedDomainAssetAdmission":
        if self.case_ids != CASE_IDS:
            raise ValueError("hardened V2 case order is not canonical")
        if len(self.artifact_sha256) != 6:
            raise ValueError("hardened V2 admission must bind six artifacts")
        if len(set(self.forbidden_marker_sha256)) != len(
            self.forbidden_marker_sha256
        ):
            raise ValueError("hardened V2 marker digests must be unique")
        return self


def admit_hardened_domain_assets(
    *,
    project_root: str | Path,
    confirm_rules_frozen: bool = False,
    protocol_path: str | Path = PROTOCOL_PATH,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
) -> GLM53HardenedDomainAssetAdmission:
    """Cross-check the hardened V2 exam without credentials or Provider I/O."""

    if confirm_rules_frozen is not True:
        raise RuntimeError("held-out asset admission requires frozen-rule confirmation")
    root = Path(project_root).resolve()
    protocol_file = _inside(root, protocol_path)
    dataset_file = _inside(root, dataset_path)
    plan_file = _inside(root, input_plan_path)
    snapshot_file = _inside(root, snapshot_path)

    protocol = HardenedDomainProtocol.model_validate_json(
        protocol_file.read_bytes()
    )
    dataset = load_domain_dataset(dataset_file)
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if (dataset.dataset_id, dataset.dataset_version) != (
        DATASET_ID,
        DATASET_VERSION,
    ):
        raise ValueError("unexpected hardened V2 Dataset identity")
    if tuple(case.case_id for case in dataset.cases) != CASE_IDS:
        raise ValueError("hardened V2 Dataset case IDs drifted")
    if any(case.case_id in HISTORICAL_CASE_IDS for case in dataset.cases):
        raise ValueError("hardened V2 Dataset reuses a historical case ID")
    if any(
        case.requirements.minimum_evidence_sources != protocol.minimum_evidence_sources
        for case in dataset.cases
    ):
        raise ValueError("Dataset does not bind the hardened evidence-source floor")
    if any(
        case.requirements.maximum_provider_calls != protocol.case_max_calls
        or case.requirements.maximum_total_tokens != protocol.case_max_tokens
        for case in dataset.cases
    ):
        raise ValueError("Dataset resource walls differ from hardened protocol")

    snapshot = load_prompt_context_snapshot(snapshot_file)
    if (snapshot.snapshot_id, snapshot.snapshot_sha256) != (
        SNAPSHOT_ID,
        dataset.contract_snapshot.prompt_context_snapshot_sha256,
    ):
        raise ValueError("Dataset and hardened Context snapshot identities differ")
    plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
    )
    if plan.artifact.schema_version != "1.1":
        raise ValueError("hardened V2 input plan must use schema 1.1")
    if plan.artifact.prompt_context_snapshot_id != snapshot.snapshot_id:
        raise ValueError("input plan snapshot ID differs")
    if plan.artifact.prompt_context_snapshot_sha256 != snapshot.snapshot_sha256:
        raise ValueError("input plan snapshot digest differs")
    if plan.artifact.sdk_max_retries != 0 or plan.artifact.max_revisions != 0:
        raise ValueError("hardened V2 plan must disable retries and revisions")

    expected_commitments = tuple(
        (row.case_id, row.context_sha256)
        for row in plan.artifact.case_context_commitments
    )
    actual_commitments = tuple(
        (row.case_id, case_context_sha256(row)) for row in snapshot.case_contexts
    )
    if expected_commitments != actual_commitments:
        raise ValueError("input plan Context commitments differ from snapshot")
    policy_digest = _sha256_text(CANDIDATE_CONTEXT_SAFETY_POLICY_V1.strip())
    for context in snapshot.case_contexts:
        policy_sections = tuple(
            section
            for section in context.sections
            if section.section_id == "candidate:policy_addendum"
        )
        if len(policy_sections) != 1:
            raise ValueError("hardened Context must contain one candidate policy")
        policy = policy_sections[0]
        if (
            policy.trust != "internal_policy"
            or policy.source != "candidate-output-safety-v1"
            or policy.content_sha256 != policy_digest
        ):
            raise ValueError("hardened Context candidate policy identity differs")

    summary = json.loads(plan.player_summary_path.read_text(encoding="utf-8"))
    report = plan.deterministic_report_path.read_text(encoding="utf-8")
    rebuilt = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=summary,
        deterministic_report=report,
        cases=plan.artifact.cases,
        snapshot_id=snapshot.snapshot_id,
        evaluation_contract_version=(
            snapshot.evaluation_contract.rsplit("@", 1)[-1]
        ),
        policy_addendum=CANDIDATE_CONTEXT_SAFETY_POLICY_V1,
    )
    if rebuilt != snapshot:
        raise ValueError("hardened Prompt/Context snapshot mismatch")

    markers = tuple(
        marker
        for case in plan.artifact.cases
        for marker in case.forbidden_output_markers
    )
    if any(marker in HISTORICAL_MARKERS for marker in markers):
        raise ValueError("hardened V2 Dataset reuses a historical marker")
    if len(set(markers)) != len(markers):
        raise ValueError("hardened V2 markers must be unique")

    artifacts = (
        protocol_file,
        dataset_file,
        plan_file,
        snapshot_file,
        plan.player_summary_path,
        plan.deterministic_report_path,
    )
    return GLM53HardenedDomainAssetAdmission(
        case_ids=CASE_IDS,
        forbidden_marker_sha256=tuple(_sha256_text(marker) for marker in markers),
        artifact_sha256=tuple(_sha256_file(path) for path in artifacts),
    )


def _inside(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError(
            "hardened asset path must be a file inside the repository"
        )
    return resolved


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "CASE_IDS",
    "DATASET_ID",
    "GLM53HardenedDomainAssetAdmission",
    "HISTORICAL_MARKERS",
    "HardenedDomainProtocol",
    "PROTOCOL_ID",
    "QUALITY_HARDENING_VERSION",
    "admit_hardened_domain_assets",
]
