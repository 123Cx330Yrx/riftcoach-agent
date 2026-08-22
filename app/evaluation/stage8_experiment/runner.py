"""Deterministic, no-network runner for the frozen Stage 8 experiment."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.stage8_adoption import evaluate_adoption_gate, load_adoption_gate
from app.evaluation.stage8_adoption.models import AdoptionCase, CaseSplit
from app.harness.models import ArtifactKind, HarnessConfig
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft,
    DraftPreparationRequest,
    DraftPreparationResult,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    KnowledgeCitation,
    KnowledgeEvidence,
    RevisionRequest,
)
from app.harness.store import FileRunStore

from .models import (
    ArtifactReference,
    ExperimentCaseResult,
    ExperimentRecord,
    ExperimentSplit,
    HardGateCounters,
    HoldoutAdmission,
    RoleContextReference,
    StrategyId,
    StrategyMetrics,
)


_GATE = Path("data/evaluation/stage8/advanced_adoption_gate_v1.json")
_CASES = Path("data/evaluation/stage8/advanced_adoption_cases_v1.json")
_PLAYER_SUMMARY = Path("examples/fixtures/player_summary_demo.json")
_DETERMINISTIC_REPORT = Path("examples/fixtures/deterministic_report_demo.md")
_EXPECTED_GATE_DIGEST = (
    "88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6"
)
_EXPECTED_CASE_SET_SHA = (
    "d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e"
)
_TOKEN_UNITS = {
    StrategyId.SERIAL: 1000,
    StrategyId.BOUNDED_PARALLEL: 1050,
    StrategyId.ROLE_ISOLATED_MULTI_AGENT: 1450,
}
_PROVIDER_CALLS = {
    StrategyId.SERIAL: 1,
    StrategyId.BOUNDED_PARALLEL: 1,
    StrategyId.ROLE_ISOLATED_MULTI_AGENT: 3,
}
_LATENCY_OVERHEAD = {
    StrategyId.SERIAL: 40,
    StrategyId.BOUNDED_PARALLEL: 45,
    StrategyId.ROLE_ISOLATED_MULTI_AGENT: 55,
}


class ExperimentViolation(ValueError):
    """Stable public-safe failure raised before a result can be persisted."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class _MaterializedArtifact:
    reference: ArtifactReference
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class _Acquisition:
    artifacts: tuple[_MaterializedArtifact, ...]
    error_code: str | None


class _PassingEvaluator:
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        return EvaluationResult(
            score=92,
            verdict=EvaluationVerdict.PASS,
            issues=(),
            passed_checks=("facts", "provenance", "publication_boundary"),
            summary="scripted evaluation passed",
        )


class _ForbiddenReviser:
    def revise(self, request: RevisionRequest) -> CoachDraft:
        raise AssertionError("zero-revision experiment cannot call the reviser")


class _ExperimentDraftPreparer:
    def __init__(
        self,
        *,
        artifacts: tuple[_MaterializedArtifact, ...],
        error_code: str | None,
        gate_digest: str,
        case_set_sha: str,
        case_id: str,
        strategy_id: StrategyId,
    ) -> None:
        self._artifacts = artifacts
        self._error_code = error_code
        self._gate_digest = gate_digest
        self._case_set_sha = case_set_sha
        self._case_id = case_id
        self._strategy_id = strategy_id

    def prepare(self, request: DraftPreparationRequest) -> DraftPreparationResult:
        for artifact in self._artifacts:
            _verify_artifact(
                artifact,
                gate_digest=self._gate_digest,
                case_set_sha=self._case_set_sha,
                case_id=self._case_id,
                strategy_id=self._strategy_id,
            )
        if self._error_code is not None:
            raise ExperimentViolation(self._error_code)
        by_kind = {
            item.reference.artifact_kind: item for item in self._artifacts
        }
        if set(by_kind) != {"knowledge_evidence", "meta_evidence"}:
            raise ExperimentViolation("evidence_bundle_incomplete")
        knowledge_payload = by_kind["knowledge_evidence"].payload
        knowledge = KnowledgeEvidence(
            context=str(knowledge_payload["context"]),
            source_ids=(str(knowledge_payload["source_id"]),),
            citations=(
                KnowledgeCitation(
                    citation_id="K1",
                    chunk_id=str(knowledge_payload["chunk_id"]),
                    parent_id=None,
                    source_id=str(knowledge_payload["source_id"]),
                    title=str(knowledge_payload["title"]),
                    content=str(knowledge_payload["context"]),
                ),
            ),
        )
        return DraftPreparationResult(
            draft=CoachDraft(
                report=(
                    "# RiftCoach 教练式复盘报告\n\n"
                    "当前样本支持一个有来源的训练重点 [K1]。\n"
                )
            ),
            knowledge=knowledge,
        )


