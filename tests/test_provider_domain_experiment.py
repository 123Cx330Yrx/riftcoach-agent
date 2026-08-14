from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.evaluation.domain_e2e import (
    ContractSnapshot,
    DomainCaseRequirements,
    DomainDatasetRole,
    DomainEvaluationCase,
    DomainEvaluationDataset,
)
from app.evaluation.provider_adoption import (
    ExperimentFailureCode,
    ExperimentPreparationReport,
)
from app.evaluation.provider_domain_experiment import (
    DomainCaseExecutionPlan,
    DomainCaseSemanticObservation,
    ImmutableDomainExperimentOutput,
    domain_dataset_sha256,
    load_protocol_artifact,
    prepare_deepseek_domain_heldout_run,
    run_deepseek_domain_heldout_experiment,
    write_immutable_domain_experiment_record,
)
from app.evaluation.provider_protocol_experiment import (
    ProviderAdapterProtocolExperimentRecord,
    run_deepseek_adapter_protocol_experiment,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
)
from tests.test_deepseek_protocol_experiment import successful_provider


CASE_IDS = ("case_normal", "case_user_injection", "case_rag_injection")
RAW_SECRET = "RAW_PROMPT_ATTACK_MODEL_TEXT_REQUEST_ID_EXCEPTION_KEY"


def contract() -> ContractSnapshot:
    return ContractSnapshot(
        skill_name="recent-form-review",
        skill_version="0.2.0",
        context_contract="context-builder-v1",
        evaluation_contract="coach_evaluation@1.1.0",
        prompt_context_snapshot_id="recent-form-prompt-context-v1-1",
        prompt_context_snapshot_sha256="c" * 64,
    )


def requirements(**updates) -> DomainCaseRequirements:
    values = {
        "minimum_normalized_responses": 0,
        "expected_agent_status": None,
        "expected_agent_stop_reason": None,
        "required_tool_names": (),
        "minimum_successful_tool_executions": 0,
        "minimum_evidence_sources": 0,
        "require_fact_check": False,
        "require_citation_check": False,
        "require_injection_check": False,
        "require_validated_evaluation": False,
        "minimum_evaluation_score": None,
        "allowed_terminal_statuses": ("degraded",),
        "maximum_provider_calls": 4,
        "maximum_latency_ms": None,
        "maximum_total_tokens": 4000,
        "maximum_estimated_cost": None,
    }
    values.update(updates)
    return DomainCaseRequirements(**values)


def dataset(*, case_requirements=None) -> DomainEvaluationDataset:
    rows = []
    for index, case_id in enumerate(CASE_IDS):
        row_requirements = (
            case_requirements[index]
            if case_requirements is not None
            else requirements()
        )
        rows.append(
            DomainEvaluationCase(
                case_id=case_id,
                category="synthetic_control",
                expect_task_success=True,
                expected_primary_failure=None,
                requirements=row_requirements,
                contamination_sources=(),
            )
        )
    return DomainEvaluationDataset(
        schema_version="1.2",
        dataset_id="synthetic-held-out",
        dataset_version="1.0.0",
        role=DomainDatasetRole.HELD_OUT,
        calibration_excluded=True,
        created_at="2026-08-14",
        case_count=3,
        contract_snapshot=contract(),
        contamination_notes=(),
        lifecycle_policy="Synthetic test fixture; rules must be frozen.",
        cases=tuple(rows),
    )


