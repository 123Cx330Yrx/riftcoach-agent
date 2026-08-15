"""Run the explicitly confirmed, bounded DeepSeek domain held-out gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.domain_e2e import DomainEvaluationDataset, load_domain_dataset
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    load_prompt_context_snapshot,
)
from app.evaluation.provider_domain_experiment import (
    ImmutableDomainExperimentOutput,
    load_protocol_artifact,
    run_deepseek_domain_heldout_experiment,
)
from app.evaluation.provider_domain_plan import (
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_production import (
    ProductionDomainCaseExecutor,
)
from app.evaluation.provider_domain_readmission import (
    FreshDomainHeldOutAdmission,
    MultiToolRepairEvidence,
    build_fresh_domain_preparation,
    finalize_fresh_domain_experiment,
    load_fresh_domain_asset_freeze_evidence,
    load_historical_domain_evidence,
    prepare_fresh_domain_heldout_admission,
)
from app.providers.config import (
    DeepSeekSettings,
    create_deepseek_provider,
    load_deepseek_settings,
)
from app.providers.protocol import LLMProvider
from scripts.prepare_second_provider_experiment import read_clean_code_sha


_DEFAULT_DATASET = Path(
    "data/evaluation/domain_e2e_v2_secure_held_out_cases.json"
)
_DEFAULT_SNAPSHOT = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1_2.json"
)
_DEFAULT_PLAN = Path(
    "data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json"
)
_DEFAULT_PROTOCOL = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)
_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_adoption_v2.json"
)
_DEFAULT_REJECTED_DOMAIN_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_heldout.json"
)
_EXPECTED_PROTOCOL_SHA256 = (
    "575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1"
)
_REPAIR_SHA = "037a47fecf058b2430efeeb59858e24cdb3b28eb"
_REPAIR_CI_RUN_ID = 31817798170


@dataclass(frozen=True)
class DeepSeekDomainCliOptions:
    confirm_real_call: bool
    confirm_public_ci_success: bool
    public_ci_sha: str
    prepare_only: bool = False
    max_calls: int = 12
    dataset: Path = _DEFAULT_DATASET
    snapshot: Path = _DEFAULT_SNAPSHOT
    input_plan: Path = _DEFAULT_PLAN
    protocol_result: Path = _DEFAULT_PROTOCOL
    rejected_domain_result: Path = _DEFAULT_REJECTED_DOMAIN_RESULT
    output: Path = _DEFAULT_OUTPUT
    runs_root: Path = Path("data/runs/evaluation/deepseek_domain")


@dataclass(frozen=True)
class FreshDomainPreparedRun:
    admission: FreshDomainHeldOutAdmission
    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan


PreflightRunner = Callable[..., FreshDomainPreparedRun]
ProviderFactory = Callable[[DeepSeekSettings], LLMProvider]
EnvironmentLoader = Callable[[Path], Mapping[str, str]]
CodeShaReader = Callable[[Path], str]


def run_cli(
    options: DeepSeekDomainCliOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    preflight_runner: PreflightRunner | None = None,
    environment_loader: EnvironmentLoader | None = None,
    provider_factory: ProviderFactory = create_deepseek_provider,
    code_sha_reader: CodeShaReader = read_clean_code_sha,
) -> object:
    """Admit local inputs first; read the Key only after output reservation."""

    if not options.prepare_only and not options.confirm_real_call:
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
    rejected_path = _inside_project(
        root,
        options.rejected_domain_result,
        label="rejected domain result",
    )
    runs_root = _inside_project(root, options.runs_root, label="runs root")
    output = _resolve_new_output(root, options.output)

    preflight = preflight_runner or _run_preflight
    prepared = preflight(
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        repository_root=root,
        dataset=dataset_path,
        snapshot=snapshot_path,
        input_plan=plan_path,
        protocol_result=protocol_path,
        rejected_domain_result=rejected_path,
        code_sha_reader=code_sha_reader,
    )
    if not isinstance(prepared, FreshDomainPreparedRun):
        raise TypeError("preflight must return FreshDomainPreparedRun")
    if options.prepare_only:
        return prepared.admission

    reservation = ImmutableDomainExperimentOutput.reserve(
        output,
        experiment_id=prepared.admission.experiment_id,
    )

    try:
        load_environment = environment_loader or _load_environment
        settings = load_deepseek_settings(load_environment(root))
        provider = provider_factory(settings)
        executor = ProductionDomainCaseExecutor(
            project_root=root,
            input_plan=prepared.input_plan,
            runs_root=runs_root,
        )
        domain_result = run_deepseek_domain_heldout_experiment(
            admission=prepared.admission.run_admission,
            dataset=prepared.dataset,
            provider=provider,
            case_executor=executor,
        )
        record = finalize_fresh_domain_experiment(
            admission=prepared.admission,
            domain_result=domain_result,
            explicit_real_call_confirmed=options.confirm_real_call,
        )
        reservation.commit_payload(record)
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
    input_plan: Path,
    protocol_result: Path,
    rejected_domain_result: Path,
    code_sha_reader: CodeShaReader,
) -> FreshDomainPreparedRun:
    code_sha = code_sha_reader(repository_root)
    domain_dataset = load_domain_dataset(dataset)
    loaded_plan = load_domain_case_input_plan(
        input_plan,
        project_root=repository_root,
        dataset=domain_dataset,
    )
    frozen_snapshot = load_prompt_context_snapshot(snapshot)
    current_snapshot = build_prompt_context_snapshot_for_cases(
        skills_root=repository_root / "skills",
        player_summary=json.loads(
            loaded_plan.player_summary_path.read_text(encoding="utf-8")
        ),
        deterministic_report=loaded_plan.deterministic_report_path.read_text(
            encoding="utf-8"
        ),
        cases=loaded_plan.artifact.cases,
        snapshot_id=frozen_snapshot.snapshot_id,
        evaluation_contract_version="1.1.0",
    )
    assets = load_fresh_domain_asset_freeze_evidence(
        dataset_path=dataset,
        input_plan_path=input_plan,
        snapshot_path=snapshot,
        loaded_input_plan=loaded_plan,
    )
    historical = load_historical_domain_evidence(
        protocol_result_path=protocol_result,
        rejected_domain_result_path=rejected_domain_result,
        multi_tool_repair=MultiToolRepairEvidence(
            code_sha=_REPAIR_SHA,
            public_ci_sha=_REPAIR_SHA,
            public_ci_run_id=_REPAIR_CI_RUN_ID,
            public_ci_success_confirmed=True,
        ),
    )
    preparation = build_fresh_domain_preparation(
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        confirm_public_ci_success=confirm_public_ci_success,
        dataset=domain_dataset,
        frozen_snapshot=frozen_snapshot,
    )
    protocol = load_protocol_artifact(protocol_result)
    if protocol.result_sha256 != _EXPECTED_PROTOCOL_SHA256:
        raise ValueError("protocol result bytes do not match frozen evidence")
    admission = prepare_fresh_domain_heldout_admission(
        historical=historical,
        asset_freeze=assets,
        preparation=preparation,
        dataset=domain_dataset,
        loaded_input_plan=loaded_plan,
        frozen_snapshot=frozen_snapshot,
        current_snapshot=current_snapshot,
        protocol_record=protocol.record,
        protocol_result_sha256=protocol.result_sha256,
    )
    return FreshDomainPreparedRun(
        admission=admission,
        dataset=domain_dataset,
        input_plan=loaded_plan,
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
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--max-calls", type=int, default=12)
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--snapshot", type=Path, default=_DEFAULT_SNAPSHOT)
    parser.add_argument("--input-plan", type=Path, default=_DEFAULT_PLAN)
    parser.add_argument("--protocol-result", type=Path, default=_DEFAULT_PROTOCOL)
    parser.add_argument(
        "--rejected-domain-result",
        type=Path,
        default=_DEFAULT_REJECTED_DOMAIN_RESULT,
    )
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
        prepare_only=values.prepare_only,
        max_calls=values.max_calls,
        dataset=values.dataset,
        snapshot=values.snapshot,
        input_plan=values.input_plan,
        protocol_result=values.protocol_result,
        rejected_domain_result=values.rejected_domain_result,
        output=values.output,
        runs_root=values.runs_root,
    )


if __name__ == "__main__":
    record = run_cli(_parse_args())
    if isinstance(record, FreshDomainHeldOutAdmission):
        print(
            f"provider={record.preparation.provider_id} "
            f"model={record.preparation.requested_model} "
            "no_io_admitted=true external_provider_calls=0 "
            "held_out_executed=false"
        )
    else:
        print(
            f"provider={record.admission.preparation.provider_id} "
            f"model={record.admission.preparation.requested_model} "
            f"admitted={str(record.admitted).lower()}"
        )
