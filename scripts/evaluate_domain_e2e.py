import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    evaluate_domain_candidate,
    load_domain_candidate,
    load_domain_dataset,
    validate_domain_dataset_usage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate recorded RiftCoach domain-Agent observations."
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/domain_e2e_v1_development_cases.json",
    )
    parser.add_argument(
        "--candidate",
        default=(
            "data/evaluation/candidates/"
            "domain_e2e_v1_offline_baseline.json"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("development", "held_out"),
        default="development",
    )
    parser.add_argument("--confirm-rules-frozen", action="store_true")
    parser.add_argument(
        "--output",
        default="data/evaluation/results/domain_e2e_v1_offline_baseline.json",
    )
    args = parser.parse_args()

    dataset = load_domain_dataset(args.dataset)
    candidate = load_domain_candidate(args.candidate)
    try:
        validate_domain_dataset_usage(
            dataset,
            DomainDatasetRole(args.mode),
            confirm_rules_frozen=args.confirm_rules_frozen,
        )
        result = evaluate_domain_candidate(dataset, candidate)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Dataset: {result.dataset_version} ({result.dataset_role.value})")
    print(f"Candidate: {result.candidate_id} ({result.candidate_kind})")
    print(f"External Provider calls: {result.external_provider_calls}")
    print(f"Cases: {result.case_count}")
    print(f"Task outcome accuracy: {result.task_outcome_accuracy:.4f}")
    print(
        "Failure classification accuracy: "
        f"{result.failure_classification_accuracy:.4f}"
    )
    print(f"Unsafe publication rate: {result.unsafe_publication_rate:.4f}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
