"""Candidate-only real gate for the post-RQ-228 hardened V2 exam.

This coordinator gives the RQ-229 assets their own protocol and receipt
identity while reusing the already-tested low-profile budget and evaluation
machinery.  It is no-I/O until the caller confirms both exact-SHA public CI
and the real call.  Product registration and default routing remain closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, model_validator

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.evaluation.domain_e2e import DomainEvaluationDataset, load_domain_dataset
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    MODEL,
    PROFILE_ID,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
)
from app.evaluation.glm53_hardened_domain_assets import (
    DATASET_PATH,
    INPUT_PLAN_PATH,
    PROTOCOL_ID,
    PROTOCOL_PATH,
    QUALITY_HARDENING_VERSION,
    SNAPSHOT_ID,
    SNAPSHOT_PATH,
    GLM53HardenedDomainAssetAdmission,
    HardenedDomainProtocol,
    admit_hardened_domain_assets,
)
from app.evaluation.glm53_low_profile_budget import (
    CANDIDATE_DOMAIN_MAX_CALLS,
)
from app.evaluation.glm53_low_profile_domain_gate import (
    PROTOCOL_MAX_CALLS,
    LowProfileDomainAdmission,
    LowProfileDomainGateResult,
    _admission_identity,
    _assert_body_free,
    _digest_json,
    _inside_directory,
    _inside_file,
    _inside_output,
    _is_ancestor,
    _load_environment,
    _read_head_sha,
    _require_clean_worktree,
    _require_git_sha,
    _sha256_file,
    create_low_profile_provider,
    run_low_profile_domain_gate,
)
from app.evaluation.glm53_low_profile_protocol import GLM53LowProfileProtocolReport
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    load_prompt_context_snapshot,
)
from app.evaluation.provider_domain_plan import (
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import ZhipuSettings, load_zhipu_settings
from app.providers.protocol import LLMProvider


SCHEMA_VERSION = "1.0"
DEFAULT_PROTOCOL_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json"
)
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_hardened_domain_v2_rq230_v1.json"
)
DEFAULT_RUNS_ROOT = Path("data/runs/evaluation/glm53_hardened_domain_v2")

Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class HardenedDomainAdmission(LowProfileDomainAdmission):
    """No-I/O proof for the exact hardened V2 implementation and assets."""

    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    asset_admission: GLM53HardenedDomainAssetAdmission
    protocol_plan_file_sha256: Sha256Text
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    minimum_evidence_sources: Literal[1] = 1

    @model_validator(mode="after")
    def validate_hardened_identity(self) -> "HardenedDomainAdmission":
        if self.protocol_plan_file_sha256 != self.asset_admission.protocol_file_sha256:
            raise ValueError("protocol plan identity does not match asset admission")
        if self.prompt_context_snapshot_file_sha256 != (
            self.asset_admission.snapshot_file_sha256
        ):
            raise ValueError("snapshot file identity does not match asset admission")
        return self


class HardenedDomainGateResult(LowProfileDomainGateResult):
    """Immutable body-free result for one authorized hardened V2 attempt."""

    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    admission: HardenedDomainAdmission
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    minimum_evidence_sources: Literal[1] = 1


@dataclass(frozen=True)
class HardenedPreparedRun:
    admission: HardenedDomainAdmission
    assets: GLM53HardenedDomainAssetAdmission
    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan


@dataclass(frozen=True)
class HardenedDomainGateOptions:
    confirm_real_call: bool
    public_ci_sha: str | None = None
    confirm_public_ci_success: bool = False
    implementation_sha: str | None = None
    preflight_only: bool = False
    max_calls: int = CANDIDATE_DOMAIN_MAX_CALLS
    protocol_plan: Path = PROTOCOL_PATH
    dataset: Path = DATASET_PATH
    input_plan: Path = INPUT_PLAN_PATH
    snapshot: Path = SNAPSHOT_PATH
    protocol_result: Path = DEFAULT_PROTOCOL_RESULT
    output: Path = DEFAULT_OUTPUT
    runs_root: Path = DEFAULT_RUNS_ROOT


def build_hardened_domain_preflight(
    *,
    project_root: str | Path,
    implementation_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    protocol_plan_path: str | Path = PROTOCOL_PATH,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
    protocol_result_path: str | Path = DEFAULT_PROTOCOL_RESULT,
) -> HardenedPreparedRun:
    """Bind V2 assets, prior live protocol evidence, and exact-SHA CI."""

    _require_git_sha(implementation_sha, "implementation_sha")
    _require_git_sha(public_ci_sha, "public_ci_sha")
    if implementation_sha != public_ci_sha or confirm_public_ci_success is not True:
        raise ValueError("implementation/public CI identity is not confirmed")
    root = Path(project_root).resolve()
    protocol_plan_file = _inside_file(root, protocol_plan_path, "protocol plan")
    dataset_file = _inside_file(root, dataset_path, "dataset")
    plan_file = _inside_file(root, input_plan_path, "input plan")
    snapshot_file = _inside_file(root, snapshot_path, "snapshot")
    protocol_result_file = _inside_file(root, protocol_result_path, "protocol result")

    protocol_plan = HardenedDomainProtocol.model_validate_json(
        protocol_plan_file.read_bytes()
    )
    assets = admit_hardened_domain_assets(
        project_root=root,
        confirm_rules_frozen=True,
        protocol_path=protocol_plan_file,
        dataset_path=dataset_file,
        input_plan_path=plan_file,
        snapshot_path=snapshot_file,
    )
    dataset = load_domain_dataset(dataset_file)
    loaded_plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
    )
    snapshot = load_prompt_context_snapshot(snapshot_file)
    if _sha256_file(protocol_plan_file) != assets.protocol_file_sha256:
        raise ValueError("protocol plan bytes changed after asset admission")
    if _sha256_file(dataset_file) != assets.dataset_sha256:
        raise ValueError("dataset bytes changed after asset admission")
    if _sha256_file(plan_file) != assets.input_plan_sha256:
        raise ValueError("input plan bytes changed after asset admission")
    if _sha256_file(snapshot_file) != assets.snapshot_file_sha256:
        raise ValueError("snapshot bytes changed after asset admission")
    if snapshot.snapshot_id != SNAPSHOT_ID:
        raise ValueError("snapshot identity does not match hardened V2 gate")

    summary = json.loads(loaded_plan.player_summary_path.read_text(encoding="utf-8"))
    report = loaded_plan.deterministic_report_path.read_text(encoding="utf-8")
    rebuilt = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=summary,
        deterministic_report=report,
        cases=loaded_plan.artifact.cases,
        snapshot_id=snapshot.snapshot_id,
        evaluation_contract_version=snapshot.evaluation_contract.rsplit("@", 1)[-1],
        policy_addendum=CANDIDATE_CONTEXT_SAFETY_POLICY_V1,
    )
    if rebuilt != snapshot:
        raise ValueError("frozen hardened V2 Context snapshot cannot be rebuilt")

    protocol_raw = protocol_result_file.read_bytes()
    prior_protocol = GLM53LowProfileProtocolReport.model_validate_json(protocol_raw)
    if (
        not prior_protocol.protocol.admitted
        or prior_protocol.provider_id != PROVIDER_ID
        or prior_protocol.requested_model != MODEL
        or prior_protocol.provider_call_count != PROTOCOL_MAX_CALLS
        or prior_protocol.protocol_code_sha != prior_protocol.implementation_sha
        or prior_protocol.request_policy_id != REQUEST_POLICY_ID
        or prior_protocol.candidate_profile_id != PROFILE_ID
        or prior_protocol.evidence_origin != "real_provider"
    ):
        raise ValueError("prior low-profile protocol evidence is not admitted")
    if prior_protocol.implementation_sha != implementation_sha and not _is_ancestor(
        root,
        prior_protocol.implementation_sha,
        implementation_sha,
    ):
        raise ValueError("prior protocol code is not an ancestor of this gate")

    admission_data: dict[str, Any] = {
        "experiment_id": "0" * 64,
        "protocol_id": PROTOCOL_ID,
        "implementation_sha": implementation_sha,
        "public_ci_sha": public_ci_sha,
        "public_ci_scope": "candidate-hardened-domain-v2-exact-sha",
        "asset_admission": assets,
        "dataset_sha256": _digest_json(dataset.model_dump(mode="json")),
        "dataset_file_sha256": _sha256_file(dataset_file),
        "input_plan_file_sha256": _sha256_file(plan_file),
        "prompt_context_snapshot_sha256": snapshot.snapshot_sha256,
        "prompt_context_snapshot_file_sha256": _sha256_file(snapshot_file),
        "execution_plan": loaded_plan.execution_plan,
        "protocol_result_sha256": hashlib.sha256(protocol_raw).hexdigest(),
        "protocol_code_sha": prior_protocol.protocol_code_sha,
        "protocol_input_tokens": prior_protocol.input_tokens,
        "protocol_output_tokens": prior_protocol.output_tokens,
        "protocol_total_tokens": prior_protocol.total_tokens,
        "protocol_plan_file_sha256": _sha256_file(protocol_plan_file),
        "quality_hardening_version": protocol_plan.quality_hardening_version,
        "minimum_evidence_sources": protocol_plan.minimum_evidence_sources,
    }
    draft = HardenedDomainAdmission.model_construct(**admission_data)
    admission_data["experiment_id"] = _admission_identity(draft)
    admission = HardenedDomainAdmission(**admission_data)
    return HardenedPreparedRun(
        admission=admission,
        assets=assets,
        dataset=dataset,
        input_plan=loaded_plan,
    )


def run_hardened_domain_gate(
    *,
    admission: HardenedDomainAdmission,
    dataset: DomainEvaluationDataset,
    provider: LLMProvider,
    case_executor: Any,
    confirm_real_call: bool = True,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    clock: Callable[[], float] = time.monotonic,
) -> HardenedDomainGateResult:
    """Execute the V2 cases through the mandatory RQ-228 quality boundary."""

    if not isinstance(admission, HardenedDomainAdmission):
        raise TypeError("admission must be a HardenedDomainAdmission")
    if confirm_real_call is not True:
        raise RuntimeError("real hardened domain calls require explicit confirmation")
    if getattr(case_executor, "quality_hardening", None) is not True:
        raise ValueError("hardened V2 executor must enable quality hardening")
    base = run_low_profile_domain_gate(
        admission=admission,
        dataset=dataset,
        provider=provider,
        case_executor=case_executor,
        confirm_real_call=True,
        now=now,
        clock=clock,
    )
    candidate = base.candidate
    evaluation = base.evaluation
    if candidate is not None and evaluation is not None:
        candidate_id = f"zhipu-glm53-flash-hardened-domain-{admission.experiment_id[:16]}"
        candidate = candidate.model_copy(update={"candidate_id": candidate_id})
        evaluation = evaluation.model_copy(update={"candidate_id": candidate_id})
    return HardenedDomainGateResult(
        protocol_id=PROTOCOL_ID,
        experiment_id=base.experiment_id,
        run_timestamp_utc=base.run_timestamp_utc,
        admission=admission,
        resources=base.resources,
        control=base.control,
        protocol_calls=base.protocol_calls,
        protocol_total_tokens=base.protocol_total_tokens,
        domain_calls_used=base.domain_calls_used,
        domain_total_tokens=base.domain_total_tokens,
        cumulative_calls_used=base.cumulative_calls_used,
        cumulative_total_tokens=base.cumulative_total_tokens,
        explicit_real_call_confirmed=base.explicit_real_call_confirmed,
        network_used=base.network_used,
        held_out_executed=base.held_out_executed,
        cases=base.cases,
        candidate=candidate,
        evaluation=evaluation,
        candidate_registered=False,
        production_admitted=False,
        admitted=base.admitted,
        unsupported_boundaries=base.unsupported_boundaries,
        quality_hardening_version=QUALITY_HARDENING_VERSION,
        minimum_evidence_sources=1,
    )


def canonical_hardened_result_bytes(result: HardenedDomainGateResult) -> bytes:
    if not isinstance(result, HardenedDomainGateResult):
        raise TypeError("result must be a HardenedDomainGateResult")
    payload = result.model_dump(mode="json")
    _assert_body_free(payload)
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


class _HardenedOutputReservation:
    def __init__(self, path: Path, experiment_id: str, stream) -> None:
        self.path = path
        self.experiment_id = experiment_id
        self._stream = stream
        self._committed = False

    @classmethod
    def reserve(
        cls,
        path: Path,
        experiment_id: str,
    ) -> "_HardenedOutputReservation":
        return cls(
            path,
            experiment_id,
            path.open("x", encoding="utf-8", newline="\n"),
        )

    def commit(self, result: HardenedDomainGateResult) -> None:
        if self._committed or self._stream.closed:
            raise RuntimeError("hardened V2 output is already finalized")
        if result.experiment_id != self.experiment_id:
            raise ValueError("result does not match reserved experiment")
        self._stream.write(canonical_hardened_result_bytes(result).decode("utf-8"))
        self._stream.flush()
        self._stream.close()
        self._committed = True

    def abandon(self) -> None:
        if not self._stream.closed:
            self._stream.close()


def run_cli(
    options: HardenedDomainGateOptions,
    *,
    repository_root: Path | None = None,
    environment_loader: Callable[[Path], Mapping[str, str]] | None = None,
    provider_factory: Callable[[ZhipuSettings], LLMProvider] = create_low_profile_provider,
    code_sha_reader: Callable[[Path], str] | None = None,
) -> HardenedDomainAdmission | HardenedDomainGateResult:
    if options.max_calls != CANDIDATE_DOMAIN_MAX_CALLS:
        raise ValueError("hardened V2 domain gate requires exactly 12 calls")
    if not options.preflight_only and options.confirm_real_call is not True:
        raise RuntimeError("real hardened domain calls require explicit confirmation")
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    if not options.preflight_only:
        _require_clean_worktree(root)
    current_sha = options.implementation_sha or (code_sha_reader or _read_head_sha)(root)
    public_sha = options.public_ci_sha or current_sha
    prepared = build_hardened_domain_preflight(
        project_root=root,
        implementation_sha=current_sha,
        public_ci_sha=public_sha,
        confirm_public_ci_success=(
            options.confirm_public_ci_success or options.preflight_only
        ),
        protocol_plan_path=options.protocol_plan,
        dataset_path=options.dataset,
        input_plan_path=options.input_plan,
        snapshot_path=options.snapshot,
        protocol_result_path=options.protocol_result,
    )
    if options.preflight_only:
        return prepared.admission

    output = _inside_output(root, options.output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("hardened V2 domain evidence is immutable")
    output.parent.mkdir(parents=True, exist_ok=True)
    reservation = _HardenedOutputReservation.reserve(
        output,
        prepared.admission.experiment_id,
    )
    try:
        settings = load_zhipu_settings(
            (environment_loader or _load_environment)(root)
        )
        provider = provider_factory(settings)
        runs_root = _inside_directory(root, options.runs_root, "runs root")
        runs_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="glm53-hardened-domain-v2-",
            dir=str(runs_root.parent),
        ) as temporary:
            executor = ProductionDomainCaseExecutor(
                project_root=root,
                input_plan=prepared.input_plan,
                runs_root=Path(temporary),
                request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
                quality_hardening=True,
            )
            result = run_hardened_domain_gate(
                admission=prepared.admission,
                dataset=prepared.dataset,
                provider=provider,
                case_executor=executor,
                confirm_real_call=True,
            )
        reservation.commit(result)
        return result
    except Exception:
        reservation.abandon()
        raise


def _parse_args(argv: Sequence[str] | None = None) -> HardenedDomainGateOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded GLM-5.3 hardened V2 held-out domain gate."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--implementation-sha")
    parser.add_argument("--public-ci-sha")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--max-calls", type=int, default=CANDIDATE_DOMAIN_MAX_CALLS)
    parser.add_argument("--protocol-plan", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--input-plan", type=Path, default=INPUT_PLAN_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--protocol-result", type=Path, default=DEFAULT_PROTOCOL_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    values = parser.parse_args(argv)
    return HardenedDomainGateOptions(
        confirm_real_call=values.confirm_real_call,
        public_ci_sha=values.public_ci_sha,
        confirm_public_ci_success=values.confirm_public_ci_success,
        implementation_sha=values.implementation_sha,
        preflight_only=values.preflight_only,
        max_calls=values.max_calls,
        protocol_plan=values.protocol_plan,
        dataset=values.dataset,
        input_plan=values.input_plan,
        snapshot=values.snapshot,
        protocol_result=values.protocol_result,
        output=values.output,
        runs_root=values.runs_root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    result = run_cli(_parse_args(argv))
    if isinstance(result, HardenedDomainAdmission):
        print(
            f"provider={result.provider_id} model={result.requested_model} "
            "preflight=true external_provider_calls=0 held_out_executed=false"
        )
    else:
        print(
            f"provider={result.admission.provider_id} "
            f"model={result.admission.requested_model} "
            f"domain_calls={result.domain_calls_used}/{CANDIDATE_DOMAIN_MAX_CALLS} "
            f"cumulative_calls={result.cumulative_calls_used}/"
            f"{PROTOCOL_MAX_CALLS + CANDIDATE_DOMAIN_MAX_CALLS} "
            f"admitted={str(result.admitted).lower()}"
        )
    return 0


__all__ = [
    "DEFAULT_OUTPUT",
    "HardenedDomainAdmission",
    "HardenedDomainGateOptions",
    "HardenedDomainGateResult",
    "HardenedPreparedRun",
    "build_hardened_domain_preflight",
    "canonical_hardened_result_bytes",
    "main",
    "run_cli",
    "run_hardened_domain_gate",
]