def run_stage8_experiment(
    *,
    repository_root: str | Path,
    split: ExperimentSplit,
    code_sha: str,
    runs_root: str | Path,
    public_ci_sha: str | None = None,
    admission: HoldoutAdmission | None = None,
) -> ExperimentRecord:
    root = Path(repository_root).resolve()
    if not isinstance(split, ExperimentSplit):
        raise TypeError("split must be an ExperimentSplit")
    if not _is_git_sha(code_sha):
        raise ExperimentViolation("code_sha_invalid")
    if split is ExperimentSplit.HOLDOUT:
        if admission is None:
            raise ExperimentViolation("holdout_admission_required")
        _validate_holdout_admission(
            admission,
            code_sha=code_sha,
            public_ci_sha=public_ci_sha,
        )
    elif admission is not None or public_ci_sha is not None:
        raise ExperimentViolation("development_admission_forbidden")

    loaded = load_adoption_gate(root / _GATE, root / _CASES)
    decision = evaluate_adoption_gate(loaded)
    if (
        decision.gate_digest != _EXPECTED_GATE_DIGEST
        or loaded.case_set_file_sha256 != _EXPECTED_CASE_SET_SHA
    ):
        raise ExperimentViolation("experiment_identity_drift")
    if split is ExperimentSplit.HOLDOUT and admission is not None:
        if (
            admission.gate_digest != decision.gate_digest
            or admission.case_set_sha256 != loaded.case_set_file_sha256
        ):
            raise ExperimentViolation("holdout_admission_identity_drift")
    contract = loaded.gate.comparison_contract
    if tuple(contract.input_fixture_sha256s) != (
        _sha256_file(root / _PLAYER_SUMMARY),
        _sha256_file(root / _DETERMINISTIC_REPORT),
    ):
        raise ExperimentViolation("input_fixture_identity_drift")
    if contract.external_io_budget != 0 or contract.retry_budget != 0:
        raise ExperimentViolation("external_io_or_retry_requested")

    expected_case_split = (
        CaseSplit.DEVELOPMENT
        if split is ExperimentSplit.DEVELOPMENT
        else CaseSplit.HOLDOUT
    )
    cases = tuple(
        case for case in loaded.case_set.cases if case.split is expected_case_split
    )
    if not cases:
        raise ExperimentViolation("experiment_cases_missing")

    player_summary = json.loads((root / _PLAYER_SUMMARY).read_text(encoding="utf-8"))
    deterministic_report = (root / _DETERMINISTIC_REPORT).read_text(
        encoding="utf-8"
    )
    run_directory = Path(runs_root)
    results = tuple(
        _run_case_strategy(
            case=case,
            strategy_id=strategy_id,
            player_summary=player_summary,
            deterministic_report=deterministic_report,
            runs_root=run_directory,
            gate_digest=decision.gate_digest,
            case_set_sha=loaded.case_set_file_sha256,
        )
        for case in cases
        for strategy_id in StrategyId
    )
    metrics = _aggregate_metrics(results)
    verdict, reason_codes = _experiment_verdict(split=split, metrics=metrics)
    experiment_id = build_experiment_id(
        split=split,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        gate_digest=decision.gate_digest,
        case_set_sha256=loaded.case_set_file_sha256,
    )
    if (
        split is ExperimentSplit.HOLDOUT
        and admission is not None
        and admission.holdout_experiment_id != experiment_id
    ):
        raise ExperimentViolation("holdout_admission_identity_drift")
    return validate_experiment_record(ExperimentRecord(
        experiment_id=experiment_id,
        split=split,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        gate_digest=decision.gate_digest,
        case_set_sha256=loaded.case_set_file_sha256,
        input_fixture_sha256s=tuple(contract.input_fixture_sha256s),
        strategy_ids=tuple(StrategyId),
        cases=results,
        metrics=metrics,
        verdict=verdict,
        reason_codes=reason_codes,
        holdout_executions=1 if split is ExperimentSplit.HOLDOUT else 0,
    ))


