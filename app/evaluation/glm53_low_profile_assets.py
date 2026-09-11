"""No-I/O admission for the fresh low-profile held-out assets.

The admission function only reads and cross-checks committed bytes.  It does
not load credentials, construct a Provider, run a Skill, or create a result
file.  A later domain runner must consume the returned identities explicitly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .domain_e2e import DomainDatasetRole, load_domain_dataset, validate_domain_dataset_usage
from .prompt_context_identity import case_context_sha256, load_prompt_context_snapshot
from .provider_domain_plan import load_domain_case_input_plan


DATASET_PATH = Path("data/evaluation/glm53_flash_low_profile_domain_heldout_v1.json")
INPUT_PLAN_PATH = Path("data/evaluation/glm53_flash_low_profile_domain_v1_1_input_plan.json")
SNAPSHOT_PATH = Path("data/evaluation/contracts/glm53_flash_low_profile_context_v1.json")
DATASET_ID = "glm53-flash-low-profile-heldout-v1"
DATASET_VERSION = "1.0.0"
SNAPSHOT_ID = "glm53-flash-low-profile-context-v1"
CASE_IDS = (
    "low_gate_baseline_17",
    "low_gate_user_boundary_23",
    "low_gate_knowledge_boundary_31",
)

# IDs and markers from earlier calibration/development gates.  The fresh
# asset admission rejects any accidental reuse before a Provider can exist.
HISTORICAL_CASE_IDS = frozenset(
    {
        "flash_gate_baseline_01",
        "flash_gate_user_guard_02",
        "flash_gate_knowledge_guard_03",
        "adoption_v2_form_baseline",
        "adoption_v2_user_note_boundary",
        "adoption_v2_knowledge_note_boundary",
        "heldout_recent_form_normal",
        "heldout_user_injection",
        "heldout_knowledge_injection",
    }
)
HISTORICAL_MARKERS = frozenset(
    {
        "AURORA_CIPHER_418",
        "NEBULA_TRACE_629",
        "USER_INJECTION_ACCEPTED",
        "KNOWLEDGE_INJECTION_ACCEPTED",
    }
)

GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GLM53LowProfileAssetAdmission(_FrozenModel):
    """Public-safe identity returned by the no-I/O asset gate."""

    schema_version: Literal["1.0"] = "1.0"
    admission_id: NonBlankText = "glm53-low-profile-assets-admission-v1"
    dataset_id: Literal[DATASET_ID] = DATASET_ID
    dataset_version: Literal[DATASET_VERSION] = DATASET_VERSION
    dataset_sha256: Sha256Text
    input_plan_id: NonBlankText
    input_plan_version: NonBlankText
    input_plan_sha256: Sha256Text
    snapshot_id: Literal[SNAPSHOT_ID] = SNAPSHOT_ID
    snapshot_sha256: Sha256Text
    case_ids: tuple[NonBlankText, ...]
    forbidden_marker_sha256: tuple[Sha256Text, ...]
    rules_frozen: Literal[True] = True
    external_provider_calls: Literal[0] = 0
    admitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "GLM53LowProfileAssetAdmission":
        if self.case_ids != CASE_IDS:
            raise ValueError("fresh asset case order is not canonical")
        if len(set(self.forbidden_marker_sha256)) != len(
            self.forbidden_marker_sha256
        ):
            raise ValueError("fresh asset marker digests must be unique")
        return self


def admit_low_profile_assets(
    *,
    project_root: str | Path,
    confirm_rules_frozen: bool = False,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
) -> GLM53LowProfileAssetAdmission:
    """Read and cross-check the fresh assets without any external I/O."""

    if confirm_rules_frozen is not True:
        raise RuntimeError("held-out asset admission requires frozen-rule confirmation")
    root = Path(project_root).resolve()
    dataset_file = _inside(root, dataset_path)
    plan_file = _inside(root, input_plan_path)
    snapshot_file = _inside(root, snapshot_path)
    dataset = load_domain_dataset(dataset_file)
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if (dataset.dataset_id, dataset.dataset_version) != (DATASET_ID, DATASET_VERSION):
        raise ValueError("unexpected fresh low-profile Dataset identity")
    if tuple(case.case_id for case in dataset.cases) != CASE_IDS:
        raise ValueError("fresh low-profile Dataset case IDs drifted")
    if any(case.case_id in HISTORICAL_CASE_IDS for case in dataset.cases):
        raise ValueError("fresh low-profile Dataset reuses a historical case ID")
    snapshot = load_prompt_context_snapshot(snapshot_file)
    if (snapshot.snapshot_id, snapshot.snapshot_sha256) != (
        SNAPSHOT_ID,
        dataset.contract_snapshot.prompt_context_snapshot_sha256,
    ):
        raise ValueError("Dataset and Prompt/Context snapshot identities differ")
    plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
    )
    if plan.artifact.schema_version != "1.1":
        raise ValueError("fresh low-profile input plan must use schema 1.1")
    if plan.artifact.prompt_context_snapshot_id != snapshot.snapshot_id:
        raise ValueError("input plan snapshot ID differs")
    expected_commitments = tuple(
        (row.case_id, row.context_sha256)
        for row in plan.artifact.case_context_commitments
    )
    actual_commitments = tuple(
        (row.case_id, case_context_sha256(row)) for row in snapshot.case_contexts
    )
    if expected_commitments != actual_commitments:
        raise ValueError("input plan Context commitments differ from snapshot")
    if plan.artifact.sdk_max_retries != 0 or plan.artifact.max_revisions != 0:
        raise ValueError("fresh low-profile plan must disable retries and revisions")
    markers = tuple(
        marker
        for case in plan.artifact.cases
        for marker in case.forbidden_output_markers
    )
    if any(marker in HISTORICAL_MARKERS for marker in markers):
        raise ValueError("fresh low-profile Dataset reuses a historical marker")
    if len(set(markers)) != len(markers):
        raise ValueError("fresh low-profile markers must be unique")

    return GLM53LowProfileAssetAdmission(
        dataset_sha256=_sha256_file(dataset_file),
        input_plan_id=plan.artifact.plan_id,
        input_plan_version=plan.artifact.plan_version,
        input_plan_sha256=_sha256_file(plan_file),
        snapshot_sha256=snapshot.snapshot_sha256,
        case_ids=CASE_IDS,
        forbidden_marker_sha256=tuple(_sha256_text(marker) for marker in markers),
    )


def _inside(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError("fresh asset path must be a file inside the repository")
    return resolved


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "CASE_IDS",
    "DATASET_ID",
    "DATASET_PATH",
    "DATASET_VERSION",
    "GLM53LowProfileAssetAdmission",
    "INPUT_PLAN_PATH",
    "SNAPSHOT_ID",
    "SNAPSHOT_PATH",
    "admit_low_profile_assets",
]
