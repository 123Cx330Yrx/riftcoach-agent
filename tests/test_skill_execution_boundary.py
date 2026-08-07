from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from app.harness.models import ArtifactKind
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    InputArtifactCommitment,
    SkillExecutionBoundary,
    SkillExecutionBoundaryError,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.recent_form_review import RecentFormReviewInput
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import (
    RouteEvidence,
    RouteOutcome,
    RouteReason,
    RouterDecision,
    RouterRequest,
)
from app.skills.single_match_review import SingleMatchReviewInput


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


def selected_decision(utterance: str, catalog: SkillCatalog) -> RouterDecision:
    return DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )


def build_request(
    *,
    catalog: SkillCatalog,
    utterance: str,
    payload: dict,
    run_id: str = "review_5d1_example",
) -> SkillExecutionRequest:
    decision = selected_decision(utterance, catalog)
    assert decision.selected_skill is not None
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    typed_input = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    return SkillExecutionRequest(
        run_id=run_id,
        user_utterance=f"  {utterance}  ",
        router_decision=decision,
        input_payload=payload,
        input_artifacts=binding,
    )


@pytest.mark.parametrize(
    ("utterance", "payload", "expected_name", "expected_type"),
    [
        (
            "分析我最近十局的状态",
            {
                "player_summary": valid_summary(),
                "deterministic_report": "  # Deterministic facts  ",
                "focus": "survival",
            },
            "recent-form-review",
            RecentFormReviewInput,
        ),
        (
            "深入复盘这一场的表现",
            {
                "player_summary": valid_summary(),
                "deterministic_report": "  # Deterministic facts  ",
                "target_match_id": "KR_1",
                "focus": "laning",
            },
            "single-match-review",
            SingleMatchReviewInput,
        ),
    ],
)
def test_boundary_validates_both_real_skills_without_executing_them(
    utterance: str,
    payload: dict,
    expected_name: str,
    expected_type: type,
):
    catalog = SkillCatalog.from_directory("skills")
    request = build_request(
        catalog=catalog,
        utterance=utterance,
        payload=payload,
    )

    validated = SkillExecutionBoundary(catalog).validate(request)

    assert validated.run_id == "review_5d1_example"
    assert validated.user_utterance == utterance
    assert validated.skill.manifest.name == expected_name
    assert validated.skill.manifest.version == (
        request.router_decision.selected_skill_version
    )
    assert isinstance(validated.typed_input, expected_type)
    assert validated.typed_input.deterministic_report == "# Deterministic facts"
    assert validated.input_artifacts == request.input_artifacts


def test_input_binding_hashes_the_exact_future_harness_artifact_bytes():
    summary = valid_summary()
    report = "# 确定性报告\n"

    binding = SkillInputArtifactBinding.from_content(
        run_id="review_digest_example",
        player_summary=summary,
        deterministic_report=report,
    )

    summary_bytes = (
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
        + b"\n"
    )
    assert binding.player_summary.kind is ArtifactKind.PLAYER_SUMMARY
    assert binding.player_summary.schema_version == "1.0"
    assert binding.player_summary.sha256 == hashlib.sha256(
        summary_bytes
    ).hexdigest()
    assert binding.deterministic_report.kind is ArtifactKind.DETERMINISTIC_REPORT
    assert binding.deterministic_report.schema_version == "1.0"
    assert binding.deterministic_report.sha256 == hashlib.sha256(
        report.encode("utf-8")
    ).hexdigest()


def test_request_rejects_blank_user_text_and_run_id_binding_mismatch():
    binding = SkillInputArtifactBinding.from_content(
        run_id="review_binding_example",
        player_summary=valid_summary(),
        deterministic_report="facts",
    )
    decision = selected_decision(
        "分析我最近十局的状态",
        SkillCatalog.from_directory("skills"),
    )

    with pytest.raises(ValidationError, match="user_utterance"):
        SkillExecutionRequest(
            run_id=binding.run_id,
            user_utterance="   ",
            router_decision=decision,
            input_payload={},
            input_artifacts=binding,
        )

    with pytest.raises(ValidationError, match="run_id must match"):
        SkillExecutionRequest(
            run_id="review_other_run",
            user_utterance="分析我最近十局的状态",
            router_decision=decision,
            input_payload={},
            input_artifacts=binding,
        )


@pytest.mark.parametrize(
    "utterance",
    (
        "上海明天会下雨吗",
        "分析最近十局状态，再复盘这一场",
    ),
)
def test_boundary_rejects_non_selected_router_decisions(utterance: str):
    catalog = SkillCatalog.from_directory("skills")
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    assert decision.outcome in {RouteOutcome.REJECTED, RouteOutcome.AMBIGUOUS}
    binding = SkillInputArtifactBinding.from_content(
        run_id="review_non_selected",
        player_summary=valid_summary(),
        deterministic_report="facts",
    )
    request = SkillExecutionRequest(
        run_id=binding.run_id,
        user_utterance=utterance,
        router_decision=decision,
        input_payload={
            "player_summary": valid_summary(),
            "deterministic_report": "facts",
        },
        input_artifacts=binding,
    )

    with pytest.raises(SkillExecutionBoundaryError, match="selected"):
        SkillExecutionBoundary(catalog).validate(request)