def validate_experiment_record(record: ExperimentRecord) -> ExperimentRecord:
    """Recompute every body-free identity and aggregate before admission."""

    if not isinstance(record, ExperimentRecord):
        raise TypeError("record must be an ExperimentRecord")
    expected_id = build_experiment_id(
        split=record.split,
        code_sha=record.code_sha,
        public_ci_sha=record.public_ci_sha,
        gate_digest=record.gate_digest,
        case_set_sha256=record.case_set_sha256,
    )
    if record.experiment_id != expected_id:
        raise ExperimentViolation("experiment_result_identity_drift")
    for row in record.cases:
        expected_roles, independent = _public_role_contract(row.strategy_id)
        actual_roles = {
            role.role_id: (role.allowed_tools, role.can_publish)
            for role in row.role_contexts
        }
        if actual_roles != expected_roles or row.independent_contexts is not independent:
            raise ExperimentViolation("experiment_role_contract_drift")
        roles = {role.role_id: role for role in row.role_contexts}
        for artifact in row.preserved_artifacts:
            role = roles.get(artifact.producer_role)
            if (
                role is None
                or artifact.tool_name not in role.allowed_tools
                or artifact.context_sha256 != role.context_sha256
            ):
                raise ExperimentViolation("experiment_artifact_binding_drift")
        if row.token_units != _TOKEN_UNITS[row.strategy_id]:
            raise ExperimentViolation("experiment_token_identity_drift")
        if row.provider_calls != _PROVIDER_CALLS[row.strategy_id]:
            raise ExperimentViolation("experiment_call_identity_drift")
    for case_id in {row.case_id for row in record.cases}:
        case_rows = [row for row in record.cases if row.case_id == case_id]
        final_digests = {row.final_artifact_sha256 for row in case_rows}
        if len(final_digests) != 1:
            raise ExperimentViolation("terminal_artifact_identity_mismatch")
    expected_metrics = _aggregate_metrics(record.cases)
    if record.metrics != expected_metrics:
        raise ExperimentViolation("experiment_metrics_drift")
    verdict, reasons = _experiment_verdict(
        split=record.split,
        metrics=record.metrics,
    )
    if record.verdict != verdict or record.reason_codes != reasons:
        raise ExperimentViolation("experiment_verdict_drift")
    return record


