from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.agent.compiler import AgentRunCompileError, AgentRunCompiler
from app.agent.context import ContextBuilderV1
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.models import ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry


FIXTURES = Path("examples/fixtures")


def demo_summary() -> dict:
    return json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )


def demo_report() -> str:
    return (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )


def knowledge_definition() -> ToolDefinition:
    return ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable test knowledge.",
        handler=lambda params, context: {"chunks": []},
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"chunks": {"type": "array"}},
            "required": ["chunks"],
            "additionalProperties": False,
        },
        policy=ToolPolicy(),
    )


def registered_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(knowledge_definition())
    return registry


def validated_execution(*, utterance: str, payload: dict, run_id: str):
    catalog = SkillCatalog.from_directory("skills")
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    typed_input = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    request = SkillExecutionRequest(
        run_id=run_id,
        user_utterance=utterance,
        router_decision=decision,
        input_payload=payload,
        input_artifacts=binding,
    )
    return SkillExecutionBoundary(catalog).validate(request)


@pytest.mark.parametrize(
    ("utterance", "payload", "run_id"),
    (
        (
            "分析我最近十局的状态",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "focus": "survival",
            },
            "review_compile_recent",
        ),
        (
            "深入复盘这一场的表现",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "target_match_id": "SYNTHETIC_WIN_001",
                "focus": "laning",
            },
            "review_compile_single",
        ),
    ),
)
def test_compiler_maps_only_verified_manifest_context_and_artifact_identity(
    utterance: str,
    payload: dict,
    run_id: str,
):
    execution = validated_execution(
        utterance=utterance,
        payload=payload,
        run_id=run_id,
    )
    context = ContextBuilderV1().build(execution)

    request = AgentRunCompiler(registered_tools()).compile(execution, context)
    manifest = execution.skill.manifest

    assert request.messages == context.messages
    assert request.allowed_tools == manifest.permissions.allowed_tools
    assert request.max_iterations == manifest.budgets.max_iterations
    assert request.max_tool_calls == manifest.budgets.max_tool_calls
    assert request.timeout_s == manifest.budgets.timeout_s
    assert request.max_context_tokens == context.max_context_tokens
    assert dict(request.metadata) == {
        "context_estimated_tokens": context.estimated_tokens,
        "context_max_tokens": context.max_context_tokens,
        "context_omitted_section_ids": context.omitted_section_ids,
        "deterministic_report_sha256": (
            execution.input_artifacts.deterministic_report.sha256
        ),
        "player_summary_sha256": (
            execution.input_artifacts.player_summary.sha256
        ),
        "run_id": run_id,
        "skill_name": manifest.name,
        "skill_version": manifest.version,
    }


@pytest.mark.parametrize(
    ("field_name", "drifted_value"),
    (
        ("run_id", "review_other_run"),
        ("skill_name", "other-skill"),
        ("skill_version", "9.9.9"),
    ),
)
def test_compiler_rejects_execution_context_identity_drift(
    field_name: str,
    drifted_value: str,
):
    execution = validated_execution(
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
        },
        run_id="review_compile_identity",
    )
    context = ContextBuilderV1().build(execution)
    drifted = replace(context, **{field_name: drifted_value})

    with pytest.raises(AgentRunCompileError, match="identity mismatch"):
        AgentRunCompiler(registered_tools()).compile(execution, drifted)


def test_compiler_rejects_context_ceiling_above_verified_manifest():
    execution = validated_execution(
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
        },
        run_id="review_compile_ceiling",
    )
    context = ContextBuilderV1().build(execution)
    raised = replace(
        context,
        max_context_tokens=(
            execution.skill.manifest.budgets.max_context_tokens + 1
        ),
    )

    with pytest.raises(AgentRunCompileError, match="Manifest ceiling"):
        AgentRunCompiler(registered_tools()).compile(execution, raised)


def test_compiler_reestimates_messages_and_rejects_actual_overflow():
    class OversizedSizer:
        def estimate_messages(self, messages):
            return 999_999

    execution = validated_execution(
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
        },
        run_id="review_compile_reestimate",
    )
    context = ContextBuilderV1().build(execution)

    with pytest.raises(AgentRunCompileError, match="actual messages"):
        AgentRunCompiler(
            registered_tools(),
            sizer=OversizedSizer(),
        ).compile(execution, context)


def test_compiler_rejects_unregistered_manifest_tool_before_agent_run():
    execution = validated_execution(
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
        },
        run_id="review_compile_missing_tool",
    )
    context = ContextBuilderV1().build(execution)

    with pytest.raises(AgentRunCompileError, match="unregistered tools"):
        AgentRunCompiler(ToolRegistry()).compile(execution, context)
