"""Strict, project-bound inputs for the Provider domain held-out executor."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.harness.run_ids import normalize_run_id

from .domain_e2e import DomainEvaluationDataset
from .provider_domain_experiment import DomainCaseExecutionPlan


NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
SafeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$"),
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Focus = Literal["overall", "laning", "survival", "economy", "vision"]
KnowledgeMode = Literal["standard", "append_injected_evidence"]


class DomainFixtureCommitment(BaseModel):
    """One exact project-relative fixture and its file-byte digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: NonBlankText
    sha256: Sha256Text

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or "\\" in value
            or str(path) != value
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise ValueError(
                "fixture path must be a normalized project-relative path"
            )
        return value


class DomainCaseInput(BaseModel):
    """Raw input for one case, intentionally excluding evaluation oracle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    run_id: NonBlankText
    user_utterance: NonBlankText
    focus: Focus
    knowledge_mode: KnowledgeMode
    injected_evidence_text: str | None = None
    forbidden_output_markers: tuple[NonBlankText, ...] = ()

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @model_validator(mode="after")
    def validate_knowledge_mode(self) -> "DomainCaseInput":
        if self.knowledge_mode == "append_injected_evidence":
            if not self.injected_evidence_text or not self.injected_evidence_text.strip():
                raise ValueError(
                    "injected knowledge mode requires injected evidence text"
                )
        elif self.injected_evidence_text is not None:
            raise ValueError(
                "standard knowledge mode cannot carry injected evidence text"
            )
        if len(set(self.forbidden_output_markers)) != len(
            self.forbidden_output_markers
        ):
            raise ValueError("forbidden output markers must be unique")
        return self


class DomainCaseContextCommitment(BaseModel):
    """Canonical Context identity for one case, never its raw content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    context_sha256: Sha256Text


class DomainCaseInputPlanArtifact(BaseModel):
    """Sealed input plan whose exact file bytes identify the real run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0", "1.1"] = "1.0"
    plan_id: SafeCodeText
    plan_version: NonBlankText
    dataset_id: NonBlankText
    dataset_version: NonBlankText
    skill_name: NonBlankText
    skill_version: NonBlankText
    player_summary: DomainFixtureCommitment
    deterministic_report: DomainFixtureCommitment
    sdk_max_retries: Literal[0]
    max_revisions: Literal[0]
    prompt_context_snapshot_id: SafeCodeText | None = None
    prompt_context_snapshot_sha256: Sha256Text | None = None
    case_context_commitments: tuple[DomainCaseContextCommitment, ...] = ()
    case_count: int = Field(gt=0)
    cases: tuple[DomainCaseInput, ...]

    @model_validator(mode="after")
    def validate_cases(self) -> "DomainCaseInputPlanArtifact":
        if self.case_count != len(self.cases):
            raise ValueError("input plan case_count does not match cases")
        case_ids = tuple(case.case_id for case in self.cases)
        run_ids = tuple(case.run_id for case in self.cases)
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("input plan case IDs must be unique")
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("input plan run IDs must be unique")
        snapshot_identity = (
            self.prompt_context_snapshot_id,
            self.prompt_context_snapshot_sha256,
        )
        if self.schema_version == "1.0":
            if any(value is not None for value in snapshot_identity) or (
                self.case_context_commitments
            ):
                raise ValueError(
                    "input plan schema 1.0 cannot carry fresh Context commitments"
                )
            return self
        if any(value is None for value in snapshot_identity):
            raise ValueError(
                "input plan schema 1.1 requires the Prompt/Context snapshot identity"
            )
        committed_case_ids = tuple(
            row.case_id for row in self.case_context_commitments
        )
        if not committed_case_ids:
            raise ValueError(
                "input plan schema 1.1 requires per-case Context commitments"
            )
        if committed_case_ids != case_ids:
            raise ValueError(
                "Context commitment case order must match input plan case order"
            )
        return self

    def case(self, case_id: str) -> DomainCaseInput:
        for row in self.cases:
            if row.case_id == case_id:
                return row
        raise KeyError("case ID is not present in the admitted input plan")


@dataclass(frozen=True)
class LoadedDomainCaseInputPlan:
    """Validated internal inputs plus the public non-sensitive plan identity."""

    artifact: DomainCaseInputPlanArtifact
    execution_plan: DomainCaseExecutionPlan
    player_summary_path: Path
    deterministic_report_path: Path


def load_domain_case_input_plan(
    path: str | Path,
    *,
    project_root: str | Path,
    dataset: DomainEvaluationDataset,
) -> LoadedDomainCaseInputPlan:
    """Load exact bytes and reject identity or fixture drift before Provider I/O."""

    if not isinstance(dataset, DomainEvaluationDataset):
        raise TypeError("dataset must be a DomainEvaluationDataset")
    raw = Path(path).read_bytes()
    artifact = DomainCaseInputPlanArtifact.model_validate_json(raw)
    if (artifact.dataset_id, artifact.dataset_version) != (
        dataset.dataset_id,
        dataset.dataset_version,
    ):
        raise ValueError("input plan Dataset identity does not match held-out")
    if (artifact.skill_name, artifact.skill_version) != (
        dataset.contract_snapshot.skill_name,
        dataset.contract_snapshot.skill_version,
    ):
        raise ValueError("input plan Skill identity does not match held-out")
    case_ids = tuple(case.case_id for case in artifact.cases)
    if case_ids != tuple(case.case_id for case in dataset.cases):
        raise ValueError("input plan case order does not match held-out")

    root = Path(project_root).resolve()
    player_summary_path = _verify_fixture(root, artifact.player_summary)
    deterministic_report_path = _verify_fixture(
        root,
        artifact.deterministic_report,
    )
    execution_plan = DomainCaseExecutionPlan(
        plan_id=artifact.plan_id,
        plan_version=artifact.plan_version,
        plan_sha256=hashlib.sha256(raw).hexdigest(),
        case_ids=case_ids,
    )
    return LoadedDomainCaseInputPlan(
        artifact=artifact,
        execution_plan=execution_plan,
        player_summary_path=player_summary_path,
        deterministic_report_path=deterministic_report_path,
    )


def _verify_fixture(
    project_root: Path,
    commitment: DomainFixtureCommitment,
) -> Path:
    path = (project_root / PurePosixPath(commitment.relative_path)).resolve()
    if not path.is_relative_to(project_root):
        raise ValueError("fixture path must remain project-relative")
    if not path.is_file():
        raise FileNotFoundError(f"frozen fixture does not exist: {path.name}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != commitment.sha256:
        raise ValueError("fixture digest does not match input plan")
    return path


__all__ = [
    "DomainCaseContextCommitment",
    "DomainCaseInput",
    "DomainCaseInputPlanArtifact",
    "DomainFixtureCommitment",
    "LoadedDomainCaseInputPlan",
    "load_domain_case_input_plan",
]