def preparation(value: DomainEvaluationDataset) -> ExperimentPreparationReport:
    return ExperimentPreparationReport(
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        sdk_max_retries=0,
        stream=False,
        thinking="disabled",
        code_sha="d" * 40,
        public_ci_sha="d" * 40,
        public_ci_success_confirmed=True,
        dataset_id=value.dataset_id,
        dataset_version=value.dataset_version,
        dataset_sha256=domain_dataset_sha256(value),
        prompt_context_snapshot_id=(
            value.contract_snapshot.prompt_context_snapshot_id
        ),
        prompt_context_snapshot_sha256=(
            value.contract_snapshot.prompt_context_snapshot_sha256
        ),
        evaluation_contract=value.contract_snapshot.evaluation_contract,
        protocol_max_calls=3,
        domain_max_calls=12,
        cumulative_max_calls=15,
        maximum_total_tokens=16_000,
        maximum_output_tokens_per_request=1024,
        maximum_estimated_cost="0.10",
        currency="USD",
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )


def protocol_preparation(value: DomainEvaluationDataset):
    return preparation(value).model_copy(
        update={"code_sha": "a" * 40, "public_ci_sha": "a" * 40}
    )


def protocol_record(
    value: DomainEvaluationDataset,
) -> ProviderAdapterProtocolExperimentRecord:
    return run_deepseek_adapter_protocol_experiment(
        preparation=protocol_preparation(value),
        provider=successful_provider(),
        clock=lambda: 0.0,
        now=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def plan() -> DomainCaseExecutionPlan:
    return DomainCaseExecutionPlan(
        plan_id="synthetic-domain-plan",
        plan_version="1.0.0",
        plan_sha256="e" * 64,
        case_ids=CASE_IDS,
    )


def request() -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, RAW_SECRET),),
        max_tokens=1,
    )


@dataclass
class RecordingProvider:
    provider_name: str = "deepseek"
    model_name: str = "deepseek-v4-pro"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)
    input_tokens: int = 10
    output_tokens: int = 5

    def chat(self, value: ChatRequest) -> ChatResponse:
        self.requests.append(value)
        return ChatResponse(
            content=RAW_SECRET,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
            request_id=RAW_SECRET,
        )


@dataclass
class SyntheticExecutor:
    calls_by_case: dict[str, int]
    execution_plan: DomainCaseExecutionPlan = field(default_factory=plan)

    def execute(self, *, case, provider) -> DomainCaseSemanticObservation:
        responses = [provider.chat(request()) for _ in range(self.calls_by_case[case.case_id])]
        return DomainCaseSemanticObservation(
            case_id=case.case_id,
            normalized_response_count=len(responses),
            safe_provider_error_code=None,
            agent_status=None,
            agent_stop_reason=None,
            proposed_tool_names=(),
            successful_tool_names=(),
            evidence_source_ids=(),
            fact_check_passed=None,
            citation_check_passed=None,
            injection_check_passed=None,
            evaluation_validated=False,
            evaluation_score=None,
            terminal_status="degraded",
            terminal_reason="deterministic_fallback",
            provenance_sha256=hashlib.sha256(case.case_id.encode()).hexdigest(),
        )


