"""Run the explicitly confirmed, bounded DeepSeek domain held-out gate."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.provider_adoption import ExperimentPreparationReport
from app.evaluation.provider_domain_experiment import (
    ImmutableDomainExperimentOutput,
    load_protocol_artifact,
    prepare_deepseek_domain_heldout_run,
    run_deepseek_domain_heldout_experiment,
)
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.provider_domain_production import (
    ProductionDomainCaseExecutor,
)
from app.providers.config import (
    DeepSeekSettings,
    create_deepseek_provider,
    load_deepseek_settings,
)
from app.providers.protocol import LLMProvider
from scripts.prepare_second_provider_experiment import (
    NoIoExperimentOptions,
    run_cli as run_no_io_preflight,
)


_DEFAULT_DATASET = Path(
    "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
)
_DEFAULT_SNAPSHOT = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1_1.json"
)
_DEFAULT_PLAN = Path(
    "data/evaluation/deepseek_v4_pro_domain_heldout_input_plan.json"
)
_DEFAULT_PROTOCOL = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)
_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_heldout.json"
)
_EXPECTED_PROTOCOL_SHA256 = (
    "575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1"
)


@dataclass(frozen=True)
class DeepSeekDomainCliOptions:
    confirm_real_call: bool
    confirm_public_ci_success: bool
    public_ci_sha: str
    max_calls: int = 12
    dataset: Path = _DEFAULT_DATASET
    snapshot: Path = _DEFAULT_SNAPSHOT
    input_plan: Path = _DEFAULT_PLAN
    protocol_result: Path = _DEFAULT_PROTOCOL
    output: Path = _DEFAULT_OUTPUT
    runs_root: Path = Path("data/runs/evaluation/deepseek_domain")


PreflightRunner = Callable[..., ExperimentPreparationReport]
ProviderFactory = Callable[[DeepSeekSettings], LLMProvider]
EnvironmentLoader = Callable[[Path], Mapping[str, str]]


def run_cli(
    options: DeepSeekDomainCliOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    preflight_runner: PreflightRunner | None = None,
    environment_loader: EnvironmentLoader | None = None,
    provider_factory: ProviderFactory = create_deepseek_provider,
) -> object:
    """Admit local inputs first; read the Key only after output reservation."""

    if not options.confirm_real_call:
        raise RuntimeError("Domain held-out calls require explicit confirmation.")
    if options.max_calls != 12:
        raise ValueError("DeepSeek domain gate requires exactly 12 calls.")

    root = repository_root.resolve()
    dataset_path = _inside_project(root, options.dataset, label="dataset")
    snapshot_path = _inside_project(root, options.snapshot, label="snapshot")
    plan_path = _inside_project(root, options.input_plan, label="input plan")
    protocol_path = _inside_project(
        root,
        options.protocol_result,
        label="protocol result",
    )
    runs_root = _inside_project(root, options.runs_root, label="runs root")
    output = _resolve_new_output(root, options.output)

    preflight = preflight_runner or _run_preflight
    preparation = preflight(
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        repository_root=root,
        dataset=dataset_path,
        snapshot=snapshot_path,
    )
    dataset = load_domain_dataset(dataset_path)
    loaded_plan = load_domain_case_input_plan(
        plan_path,
        project_root=root,
        dataset=dataset,
    )
    protocol = load_protocol_artifact(protocol_path)
    if protocol.result_sha256 != _EXPECTED_PROTOCOL_SHA256:
        raise ValueError("protocol result bytes do not match frozen evidence")
    admission = prepare_deepseek_domain_heldout_run(
        preparation=preparation,
        protocol_record=protocol.record,
        protocol_result_sha256=protocol.result_sha256,
        dataset=dataset,
        execution_plan=loaded_plan.execution_plan,
    )
    reservation = ImmutableDomainExperimentOutput.reserve(
        output,
        experiment_id=admission.experiment_id,
    )

    try:
        load_environment = environment_loader or _load_environment
        settings = load_deepseek_settings(load_environment(root))
        provider = provider_factory(settings)
        executor = ProductionDomainCaseExecutor(
            project_root=root,
            input_plan=loaded_plan,
            runs_root=runs_root,
        )
        record = run_deepseek_domain_heldout_experiment(
            admission=admission,
            dataset=dataset,
            provider=provider,
            case_executor=executor,
        )
        reservation.commit(record)
        return record
    except Exception:
        reservation.abandon()
        raise


def _run_preflight(
    *,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    repository_root: Path,
    dataset: Path,
    snapshot: Path,
) -> ExperimentPreparationReport:
    return run_no_io_preflight(
        NoIoExperimentOptions(
            public_ci_sha=public_ci_sha,
            confirm_public_ci_success=confirm_public_ci_success,
            dataset=dataset,
            snapshot=snapshot,
        ),
        repository_root=repository_root,
    )


def _load_environment(repository_root: Path) -> Mapping[str, str]:
    load_dotenv(repository_root / ".env")
    return os.environ


def _inside_project(root: Path, value: Path, *, label: str) -> Path:
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must remain inside the project root")
    return resolved


def _resolve_new_output(repository_root: Path, value: Path) -> Path:
    allowed_root = (
        repository_root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    output = value if value.is_absolute() else repository_root / value
    output = output.resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError(
            "Output must remain inside the provider capability result directory."
        )
    if output.suffix.lower() != ".json":
        raise ValueError("Output must be a JSON result file.")
    if output.exists():
        raise FileExistsError(
            "Provider domain evidence is immutable and cannot be overwritten."
        )
    return output


def _parse_args(argv: Sequence[str] | None = None) -> DeepSeekDomainCliOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded DeepSeek domain held-out gate after strict local "
            "admission."
        )
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--max-calls", type=int, default=12)
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--snapshot", type=Path, default=_DEFAULT_SNAPSHOT)
    parser.add_argument("--input-plan", type=Path, default=_DEFAULT_PLAN)
    parser.add_argument("--protocol-result", type=Path, default=_DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("data/runs/evaluation/deepseek_domain"),
    )
    values = parser.parse_args(argv)
    return DeepSeekDomainCliOptions(
        confirm_real_call=values.confirm_real_call,
        confirm_public_ci_success=values.confirm_public_ci_success,
        public_ci_sha=values.public_ci_sha,
        max_calls=values.max_calls,
        dataset=values.dataset,
        snapshot=values.snapshot,
        input_plan=values.input_plan,
        protocol_result=values.protocol_result,
        output=values.output,
        runs_root=values.runs_root,
    )


if __name__ == "__main__":
    record = run_cli(_parse_args())
    print(
        f"provider={record.preparation.provider_id} "
        f"model={record.preparation.requested_model} "
        f"admitted={str(record.admitted).lower()}"
    )
