"""Offline-only loader and structural eligibility gate for Stage 8 Advanced."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from .models import (
    AdoptionCaseSet,
    AdvancedAdoptionDecision,
    AdvancedAdoptionGate,
    CandidateDefinition,
    CandidateDecision,
    CandidateDisposition,
    CandidateKind,
    CandidateOutcome,
    CaseSplit,
    LoadedAdoptionGate,
)


_MAX_FILE_BYTES = 512 * 1024
_ALLOWED_EXPERIMENT_TOOLS = frozenset({"knowledge.search", "opgg.lane_meta"})
_REQUIRED_HARD_METRICS = frozenset(
    {
        "cross_role_context_leaks",
        "terminal_identity_mismatches",
        "unauthorized_tool_calls",
        "unprovenanced_evidence",
        "unsafe_publications",
    }
)
_REQUIRED_STOP_CONDITIONS = frozenset(
    {
        "case_set_identity_drift",
        "comparison_identity_drift",
        "cross_role_context_leak",
        "hard_gate_failed",
        "holdout_reexecution_requested",
        "no_incremental_benefit_over_parallel",
        "real_external_io_requested",
        "result_overwrite_requested",
        "role_tool_permission_overlap",
        "token_or_call_budget_exceeded",
        "unsafe_publication",
    }
)
_REQUIRED_MULTI_AGENT_METRICS = frozenset(
    {
        "cross_role_context_isolation",
        "modeled_latency_improvement",
        "safe_degraded_rate",
    }
)
_COACH_CONTEXT_SCOPES = frozenset(
    {
        "deterministic_facts",
        "external_meta_evidence",
        "knowledge_evidence",
        "user_goal",
    }
)
_EXPECTED_ACTIVE_ROLE_CONTRACTS = {
    CandidateKind.SERIAL_BASELINE: {
        "single_coach_runtime": (
            _COACH_CONTEXT_SCOPES,
            frozenset({"knowledge.search", "opgg.lane_meta"}),
            False,
        ),
    },
    CandidateKind.BOUNDED_PARALLEL: {
        "knowledge_branch": (
            frozenset({"deterministic_facts", "knowledge_query"}),
            frozenset({"knowledge.search"}),
            False,
        ),
        "meta_branch": (
            frozenset({"meta_allowlisted_query"}),
            frozenset({"opgg.lane_meta"}),
            False,
        ),
        "coach_merge": (_COACH_CONTEXT_SCOPES, frozenset(), False),
    },
    CandidateKind.ROLE_ISOLATED_MULTI_AGENT: {
        "knowledge_agent": (
            frozenset({"deterministic_facts", "knowledge_query"}),
            frozenset({"knowledge.search"}),
            True,
        ),
        "meta_agent": (
            frozenset({"meta_allowlisted_query"}),
            frozenset({"opgg.lane_meta"}),
            True,
        ),
        "coach_agent": (_COACH_CONTEXT_SCOPES, frozenset(), True),
    },
}


class AdoptionGateError(ValueError):
    """Stable, body-free adoption-gate failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def load_adoption_gate(
    gate_path: str | Path,
    case_set_path: str | Path,
) -> LoadedAdoptionGate:
    gate_file = Path(gate_path)
    cases_file = Path(case_set_path)
    gate_bytes = _read_bounded(gate_file, code="gate_file_invalid")
    case_bytes = _read_bounded(cases_file, code="case_set_file_invalid")
    try:
        json.loads(
            gate_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
        json.loads(
            case_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise AdoptionGateError("adoption_gate_json_invalid") from exc

    try:
        gate = AdvancedAdoptionGate.model_validate_json(gate_bytes, strict=True)
    except ValidationError as exc:
        raise AdoptionGateError("gate_contract_invalid") from exc
    try:
        case_set = AdoptionCaseSet.model_validate_json(case_bytes, strict=True)
    except ValidationError as exc:
        raise AdoptionGateError("case_set_contract_invalid") from exc

    gate_sha = hashlib.sha256(gate_bytes).hexdigest()
    case_sha = hashlib.sha256(case_bytes).hexdigest()
    if gate.case_set.sha256 != case_sha:
        raise AdoptionGateError("case_set_identity_drift")

    loaded = LoadedAdoptionGate(
        gate=gate,
        case_set=case_set,
        gate_path=gate_file,
        case_set_path=cases_file,
        gate_file_sha256=gate_sha,
        case_set_file_sha256=case_sha,
    )
    _validate_loaded_gate(loaded)
    return loaded


def evaluate_adoption_gate(loaded: LoadedAdoptionGate) -> AdvancedAdoptionDecision:
    if not isinstance(loaded, LoadedAdoptionGate):
        raise TypeError("loaded must be a LoadedAdoptionGate")
    _validate_loaded_gate(loaded)
    decisions: list[CandidateDecision] = []
    for candidate in loaded.gate.candidates:
        if candidate.disposition is CandidateDisposition.BASELINE:
            outcome = CandidateOutcome.BASELINE
            reasons = ("comparison_baseline",)
        elif candidate.disposition is CandidateDisposition.EVALUATE:
            outcome = CandidateOutcome.CANDIDATE
            reasons = ("eligible_for_8b",)
        else:
            outcome = CandidateOutcome.DEFERRED
            reasons = candidate.deferred_reason_codes
        decisions.append(
            CandidateDecision(
                candidate_id=candidate.candidate_id,
                outcome=outcome,
                reason_codes=reasons,
            )
        )

    comparison = loaded.gate.comparison_contract
    digest = _canonical_digest(
        {
            "gate": loaded.gate.model_dump(mode="json"),
            "case_set_sha256": loaded.case_set_file_sha256,
        }
    )
    return AdvancedAdoptionDecision(
        gate_id=loaded.gate.gate_id,
        gate_digest=digest,
        case_set_sha256=loaded.case_set_file_sha256,
        baseline_id=comparison.baseline_id,
        primary_candidate_id=comparison.primary_candidate_id,
        comparator_ids=comparison.comparator_ids,
        candidates=tuple(decisions),
    )


def _validate_loaded_gate(loaded: LoadedAdoptionGate) -> None:
    gate = loaded.gate
    case_set = loaded.case_set
    comparison = gate.comparison_contract

    if gate.case_set.case_set_id != case_set.case_set_id:
        raise AdoptionGateError("case_set_id_mismatch")
    if gate.product_slice_id != case_set.product_slice_id:
        raise AdoptionGateError("product_slice_identity_drift")
    if gate.source_product_sha != case_set.source_product_sha:
        raise AdoptionGateError("source_product_identity_drift")

    _validate_case_set(case_set)
    if comparison.external_io_budget != 0:
        raise AdoptionGateError("real_external_io_requested")
    if comparison.retry_budget != 0:
        raise AdoptionGateError("retry_budget_forbidden")
    if comparison.holdout_max_executions != 1:
        raise AdoptionGateError("holdout_execution_budget_invalid")
    if comparison.result_overwrite_allowed:
        raise AdoptionGateError("result_overwrite_requested")
    if len(set(comparison.comparator_ids)) != len(comparison.comparator_ids):
        raise AdoptionGateError("comparator_identity_duplicate")
    if len(set(comparison.input_fixture_sha256s)) != 2:
        raise AdoptionGateError("input_fixture_identity_invalid")
    if len(set(comparison.tool_fixture_ids)) != 2:
        raise AdoptionGateError("tool_fixture_identity_invalid")

    if not _REQUIRED_HARD_METRICS.issubset(gate.hard_gate_metrics):
        raise AdoptionGateError("hard_gate_metrics_incomplete")
    if not _REQUIRED_STOP_CONDITIONS.issubset(gate.stop_condition_codes):
        raise AdoptionGateError("stop_conditions_incomplete")
    if len(set(gate.hard_gate_metrics)) != len(gate.hard_gate_metrics):
        raise AdoptionGateError("hard_gate_metrics_duplicate")
    if len(set(gate.stop_condition_codes)) != len(gate.stop_condition_codes):
        raise AdoptionGateError("stop_conditions_duplicate")
    _validate_benefit_thresholds(gate)

    candidate_ids = tuple(row.candidate_id for row in gate.candidates)
    if len(set(candidate_ids)) != len(candidate_ids):
        raise AdoptionGateError("candidate_identity_duplicate")
    baseline_ids = {
        row.candidate_id
        for row in gate.candidates
        if row.disposition is CandidateDisposition.BASELINE
    }
    if baseline_ids != {comparison.baseline_id}:
        raise AdoptionGateError("baseline_identity_invalid")
    by_id = {row.candidate_id: row for row in gate.candidates}
    baseline = by_id.get(comparison.baseline_id)
    primary = by_id.get(comparison.primary_candidate_id)
    if baseline is None or baseline.disposition is not CandidateDisposition.BASELINE:
        raise AdoptionGateError("baseline_identity_invalid")
    if baseline.kind is not CandidateKind.SERIAL_BASELINE:
        raise AdoptionGateError("baseline_kind_invalid")
    if primary is None or primary.disposition is not CandidateDisposition.EVALUATE:
        raise AdoptionGateError("primary_candidate_not_evaluable")
    if primary.kind is not CandidateKind.ROLE_ISOLATED_MULTI_AGENT:
        raise AdoptionGateError("primary_candidate_kind_invalid")
    for comparator_id in comparison.comparator_ids:
        comparator = by_id.get(comparator_id)
        if comparator is None or comparator.disposition is not CandidateDisposition.EVALUATE:
            raise AdoptionGateError("comparator_not_evaluable")
        if comparator.kind is not CandidateKind.BOUNDED_PARALLEL:
            raise AdoptionGateError("parallel_comparator_required")
    active_candidate_ids = {
        row.candidate_id
        for row in gate.candidates
        if row.disposition is CandidateDisposition.EVALUATE
    }
    registered_active_ids = {
        comparison.primary_candidate_id,
        *comparison.comparator_ids,
    }
    if active_candidate_ids != registered_active_ids:
        raise AdoptionGateError("active_candidate_identity_invalid")

    bad_case_ids = {case.bad_case_id for case in case_set.cases}
    for candidate in gate.candidates:
        _validate_candidate(candidate, bad_case_ids)


def _validate_case_set(case_set: AdoptionCaseSet) -> None:
    case_ids = tuple(case.case_id for case in case_set.cases)
    if len(set(case_ids)) != len(case_ids):
        raise AdoptionGateError("case_identity_duplicate")
    development = tuple(
        case for case in case_set.cases if case.split is CaseSplit.DEVELOPMENT
    )
    holdout = tuple(case for case in case_set.cases if case.split is CaseSplit.HOLDOUT)
    if not development:
        raise AdoptionGateError("development_cases_missing")
    if not holdout:
        raise AdoptionGateError("holdout_cases_missing")
    if any(case.calibration_excluded for case in development):
        raise AdoptionGateError("development_calibration_policy_invalid")
    if any(not case.calibration_excluded for case in holdout):
        raise AdoptionGateError("holdout_calibration_policy_invalid")
    policy = case_set.calibration_policy
    if not policy.development_may_shape_implementation:
        raise AdoptionGateError("development_policy_invalid")
    if not policy.holdout_calibration_excluded:
        raise AdoptionGateError("holdout_calibration_policy_invalid")
    if policy.holdout_max_executions != 1:
        raise AdoptionGateError("holdout_execution_budget_invalid")
    if policy.holdout_result_overwrite_allowed:
        raise AdoptionGateError("result_overwrite_requested")
    for case in case_set.cases:
        if len(set(case.expected_preserved_artifacts)) != len(
            case.expected_preserved_artifacts
        ):
            raise AdoptionGateError("expected_artifact_duplicate")
        if case.expected_terminal.value == "failed" and not case.expected_error_code:
            raise AdoptionGateError("failed_case_error_code_missing")
        if case.expected_terminal.value != "failed" and case.expected_error_code:
            raise AdoptionGateError("non_failed_case_error_code_forbidden")


def _validate_benefit_thresholds(gate: AdvancedAdoptionGate) -> None:
    thresholds = gate.benefit_thresholds
    if thresholds.min_harness_decision_match_rate != 1.0:
        raise AdoptionGateError("harness_match_threshold_invalid")
    if thresholds.min_safe_degraded_rate != 1.0:
        raise AdoptionGateError("safe_degraded_threshold_invalid")
    if thresholds.min_modeled_latency_improvement_ratio != 0.2:
        raise AdoptionGateError("latency_threshold_invalid")
    if thresholds.max_total_token_ratio != 1.5:
        raise AdoptionGateError("token_ratio_threshold_invalid")
    if thresholds.max_extra_provider_calls != 2:
        raise AdoptionGateError("provider_call_threshold_invalid")
    if not thresholds.allow_failure_isolation_instead_of_latency:
        raise AdoptionGateError("failure_isolation_alternative_required")


def _validate_candidate(
    candidate: CandidateDefinition,
    bad_case_ids: set[str],
) -> None:
    if candidate.production_dependency_allowed:
        raise AdoptionGateError("production_dependency_forbidden")
    if candidate.product_runtime_changes_allowed:
        raise AdoptionGateError("product_runtime_change_forbidden")
    if any(role.can_publish for role in candidate.roles):
        raise AdoptionGateError("unsafe_publication")
    if len({role.role_id for role in candidate.roles}) != len(candidate.roles):
        raise AdoptionGateError("role_identity_duplicate")
    if any(len(set(role.context_scopes)) != len(role.context_scopes) for role in candidate.roles):
        raise AdoptionGateError("context_scope_duplicate")
    if any(len(set(role.allowed_tools)) != len(role.allowed_tools) for role in candidate.roles):
        raise AdoptionGateError("role_tool_duplicate")
    if any(
        tool not in _ALLOWED_EXPERIMENT_TOOLS
        for role in candidate.roles
        for tool in role.allowed_tools
    ):
        raise AdoptionGateError("role_tool_not_allowed")

    if candidate.disposition is CandidateDisposition.DEFERRED:
        if not candidate.deferred_reason_codes:
            raise AdoptionGateError("deferred_reason_required")
        if candidate.roles or candidate.expected_benefit_metrics:
            raise AdoptionGateError("deferred_candidate_scope_invalid")
        return
    if candidate.deferred_reason_codes:
        raise AdoptionGateError("active_candidate_deferred_reason_forbidden")
    if not candidate.roles:
        raise AdoptionGateError("active_candidate_roles_missing")
    if not candidate.target_bad_case_ids:
        raise AdoptionGateError("candidate_bad_case_missing")
    if not set(candidate.target_bad_case_ids).issubset(bad_case_ids):
        raise AdoptionGateError("candidate_bad_case_unknown")

    coach = None
    if candidate.kind is CandidateKind.ROLE_ISOLATED_MULTI_AGENT:
        coach = next(
            (role for role in candidate.roles if role.role_id == "coach_agent"),
            None,
        )
        if coach is None:
            raise AdoptionGateError("coach_role_required")
        if coach.allowed_tools:
            raise AdoptionGateError("coach_tool_permission_forbidden")

    tool_owners: dict[str, str] = {}
    for role in candidate.roles:
        for tool in role.allowed_tools:
            if tool in tool_owners:
                raise AdoptionGateError("role_tool_permission_overlap")
            tool_owners[tool] = role.role_id

    if candidate.kind is CandidateKind.ROLE_ISOLATED_MULTI_AGENT:
        if any(not role.independent_context for role in candidate.roles):
            raise AdoptionGateError("independent_context_required")
        if not _REQUIRED_MULTI_AGENT_METRICS.issubset(
            candidate.expected_benefit_metrics
        ):
            raise AdoptionGateError("multi_agent_benefit_metrics_incomplete")
    elif candidate.disposition is CandidateDisposition.EVALUATE:
        if not candidate.expected_benefit_metrics:
            raise AdoptionGateError("candidate_benefit_metric_missing")

    actual_roles = {
        role.role_id: (
            frozenset(role.context_scopes),
            frozenset(role.allowed_tools),
            role.independent_context,
        )
        for role in candidate.roles
    }
    expected_roles = _EXPECTED_ACTIVE_ROLE_CONTRACTS.get(candidate.kind)
    if actual_roles != expected_roles:
        if candidate.kind is CandidateKind.ROLE_ISOLATED_MULTI_AGENT:
            raise AdoptionGateError("multi_agent_role_contract_invalid")
        raise AdoptionGateError("candidate_role_contract_invalid")


def _read_bounded(path: Path, *, code: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AdoptionGateError(code) from exc
    if not data or len(data) > _MAX_FILE_BYTES:
        raise AdoptionGateError(code)
    return data


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
