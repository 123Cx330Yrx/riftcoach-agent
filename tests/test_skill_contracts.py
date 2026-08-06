from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.skills.loader import (
    SkillContractError,
    load_skill,
    validate_skill_tools,
)
from app.skills.models import SkillManifest, SkillTriggerGroup, SkillTriggers
from app.skills.recent_form_review import (
    RecentFormReviewInput,
    RecentFormReviewOutput,
)
from app.tools.models import ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry


SKILL_ROOT = Path("skills/recent-form-review")


def valid_summary() -> dict:
    return {
        "schema_version": "1.0",
        "metadata": {},
        "player": {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "riot_id": "DemoPlayer#TEST",
        },
        "request": {"count": 10},
        "recent_summary": {"games_analyzed": 1},
        "matches": [
            {
                "match_id": "KR_1",
                "game_duration_seconds": 1800,
                "champion_id": 103,
                "champion_name": "Ahri",
                "role": "MIDDLE",
                "win": True,
                "timeline_status": "available",
                "included_in_aggregate": True,
            }
        ],
        "failed_matches": [],
        "excluded_matches": [],
    }


def knowledge_definition() -> ToolDefinition:
    return ToolDefinition(
        name="knowledge.search",
        version="1.0.0",
        description="Search test knowledge.",
        handler=lambda params, context: {"chunks": []},
        input_schema={
            "type": "object",
            "properties": {},
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


def test_loads_recent_form_skill_and_resolves_typed_models():
    skill = load_skill(SKILL_ROOT)

    assert skill.manifest.name == "recent-form-review"
    assert skill.manifest.permissions.allowed_tools == ("knowledge.search",)
    assert tuple(
        group.name for group in skill.manifest.triggers.required_signal_groups
    ) == ("recent_scope", "review_goal")
    assert "版本" in skill.manifest.triggers.excluded_signals
    assert skill.input_model is RecentFormReviewInput
    assert skill.output_model is RecentFormReviewOutput
    assert "Do not invent rank" in skill.instructions


def test_recent_form_input_reuses_player_summary_validation():
    value = RecentFormReviewInput(
        player_summary=valid_summary(),
        deterministic_report="# Deterministic facts",
        focus="survival",
    )

    assert value.player_summary["schema_version"] == "1.0"
    assert value.focus == "survival"

    invalid = valid_summary()
    invalid["schema_version"] = "0.9"
    with pytest.raises(ValueError, match="Unsupported summary schema"):
        RecentFormReviewInput(
            player_summary=invalid,
            deterministic_report="facts",
        )


def test_recent_form_output_enforces_publication_boundary():
    published = RecentFormReviewOutput(
        run_id="run-1",
        status="published",
        report="# Coach report",
        evaluation_score=91,
        evidence_source_ids=("metric_rules.md",),
    )
    assert published.evaluation_score == 91

    with pytest.raises(ValidationError, match="requires a report"):
        RecentFormReviewOutput(run_id="run-2", status="degraded")

    with pytest.raises(ValidationError, match="must not expose a report"):
        RecentFormReviewOutput(
            run_id="run-3",
            status="rejected",
            report="unapproved draft",
        )


def test_manifest_rejects_unknown_fields_and_overlapping_triggers():
    raw = yaml.safe_load((SKILL_ROOT / "manifest.yaml").read_text("utf-8"))
    raw["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SkillManifest.model_validate(raw)

    raw.pop("unexpected")
    raw["triggers"]["negative_examples"] = [
        raw["triggers"]["positive_examples"][0]
    ]
    with pytest.raises(ValidationError, match="must not overlap"):
        SkillManifest.model_validate(raw)


def test_trigger_rules_require_unique_groups_and_non_overlapping_signals():
    scope = SkillTriggerGroup(
        name="recent_scope",
        any_of=("最近", "近期"),
    )
    goal = SkillTriggerGroup(
        name="review_goal",
        any_of=("状态", "表现"),
    )

    triggers = SkillTriggers(
        intent="recent_form_review",
        positive_examples=("分析最近十局的状态",),
        negative_examples=("分析当前版本",),
        required_signal_groups=(scope, goal),
        excluded_signals=("版本",),
    )
    assert triggers.required_signal_groups == (scope, goal)

    with pytest.raises(ValidationError, match="group names must be unique"):
        SkillTriggers(
            intent="recent_form_review",
            positive_examples=("分析最近十局的状态",),
            required_signal_groups=(
                scope,
                SkillTriggerGroup(
                    name="recent_scope",
                    any_of=("状态",),
                ),
            ),
        )

    with pytest.raises(ValidationError, match="must not overlap"):
        SkillTriggers(
            intent="recent_form_review",
            positive_examples=("分析最近十局的状态",),
            required_signal_groups=(scope, goal),
            excluded_signals=("最 近",),
        )


def test_trigger_group_rejects_signals_that_normalize_to_duplicates():
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        SkillTriggerGroup(
            name="match_scope",
            any_of=("MATCH ID", "match_id"),
        )


def test_skill_tool_permissions_must_exist_in_active_registry():
    skill = load_skill(SKILL_ROOT)
    empty_registry = ToolRegistry()
    with pytest.raises(SkillContractError, match="unregistered tools"):
        validate_skill_tools(skill, empty_registry)

    registry = ToolRegistry()
    registry.register(knowledge_definition())
    validate_skill_tools(skill, registry)


def test_loader_rejects_manifest_and_frontmatter_drift(tmp_path):
    skill_dir = tmp_path / "recent-form-review"
    skill_dir.mkdir()
    manifest = (SKILL_ROOT / "manifest.yaml").read_text("utf-8")
    instructions = (SKILL_ROOT / "SKILL.md").read_text("utf-8")
    (skill_dir / "manifest.yaml").write_text(manifest, encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        instructions.replace(
            "name: recent-form-review",
            "name: single-match-review",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(SkillContractError, match="name must match"):
        load_skill(skill_dir)