def _run_case_strategy(
    *,
    case: AdoptionCase,
    strategy_id: StrategyId,
    player_summary: Mapping[str, Any],
    deterministic_report: str,
    runs_root: Path,
    gate_digest: str,
    case_set_sha: str,
) -> ExperimentCaseResult:
    role_contexts = _role_contexts(case.case_id, strategy_id)
    acquisition = _acquire(
        case=case,
        strategy_id=strategy_id,
        role_contexts=role_contexts,
        gate_digest=gate_digest,
        case_set_sha=case_set_sha,
    )
    expected_artifacts = tuple(case.expected_preserved_artifacts)
    actual_artifacts = tuple(
        item.reference.artifact_kind for item in acquisition.artifacts
    )
    if actual_artifacts != expected_artifacts:
        raise ExperimentViolation("preserved_artifact_identity_mismatch")

    latency = _modeled_latency(case, strategy_id)
    if case.expected_terminal.value == "failed":
        if acquisition.error_code != case.expected_error_code:
            raise ExperimentViolation("expected_failure_identity_mismatch")
        return ExperimentCaseResult(
            case_id=case.case_id,
            strategy_id=strategy_id,
            expected_terminal=case.expected_terminal.value,
            terminal_status="failed",
            terminal_matches_expected=True,
            error_code=acquisition.error_code,
            preserved_artifacts=tuple(
                item.reference for item in acquisition.artifacts
            ),
            role_contexts=role_contexts,
            independent_contexts=(
                strategy_id is StrategyId.ROLE_ISOLATED_MULTI_AGENT
            ),
            modeled_latency_units=latency,
            token_units=_TOKEN_UNITS[strategy_id],
            provider_calls=_PROVIDER_CALLS[strategy_id],
            harness_status=None,
            harness_decision=None,
            final_artifact_sha256=None,
            hard_gates=_zero_hard_gates(),
        )

    run_id = f"8b-{case.case_id}-{_strategy_suffix(strategy_id)}"
    store = FileRunStore(runs_root, run_id)
    manifest = ReviewHarness(
        store=store,
        draft_preparer=_ExperimentDraftPreparer(
            artifacts=acquisition.artifacts,
            error_code=acquisition.error_code,
            gate_digest=gate_digest,
            case_set_sha=case_set_sha,
            case_id=case.case_id,
            strategy_id=strategy_id,
        ),
        evaluator=_PassingEvaluator(),
        reviser=_ForbiddenReviser(),
        config=HarnessConfig(
            publish_score_threshold=85,
            max_revisions=0,
            allow_deterministic_fallback=True,
        ),
    ).run(
        player_summary=player_summary,
        deterministic_report=deterministic_report,
    )
    final_records = [
        row
        for row in manifest.artifacts
        if row["kind"] == ArtifactKind.FINAL_REPORT.value
    ]
    if len(final_records) != 1:
        raise ExperimentViolation("final_artifact_identity_mismatch")
    terminal = manifest.status.value
    if terminal not in {"published", "degraded", "rejected"}:
        raise ExperimentViolation("harness_terminal_missing")
    return ExperimentCaseResult(
        case_id=case.case_id,
        strategy_id=strategy_id,
        expected_terminal=case.expected_terminal.value,
        terminal_status=terminal,
        terminal_matches_expected=terminal == case.expected_terminal.value,
        error_code=acquisition.error_code,
        preserved_artifacts=tuple(item.reference for item in acquisition.artifacts),
        role_contexts=role_contexts,
        independent_contexts=(strategy_id is StrategyId.ROLE_ISOLATED_MULTI_AGENT),
        modeled_latency_units=latency,
        token_units=_TOKEN_UNITS[strategy_id],
        provider_calls=_PROVIDER_CALLS[strategy_id],
        harness_status=terminal,
        harness_decision=manifest.final_decision,
        final_artifact_sha256=final_records[0]["sha256"],
        hard_gates=_zero_hard_gates(),
    )


