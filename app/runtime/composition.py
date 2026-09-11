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
from app.model_runtime import (
    ModelRuntimeProfile,
    require_registered_model_runtime_profile,
    resolve_model_runtime_profile,
)
from app.prompt_program import PromptProgramCatalog, PromptProgramResolver
from app.skills.catalog import SkillCatalog
from .coach_contract import COACH_CONTRACT, GROUNDED_COACH_CONTRACT, BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT
from .coach_context import CoachContextBuilder

from .runtime import (
    AgentRuntimeV1,
    RuntimeCompositionError,
    RuntimeExecutionFactory,
)


def build_secure_product_execution_factory(
    *,
    knowledge_provider: Any,
    runtime_profile: ModelRuntimeProfile | None = None,
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
        runtime_profile=runtime_profile,
    )


@dataclass(frozen=True)
class RuntimeCompositionRoot:
    """Create long-lived Catalog/Resolver dependencies in one place.

    This root deliberately does not construct FastAPI, read API keys, or make
    network calls.  Product Application Services and HTTP adapters are
    assembled one layer outward and receive the built Runtime explicitly.
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
        coach_contract=None,
    ) -> "RuntimeCompositionRoot":
        skill_catalog = SkillCatalog.from_directory(skills_root)
        prompt_program_catalog = PromptProgramCatalog.from_directory(
            prompt_programs_root
        )
        resolver = PromptProgramResolver(
            prompt_program_catalog,
            skill_catalog,
            coach_contract=coach_contract,
        )
        # Composition is the product startup boundary: a stale manifest must
        # stop construction before any Runtime or Provider can be used.
        resolver.verify_all()
        return cls(
            skill_catalog=skill_catalog,
            prompt_program_catalog=prompt_program_catalog,
            prompt_program_resolver=resolver,
        )

    def build_offline_coach_runtime(self, *, runs_root, provider, knowledge_provider, context_builder=None):
        """Explicit migration seam; ordinary build_runtime and worker startup stay unchanged."""
        from app.rag.coaching_query import CoachingQueryKnowledgeProvider
        from app.evaluation.glm53_report_contract import build_aligned_revision_prompt
        contract = self.prompt_program_resolver.coach_contract
        if all(contract is not c for c in (COACH_CONTRACT, GROUNDED_COACH_CONTRACT, BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT)):
            raise RuntimeCompositionError("independent Coach assets must be explicitly verified")
        contract.require_provider(provider)
        evaluator_type, reviser_type = SecureChatEvaluationAdapter, ChatCoachReviser
        if contract.grounded:
            from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter, GroundedCoachReviser
            evaluator_type, reviser_type = GroundedChatEvaluationAdapter, GroundedCoachReviser
        factory = RuntimeExecutionFactory(
            knowledge_provider=CoachingQueryKnowledgeProvider(knowledge_provider),
            evaluator_factory=lambda runtime: evaluator_type(
                runtime=runtime, system_prompt=EVALUATOR_SYSTEM_PROMPT, fact_pack_builder=build_fact_pack,
                **({"inference_audit": "coverage" if contract is COVERAGE_COACH_CONTRACT else "v3" if contract is ANCHOR_COACH_CONTRACT else "v2" if contract is CLAIM_COACH_CONTRACT else True} if contract in (INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT) else {}),
                **({"include_generation_facts": True} if contract.descriptor().get("include_generation_facts") else {}),
                **({"compact_report_policy": contract.compact_report_policy} if contract.compact_report_policy else {}),
                **({"source_use_policy": contract.source_use_policy} if contract.source_use_policy else {}),
                **({"position_policy": contract.position_policy} if contract.position_policy else {}),
                **({"include_deterministic_facts": True} if contract.descriptor().get("include_deterministic_source_facts") else {})),
            reviser_factory=lambda runtime: reviser_type(
                runtime=runtime, system_prompt=REVISER_SYSTEM_PROMPT,
                **({"inference_audit": "coverage" if contract is COVERAGE_COACH_CONTRACT else "v3" if contract is ANCHOR_COACH_CONTRACT else "v2" if contract is CLAIM_COACH_CONTRACT else True} if contract in (INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT) else {}),
                prompt_builder=build_aligned_revision_prompt, validator=validate_revised_report,
                **({"include_generation_facts": True} if contract.descriptor().get("include_generation_facts") else {}),
                **({"compact_report_policy": contract.compact_report_policy} if contract.compact_report_policy else {}),
                **({"source_use_policy": contract.source_use_policy} if contract.source_use_policy else {}),
                **({"position_policy": contract.position_policy} if contract.position_policy else {}),
                **({"include_deterministic_facts": True} if contract.descriptor().get("include_deterministic_source_facts") else {})),
            coach_contract=contract,
        )
        return AgentRuntimeV1(
            runs_root=runs_root, catalog=self.skill_catalog, provider=provider,
            execution_factory=factory, context_builder=context_builder or CoachContextBuilder(coach_contract=contract),
            prompt_program_resolver=self.prompt_program_resolver,
        )

    def build_runtime(
        self,
        *,
        runs_root: str | Path,
        provider: Any,
        execution_factory: RuntimeExecutionFactory | None = None,
        knowledge_provider: Any | None = None,
        context_builder: Any | None = None,
        runtime_profile: ModelRuntimeProfile | None = None,
    ) -> AgentRuntimeV1:
        """Build Runtime with verified Program and secure product defaults."""

        expected_profile = resolve_model_runtime_profile(
            getattr(provider, "provider_name", ""),
            getattr(provider, "model_name", ""),
        )
        provider_profile = getattr(provider, "runtime_profile", None)
        requested_profile = (
            require_registered_model_runtime_profile(runtime_profile)
            if runtime_profile is not None
            else None
        )

        if execution_factory is None:
            selected_profile = requested_profile
            if expected_profile is not None:
                if provider_profile != expected_profile:
                    raise RuntimeCompositionError(
                        "Flash Provider requires the registered runtime profile"
                    )
                if selected_profile is None:
                    selected_profile = expected_profile
            execution_factory = build_secure_product_execution_factory(
                knowledge_provider=knowledge_provider,
                runtime_profile=selected_profile,
            )
            runtime_profile = selected_profile
        elif knowledge_provider is not None:
            raise RuntimeCompositionError(
                "knowledge_provider cannot accompany an explicit execution_factory"
            )
        else:
            factory_profile = execution_factory.runtime_profile
            if requested_profile is not None:
                if factory_profile != requested_profile:
                    raise RuntimeCompositionError(
                        "explicit runtime_profile must be bound to the execution_factory"
                    )
                runtime_profile = requested_profile
            else:
                runtime_profile = factory_profile

            if expected_profile is not None:
                if provider_profile != expected_profile:
                    raise RuntimeCompositionError(
                        "Flash Provider requires the registered runtime profile"
                    )
                if runtime_profile is None:
                    runtime_profile = expected_profile
            elif runtime_profile is not None and not runtime_profile.matches(
                getattr(provider, "provider_name", ""),
                getattr(provider, "model_name", ""),
            ):
                raise RuntimeCompositionError(
                    "runtime_profile does not match the Runtime Provider"
                )

        # A custom factory may have been supplied with no profile while a
        # concrete Flash Provider lets us infer the registered profile.  The
        # AgentRuntime and factory each re-check this same pair before use.
        if execution_factory is not None and runtime_profile is not None:
            factory_profile = execution_factory.runtime_profile
            if factory_profile is not None and factory_profile != runtime_profile:
                raise RuntimeCompositionError(
                    "Runtime and execution factory profiles do not match"
                )
        if expected_profile is not None:
            if provider_profile != expected_profile:
                raise RuntimeCompositionError(
                    "Flash Provider requires the registered runtime profile"
                )
            if runtime_profile is None:
                runtime_profile = expected_profile
        elif runtime_profile is not None and not runtime_profile.matches(
            getattr(provider, "provider_name", ""),
            getattr(provider, "model_name", ""),
        ):
            raise RuntimeCompositionError(
                "runtime_profile does not match the Runtime Provider"
            )

        return AgentRuntimeV1(
            runs_root=runs_root,
            catalog=self.skill_catalog,
            provider=provider,
            execution_factory=execution_factory,
            context_builder=context_builder,
            prompt_program_resolver=self.prompt_program_resolver,
            runtime_profile=runtime_profile,
        )


__all__ = [
    "RuntimeCompositionRoot",
    "build_secure_product_execution_factory",
]
