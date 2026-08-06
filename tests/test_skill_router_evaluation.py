from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.skills.catalog import SkillCatalog
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_evaluation import (
    RoutingCase,
    RoutingDatasetRole,
    evaluate_routing,
    load_routing_dataset,
    validate_candidate_snapshot,
    validate_dataset_usage,
)
from app.skills.routing_models import RouteOutcome, RouteReason


DEVELOPMENT_PATH = Path(
    "data/evaluation/skill_router_v1_development_cases.json"
)
HOLDOUT_PATH = Path("data/evaluation/skill_router_v1_holdout_cases.json")
ARCHIVE_MANIFEST_PATH = Path(
    "data/evaluation/history/skill_router_v1_single_skill_baseline_manifest.json"
)


def test_development_dataset_records_two_skill_snapshot_and_contamination():
    dataset = load_routing_dataset(DEVELOPMENT_PATH)

    assert dataset.dataset_id == "skill-router-v1-two-skill-development"
    assert dataset.dataset_version == "2.0.0"
    assert dataset.role is RoutingDatasetRole.DEVELOPMENT
    assert dataset.calibration_excluded is False
    assert len(dataset.cases) == 23
    assert {skill.name: skill.version for skill in dataset.candidate_snapshot.skills} == {
        "recent-form-review": "0.2.0",
        "single-match-review": "0.1.0",
    }
    assert dataset.contamination_notes
    assert any(case.contamination_sources for case in dataset.cases)


def test_holdout_dataset_is_sealed_and_has_no_calibration_sources():
    dataset = load_routing_dataset(HOLDOUT_PATH)

    assert dataset.dataset_id == "skill-router-v1-two-skill-holdout"
    assert dataset.dataset_version == "1.0.0"
    assert dataset.role is RoutingDatasetRole.HELD_OUT
    assert dataset.calibration_excluded is True
    assert len(dataset.cases) == 12
    assert dataset.metadata["sealed_before_first_run"] is True
    assert all(not case.contamination_sources for case in dataset.cases)


def test_candidate_snapshot_matches_current_catalog():
    catalog = SkillCatalog.from_directory("skills")

    validate_candidate_snapshot(
        load_routing_dataset(DEVELOPMENT_PATH),
        catalog.route_candidates,
    )
    validate_candidate_snapshot(
        load_routing_dataset(HOLDOUT_PATH),
        catalog.route_candidates,
    )


def test_candidate_snapshot_rejects_version_drift():
    catalog = SkillCatalog.from_directory("skills")
    drifted = tuple(
        candidate.model_copy(update={"version": "9.9.9"})
        if candidate.name == "recent-form-review"
        else candidate
        for candidate in catalog.route_candidates
    )

    with pytest.raises(ValueError, match="candidate snapshot mismatch"):
        validate_candidate_snapshot(
            load_routing_dataset(DEVELOPMENT_PATH),
            drifted,
        )


def test_holdout_cannot_be_loaded_as_development():
    dataset = load_routing_dataset(HOLDOUT_PATH)

    with pytest.raises(ValueError, match="role is held_out"):
        validate_dataset_usage(dataset, RoutingDatasetRole.DEVELOPMENT)


def test_holdout_requires_explicit_rules_frozen_confirmation():
    dataset = load_routing_dataset(HOLDOUT_PATH)

    with pytest.raises(ValueError, match="rules are frozen"):
        validate_dataset_usage(dataset, RoutingDatasetRole.HELD_OUT)

    validate_dataset_usage(
        dataset,
        RoutingDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )


def test_development_cli_rejects_holdout_before_writing_result(tmp_path: Path):
    output_path = tmp_path / "must-not-exist.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_skill_routing.py",
            "--cases",
            str(HOLDOUT_PATH),
            "--mode",
            "development",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert "role is held_out, expected development" in completed.stderr
    assert not output_path.exists()


def test_historical_files_match_the_frozen_archive_hashes():
    manifest = json.loads(ARCHIVE_MANIFEST_PATH.read_text(encoding="utf-8"))

    dataset_path = Path(manifest["archived_dataset_path"])
    result_path = Path(manifest["archived_result_path"])
    assert _sha256(dataset_path) == manifest["dataset_sha256"]
    assert _sha256(result_path) == manifest["result_sha256"]
    assert manifest["candidate_snapshot"]["skills"] == [
        {
            "name": "recent-form-review",
            "version": "0.1.0",
            "manifest_git_blob": "ef1c95d7c074a1aab1880fe327570eaa6e34100a",
        }
    ]
    assert manifest["provenance"]["exact_run_commit_known"] is False


def test_evaluator_reports_ambiguity_accuracy():
    case = RoutingCase(
        case_id="synthetic_ambiguity",
        utterance="分析最近十局状态，再复盘这一场",
        category="ambiguous_mixed_scope",
        expected_outcome=RouteOutcome.AMBIGUOUS,
        expected_reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
        expected_selected_skill=None,
        expected_candidate_skills=(
            "recent-form-review",
            "single-match-review",
        ),
    )

    evaluation = evaluate_routing(
        DeterministicSkillRouter(),
        SkillCatalog.from_directory("skills").route_candidates,
        (case,),
    )

    assert evaluation.exact_match_accuracy == 1.0
    assert evaluation.ambiguity_accuracy == 1.0


def test_ambiguity_evaluation_does_not_depend_on_candidate_order():
    case = RoutingCase(
        case_id="synthetic_reversed_ambiguity",
        utterance="分析最近十局状态，再复盘这一场",
        category="ambiguous_mixed_scope",
        expected_outcome=RouteOutcome.AMBIGUOUS,
        expected_reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
        expected_selected_skill=None,
        expected_candidate_skills=(
            "recent-form-review",
            "single-match-review",
        ),
        available_skill_names=(
            "single-match-review",
            "recent-form-review",
        ),
    )

    evaluation = evaluate_routing(
        DeterministicSkillRouter(),
        SkillCatalog.from_directory("skills").route_candidates,
        (case,),
    )

    assert evaluation.exact_match_accuracy == 1.0
    assert evaluation.ambiguity_accuracy == 1.0


def test_evaluator_rejects_case_that_references_unknown_skill():
    case = RoutingCase(
        case_id="unknown_skill",
        utterance="test",
        category="invalid_fixture",
        available_skill_names=("missing-skill",),
        expected_outcome=RouteOutcome.REJECTED,
        expected_reason=RouteReason.NO_MATCHING_SKILL,
        expected_selected_skill=None,
        expected_candidate_skills=(),
    )

    with pytest.raises(ValueError, match="unknown Skill"):
        evaluate_routing(
            DeterministicSkillRouter(),
            SkillCatalog.from_directory("skills").route_candidates,
            (case,),
        )


def test_evaluator_rejects_unknown_skill_in_expected_decision():
    case = RoutingCase(
        case_id="unknown_expected_skill",
        utterance="test",
        category="invalid_fixture",
        expected_outcome=RouteOutcome.SELECTED,
        expected_reason=RouteReason.MATCHED_SKILL,
        expected_selected_skill="missing-skill",
        expected_candidate_skills=("missing-skill",),
    )

    with pytest.raises(ValueError, match="expects unknown Skill"):
        evaluate_routing(
            DeterministicSkillRouter(),
            SkillCatalog.from_directory("skills").route_candidates,
            (case,),
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
