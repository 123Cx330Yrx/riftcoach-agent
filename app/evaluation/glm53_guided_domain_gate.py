"""V4 guided GLM-5.3 Flash domain runner.

The runner is intentionally separate from the historical V3 gate.  It binds
the fresh four-case assets and fresh G53-3-L receipt, then uses the shared
bounded provider wrapper for one pass over the cases.  Public output is
body-free and create-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.domain_e2e import (
    DomainCandidate,
    DomainCandidateCase,
    DomainEvaluationDataset,
    DomainEvaluationResult,
    evaluate_domain_candidate,
)
from app.evaluation.glm53_bounded_revision_budget import (
    BoundedRevisionBudgetedProvider,
    BoundedRevisionBudgetState,
)
from app.evaluation.glm53_guided_candidate import GuidedCandidateExecutor
from app.evaluation.glm53_guided_domain_assets import (
    DATASET_PATH,
    INPUT_PLAN_PATH,
    PROTOCOL_PATH,
    CONTEXT_PATH,
    BUDGET_PATH,
    GuidedDomainAssetBundle,
    admit_guided_domain_assets,
)
from app.evaluation.glm53_low_profile_domain_gate import create_low_profile_provider
from app.evaluation.provider_domain_experiment import DomainCaseExecutionPlan
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import ZhipuSettings, load_zhipu_settings
from app.providers.errors import ProviderError
from app.providers.protocol import LLMProvider

PROTOCOL_RESULT_PATH = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_guided_g53_3l_rq239_v1.json"
)
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_guided_domain_v4_rq239_v1.json"
)
DEFAULT_RUNS_ROOT = Path("data/runs/evaluation/glm53_guided_domain_v4")


class _GuidedReceiptModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GuidedCaseResource(_GuidedReceiptModel):
    calls_used: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "GuidedCaseResource":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("guided case resource token total is inconsistent")
        return self


class GuidedResourceSnapshot(_GuidedReceiptModel):
    calls_used: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    stop_code: str | None = None
    provider_error_code: str | None = None
    cases: dict[str, GuidedCaseResource]

    @model_validator(mode="after")
    def validate_totals(self) -> "GuidedResourceSnapshot":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("guided resource token total is inconsistent")
        if sum(row.calls_used for row in self.cases.values()) != self.calls_used:
            raise ValueError("guided case calls do not match resource calls")
        if sum(row.input_tokens for row in self.cases.values()) != self.input_tokens:
            raise ValueError("guided case input does not match resource input")
        if sum(row.output_tokens for row in self.cases.values()) != self.output_tokens:
            raise ValueError("guided case output does not match resource output")
        return self


class GuidedCaseRecord(_GuidedReceiptModel):
    case_id: str = Field(min_length=1)
    status: Literal["executed", "failed", "skipped"]
    failure_code: str | None = None
    terminal_status: str | None = None
    terminal_reason: str | None = None
    provider_calls: int | None = Field(default=None, ge=0)
    normalized_response_count: int | None = Field(default=None, ge=0)
    evidence_source_count: int | None = Field(default=None, ge=0)
    evaluation_score: float | None = Field(default=None, ge=0, le=100)
    revision_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_status(self) -> "GuidedCaseRecord":
        if self.status == "executed" and self.provider_calls is None:
            raise ValueError("executed guided case must include provider calls")
        if self.status != "executed" and not self.failure_code:
            raise ValueError("failed or skipped guided case must include failure code")
        return self


class GuidedDomainGateReceipt(_GuidedReceiptModel):
    schema_version: Literal["1.0"] = "1.0"
    protocol_id: Literal["glm53-flash-guided-domain-observation-v4"]
    implementation_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    asset_dataset_id: str = Field(min_length=1)
    context_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    guidance_id: str = Field(min_length=1)
    guidance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_origin: Literal["real_provider", "offline_fake"]
    network_used: bool
    explicit_real_call_confirmed: bool
    resources: GuidedResourceSnapshot
    cases: tuple[GuidedCaseRecord, ...]
    evaluation: DomainEvaluationResult | None = None
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    admitted: bool
    unsupported_boundaries: tuple[str, ...]
    run_timestamp_utc: str = Field(min_length=20)

    @model_validator(mode="after")
    def validate_identity(self) -> "GuidedDomainGateReceipt":
        if self.evidence_origin == "real_provider" and not self.network_used:
            raise ValueError("real guided receipt must record network use")
        if self.evidence_origin == "offline_fake" and self.network_used:
            raise ValueError("offline guided receipt cannot record network use")
        if self.admitted and (not self.network_used or self.evaluation is None):
            raise ValueError("admitted guided receipt requires evaluation and network")
        return self


def build_guided_domain_preflight(
    *,
    project_root: str | Path,
    implementation_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    protocol_result_path: str | Path = PROTOCOL_RESULT_PATH,
) -> GuidedDomainAssetBundle:
    if implementation_sha != public_ci_sha or not confirm_public_ci_success:
        raise ValueError("implementation/public CI identity is not confirmed")
    root = Path(project_root).resolve()
    bundle = admit_guided_domain_assets(project_root=root)
    protocol_path = _inside(root, protocol_result_path)
    receipt = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (
        receipt.get("evidence_origin") != "real_provider"
        or receipt.get("provider_call_count") != 3
        or receipt.get("network_used") is not True
        or receipt.get("implementation_sha") != implementation_sha
        or receipt.get("protocol_code_sha") != implementation_sha
        or receipt.get("protocol", {}).get("admitted") is not True
    ):
        raise ValueError("fresh G53-3-L protocol evidence is missing or stale")
    return bundle


def run_guided_domain(
    *,
    bundle: GuidedDomainAssetBundle,
    implementation_sha: str,
    provider: LLMProvider,
    project_root: str | Path,
    runs_root: str | Path,
    confirm_real_call: bool,
    evidence_origin: str = "real_provider",
) -> dict[str, Any]:
    if evidence_origin == "real_provider" and not confirm_real_call:
        raise RuntimeError("real guided domain calls require explicit confirmation")
    if getattr(provider, "provider_name", None) != "zhipu" or getattr(provider, "model_name", None) != "glm-5.3-flash":
        raise ValueError("provider does not match the guided Flash candidate")
    state = BoundedRevisionBudgetState(max_cases=4)
    observations: list[DomainCandidateCase] = []
    records: list[dict[str, Any]] = []
    executor = GuidedCandidateExecutor(
        project_root=project_root,
        input_plan=bundle.input_plan,
        runs_root=runs_root,
    )
    for case in bundle.dataset.cases:
        if state.stop_code is not None:
            records.append({"case_id": case.case_id, "status": "skipped", "failure_code": state.stop_code})
            continue
        state.register_case(case.case_id)
        before = state.case_snapshot(case.case_id)
        controlled = BoundedRevisionBudgetedProvider(
            provider=provider,
            state=state,
            case_id=case.case_id,
            case_max_tokens=205_000,
            domain_max_tokens=806_000,
            domain_max_calls=36,
        )
        try:
            semantic = executor.execute(case_id=case.case_id, provider=controlled)
            after = state.case_snapshot(case.case_id)
            observation = _candidate_case(semantic, before=before, after=after)
            observations.append(observation)
            records.append({
                "case_id": case.case_id,
                "status": "executed",
                "terminal_status": observation.terminal_status,
                "terminal_reason": observation.terminal_reason,
                "provider_calls": observation.provider_calls,
                "normalized_response_count": observation.normalized_response_count,
                "evidence_source_count": len(observation.evidence_source_ids),
                "evaluation_score": observation.evaluation_score,
                "revision_count": observation.revision_count,
            })
        except ProviderError as exc:
            state.stop("provider_error", provider_error_code=exc.code)
            records.append({"case_id": case.case_id, "status": "failed", "failure_code": exc.code})
        except Exception:
            state.stop("domain_case_observation_invalid")
            records.append({"case_id": case.case_id, "status": "failed", "failure_code": "domain_case_observation_invalid"})
    candidate = None
    evaluation = None
    if len(observations) == len(bundle.dataset.cases) and evidence_origin == "real_provider":
        candidate = DomainCandidate(
            schema_version=bundle.dataset.schema_version,
            candidate_id=f"zhipu-glm53-flash-guided-v4-{bundle.context_snapshot_sha256[:16]}",
            candidate_kind="real_provider_recorded" if evidence_origin == "real_provider" else "offline_recorded",
            dataset_id=bundle.dataset.dataset_id,
            dataset_version=bundle.dataset.dataset_version,
            contract_snapshot=bundle.dataset.contract_snapshot,
            external_provider_calls=state.calls_used,
            case_count=len(observations),
            cases=tuple(observations),
        )
        evaluation = evaluate_domain_candidate(bundle.dataset, candidate)
    snapshot = state.snapshot()
    return {
        "schema_version": "1.0",
        "protocol_id": bundle.protocol.protocol_id,
        "implementation_sha": implementation_sha,
        "asset_dataset_id": bundle.dataset.dataset_id,
        "context_snapshot_sha256": bundle.context_snapshot_sha256,
        "guidance_id": bundle.protocol.retrieval_guidance_id,
        "guidance_sha256": bundle.protocol.retrieval_guidance_sha256,
        "evidence_origin": evidence_origin,
        "network_used": evidence_origin == "real_provider" and state.calls_used > 0,
        "explicit_real_call_confirmed": confirm_real_call,
        "resources": snapshot,
        "cases": records,
        "evaluation": None if evaluation is None else evaluation.model_dump(mode="json"),
        "candidate_registered": False,
        "production_admitted": False,
        "admitted": bool(evaluation is not None and evaluation.task_outcome_accuracy == 1.0 and evaluation.failure_classification_accuracy == 1.0 and evaluation.unsafe_publication_rate == 0.0 and state.stop_code is None),
        "unsupported_boundaries": ["产品 Runtime 注册", "默认模型切换", "安全/部署/合规", "8F final evaluation"],
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def canonical_result_bytes(result: Mapping[str, Any] | GuidedDomainGateReceipt) -> bytes:
    receipt = (
        result
        if isinstance(result, GuidedDomainGateReceipt)
        else GuidedDomainGateReceipt.model_validate(result)
    )
    payload = receipt.model_dump(mode="json", exclude_none=False)
    payload = _drop_optional_nulls(payload)
    forbidden = {"content", "reasoning", "messages", "tool_arguments", "tool_results", "api_key", "authorization", "prompt"}
    if any(key in forbidden for key in _walk_keys(payload)):
        raise ValueError("guided domain result is not body-free")
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _candidate_case(semantic, *, before: Mapping[str, int], after: Mapping[str, int]) -> DomainCandidateCase:
    return DomainCandidateCase(
        case_id=semantic.case_id,
        provider_calls=after["calls_used"] - before["calls_used"],
        normalized_response_count=semantic.normalized_response_count,
        safe_provider_error_code=semantic.safe_provider_error_code,
        agent_status=semantic.agent_status,
        agent_stop_reason=semantic.agent_stop_reason,
        proposed_tool_names=semantic.proposed_tool_names,
        successful_tool_names=semantic.successful_tool_names,
        evidence_source_ids=semantic.evidence_source_ids,
        evidence_diagnostics=semantic.evidence_diagnostics,
        revision_count=semantic.revision_count,
        evaluation_diagnostics=semantic.evaluation_diagnostics,
        fact_check_passed=semantic.fact_check_passed,
        citation_check_passed=semantic.citation_check_passed,
        injection_check_passed=semantic.injection_check_passed,
        evaluation_validated=semantic.evaluation_validated,
        evaluation_score=semantic.evaluation_score,
        terminal_status=semantic.terminal_status,
        terminal_reason=semantic.terminal_reason,
        latency_ms=after["latency_ms"] - before["latency_ms"],
        input_tokens=after["input_tokens"] - before["input_tokens"],
        output_tokens=after["output_tokens"] - before["output_tokens"],
        estimated_cost=None,
        provenance_sha256=semantic.provenance_sha256,
    )


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _drop_optional_nulls(value: Any, *, key: str | None = None) -> Any:
    preserve = {
        "evaluation",
        "evaluation_score",
        "expected_primary_failure",
        "primary_failure",
        "provider_error_code",
        "stop_code",
    }
    if isinstance(value, dict):
        return {
            name: _drop_optional_nulls(child, key=name)
            for name, child in value.items()
            if child is not None or name in preserve
        }
    if isinstance(value, list):
        return [_drop_optional_nulls(child) for child in value]
    return value


def _inside(root: Path, value: str | Path) -> Path:
    path = (root / Path(value)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FileNotFoundError("guided protocol receipt is missing")
    return path


__all__ = [
    "GuidedDomainGateReceipt",
    "build_guided_domain_preflight",
    "canonical_result_bytes",
    "run_guided_domain",
]