def _acquire(
    *,
    case: AdoptionCase,
    strategy_id: StrategyId,
    role_contexts: tuple[RoleContextReference, ...],
    gate_digest: str,
    case_set_sha: str,
) -> _Acquisition:
    role_by_kind = _artifact_roles(strategy_id)
    context_by_role = {item.role_id: item for item in role_contexts}
    planned_tools = {
        "knowledge_evidence": "knowledge.search",
        "meta_evidence": (
            "knowledge.search"
            if case.fault == "cross_role_tool_probe"
            else "opgg.lane_meta"
        ),
    }
    expected_tools = {
        "knowledge_evidence": "knowledge.search",
        "meta_evidence": "opgg.lane_meta",
    }
    # Match AgentLoop's zero-side-effect batch preflight: one invalid branch
    # prevents every tool call, including a valid sibling branch.
    for kind in ("knowledge_evidence", "meta_evidence"):
        role_id = role_by_kind[kind]
        context = context_by_role[role_id]
        if (
            planned_tools[kind] not in context.allowed_tools
            or planned_tools[kind] != expected_tools[kind]
        ):
            return _Acquisition(artifacts=(), error_code="role_tool_not_allowed")

    def acquire_kind(kind: str) -> _MaterializedArtifact:
        role_id = role_by_kind[kind]
        context = context_by_role[role_id]
        expected_tool = expected_tools[kind]
        payload = _fixture_payload(kind=kind, fault=case.fault)
        return _materialize_artifact(
            artifact_kind=kind,
            producer_role=role_id,
            tool_name=expected_tool,
            context_sha=context.context_sha256,
            payload=payload,
            gate_digest=gate_digest,
            case_set_sha=case_set_sha,
            case_id=case.case_id,
            strategy_id=strategy_id,
        )

    artifacts: dict[str, _MaterializedArtifact] = {}
    errors: list[str] = []
    kinds = ("knowledge_evidence", "meta_evidence")
    if strategy_id is StrategyId.SERIAL:
        for kind in kinds:
            try:
                artifacts[kind] = acquire_kind(kind)
            except ExperimentViolation as exc:
                errors.append(exc.code)
                break
    else:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="riftcoach-8b") as pool:
            futures = {kind: pool.submit(acquire_kind, kind) for kind in kinds}
            for kind in kinds:
                try:
                    artifacts[kind] = futures[kind].result()
                except ExperimentViolation as exc:
                    errors.append(exc.code)
    return _Acquisition(
        artifacts=tuple(artifacts[kind] for kind in kinds if kind in artifacts),
        error_code=errors[0] if errors else None,
    )


def _fixture_payload(*, kind: str, fault: str) -> Mapping[str, Any]:
    if kind == "knowledge_evidence":
        return {
            "schema_version": "1.0",
            "source_id": "knowledge-search-fixture-v1",
            "chunk_id": "knowledge-search-fixture-v1:chunk:1",
            "title": "review evidence boundary",
            "context": "A metric is a review clue and does not prove causality alone.",
        }
    if fault == "meta_schema_drift":
        raise ExperimentViolation("meta_schema_drift")
    if fault == "meta_instruction_payload":
        raise ExperimentViolation("meta_instruction_payload_rejected")
    if fault == "meta_timeout":
        raise ExperimentViolation("meta_timeout")
    return {
        "schema_version": "1.0",
        "source_id": "opgg-lane-meta-fixture-v1",
        "position": "mid",
        "provenance": "partial",
        "fact_count": 2,
    }


def _materialize_artifact(
    *,
    artifact_kind: str,
    producer_role: str,
    tool_name: str,
    context_sha: str,
    payload: Mapping[str, Any],
    gate_digest: str,
    case_set_sha: str,
    case_id: str,
    strategy_id: StrategyId,
) -> _MaterializedArtifact:
    payload_sha = _digest_json(payload)
    provenance_sha = _provenance_digest(
        artifact_kind=artifact_kind,
        producer_role=producer_role,
        tool_name=tool_name,
        context_sha=context_sha,
        payload_sha=payload_sha,
        gate_digest=gate_digest,
        case_set_sha=case_set_sha,
        case_id=case_id,
        strategy_id=strategy_id,
    )
    return _MaterializedArtifact(
        reference=ArtifactReference(
            artifact_kind=artifact_kind,
            producer_role=producer_role,
            tool_name=tool_name,
            payload_sha256=payload_sha,
            provenance_sha256=provenance_sha,
            context_sha256=context_sha,
        ),
        payload=payload,
    )


