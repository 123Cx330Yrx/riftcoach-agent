import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.prompt_context_identity import prepare_domain_experiment


def _inside_project(value: str, *, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{label} must be inside the project root"
        ) from exc
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare an offline Prompt/Context-bound domain experiment."
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/domain_e2e_v1_development_cases.json",
    )
    parser.add_argument(
        "--snapshot",
        default=(
            "data/evaluation/contracts/"
            "recent_form_prompt_context_v1.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "data/evaluation/results/"
            "domain_e2e_v1_experiment_admission.json"
        ),
    )
    args = parser.parse_args()

    try:
        dataset_path = _inside_project(args.dataset, label="dataset")
        snapshot_path = _inside_project(args.snapshot, label="snapshot")
        output_path = Path(args.output).resolve()
        admission = prepare_domain_experiment(
            project_root=PROJECT_ROOT,
            dataset_path=dataset_path,
            snapshot_path=snapshot_path,
        )
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        admission.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Admission: {admission.admission_id}")
    print(f"Dataset: {admission.dataset_version}")
    print(f"Prompt/Context snapshot: {admission.prompt_context_snapshot_id}")
    print(f"External Provider calls: {admission.external_provider_calls}")
    print(f"Admitted: {str(admission.admitted).lower()}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
