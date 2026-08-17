"""The thin product composition root for verified Prompt Programs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.evaluation.coach_report import (
    EVALUATOR_SYSTEM_PROMPT,
    REVISER_SYSTEM_PROMPT,
    build_fact_pack,
    build_revision_prompt,
    validate_revised_report,
)
from app.harness.adapters import ChatCoachReviser, SecureChatEvaluationAdapter
from app.prompt_program import PromptProgramCatalog, PromptProgramResolver
from app.skills.catalog import SkillCatalog

from .runtime import (
    AgentRuntimeV1,
    RuntimeCompositionError,
    RuntimeExecutionFactory,
)


def build_secure_product_execution_factory(
    *,
    knowledge_provider: Any,
) -> RuntimeExecutionFactory:
    """Bind the verified product Program to its actual Harness adapters.

    Constructing this factory is local and side-effect free: provider calls
    can only happen later when AgentRuntime executes a request.
    """

    if knowledge_provider is None:
        raise RuntimeCompositionError("knowledge_provider is required")
    return RuntimeExecutionFactory(
        knowledge_provider=knowledge_provider,
        evaluator_factory=lambda runtime: SecureChatEvaluationAdapter(
            runtime=runtime,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            fact_pack_builder=build_fact_pack,
        ),
        reviser_factory=lambda runtime: ChatCoachReviser(
            runtime=runtime,
            system_prompt=REVISER_SYSTEM_PROMPT,
            prompt_builder=build_revision_prompt,
            validator=validate_revised_report,
        ),
    )


@dataclass(frozen=True)
class RuntimeCompositionRoot:
    """Create long-lived Catalog/Resolver dependencies in one place.

    This root deliberately does not construct FastAPI, read API keys, or make
    network calls.  5P-3 will add the application service that uses this root.
    """

    skill_catalog: SkillCatalog
    prompt_program_catalog: PromptProgramCatalog
    prompt_program_resolver: PromptProgramResolver

    @classmethod
    def from_directories(
        cls,
        *,
        skills_root: str | Path,
        prompt_programs_root: str | Path,
    ) -> "RuntimeCompositionRoot":
        skill_catalog = SkillCatalog.from_directory(skills_root)
        prompt_program_catalog = PromptProgramCatalog.from_directory(
            prompt_programs_root
        )
        resolver = PromptProgramResolver(
            prompt_program_catalog,
            skill_catalog,
        )
        # Composition is the product startup boundary: a stale manifest must
        # stop construction before any Runtime or Provider can be used.
        resolver.verify_all()
        return cls(
            skill_catalog=skill_catalog,
            prompt_program_catalog=prompt_program_catalog,
            prompt_program_resolver=resolver,
        )

    def build_runtime(
        self,
        *,
        runs_root: str | Path,
        provider: Any,
        execution_factory: RuntimeExecutionFactory | None = None,
        knowledge_provider: Any | None = None,
        context_builder: Any | None = None,
    ) -> AgentRuntimeV1:
        """Build Runtime with verified Program and secure product defaults."""

        if execution_factory is None:
            execution_factory = build_secure_product_execution_factory(
                knowledge_provider=knowledge_provider
            )
        elif knowledge_provider is not None:
            raise RuntimeCompositionError(
                "knowledge_provider cannot accompany an explicit execution_factory"
            )

        return AgentRuntimeV1(
            runs_root=runs_root,
            catalog=self.skill_catalog,
            provider=provider,
            execution_factory=execution_factory,
            context_builder=context_builder,
            prompt_program_resolver=self.prompt_program_resolver,
        )


__all__ = [
    "RuntimeCompositionRoot",
    "build_secure_product_execution_factory",
]
