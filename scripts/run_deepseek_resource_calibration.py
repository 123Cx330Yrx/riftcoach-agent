"""Run one explicitly confirmed DeepSeek V4 Pro development Usage replay."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.provider_resource_calibration import (
    FrozenCalibrationRequestSet,
    ImmutableResourceCalibrationOutput,
    RealResourceCalibrationResult,
    ResourceCalibrationAdmission,
    ResourceCalibrationRequestSnapshot,
    V3ResourceBudgetRecord,
    build_v3_resource_budget_record,
    capture_resource_calibration_requests,
    load_resource_calibration_profiles,
    prepare_resource_calibration_admission,
    prepare_resource_calibration_run_admission,
    run_real_resource_calibration,
)
from app.providers.config import (
    DeepSeekSettings,
    create_deepseek_provider,
    load_deepseek_settings,
)
from app.providers.protocol import LLMProvider
from scripts.prepare_second_provider_experiment import read_clean_code_sha


_DEFAULT_PROFILES = Path(
    "data/evaluation/"
    "deepseek_v4_pro_resource_calibration_development_profiles.json"
)
_DEFAULT_REQUEST_SNAPSHOT = Path(
    "data/evaluation/contracts/"
    "deepseek_v4_pro_resource_calibration_requests_v1.json"
)
_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_resource_calibration_v1.json"
)
_DEFAULT_BUDGET_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_resource_budget_v3.json"
)
_PROTECTED_V2_PATHS = (
    Path("data/evaluation/domain_e2e_v2_secure_held_out_cases.json"),
    Path("data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json"),
    Path(
        "data/evaluation/results/provider_capabilities/"
        "deepseek_v4_pro_domain_adoption_v2.json"
    ),
)


@dataclass(frozen=True)
class DeepSeekResourceCalibrationCliOptions:
    confirm_real_call: bool
    confirm_public_ci_success: bool
    public_ci_sha: str
    prepare_only: bool = False
    max_calls: int = 8
    profiles: Path = _DEFAULT_PROFILES
    request_snapshot: Path = _DEFAULT_REQUEST_SNAPSHOT
    output: Path = _DEFAULT_OUTPUT
    budget_output: Path = _DEFAULT_BUDGET_OUTPUT


@dataclass(frozen=True)
class ResourceCalibrationPreparedRun:
    admission: ResourceCalibrationAdmission
    frozen_requests: FrozenCalibrationRequestSet


@dataclass(frozen=True)
class ResourceCalibrationRunOutput:
    result: RealResourceCalibrationResult
    budget: V3ResourceBudgetRecord | None


PreflightRunner = Callable[..., ResourceCalibrationPreparedRun]
ProviderFactory = Callable[[DeepSeekSettings], LLMProvider]
EnvironmentLoader = Callable[[Path], Mapping[str, str]]
CodeShaReader = Callable[[Path], str]


def run_cli(
    options: DeepSeekResourceCalibrationCliOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    preflight_runner: PreflightRunner | None = None,
    environment_loader: EnvironmentLoader | None = None,
    provider_factory: ProviderFactory = create_deepseek_provider,
    code_sha_reader: CodeShaReader = read_clean_code_sha,
    clock: Callable[[], float] = time.monotonic,
) -> ResourceCalibrationAdmission | ResourceCalibrationRunOutput:
    """Finish all no-I/O checks and reserve output before loading the Key."""

    if not options.prepare_only and not options.confirm_real_call:
        raise RuntimeError("real calibration calls require explicit confirmation")
    if options.max_calls != 8:
        raise ValueError("DeepSeek resource calibration requires exactly 8 calls")

    root = repository_root.resolve()
    profiles = _inside_project(root, options.profiles, label="profiles")
    request_snapshot = _inside_project(
        root,
        options.request_snapshot,
        label="request snapshot",
    )
    protected_paths = tuple(
        _inside_project(root, path, label="protected V2 evidence")
        for path in _PROTECTED_V2_PATHS
    )
    output = _resolve_new_output(root, options.output, label="result")
    budget_output = _resolve_new_output(
        root,
        options.budget_output,
        label="budget",
    )
    if output == budget_output:
        raise ValueError("result and budget outputs must be different files")

    preflight = preflight_runner or _run_preflight
    prepared = preflight(
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        repository_root=root,
        profiles=profiles,
        request_snapshot=request_snapshot,
        protected_paths=protected_paths,
        code_sha_reader=code_sha_reader,
    )
    if not isinstance(prepared, ResourceCalibrationPreparedRun):
        raise TypeError("preflight must return ResourceCalibrationPreparedRun")
    if options.prepare_only:
        return prepared.admission

    run_admission = prepare_resource_calibration_run_admission(
        admission=prepared.admission,
        frozen_requests=prepared.frozen_requests,
        explicit_real_call_confirmed=options.confirm_real_call,
        maximum_calls=options.max_calls,
        result_relative_path=output.relative_to(root).as_posix(),
    )
    reservation = ImmutableResourceCalibrationOutput.reserve(
        output,
        experiment_id=run_admission.experiment_id,
    )
    try:
        load_environment = environment_loader or _load_environment
        settings = load_deepseek_settings(load_environment(root))
        provider = provider_factory(settings)
        result = run_real_resource_calibration(
            admission=run_admission,
            frozen=prepared.frozen_requests,
            provider=provider,
            clock=clock,
        )
        reservation.commit(result)

        budget: V3ResourceBudgetRecord | None = None
        if result.v3_budget_derivation_ready:
            result_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
            budget = build_v3_resource_budget_record(
                result=result,
                calibration_result_sha256=result_sha256,
            )
            _write_new_json(budget_output, budget)
        return ResourceCalibrationRunOutput(result=result, budget=budget)
    except Exception:
        reservation.abandon()
        raise


def _run_preflight(
    *,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    repository_root: Path,
    profiles: Path,
    request_snapshot: Path,
    protected_paths: tuple[Path, ...],
    code_sha_reader: CodeShaReader,
) -> ResourceCalibrationPreparedRun:
    code_sha = code_sha_reader(repository_root)
    loaded = load_resource_calibration_profiles(
        profiles,
        project_root=repository_root,
        protected_paths=protected_paths,
    )
    with tempfile.TemporaryDirectory(
        prefix="riftcoach-resource-calibration-"
    ) as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=repository_root,
            runs_root=directory,
        )
    public_snapshot = ResourceCalibrationRequestSnapshot.model_validate_json(
        request_snapshot.read_bytes()
    )
    if public_snapshot != frozen.snapshot:
        raise ValueError("calibration request snapshot identity drifted")
    admission = prepare_resource_calibration_admission(
        loaded=loaded,
        frozen_requests=frozen,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        public_ci_success_confirmed=confirm_public_ci_success,
    )
    return ResourceCalibrationPreparedRun(
        admission=admission,
        frozen_requests=frozen,
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


def _resolve_new_output(root: Path, value: Path, *, label: str) -> Path:
    allowed_root = (
        root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    output = value if value.is_absolute() else root / value
    output = output.resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError(
            f"{label} output must remain inside the provider result directory"
        )
    if output.suffix.lower() != ".json":
        raise ValueError(f"{label} output must be a JSON file")
    if output.exists():
        raise FileExistsError(
            f"{label} evidence is immutable and cannot be overwritten"
        )
    return output


def _write_new_json(path: Path, record: V3ResourceBudgetRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(record.model_dump_json(indent=2))
        stream.write("\n")


def _parse_args(
    argv: Sequence[str] | None = None,
) -> DeepSeekResourceCalibrationCliOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded DeepSeek V4 Pro development Usage calibration."
        )
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--max-calls", type=int, default=8)
    parser.add_argument("--profiles", type=Path, default=_DEFAULT_PROFILES)
    parser.add_argument(
        "--request-snapshot",
        type=Path,
        default=_DEFAULT_REQUEST_SNAPSHOT,
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--budget-output",
        type=Path,
        default=_DEFAULT_BUDGET_OUTPUT,
    )
    values = parser.parse_args(argv)
    return DeepSeekResourceCalibrationCliOptions(
        confirm_real_call=values.confirm_real_call,
        confirm_public_ci_success=values.confirm_public_ci_success,
        public_ci_sha=values.public_ci_sha,
        prepare_only=values.prepare_only,
        max_calls=values.max_calls,
        profiles=values.profiles,
        request_snapshot=values.request_snapshot,
        output=values.output,
        budget_output=values.budget_output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    outcome = run_cli(_parse_args(argv))
    if isinstance(outcome, ResourceCalibrationAdmission):
        print(
            f"provider={outcome.provider_id} model={outcome.requested_model} "
            "no_io_admitted=true external_provider_calls=0 "
            "held_out_created=false"
        )
        return 0
    result = outcome.result
    allowed = (
        outcome.budget.decision.v3_gate_creation_allowed
        if outcome.budget is not None
        else False
    )
    print(
        f"provider={result.provider_id} model={result.requested_model} "
        f"status={result.status} calls={result.external_provider_calls}/8 "
        f"responses={result.responses_completed}/8 "
        f"v3_gate_creation_allowed={str(allowed).lower()}"
    )
    return 0 if result.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
