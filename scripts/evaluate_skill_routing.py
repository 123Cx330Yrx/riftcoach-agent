import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.skills.catalog import SkillCatalog
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_evaluation import (
    RoutingDatasetRole,
    evaluate_routing,
    load_routing_dataset,
    validate_candidate_snapshot,
    validate_dataset_usage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic Skill routing against fixed cases."
    )
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument(
        "--cases",
        default="data/evaluation/skill_router_v1_development_cases.json",
    )
    parser.add_argument(
        "--mode",
        choices=("development", "held_out"),
        default="development",
        help="Dataset lifecycle role; development mode cannot load holdout.",
    )
    parser.add_argument(
        "--confirm-rules-frozen",
        action="store_true",
        help="Required for a held-out run; do not use holdout results to tune.",
    )
    parser.add_argument("--output")
    parser.add_argument("--min-accuracy", type=float)
    parser.add_argument("--max-false-selection-rate", type=float)
    args = parser.parse_args()

    dataset = load_routing_dataset(Path(args.cases))
    catalog = SkillCatalog.from_directory(args.skills_dir)
    expected_role = RoutingDatasetRole(args.mode)
    try:
        validate_dataset_usage(
            dataset,
            expected_role,
            confirm_rules_frozen=args.confirm_rules_frozen,
        )
        validate_candidate_snapshot(dataset, catalog.route_candidates)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    evaluation = evaluate_routing(
        DeterministicSkillRouter(),
        catalog.route_candidates,
        dataset.cases,
    )

    payload = asdict(evaluation)
    payload["dataset_id"] = dataset.dataset_id
    payload["dataset_version"] = dataset.dataset_version
    payload["dataset_role"] = dataset.role.value
    payload["calibration_excluded"] = dataset.calibration_excluded
    payload["candidate_snapshot"] = {
        "snapshot_id": dataset.candidate_snapshot.snapshot_id,
        "skills": [
            {"name": candidate.name, "version": candidate.version}
            for candidate in catalog.route_candidates
        ],
    }
    payload["skill_names"] = [
        candidate["name"] for candidate in payload["candidate_snapshot"]["skills"]
    ]

    default_output = (
        "data/evaluation/results/skill_router_v1_holdout_baseline.json"
        if expected_role is RoutingDatasetRole.HELD_OUT
        else "data/evaluation/results/skill_router_v1_development_baseline.json"
    )
    output_path = Path(args.output or default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Dataset: {dataset.dataset_version} ({dataset.role.value})")
    print(f"Calibration excluded: {dataset.calibration_excluded}")
    print(f"Skills: {', '.join(payload['skill_names']) or 'none'}")
    print(f"Cases: {len(evaluation.cases)}")
    print(f"Exact-match accuracy: {evaluation.exact_match_accuracy:.4f}")
    print(f"Selection accuracy: {evaluation.selection_accuracy:.4f}")
    print(f"Rejection accuracy: {evaluation.rejection_accuracy:.4f}")
    print(f"Ambiguity accuracy: {evaluation.ambiguity_accuracy:.4f}")
    print(f"False-selection rate: {evaluation.false_selection_rate:.4f}")
    print(f"Saved: {output_path}")

    failures = []
    if (
        args.min_accuracy is not None
        and evaluation.exact_match_accuracy < args.min_accuracy
    ):
        failures.append(
            f"accuracy {evaluation.exact_match_accuracy:.4f} "
            f"< {args.min_accuracy:.4f}"
        )
    if (
        args.max_false_selection_rate is not None
        and evaluation.false_selection_rate
        > args.max_false_selection_rate
    ):
        failures.append(
            f"false-selection rate {evaluation.false_selection_rate:.4f} "
            f"> {args.max_false_selection_rate:.4f}"
        )
    if failures:
        print("Skill routing quality gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