def run_experiment(*, value=None, executor=None, provider=None):
    frozen = value or dataset()
    admitted = protocol_record(frozen)
    admission = prepare_deepseek_domain_heldout_run(
        preparation=preparation(frozen),
        protocol_record=admitted,
        protocol_result_sha256=hashlib.sha256(
            admitted.model_dump_json().encode()
        ).hexdigest(),
        dataset=frozen,
        execution_plan=plan(),
    )
    return run_deepseek_domain_heldout_experiment(
        admission=admission,
        dataset=frozen,
        provider=provider or RecordingProvider(),
        case_executor=executor
        or SyntheticExecutor({case_id: 4 for case_id in CASE_IDS}),
        clock=lambda: 0.0,
        now=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def test_three_cases_continue_from_protocol_and_use_exact_domain_budget():
    provider = RecordingProvider()
    record = run_experiment(provider=provider)

    assert record.admitted is True
    assert record.held_out_executed is True
    assert record.prior_protocol.calls_used == 3
    assert record.domain_calls_used == 12
    assert record.resources.calls_used == 15
    assert len(provider.requests) == 12
    assert [row.status for row in record.cases] == ["executed"] * 3
    assert [row.observation.provider_calls for row in record.cases] == [4, 4, 4]
    assert record.candidate is not None
    assert record.evaluation is not None
    assert record.evaluation.task_outcome_accuracy == 1.0


def test_fifth_case_call_stops_before_io_and_skips_remaining_cases():
    provider = RecordingProvider()
    record = run_experiment(
        provider=provider,
        executor=SyntheticExecutor(
            {
                CASE_IDS[0]: 5,
                CASE_IDS[1]: 1,
                CASE_IDS[2]: 1,
            }
        ),
    )

    assert record.admitted is False
    assert len(provider.requests) == 4
    assert [row.status for row in record.cases] == [
        "failed",
        "skipped",
        "skipped",
    ]
    assert record.cases[0].failure_code is (
        ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED
    )
    assert record.domain_calls_used == 4
    assert record.candidate is None
    assert record.evaluation is None


def test_case_result_mismatch_stops_candidate_before_second_case():
    provider = RecordingProvider()

    @dataclass
    class MismatchExecutor(SyntheticExecutor):
        def execute(self, *, case, provider):
            observed = super().execute(case=case, provider=provider)
            return observed.model_copy(update={"terminal_status": "published"})

    record = run_experiment(
        provider=provider,
        executor=MismatchExecutor({case_id: 1 for case_id in CASE_IDS}),
    )

    assert len(provider.requests) == 1
    assert record.cases[0].status == "executed"
    assert record.cases[0].failure_code is (
        ExperimentFailureCode.DOMAIN_CASE_OUTCOME_MISMATCH
    )
    assert [row.status for row in record.cases[1:]] == ["skipped", "skipped"]


def test_unsafe_publication_globally_stops_experiment():
    unsafe_requirements = requirements(
        minimum_normalized_responses=1,
        expected_agent_status="completed",
        expected_agent_stop_reason="final_response",
        required_tool_names=("knowledge.search",),
        minimum_successful_tool_executions=1,
        minimum_evidence_sources=1,
        require_fact_check=True,
        require_citation_check=True,
        require_injection_check=True,
        require_validated_evaluation=True,
        minimum_evaluation_score=80,
        allowed_terminal_statuses=("published",),
    )
    frozen = dataset(
        case_requirements=(
            unsafe_requirements,
            requirements(),
            requirements(),
        )
    )

    @dataclass
    class UnsafeExecutor(SyntheticExecutor):
        def execute(self, *, case, provider):
            observed = super().execute(case=case, provider=provider)
            return observed.model_copy(update={"terminal_status": "published"})

    record = run_experiment(
        value=frozen,
        executor=UnsafeExecutor({case_id: 1 for case_id in CASE_IDS}),
    )

    assert record.control.global_stop is ExperimentFailureCode.UNSAFE_PUBLICATION
    assert record.cases[0].failure_code is ExperimentFailureCode.UNSAFE_PUBLICATION
    assert [row.status for row in record.cases[1:]] == ["skipped", "skipped"]


def test_identity_mismatch_fails_before_provider_io():
    frozen = dataset()
    admitted = protocol_record(frozen)
    provider = RecordingProvider()

    with pytest.raises(ValueError, match="execution plan"):
        prepare_deepseek_domain_heldout_run(
            preparation=preparation(frozen),
            protocol_record=admitted,
            protocol_result_sha256="f" * 64,
            dataset=frozen,
            execution_plan=plan().model_copy(
                update={"case_ids": tuple(reversed(CASE_IDS))}
            ),
        )

    assert provider.requests == []


def test_executor_plan_mismatch_fails_before_provider_io():
    frozen = dataset()
    admitted = protocol_record(frozen)
    admission = prepare_deepseek_domain_heldout_run(
        preparation=preparation(frozen),
        protocol_record=admitted,
        protocol_result_sha256="f" * 64,
        dataset=frozen,
        execution_plan=plan(),
    )
    provider = RecordingProvider()
    executor = SyntheticExecutor(
        {case_id: 1 for case_id in CASE_IDS},
        execution_plan=plan().model_copy(update={"plan_sha256": "9" * 64}),
    )

    with pytest.raises(ValueError, match="case executor"):
        run_deepseek_domain_heldout_experiment(
            admission=admission,
            dataset=frozen,
            provider=provider,
            case_executor=executor,
        )

    assert provider.requests == []


def test_case_budget_drift_is_rejected_during_no_io_admission():
    frozen = dataset(
        case_requirements=(
            requirements(maximum_provider_calls=3),
            requirements(),
            requirements(),
        )
    )
    admitted = protocol_record(frozen)

    with pytest.raises(ValueError, match="resource contract"):
        prepare_deepseek_domain_heldout_run(
            preparation=preparation(frozen),
            protocol_record=admitted,
            protocol_result_sha256="f" * 64,
            dataset=frozen,
            execution_plan=plan(),
        )


def test_public_record_is_sanitized_and_cannot_be_overwritten(tmp_path):
    record = run_experiment(
        executor=SyntheticExecutor({case_id: 1 for case_id in CASE_IDS})
    )
    serialized = record.model_dump_json()
    assert RAW_SECRET not in serialized
    for forbidden in (
        "prompt",
        "user_utterance",
        "model_text",
        "request_id",
        "api_key",
        "exception",
    ):
        assert forbidden not in json.loads(serialized)

    output = tmp_path / "domain.json"
    write_immutable_domain_experiment_record(output, record)
    with pytest.raises(FileExistsError):
        write_immutable_domain_experiment_record(output, record)


def test_protocol_loader_binds_record_to_exact_file_bytes(tmp_path):
    frozen = dataset()
    record = protocol_record(frozen)
    path = tmp_path / "protocol.json"
    raw = record.model_dump_json(indent=2).encode("utf-8") + b"\n"
    path.write_bytes(raw)

    loaded = load_protocol_artifact(path)

    assert loaded.record == record
    assert loaded.result_sha256 == hashlib.sha256(raw).hexdigest()


def test_output_reservation_blocks_duplicate_before_record_exists(tmp_path):
    record = run_experiment(
        executor=SyntheticExecutor({case_id: 1 for case_id in CASE_IDS})
    )
    output = tmp_path / "domain.json"
    reservation = ImmutableDomainExperimentOutput.reserve(
        output,
        experiment_id=record.experiment_id,
    )

    with pytest.raises(FileExistsError):
        ImmutableDomainExperimentOutput.reserve(
            output,
            experiment_id=record.experiment_id,
        )

    reservation.commit(record)
    assert json.loads(output.read_text(encoding="utf-8"))["admitted"] is True


def test_case_token_limit_stops_after_observed_overrun():
    provider = RecordingProvider(input_tokens=2000, output_tokens=1)
    record = run_experiment(
        provider=provider,
        executor=SyntheticExecutor({case_id: 3 for case_id in CASE_IDS}),
    )

    assert len(provider.requests) == 2
    assert record.cases[0].status == "failed"
    assert record.cases[0].failure_code is (
        ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
    )
    assert record.resources.case_resources[0].total_tokens == 4002


def test_unexpected_executor_exception_is_reduced_to_safe_code():
    @dataclass
    class LeakyExecutor(SyntheticExecutor):
        def execute(self, *, case, provider):
            raise RuntimeError(RAW_SECRET)

    record = run_experiment(
        executor=LeakyExecutor({case_id: 0 for case_id in CASE_IDS})
    )

    serialized = record.model_dump_json()
    assert RAW_SECRET not in serialized
    assert record.domain_calls_used == 0
    assert record.cases[0].failure_code is (
        ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID
    )
    assert [row.status for row in record.cases[1:]] == ["skipped", "skipped"]
