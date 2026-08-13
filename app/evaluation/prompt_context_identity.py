"""Safe, reproducible identity for domain Prompt/Context experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.agent.context import ContextBuilderV1, context_contract_descriptor
from app.evaluation.coach_report import (
    EVALUATOR_SYSTEM_PROMPT,
    REVISER_SYSTEM_PROMPT,
    build_evaluation_prompt,
    build_evaluation_repair_prompt,
    build_secure_evaluation_prompt,
    build_fact_pack,
    build_revision_prompt,
    evaluation_response_contract,
    evaluation_response_contract_v11,
)
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.adapters.knowledge import build_knowledge_tools

from .domain_e2e import DomainEvaluationDataset, load_domain_dataset


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SafeIdText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:@/_-]*$"),
]

_SNAPSHOT_ID = "recent-form-prompt-context-v1"
_CONTEXT_CONTRACT = "context-builder-v1"
_EVALUATION_CONTRACT = "coach_evaluation@1.0.0"
_CASE_ID = "recent_form_demo"
_RUN_ID = "recent_form_prompt_context_snapshot"
_UTTERANCE = "分析我最近几局的状态"
_FOCUS = "survival"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ComponentFingerprint(_FrozenModel):
    component_id: SafeIdText
    source: SafeIdText
    sha256: Sha256Text


class SectionFingerprint(_FrozenModel):
    section_id: NonBlankText
    trust: NonBlankText
    source: NonBlankText
    instructional: bool
    required: bool
    priority: int = Field(ge=0)
    content_sha256: Sha256Text


class MessageFingerprint(_FrozenModel):
    role: Literal["system", "user"]
    content_sha256: Sha256Text


class CaseContextFingerprint(_FrozenModel):
    case_id: SafeIdText
    player_summary_sha256: Sha256Text
    deterministic_report_sha256: Sha256Text
    user_utterance_sha256: Sha256Text
    typed_options_sha256: Sha256Text
    selected_section_ids: tuple[NonBlankText, ...]
    omitted_section_ids: tuple[NonBlankText, ...]
    sections: tuple[SectionFingerprint, ...]
    message_fingerprints: tuple[MessageFingerprint, ...]
    estimated_tokens: int = Field(ge=0)
    max_context_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_context_identity(self) -> "CaseContextFingerprint":
        selected = self.selected_section_ids
        if not selected or len(set(selected)) != len(selected):
            raise ValueError("selected section IDs must be non-empty and unique")
        if tuple(section.section_id for section in self.sections) != selected:
            raise ValueError("section fingerprints must match selected section IDs")
        if len(set(self.omitted_section_ids)) != len(self.omitted_section_ids):
            raise ValueError("omitted section IDs must be unique")
        if set(selected) & set(self.omitted_section_ids):
            raise ValueError("selected and omitted section IDs must not overlap")
        if tuple(row.role for row in self.message_fingerprints) != (
            "system",
            "user",
        ):
            raise ValueError("message fingerprints must be system then user")
        if self.estimated_tokens > self.max_context_tokens:
            raise ValueError("estimated context must fit the maximum")
        return self


class PromptContextSnapshot(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: SafeIdText
    skill_name: NonBlankText
    skill_version: NonBlankText
    context_contract: NonBlankText
    evaluation_contract: NonBlankText
    components: tuple[ComponentFingerprint, ...]
    case_contexts: tuple[CaseContextFingerprint, ...]
    snapshot_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_snapshot(self) -> "PromptContextSnapshot":
        component_ids = tuple(row.component_id for row in self.components)
        if not component_ids or len(set(component_ids)) != len(component_ids):
            raise ValueError("component IDs must be non-empty and unique")
        case_ids = tuple(row.case_id for row in self.case_contexts)
        if not case_ids or len(set(case_ids)) != len(case_ids):
            raise ValueError("case context IDs must be non-empty and unique")
        expected = _digest_json(
            self.model_dump(mode="json", exclude={"snapshot_sha256"})
        )
        if self.snapshot_sha256 != expected:
            raise ValueError("snapshot_sha256 does not match snapshot content")
        return self


class DomainExperimentAdmission(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    admission_id: SafeIdText
    dataset_id: NonBlankText
    dataset_version: NonBlankText
    dataset_sha256: Sha256Text
    prompt_context_snapshot_id: SafeIdText
    prompt_context_snapshot_sha256: Sha256Text
    skill_name: NonBlankText
    skill_version: NonBlankText
    context_contract: NonBlankText
    evaluation_contract: NonBlankText
    external_provider_calls: Literal[0] = 0
    admitted: Literal[True] = True


def build_prompt_context_snapshot(
    *,
    skills_root: str | Path,
    player_summary: dict[str, Any],
    deterministic_report: str,
    snapshot_id: str = _SNAPSHOT_ID,
    evaluation_contract_version: str = "1.0.0",
) -> PromptContextSnapshot:
    catalog = SkillCatalog.from_directory(skills_root)
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=_UTTERANCE,
            available_skills=catalog.route_candidates,
        )
    )
    skill = catalog.get("recent-form-review")
    if skill is None or decision.selected_skill != skill.manifest.name:
        raise ValueError("snapshot fixture did not select recent-form-review")
    payload = {
        "player_summary": player_summary,
        "deterministic_report": deterministic_report,
        "focus": _FOCUS,
    }
    typed_input = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=_RUN_ID,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    execution = SkillExecutionBoundary(catalog).validate(
        SkillExecutionRequest(
            run_id=_RUN_ID,
            user_utterance=_UTTERANCE,
            router_decision=decision,
            input_payload=payload,
            input_artifacts=binding,
        )
    )
    context = ContextBuilderV1().build(execution)
    components = _component_fingerprints(
        skill,
        evaluation_contract_version=evaluation_contract_version,
    )
    case_context = CaseContextFingerprint(
        case_id=_CASE_ID,
        player_summary_sha256=binding.player_summary.sha256,
        deterministic_report_sha256=binding.deterministic_report.sha256,
        user_utterance_sha256=_digest_text(execution.user_utterance),
        typed_options_sha256=_digest_json({"focus": typed_input.focus}),
        selected_section_ids=tuple(row.section_id for row in context.sections),
        omitted_section_ids=context.omitted_section_ids,
        sections=tuple(
            SectionFingerprint(
                section_id=row.section_id,
                trust=row.trust.value,
                source=row.source,
                instructional=row.instructional,
                required=row.required,
                priority=row.priority,
                content_sha256=_digest_text(row.content),
            )
            for row in context.sections
        ),
        message_fingerprints=tuple(
            MessageFingerprint(
                role=message.role.value,
                content_sha256=_digest_text(message.content or ""),
            )
            for message in context.messages
        ),
        estimated_tokens=context.estimated_tokens,
        max_context_tokens=context.max_context_tokens,
    )
    payload_without_digest = {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "skill_name": skill.manifest.name,
        "skill_version": skill.manifest.version,
        "context_contract": _CONTEXT_CONTRACT,
        "evaluation_contract": f"coach_evaluation@{evaluation_contract_version}",
        "components": [row.model_dump(mode="json") for row in components],
        "case_contexts": [case_context.model_dump(mode="json")],
    }
    return PromptContextSnapshot(
        **payload_without_digest,
        snapshot_sha256=_digest_json(payload_without_digest),
    )


def load_prompt_context_snapshot(path: str | Path) -> PromptContextSnapshot:
    return PromptContextSnapshot.model_validate_json(Path(path).read_bytes())


def prepare_domain_experiment(
    *,
    project_root: str | Path,
    dataset_path: str | Path,
    snapshot_path: str | Path,
    skills_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    report_path: str | Path | None = None,
) -> DomainExperimentAdmission:
    root = Path(project_root).resolve()
    dataset_file = Path(dataset_path).resolve()
    snapshot_file = Path(snapshot_path).resolve()
    summary_file = Path(
        summary_path or root / "examples/fixtures/player_summary_demo.json"
    )
    report_file = Path(
        report_path or root / "examples/fixtures/deterministic_report_demo.md"
    )
    dataset = load_domain_dataset(dataset_file)
    frozen_snapshot = load_prompt_context_snapshot(snapshot_file)
    current_snapshot = build_prompt_context_snapshot(
        skills_root=skills_root or root / "skills",
        player_summary=json.loads(summary_file.read_text(encoding="utf-8")),
        deterministic_report=report_file.read_text(encoding="utf-8"),
        snapshot_id=frozen_snapshot.snapshot_id,
        evaluation_contract_version=frozen_snapshot.evaluation_contract.rsplit("@", 1)[-1],
    )
    if current_snapshot != frozen_snapshot:
        raise ValueError("Prompt/Context snapshot mismatch")
    _validate_dataset_snapshot(dataset, frozen_snapshot)
    return DomainExperimentAdmission(
        admission_id=(
            "domain-e2e-v1-1-secure-development-prompt-context"
            if frozen_snapshot.evaluation_contract == "coach_evaluation@1.1.0"
            else "domain-e2e-v1-development-prompt-context"
        ),
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=_digest_json(dataset.model_dump(mode="json")),
        prompt_context_snapshot_id=frozen_snapshot.snapshot_id,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        skill_name=frozen_snapshot.skill_name,
        skill_version=frozen_snapshot.skill_version,
        context_contract=frozen_snapshot.context_contract,
        evaluation_contract=frozen_snapshot.evaluation_contract,
    )


def _validate_dataset_snapshot(
    dataset: DomainEvaluationDataset,
    snapshot: PromptContextSnapshot,
) -> None:
    declared = dataset.contract_snapshot
    expected = (
        snapshot.skill_name,
        snapshot.skill_version,
        snapshot.context_contract,
        snapshot.evaluation_contract,
        snapshot.snapshot_id,
        snapshot.snapshot_sha256,
    )
    actual = (
        declared.skill_name,
        declared.skill_version,
        declared.context_contract,
        declared.evaluation_contract,
        declared.prompt_context_snapshot_id,
        declared.prompt_context_snapshot_sha256,
    )
    if actual != expected:
        raise ValueError("Dataset Prompt/Context contract mismatch")


def _component_fingerprints(
    skill,
    *,
    evaluation_contract_version: str = "1.0.0",
) -> tuple[ComponentFingerprint, ...]:
    secure = evaluation_contract_version == "1.1.0"
    contract = (
        evaluation_response_contract_v11()
        if secure
        else evaluation_response_contract()
    )
    probe_facts = {"probe": "FACT_SENTINEL"}
    probe_report = "REPORT_SENTINEL"
    repair_probe = build_evaluation_repair_prompt(
        contract=contract,
        invalid_content="INVALID_OUTPUT_SENTINEL",
    )
    revision_probe = build_revision_prompt(
        probe_report,
        {
            "issues": [
                {
                    "evidence": "EVIDENCE_SENTINEL",
                    "suggested_correction": "CORRECTION_SENTINEL",
                }
            ]
        },
    )
    fact_pack_probe = build_fact_pack(
        {
            "player": {"riot_id": "PLAYER_SENTINEL"},
            "request": {"count": 1},
            "recent_summary": {
                "games_analyzed": 1,
                "wins": 1,
                "losses": 0,
            },
            "matches": [
                {
                    "match_id": "MATCH_SENTINEL",
                    "champion_name": "CHAMPION_SENTINEL",
                }
            ],
            "excluded_matches": [],
            "failed_matches": [],
        }
    )
    tool = build_knowledge_tools(object())[0]
    knowledge_tool_contract = {
        "name": tool.name,
        "version": tool.version,
        "description": tool.description,
        "input_schema": dict(tool.input_schema),
        "output_schema": dict(tool.output_schema),
        "idempotent": tool.idempotent,
        "policy": {
            "timeout_s": tool.policy.timeout_s,
            "retry": {
                "max_attempts": tool.policy.retry.max_attempts,
                "base_delay_s": tool.policy.retry.base_delay_s,
                "max_delay_s": tool.policy.retry.max_delay_s,
            },
            "cache_ttl_s": tool.policy.cache.ttl_s,
            "circuit_breaker": {
                "failure_threshold": (
                    tool.policy.circuit_breaker.failure_threshold
                ),
                "recovery_s": tool.policy.circuit_breaker.recovery_s,
            },
        },
    }
    evaluation_prompt = (
        build_secure_evaluation_prompt(
            probe_facts,
            probe_report,
            user_utterance="USER_REQUEST_SENTINEL",
            knowledge={"context": "KNOWLEDGE_SENTINEL", "citations": []},
        )
        if secure
        else build_evaluation_prompt(probe_facts, probe_report)
    )
    rows = (
        (
            "skill_manifest",
            "skills/recent-form-review/manifest",
            skill.manifest.model_dump(mode="json"),
        ),
        (
            "skill_instructions",
            "skills/recent-form-review/SKILL.md",
            skill.instructions.strip(),
        ),
        (
            "context_contract",
            "app.agent.context:context-builder-v1",
            context_contract_descriptor(),
        ),
        (
            "knowledge_tool_contract",
            "app.tools.adapters.knowledge:knowledge.search@2.0.0",
            knowledge_tool_contract,
        ),
        (
            "evaluation_schema",
            f"app.evaluation.coach_report:coach_evaluation@{evaluation_contract_version}",
            contract.schema_dict(),
        ),
        (
            "evaluation_fact_pack_probe",
            "app.evaluation.coach_report:build_fact_pack",
            fact_pack_probe,
        ),
        (
            "evaluator_system",
            "app.evaluation.coach_report:EVALUATOR_SYSTEM_PROMPT",
            EVALUATOR_SYSTEM_PROMPT,
        ),
        (
            "evaluation_prompt_probe",
            (
                "app.evaluation.coach_report:build_secure_evaluation_prompt"
                if secure
                else "app.evaluation.coach_report:build_evaluation_prompt"
            ),
            evaluation_prompt,
        ),
        (
            "evaluation_repair_probe",
            "app.evaluation.coach_report:build_evaluation_repair_prompt",
            repair_probe,
        ),
        (
            "reviser_system",
            "app.evaluation.coach_report:REVISER_SYSTEM_PROMPT",
            REVISER_SYSTEM_PROMPT,
        ),
        (
            "revision_prompt_probe",
            "app.evaluation.coach_report:build_revision_prompt",
            revision_probe,
        ),
    )
    return tuple(
        ComponentFingerprint(
            component_id=component_id,
            source=source,
            sha256=(
                _digest_text(value)
                if isinstance(value, str)
                else _digest_json(value)
            ),
        )
        for component_id, source, value in rows
    )


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "DomainExperimentAdmission",
    "PromptContextSnapshot",
    "build_prompt_context_snapshot",
    "load_prompt_context_snapshot",
    "prepare_domain_experiment",
]