def test_boundary_rejects_missing_skill_and_catalog_version_drift():
    catalog = SkillCatalog.from_directory("skills")
    binding = SkillInputArtifactBinding.from_content(
        run_id="review_identity_drift",
        player_summary=valid_summary(),
        deterministic_report="facts",
    )
    missing_decision = RouterDecision(
        outcome=RouteOutcome.SELECTED,
        reason=RouteReason.MATCHED_SKILL,
        selected_skill="missing-skill",
        selected_skill_version="1.0.0",
        candidate_skills=("missing-skill",),
        evidence=(
            RouteEvidence(
                skill_name="missing-skill",
                positive_signals=("复盘",),
            ),
        ),
        explanation="Synthetic missing Skill.",
    )
    missing_request = SkillExecutionRequest(
        run_id=binding.run_id,
        user_utterance="复盘",
        router_decision=missing_decision,
        input_payload={},
        input_artifacts=binding,
    )

    with pytest.raises(SkillExecutionBoundaryError, match="not in the Catalog"):
        SkillExecutionBoundary(catalog).validate(missing_request)

    valid_request = build_request(
        catalog=catalog,
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": valid_summary(),
            "deterministic_report": "facts",
        },
        run_id="review_version_drift",
    )
    drifted_request = valid_request.model_copy(
        update={
            "router_decision": valid_request.router_decision.model_copy(
                update={"selected_skill_version": "9.9.9"}
            )
        }
    )

    with pytest.raises(SkillExecutionBoundaryError, match="version mismatch"):
        SkillExecutionBoundary(catalog).validate(drifted_request)


def test_boundary_rejects_invalid_skill_input_before_binding_check():
    catalog = SkillCatalog.from_directory("skills")
    request = build_request(
        catalog=catalog,
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": valid_summary(),
            "deterministic_report": "facts",
        },
        run_id="review_invalid_input",
    )
    invalid_request = request.model_copy(
        update={"input_payload": {"deterministic_report": "facts"}}
    )

    with pytest.raises(SkillExecutionBoundaryError, match="input validation failed"):
        SkillExecutionBoundary(catalog).validate(invalid_request)


def test_boundary_rejects_tampered_artifact_digest_or_metadata():
    catalog = SkillCatalog.from_directory("skills")
    request = build_request(
        catalog=catalog,
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": valid_summary(),
            "deterministic_report": "facts",
        },
        run_id="review_tampered_binding",
    )
    tampered_summary = request.input_artifacts.player_summary.model_copy(
        update={"sha256": "0" * 64}
    )
    tampered_binding = request.input_artifacts.model_copy(
        update={"player_summary": tampered_summary}
    )
    tampered_request = request.model_copy(
        update={"input_artifacts": tampered_binding}
    )

    with pytest.raises(SkillExecutionBoundaryError, match="binding mismatch"):
        SkillExecutionBoundary(catalog).validate(tampered_request)

    wrong_kind = request.input_artifacts.player_summary.model_copy(
        update={"kind": ArtifactKind.COACH_DRAFT}
    )
    wrong_binding = request.input_artifacts.model_copy(
        update={"player_summary": wrong_kind}
    )
    wrong_request = request.model_copy(update={"input_artifacts": wrong_binding})

    with pytest.raises(SkillExecutionBoundaryError, match="binding mismatch"):
        SkillExecutionBoundary(catalog).validate(wrong_request)


def test_validated_input_is_detached_from_the_callers_mutable_payload():
    catalog = SkillCatalog.from_directory("skills")
    summary = valid_summary()
    payload = {
        "player_summary": summary,
        "deterministic_report": "facts",
    }
    request = build_request(
        catalog=catalog,
        utterance="分析我最近十局的状态",
        payload=payload,
        run_id="review_detached_input",
    )

    validated = SkillExecutionBoundary(catalog).validate(request)
    summary["player"]["game_name"] = "TamperedPlayer"
    request.input_payload["player_summary"]["player"]["tag_line"] = "CHANGED"

    assert validated.typed_input.player_summary["player"] == {
        "game_name": "DemoPlayer",
        "tag_line": "TEST",
        "riot_id": "DemoPlayer#TEST",
    }

    exposed_input = validated.typed_input
    exposed_input.player_summary["player"]["riot_id"] = "MUTATED#COPY"
    assert (
        validated.typed_input.player_summary["player"]["riot_id"]
        == "DemoPlayer#TEST"
    )


def test_artifact_commitment_rejects_invalid_digest_and_binding_kinds():
    with pytest.raises(ValidationError, match="lowercase SHA-256"):
        InputArtifactCommitment(
            kind=ArtifactKind.PLAYER_SUMMARY,
            schema_version="1.0",
            sha256="not-a-digest",
        )

    summary_commitment = InputArtifactCommitment(
        kind=ArtifactKind.COACH_DRAFT,
        schema_version="1.0",
        sha256="0" * 64,
    )
    report_commitment = InputArtifactCommitment(
        kind=ArtifactKind.DETERMINISTIC_REPORT,
        schema_version="1.0",
        sha256="1" * 64,
    )
    with pytest.raises(ValidationError, match="player_summary binding"):
        SkillInputArtifactBinding(
            run_id="review_wrong_kind",
            player_summary=summary_commitment,
            deterministic_report=report_commitment,
        )
