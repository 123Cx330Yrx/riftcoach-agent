"""Resolve a Prompt Program only after current assets pass the drift gate."""

from __future__ import annotations

from app.agent.context import context_contract_descriptor
from app.evaluation.prompt_context_identity import build_component_fingerprints
from app.skills.catalog import SkillCatalog
from app.runtime.coach_contract import require_coach_contract, coach_component_fingerprint

from .catalog import PromptProgramCatalog, PromptProgramCatalogError
from .models import VerifiedPromptProgram


class PromptProgramResolver:
    """Bind a checked-in manifest to the current Skill-owned components."""

    def __init__(
        self,
        catalog: PromptProgramCatalog,
        skill_catalog: SkillCatalog,
        *,
        coach_contract=None,
    ) -> None:
        self._catalog = catalog
        self._skill_catalog = skill_catalog
        self.coach_contract = require_coach_contract(coach_contract)

    def resolve(
        self,
        skill_name: str,
        skill_version: str,
    ) -> VerifiedPromptProgram:
        skill = self._skill_catalog.get(skill_name)
        if skill is None:
            raise PromptProgramCatalogError(
                f"Prompt Program resolution requires Skill {skill_name!r}"
            )
        if skill.manifest.version != skill_version:
            raise PromptProgramCatalogError(
                "Prompt Program Skill version does not match the current Catalog"
            )

        candidates = tuple(
            row
            for row in self._catalog.programs
            if row.manifest.skill_name == skill_name
        )
        if len(candidates) != 1:
            raise PromptProgramCatalogError(
                "Prompt Program resolution requires exactly one matching manifest"
            )
        manifest = candidates[0].manifest
        if manifest.skill_version != skill_version:
            raise PromptProgramCatalogError(
                "Prompt Program Skill version does not match the requested Skill"
            )

        descriptor = context_contract_descriptor()
        if manifest.context_contract_id != descriptor["contract_id"]:
            raise PromptProgramCatalogError(
                "Prompt Program context contract ID does not match"
            )
        if manifest.context_contract_version != "1.0.0":
            raise PromptProgramCatalogError(
                "Prompt Program context contract version is unsupported"
            )
        if manifest.evaluation_contract_id != "coach_evaluation":
            raise PromptProgramCatalogError(
                "Prompt Program evaluation contract ID is unsupported"
            )
        grounded = self.coach_contract is not None and self.coach_contract.grounded
        expected_evaluation = self.coach_contract.descriptor()["evaluation_contract_version"] if grounded else "1.1.0"
        if manifest.evaluation_contract_version != expected_evaluation:
            raise PromptProgramCatalogError(
                "Prompt Program evaluation version does not match execution contract"
            )

        current = build_component_fingerprints(
            skill,
            evaluation_contract_version="1.1.0",
        )
        if grounded:
            from app.evaluation.coach_grounded_contract import grounded_component_fingerprints
            current = grounded_component_fingerprints(skill)
            if self.coach_contract.version == "1.3.7":
                from app.evaluation.golden_inference_audit import inference_component_fingerprints
                current = inference_component_fingerprints(skill)
            if self.coach_contract.version == "1.3.8":
                from app.evaluation.golden_inference_audit_v2 import inference_component_fingerprints
                current = inference_component_fingerprints(skill)
            if self.coach_contract.version == "1.3.9":
                from app.evaluation.golden_inference_audit_v3 import inference_component_fingerprints
                current = inference_component_fingerprints(skill)
            if self.coach_contract.version == "1.3.10":
                from app.evaluation.golden_inference_coverage import inference_component_fingerprints
                current = inference_component_fingerprints(skill)
            if self.coach_contract.version == "1.3.11":
                from app.evaluation.golden_inference_scope import inference_component_fingerprints
                current = inference_component_fingerprints(skill)
        if self.coach_contract is not None:
            if skill_version != self.coach_contract.descriptor()["skill_version"] or manifest.program_version != self.coach_contract.descriptor()["program_version"]:
                raise PromptProgramCatalogError("Coach contract requires independent Skill/Program versions")
            current = (*current, coach_component_fingerprint(self.coach_contract))
        if current != manifest.component_fingerprints:
            raise PromptProgramCatalogError(
                "Prompt Program component fingerprint drift detected"
            )

        return VerifiedPromptProgram(manifest=manifest)

    def verify_all(self) -> tuple[VerifiedPromptProgram, ...]:
        """Recompute every catalog entry for startup/composition validation."""

        return tuple(
            self.resolve(
                row.manifest.skill_name,
                row.manifest.skill_version,
            )
            for row in self._catalog.programs
        )


__all__ = ["PromptProgramResolver"]
