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
from app.skills.single_match_review import (
    SingleMatchReviewInput,
    SingleMatchReviewOutput,
)
from app.tools.models import ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry


SKILL_ROOT = Path("skills/recent-form-review")
SINGLE_MATCH_SKILL_ROOT = Path("skills/single-match-review")


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
    assert skill.manifest.version == "0.2.0"
    assert skill.manifest.permissions.allowed_tools == ("knowledge.search",)
    assert tuple(
        group.name for group in skill.manifest.triggers.required_signal_groups
    ) == ("recent_scope", "review_goal")
    assert "版本" in skill.manifest.triggers.excluded_signals
    assert skill.input_model is RecentFormReviewInput
    assert skill.output_model is RecentFormReviewOutput
    assert "Do not invent rank" in skill.instructions


def test_loads_single_match_skill_and_resolves_typed_models():
    skill = load_skill(SINGLE_MATCH_SKILL_ROOT)

    assert skill.manifest.name == "single-match-review"
    assert skill.manifest.version == "0.1.0"
    assert skill.manifest.permissions.allowed_tools == ("knowledge.search",)
    assert tuple(
        group.name for group in skill.manifest.triggers.required_signal_groups
    ) == ("match_scope", "review_goal")
    assert "版本" in skill.manifest.triggers.excluded_signals
    assert skill.input_model is SingleMatchReviewInput
    assert skill.output_model is SingleMatchReviewOutput
    assert "Do not treat unavailable Timeline data as zero" in skill.instructions


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


def test_single_match_input_requires_exactly_one_target_match():
    value = SingleMatchReviewInput(
        player_summary=valid_summary(),
        deterministic_report="# Deterministic facts",
        target_match_id="  KR_1  ",
        focus="survival",
    )

    assert value.target_match_id == "KR_1"
    assert value.focus == "survival"

    with pytest.raises(ValidationError, match="Field required"):
        SingleMatchReviewInput(
            player_summary=valid_summary(),
            deterministic_report="facts",
        )

    invalid_summary = valid_summary()
    invalid_summary["schema_version"] = "0.9"
    with pytest.raises(ValidationError, match="Unsupported summary schema"):
        SingleMatchReviewInput(
            player_summary=invalid_summary,
            deterministic_report="facts",
            target_match_id="KR_1",
        )

    with pytest.raises(ValidationError, match="must not be blank"):
        SingleMatchReviewInput(
            player_summary=valid_summary(),
            deterministic_report="   ",
            target_match_id="KR_1",
        )

    with pytest.raises(ValidationError, match="exactly one match row"):
        SingleMatchReviewInput(
            player_summary=valid_summary(),
            deterministic_report="facts",
            target_match_id="KR_MISSING",
        )

    duplicate_summary = valid_summary()
    duplicate_summary["matches"].append(
        dict(duplicate_summary["matches"][0])
    )
    with pytest.raises(ValidationError, match="exactly one match row"):
        SingleMatchReviewInput(
            player_summary=duplicate_summary,
            deterministic_report="facts",
            target_match_id="KR_1",
        )


def test_single_match_input_accepts_short_match_and_explicit_missing_timeline():
    summary = valid_summary()
    summary["matches"][0].update(
        {
            "timeline_status": "unavailable",
            "timeline_error": "timeline unavailable",
            "is_short_game": True,
            "included_in_aggregate": False,
            "exclusion_reason": "game_duration_below_300_seconds",
            "death_times": [],
            "deaths_before_10": None,
            "deaths_before_15": None,
            "item_purchases": [],
        }
    )

    value = SingleMatchReviewInput(
        player_summary=summary,
        deterministic_report="facts",
        target_match_id="KR_1",
    )
    assert value.player_summary["matches"][0]["included_in_aggregate"] is False

    summary["matches"][0]["timeline_error"] = "  "
    with pytest.raises(ValidationError, match="timeline_error"):
        SingleMatchReviewInput(
            player_summary=summary,
            deterministic_report="facts",
            target_match_id="KR_1",
        )


def test_single_match_input_rejects_timeline_unknowns_encoded_as_zero():
    summary = valid_summary()
    summary["matches"][0].update(
        {
            "timeline_status": "unavailable",
            "timeline_error": "timeline unavailable",
            "deaths_before_15": 0,
        }
    )

    with pytest.raises(ValidationError, match="must remain unknown"):
        SingleMatchReviewInput(
            player_summary=summary,
            deterministic_report="facts",
            target_match_id="KR_1",
        )

    summary["matches"][0].update(
        {
            "deaths_before_15": None,
            "death_times": ["09:15"],
        }
    )
    with pytest.raises(ValidationError, match="collections must be empty"):
        SingleMatchReviewInput(
            player_summary=summary,
            deterministic_report="facts",
            target_match_id="KR_1",
        )


def test_single_match_output_identifies_target_and_enforces_publication_boundary():
    published = SingleMatchReviewOutput(
        run_id="run-single-1",
        target_match_id=" KR_1 ",
        status="published",
        report="# Single match review",
        evaluation_score=92,
        evidence_source_ids=("metric_rules.md",),
    )
    assert published.target_match_id == "KR_1"

    with pytest.raises(ValidationError, match="requires a report"):
        SingleMatchReviewOutput(
            run_id="run-single-2",
            target_match_id="KR_1",
            status="degraded",
        )

    with pytest.raises(ValidationError, match="must not expose a report"):
        SingleMatchReviewOutput(
            run_id="run-single-3",
            target_match_id="KR_1",
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
