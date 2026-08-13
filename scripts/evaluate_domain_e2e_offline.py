"""Execute the zero-I/O domain development controls and freeze safe results."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from app.evaluation.domain_e2e import (
    evaluate_domain_candidate,
    load_domain_dataset,
)
from app.evaluation.domain_e2e_offline import OfflineDomainExecutionRunner


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run admitted offline executable domain evaluation controls."
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/domain_e2e_v1_executable_development_cases.json",
    )
    parser.add_argument(
        "--snapshot",
        default="data/evaluation/contracts/recent_form_prompt_context_v1.json",
    )
    parser.add_argument(
        "--candidate-output",
        default=(
            "data/evaluation/candidates/"
            "domain_e2e_v1_offline_executable.json"
        ),
    )
    parser.add_argument(
        "--result-output",
        default=(
            "data/evaluation/results/"
            "domain_e2e_v1_offline_executable.json"
        ),
    )
    parser.add_argument(
        "--runs-root",
        help=(
            "Optional disposable Harness root. If omitted, a temporary directory "
            "is removed after safe observations are compiled."
        ),
    )
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    dataset_path = Path(args.dataset).resolve()
    snapshot_path = Path(args.snapshot).resolve()

    if args.runs_root:
        candidate, result = _execute(
            project_root=project_root,
            dataset_path=dataset_path,
            snapshot_path=snapshot_path,
            runs_root=Path(args.runs_root).resolve(),
        )
    else:
        with tempfile.TemporaryDirectory(
            prefix="riftcoach-domain-e2e-offline-"
        ) as directory:
            candidate, result = _execute(
                project_root=project_root,
                dataset_path=dataset_path,
                snapshot_path=snapshot_path,
                runs_root=Path(directory) / "runs",
            )

    candidate_path = Path(args.candidate_output)
    result_path = Path(args.result_output)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(
        candidate.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    result_path.write_text(
        result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Dataset: {result.dataset_id}@{result.dataset_version}")
    print(f"Candidate: {result.candidate_id} ({result.candidate_kind})")
    print(f"Cases: {result.case_count}")
    print(f"Task outcome accuracy: {result.task_outcome_accuracy:.6f}")
    print(
        "Failure classification accuracy: "
        f"{result.failure_classification_accuracy:.6f}"
    )
    print(f"Unsafe publication rate: {result.unsafe_publication_rate:.6f}")
    print(f"External Provider calls: {result.external_provider_calls}")
    return 0


def _execute(
    *,
    project_root: Path,
    dataset_path: Path,
    snapshot_path: Path,
    runs_root: Path,
):
    dataset = load_domain_dataset(dataset_path)
    candidate = OfflineDomainExecutionRunner(
        project_root=project_root,
        dataset_path=dataset_path,
        snapshot_path=snapshot_path,
        runs_root=runs_root,
        secure_evaluation=(
            dataset.contract_snapshot.evaluation_contract
            == "coach_evaluation@1.1.0"
        ),
    ).run()
    return candidate, evaluate_domain_candidate(dataset, candidate)


if __name__ == "__main__":
    raise SystemExit(main())
