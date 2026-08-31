"""Compile validated Skill/context contracts into one bounded Agent request."""

from __future__ import annotations

from app.model_runtime import (
    ModelRuntimeProfile,
    require_registered_model_runtime_profile,
)
from app.skills.execution import ValidatedSkillExecution
from app.tools.errors import ToolNotFoundError
from app.tools.registry import ToolRegistry

from .context import (
    ContextBundle,
    ContextSizer,
    DeterministicContextSizer,
)
from .loop import AgentRunRequest


class AgentRunCompileError(ValueError):
    """Raised before AgentLoop when trusted run contracts do not compose."""


class AgentRunCompiler:
    """Derive least-privilege AgentRunRequest values from a Skill Manifest."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        *,
        sizer: ContextSizer | None = None,
        runtime_profile: ModelRuntimeProfile | None = None,
    ) -> None:
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError("tool_registry must be a ToolRegistry")
        self._tool_registry = tool_registry
        self._sizer = sizer or DeterministicContextSizer()
        self._runtime_profile = (
            require_registered_model_runtime_profile(runtime_profile)
            if runtime_profile is not None
            else None
        )

    def compile(
        self,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> AgentRunRequest:
        if not isinstance(execution, ValidatedSkillExecution):
            raise AgentRunCompileError(
                "execution must be a ValidatedSkillExecution"
            )
        if not isinstance(context, ContextBundle):
            raise AgentRunCompileError("context must be a ContextBundle")

        manifest = execution.skill.manifest
        execution_identity = (
            execution.run_id,
            manifest.name,
            manifest.version,
        )
        context_identity = (
            context.run_id,
            context.skill_name,
            context.skill_version,
        )
        if context_identity != execution_identity:
            raise AgentRunCompileError(
                "execution and context identity mismatch"
            )

        if (
            context.max_context_tokens
            > manifest.budgets.max_context_tokens
        ):
            raise AgentRunCompileError(
                "context exceeds the verified Manifest ceiling"
            )

        actual_estimate = self._sizer.estimate_messages(context.messages)
        if actual_estimate > context.max_context_tokens:
            raise AgentRunCompileError(
                "actual messages exceed max_context_tokens"
            )

        missing_tools: list[str] = []
        for tool_name in manifest.permissions.allowed_tools:
            try:
                self._tool_registry.get(tool_name)
            except ToolNotFoundError:
                missing_tools.append(tool_name)
        if missing_tools:
            raise AgentRunCompileError(
                "Manifest references unregistered tools: "
                + ", ".join(missing_tools)
            )

        profile = self._runtime_profile
        metadata = {
            "context_estimated_tokens": actual_estimate,
            "context_max_tokens": context.max_context_tokens,
            "context_omitted_section_ids": context.omitted_section_ids,
            "deterministic_report_sha256": (
                execution.input_artifacts.deterministic_report.sha256
            ),
            "player_summary_sha256": (
                execution.input_artifacts.player_summary.sha256
            ),
            "run_id": execution.run_id,
            "skill_name": manifest.name,
            "skill_version": manifest.version,
        }
        if profile is not None:
            metadata.update(
                {
                    "runtime_profile_id": profile.profile_id,
                    "runtime_profile_version": profile.version,
                }
            )

        return AgentRunRequest(
            messages=context.messages,
            allowed_tools=manifest.permissions.allowed_tools,
            max_iterations=manifest.budgets.max_iterations,
            max_tool_calls=manifest.budgets.max_tool_calls,
            timeout_s=(
                profile.agent_timeout_s
                if profile is not None
                else manifest.budgets.timeout_s
            ),
            max_context_tokens=context.max_context_tokens,
            temperature=(
                profile.temperature if profile is not None else 0.0
            ),
            max_tokens=(
                profile.max_output_tokens if profile is not None else None
            ),
            top_p=profile.top_p if profile is not None else None,
            metadata=metadata,
        )
