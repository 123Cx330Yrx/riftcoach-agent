"""Resolve a Prompt Program only after current assets pass the drift gate."""

from __future__ import annotations

from app.agent.context import context_contract_descriptor
from app.evaluation.prompt_context_identity import build_component_fingerprints
from app.skills.catalog import SkillCatalog

from .catalog import PromptProgramCatalog, PromptProgramCatalogError
from .models import VerifiedPromptProgram


class PromptProgramResolver:
    """Bind a checked-in manifest to the current Skill-owned components."""

    def __init__(
        self,
        catalog: PromptProgramCatalog,
        skill_catalog: SkillCatalog,
    ) -> None:
        self._catalog = catalog
        self._skill_catalog = skill_catalog

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
        if manifest.evaluation_contract_version != "1.1.0":
            raise PromptProgramCatalogError(
                "Prompt Program requires secure Evaluation contract 1.1.0"
            )

        current = build_component_fingerprints(
            skill,
            evaluation_contract_version=manifest.evaluation_contract_version,
        )
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
