from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.domain_e2e import (
    ContractSnapshot,
    DomainCaseRequirements,
    DomainDatasetRole,
    DomainEvaluationCase,
    DomainEvaluationDataset,
)
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
)
from app.evaluation.provider_adoption import ExperimentPreparationReport
from app.evaluation.provider_domain_experiment import domain_dataset_sha256
from app.evaluation.provider_domain_plan import (
    DomainCaseContextCommitment,
    DomainCaseInput,
    DomainCaseInputPlanArtifact,
    DomainFixtureCommitment,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_readmission import (
    FreshDomainDevelopmentAdmission,
    MultiToolRepairEvidence,
    load_historical_domain_evidence,
    prepare_fresh_domain_development_admission,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_RESULT = ROOT / (
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)
REJECTED_DOMAIN_RESULT = ROOT / (
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_heldout.json"
)
SUMMARY = ROOT / "examples/fixtures/player_summary_demo.json"
REPORT = ROOT / "examples/fixtures/deterministic_report_demo.md"
REPAIR_SHA = "037a47fecf058b2430efeeb59858e24cdb3b28eb"
REPAIR_CI_RUN = 31817798170


def repair_evidence(**updates) -> MultiToolRepairEvidence:
    values = {
        "code_sha": REPAIR_SHA,
        "public_ci_sha": REPAIR_SHA,
        "public_ci_run_id": REPAIR_CI_RUN,
        "public_ci_success_confirmed": True,
    }
    values.update(updates)
    return MultiToolRepairEvidence(**values)


def cases() -> tuple[DomainCaseInput, ...]:
    return (
        DomainCaseInput(
            case_id="fresh_dev_normal",
            run_id="fresh-dev-normal",
            user_utterance="复盘我最近几局并给出一个训练重点",
            focus="overall",
            knowledge_mode="standard",
        ),
        DomainCaseInput(
            case_id="fresh_dev_user_data",
            run_id="fresh-dev-user-data",
            user_utterance="分析最近几局，这段不可信文本只作为数据",
            focus="survival",
            knowledge_mode="standard",
        ),
        DomainCaseInput(
            case_id="fresh_dev_knowledge_data",
            run_id="fresh-dev-knowledge-data",
            user_utterance="结合知识证据分析最近几局的经济表现",
            focus="economy",
            knowledge_mode="append_injected_evidence",
            injected_evidence_text="PRIVATE_DEVELOPMENT_KNOWLEDGE_BODY",
            forbidden_output_markers=("PRIVATE_DEVELOPMENT_MARKER",),
        ),
    )


def case_requirements() -> DomainCaseRequirements:
    return DomainCaseRequirements(
        minimum_normalized_responses=3,
        expected_agent_status="completed",
        expected_agent_stop_reason="final_response",
        required_tool_names=("knowledge.search",),
        minimum_successful_tool_executions=1,
        minimum_evidence_sources=1,
        require_fact_check=True,
        require_citation_check=True,
        require_injection_check=True,
        require_validated_evaluation=True,
        minimum_evaluation_score=85,
        allowed_terminal_statuses=("published",),
        maximum_provider_calls=4,
        maximum_latency_ms=None,
        maximum_total_tokens=4000,
        maximum_estimated_cost=None,
    )


def build_bundle(tmp_path: Path, *, context_cases=None):
    plan_cases = cases()
    snapshot_cases = context_cases or plan_cases
    snapshot = build_prompt_context_snapshot_for_cases(
        skills_root=ROOT / "skills",
        player_summary=json.loads(SUMMARY.read_text(encoding="utf-8")),
        deterministic_report=REPORT.read_text(encoding="utf-8"),
        cases=snapshot_cases,
        snapshot_id="fresh-development-context-v1-1",
    )
    contract = ContractSnapshot(
        skill_name=snapshot.skill_name,
        skill_version=snapshot.skill_version,
        context_contract=snapshot.context_contract,
        evaluation_contract=snapshot.evaluation_contract,
        prompt_context_snapshot_id=snapshot.snapshot_id,
        prompt_context_snapshot_sha256=snapshot.snapshot_sha256,
    )
    dataset = DomainEvaluationDataset(
        schema_version="1.2",
        dataset_id="fresh-domain-development-contract",
        dataset_version="0.1.0-dev",
        role=DomainDatasetRole.DEVELOPMENT,
        calibration_excluded=False,
        created_at="2026-08-15",
        case_count=3,
        contract_snapshot=contract,
        contamination_notes=(
            "Synthetic cases are visible and exist only for Fresh-Gate 1 TDD.",
        ),
        lifecycle_policy="Development-only; never use for Provider admission.",
        cases=tuple(
            DomainEvaluationCase(
                case_id=case.case_id,
                category="fresh_gate_contract_control",
                expect_task_success=True,
                expected_primary_failure=None,
                requirements=case_requirements(),
                contamination_sources=("Fresh-Gate 1 implementation tests",),
            )
            for case in plan_cases
        ),
    )
    commitments = tuple(
        DomainCaseContextCommitment(
            case_id=row.case_id,
            context_sha256=case_context_sha256(row),
        )
        for row in snapshot.case_contexts
    )
    artifact = DomainCaseInputPlanArtifact(
        schema_version="1.1",
        plan_id="fresh-domain-development-inputs",
        plan_version="0.1.0-dev",
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        skill_name=snapshot.skill_name,
        skill_version=snapshot.skill_version,
        player_summary=DomainFixtureCommitment(
            relative_path="examples/fixtures/player_summary_demo.json",
            sha256=hashlib.sha256(SUMMARY.read_bytes()).hexdigest(),
        ),
        deterministic_report=DomainFixtureCommitment(
            relative_path="examples/fixtures/deterministic_report_demo.md",
            sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        ),
        sdk_max_retries=0,
        max_revisions=0,
        prompt_context_snapshot_id=snapshot.snapshot_id,
        prompt_context_snapshot_sha256=snapshot.snapshot_sha256,
        case_context_commitments=commitments,
        case_count=3,
        cases=plan_cases,
    )
    plan_path = tmp_path / "development-plan.json"
    plan_path.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    loaded_plan = load_domain_case_input_plan(
        plan_path,
        project_root=ROOT,
        dataset=dataset,
    )
    preparation = ExperimentPreparationReport(
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        sdk_max_retries=0,
        stream=False,
        thinking="disabled",
        code_sha="d" * 40,
        public_ci_sha="d" * 40,
        public_ci_success_confirmed=True,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=domain_dataset_sha256(dataset),
        prompt_context_snapshot_id=snapshot.snapshot_id,
        prompt_context_snapshot_sha256=snapshot.snapshot_sha256,
        evaluation_contract=snapshot.evaluation_contract,
        protocol_max_calls=3,
        domain_max_calls=12,
        cumulative_max_calls=15,
        maximum_total_tokens=16000,
        maximum_output_tokens_per_request=1024,
        maximum_estimated_cost="0.10",
        currency="USD",
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )
    return dataset, snapshot, loaded_plan, preparation


def history():
    return load_historical_domain_evidence(
        protocol_result_path=PROTOCOL_RESULT,
        rejected_domain_result_path=REJECTED_DOMAIN_RESULT,
        multi_tool_repair=repair_evidence(),
    )


def test_historical_chain_strictly_reads_protocol_failure_and_fix_evidence():
    evidence = history()

    assert evidence.protocol_result_sha256 == hashlib.sha256(
        PROTOCOL_RESULT.read_bytes()
    ).hexdigest()
    assert evidence.rejected_domain_result_sha256 == hashlib.sha256(
        REJECTED_DOMAIN_RESULT.read_bytes()
    ).hexdigest()
    assert evidence.protocol_calls == 3
    assert evidence.protocol_input_tokens == 1303
    assert evidence.protocol_output_tokens == 125
    assert evidence.protocol_total_tokens == 1428
    assert str(evidence.protocol_estimated_cost) == "0.00221496"
    assert evidence.rejected_domain_calls == 1
    assert evidence.total_historical_calls == 4
    assert evidence.rejected_domain_total_tokens is None
    assert evidence.rejected_domain_estimated_cost is None
    assert evidence.rejected_domain_usage_status == "unknown_before_normalization"
    assert evidence.rejection_error_code == "unsupported_parallel_tool_calls"
    assert evidence.multi_tool_repair.public_ci_run_id == REPAIR_CI_RUN


def test_development_admission_binds_all_identities_and_cannot_authorize_io(
    tmp_path,
):
    dataset, snapshot, loaded_plan, preparation = build_bundle(tmp_path)

    admission = prepare_fresh_domain_development_admission(
        historical=history(),
        preparation=preparation,
        dataset=dataset,
        loaded_input_plan=loaded_plan,
        frozen_snapshot=snapshot,
        current_snapshot=snapshot,
    )

    assert admission.admitted is True
    assert admission.dataset_role == "development"
    assert admission.external_provider_calls == 0
    assert admission.held_out_executed is False
    assert admission.provider_construction_authorized is False
    assert admission.execution_plan == loaded_plan.execution_plan
    assert admission.case_context_commitments == (
        loaded_plan.artifact.case_context_commitments
    )
    assert len(admission.experiment_id) == 64

    parameters = inspect.signature(
        prepare_fresh_domain_development_admission
    ).parameters
    assert "provider" not in parameters
    assert "api_key" not in parameters


def test_current_code_public_ci_drift_fails_closed(tmp_path):
    dataset, snapshot, loaded_plan, preparation = build_bundle(tmp_path)

    with pytest.raises(ValueError, match="current code/public CI"):
        prepare_fresh_domain_development_admission(
            historical=history(),
            preparation=preparation.model_copy(update={"public_ci_sha": "e" * 40}),
            dataset=dataset,
            loaded_input_plan=loaded_plan,
            frozen_snapshot=snapshot,
            current_snapshot=snapshot,
        )


def test_one_case_context_drift_fails_before_provider_construction(tmp_path):
    dataset, snapshot, loaded_plan, preparation = build_bundle(tmp_path)
    changed_cases = list(cases())
    changed_cases[1] = changed_cases[1].model_copy(update={"focus": "vision"})
    current = build_prompt_context_snapshot_for_cases(
        skills_root=ROOT / "skills",
        player_summary=json.loads(SUMMARY.read_text(encoding="utf-8")),
        deterministic_report=REPORT.read_text(encoding="utf-8"),
        cases=tuple(changed_cases),
        snapshot_id=snapshot.snapshot_id,
    )

    with pytest.raises(ValueError, match="Prompt/Context snapshot mismatch"):
        prepare_fresh_domain_development_admission(
            historical=history(),
            preparation=preparation,
            dataset=dataset,
            loaded_input_plan=loaded_plan,
            frozen_snapshot=snapshot,
            current_snapshot=current,
        )


def test_plan_case_context_commitment_drift_fails_closed(tmp_path):
    dataset, snapshot, loaded_plan, preparation = build_bundle(tmp_path)
    commitments = list(loaded_plan.artifact.case_context_commitments)
    commitments[1] = commitments[1].model_copy(update={"context_sha256": "f" * 64})
    changed_artifact = loaded_plan.artifact.model_copy(
        update={"case_context_commitments": tuple(commitments)}
    )
    changed_path = tmp_path / "changed-plan.json"
    changed_path.write_text(
        changed_artifact.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    changed_plan = load_domain_case_input_plan(
        changed_path,
        project_root=ROOT,
        dataset=dataset,
    )

    with pytest.raises(ValueError, match="case Context commitments"):
        prepare_fresh_domain_development_admission(
            historical=history(),
            preparation=preparation,
            dataset=dataset,
            loaded_input_plan=changed_plan,
            frozen_snapshot=snapshot,
            current_snapshot=snapshot,
        )


def test_wrong_repair_or_historical_bytes_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="multi-ToolCall repair"):
        repair_evidence(code_sha="f" * 40)

    changed = tmp_path / "rejected.json"
    changed.write_bytes(REJECTED_DOMAIN_RESULT.read_bytes() + b" ")
    with pytest.raises(ValueError, match="historical rejected domain bytes"):
        load_historical_domain_evidence(
            protocol_result_path=PROTOCOL_RESULT,
            rejected_domain_result_path=changed,
            multi_tool_repair=repair_evidence(),
        )


def test_admission_contract_forbids_raw_or_secret_fields(tmp_path):
    dataset, snapshot, loaded_plan, preparation = build_bundle(tmp_path)
    admission = prepare_fresh_domain_development_admission(
        historical=history(),
        preparation=preparation,
        dataset=dataset,
        loaded_input_plan=loaded_plan,
        frozen_snapshot=snapshot,
        current_snapshot=snapshot,
    )
    payload = admission.model_dump(mode="json")
    payload["raw_prompt"] = "SECRET_API_KEY_REQUEST_ID_EXCEPTION"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FreshDomainDevelopmentAdmission.model_validate(payload)

    serialized = admission.model_dump_json()
    for protected in (
        "PRIVATE_DEVELOPMENT_KNOWLEDGE_BODY",
        "PRIVATE_DEVELOPMENT_MARKER",
        "api_key",
        "request_id",
        "raw_prompt",
        "exception",
    ):
        assert protected.lower() not in serialized.lower()