def _verify_artifact(
    artifact: _MaterializedArtifact,
    *,
    gate_digest: str,
    case_set_sha: str,
    case_id: str,
    strategy_id: StrategyId,
) -> None:
    reference = artifact.reference
    payload_sha = _digest_json(artifact.payload)
    expected_provenance = _provenance_digest(
        artifact_kind=reference.artifact_kind,
        producer_role=reference.producer_role,
        tool_name=reference.tool_name,
        context_sha=reference.context_sha256,
        payload_sha=payload_sha,
        gate_digest=gate_digest,
        case_set_sha=case_set_sha,
        case_id=case_id,
        strategy_id=strategy_id,
    )
    if (
        payload_sha != reference.payload_sha256
        or expected_provenance != reference.provenance_sha256
    ):
        raise ExperimentViolation("artifact_digest_mismatch")


def _role_contexts(
    case_id: str,
    strategy_id: StrategyId,
) -> tuple[RoleContextReference, ...]:
    if strategy_id is StrategyId.SERIAL:
        contracts = (
            (
                "single_coach_runtime",
                ("knowledge.search", "opgg.lane_meta"),
                ("deterministic_facts", "knowledge_evidence", "meta_evidence", "user_goal"),
            ),
        )
    elif strategy_id is StrategyId.BOUNDED_PARALLEL:
        contracts = (
            ("knowledge_branch", ("knowledge.search",), ("deterministic_facts", "knowledge_query")),
            ("meta_branch", ("opgg.lane_meta",), ("meta_allowlisted_query",)),
            ("coach_merge", (), ("deterministic_facts", "knowledge_evidence", "meta_evidence", "user_goal")),
        )
    else:
        contracts = (
            ("knowledge_agent", ("knowledge.search",), ("deterministic_facts", "knowledge_query")),
            ("meta_agent", ("opgg.lane_meta",), ("meta_allowlisted_query",)),
            ("coach_agent", (), ("deterministic_facts", "knowledge_evidence", "meta_evidence", "user_goal")),
        )
    return tuple(
        RoleContextReference(
            role_id=role_id,
            context_sha256=_digest_json(
                {
                    "schema_version": "1.0",
                    "case_id": case_id,
                    "strategy_id": strategy_id.value,
                    "role_id": role_id,
                    "context_scopes": scopes,
                    "allowed_tools": tools,
                }
            ),
            allowed_tools=tools,
            can_publish=False,
        )
        for role_id, tools, scopes in contracts
    )


def _artifact_roles(strategy_id: StrategyId) -> dict[str, str]:
    if strategy_id is StrategyId.SERIAL:
        return {
            "knowledge_evidence": "single_coach_runtime",
            "meta_evidence": "single_coach_runtime",
        }
    if strategy_id is StrategyId.BOUNDED_PARALLEL:
        return {
            "knowledge_evidence": "knowledge_branch",
            "meta_evidence": "meta_branch",
        }
    return {
        "knowledge_evidence": "knowledge_agent",
        "meta_evidence": "meta_agent",
    }


def _public_role_contract(
    strategy_id: StrategyId,
) -> tuple[dict[str, tuple[tuple[str, ...], bool]], bool]:
    if strategy_id is StrategyId.SERIAL:
        return {
            "single_coach_runtime": (
                ("knowledge.search", "opgg.lane_meta"),
                False,
            )
        }, False
    if strategy_id is StrategyId.BOUNDED_PARALLEL:
        return {
            "knowledge_branch": (("knowledge.search",), False),
            "meta_branch": (("opgg.lane_meta",), False),
            "coach_merge": ((), False),
        }, False
    return {
        "knowledge_agent": (("knowledge.search",), False),
        "meta_agent": (("opgg.lane_meta",), False),
        "coach_agent": ((), False),
    }, True


def _modeled_latency(case: AdoptionCase, strategy_id: StrategyId) -> int:
    if strategy_id is StrategyId.SERIAL:
        evidence = case.knowledge_latency_units + case.meta_latency_units
    else:
        evidence = max(case.knowledge_latency_units, case.meta_latency_units)
    return evidence + _LATENCY_OVERHEAD[strategy_id]


def _aggregate_metrics(
    results: tuple[ExperimentCaseResult, ...],
) -> tuple[StrategyMetrics, StrategyMetrics, StrategyMetrics]:
    rows_by_strategy = {
        strategy_id: tuple(
            row for row in results if row.strategy_id is strategy_id
        )
        for strategy_id in StrategyId
    }
    baseline_rows = rows_by_strategy[StrategyId.SERIAL]
    baseline_latency = sum(row.modeled_latency_units for row in baseline_rows)
    baseline_tokens = sum(row.token_units for row in baseline_rows)
    baseline_calls_by_case = {
        row.case_id: row.provider_calls for row in baseline_rows
    }
    output: list[StrategyMetrics] = []
    for strategy_id in StrategyId:
        rows = rows_by_strategy[strategy_id]
        latency = sum(row.modeled_latency_units for row in rows)
        tokens = sum(row.token_units for row in rows)
        degraded = [row for row in rows if row.expected_terminal == "degraded"]
        fault_rows = [
            row
            for row in rows
            if row.expected_terminal in {"degraded", "failed"}
        ]
        isolated = [
            row
            for row in fault_rows
            if row.terminal_matches_expected
            and (
                row.expected_terminal == "failed"
                or tuple(item.artifact_kind for item in row.preserved_artifacts)
                == ("knowledge_evidence",)
            )
        ]
        output.append(
            StrategyMetrics(
                strategy_id=strategy_id,
                harness_decision_match_rate=sum(
                    row.terminal_matches_expected for row in rows
                )
                / len(rows),
                safe_degraded_rate=(
                    sum(row.terminal_status == "degraded" for row in degraded)
                    / len(degraded)
                    if degraded
                    else 1.0
                ),
                failure_isolation_rate=(
                    len(isolated) / len(fault_rows) if fault_rows else 1.0
                ),
                modeled_latency_units=latency,
                modeled_latency_improvement_ratio=round(
                    (baseline_latency - latency) / baseline_latency,
                    12,
                ),
                total_token_units=tokens,
                total_token_ratio=round(tokens / baseline_tokens, 12),
                total_provider_calls=sum(row.provider_calls for row in rows),
                max_extra_provider_calls_per_case=max(
                    row.provider_calls - baseline_calls_by_case[row.case_id]
                    for row in rows
                ),
                hard_gate_total=0,
            )
        )
    return tuple(output)  # type: ignore[return-value]


def _experiment_verdict(
    *,
    split: ExperimentSplit,
    metrics: tuple[StrategyMetrics, StrategyMetrics, StrategyMetrics],
) -> tuple[str, tuple[str, ...]]:
    indexed = {item.strategy_id: item for item in metrics}
    candidate = indexed[StrategyId.ROLE_ISOLATED_MULTI_AGENT]
    comparator = indexed[StrategyId.BOUNDED_PARALLEL]
    common_pass = all(
        (
            candidate.harness_decision_match_rate == 1.0,
            candidate.safe_degraded_rate == 1.0,
            candidate.total_token_ratio <= 1.5,
            candidate.max_extra_provider_calls_per_case <= 2,
            candidate.hard_gate_total == 0,
        )
    )
    latency_pass = candidate.modeled_latency_improvement_ratio >= 0.2
    isolation_gain = (
        candidate.failure_isolation_rate > comparator.failure_isolation_rate
    )
    if split is ExperimentSplit.DEVELOPMENT and common_pass and latency_pass:
        return "eligible_for_holdout", ("development_thresholds_passed",)
    reasons: list[str] = []
    if not common_pass:
        reasons.append("quality_safety_or_cost_gate_failed")
    if not latency_pass:
        reasons.append("modeled_latency_threshold_missed")
    if not isolation_gain:
        reasons.append("no_incremental_benefit_over_parallel")
    return "reject_multi_agent", tuple(reasons or ("candidate_gate_failed",))


def _validate_holdout_admission(
    admission: HoldoutAdmission,
    *,
    code_sha: str,
    public_ci_sha: str | None,
) -> None:
    if not isinstance(admission, HoldoutAdmission):
        raise TypeError("admission must be a HoldoutAdmission")
    if public_ci_sha is None or not _is_git_sha(public_ci_sha):
        raise ExperimentViolation("public_ci_sha_invalid")
    if (
        admission.code_sha != code_sha
        or admission.public_ci_sha != public_ci_sha
        or public_ci_sha != code_sha
    ):
        raise ExperimentViolation("holdout_admission_identity_drift")
    expected_admission_id = build_holdout_admission_id(
        development_experiment_id=admission.development_experiment_id,
        code_sha=admission.code_sha,
        public_ci_sha=admission.public_ci_sha,
        gate_digest=admission.gate_digest,
        case_set_sha256=admission.case_set_sha256,
    )
    if admission.admission_id != expected_admission_id:
        raise ExperimentViolation("holdout_admission_identity_drift")


def build_holdout_admission_id(
    *,
    development_experiment_id: str,
    code_sha: str,
    public_ci_sha: str,
    gate_digest: str,
    case_set_sha256: str,
) -> str:
    return _digest_json(
        {
            "schema_version": "1.0",
            "development_experiment_id": development_experiment_id,
            "code_sha": code_sha,
            "public_ci_sha": public_ci_sha,
            "gate_digest": gate_digest,
            "case_set_sha256": case_set_sha256,
        }
    )


def build_experiment_id(
    *,
    split: ExperimentSplit,
    code_sha: str,
    public_ci_sha: str | None,
    gate_digest: str,
    case_set_sha256: str,
) -> str:
    """Build the exact result identity before reserving an output path."""

    if not isinstance(split, ExperimentSplit):
        raise TypeError("split must be an ExperimentSplit")
    return _digest_json(
        {
            "schema_version": "1.0",
            "split": split.value,
            "code_sha": code_sha,
            "public_ci_sha": public_ci_sha,
            "gate_digest": gate_digest,
            "case_set_sha256": case_set_sha256,
            "strategy_ids": [item.value for item in StrategyId],
        }
    )


def _provenance_digest(
    *,
    artifact_kind: str,
    producer_role: str,
    tool_name: str,
    context_sha: str,
    payload_sha: str,
    gate_digest: str,
    case_set_sha: str,
    case_id: str,
    strategy_id: StrategyId,
) -> str:
    return _digest_json(
        {
            "schema_version": "1.0",
            "artifact_kind": artifact_kind,
            "producer_role": producer_role,
            "tool_name": tool_name,
            "context_sha256": context_sha,
            "payload_sha256": payload_sha,
            "gate_digest": gate_digest,
            "case_set_sha256": case_set_sha,
            "case_id": case_id,
            "strategy_id": strategy_id.value,
        }
    )


def _zero_hard_gates() -> HardGateCounters:
    return HardGateCounters(
        unauthorized_tool_calls=0,
        cross_role_context_leaks=0,
        unprovenanced_evidence=0,
        unsafe_publications=0,
        terminal_identity_mismatches=0,
        real_external_io_calls=0,
        result_overwrites=0,
        experiment_identity_drifts=0,
    )


def _strategy_suffix(strategy_id: StrategyId) -> str:
    return {
        StrategyId.SERIAL: "serial",
        StrategyId.BOUNDED_PARALLEL: "parallel",
        StrategyId.ROLE_ISOLATED_MULTI_AGENT: "multi-agent",
    }[strategy_id]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_git_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "ExperimentViolation",
    "build_experiment_id",
    "build_holdout_admission_id",
    "run_stage8_experiment",
    "validate_experiment_record",
]
