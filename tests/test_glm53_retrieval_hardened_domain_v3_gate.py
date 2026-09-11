from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import pytest

from app.evaluation import glm53_retrieval_hardened_domain_v3_gate as gate
from app.evaluation import glm53_retrieval_hardened_domain_v3_assets as assets
from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from tests.test_glm53_hardened_domain_v3_gate import PassingExecutor, ScriptedProvider

from app.evaluation.glm53_retrieval_hardened_domain_v3_gate import (
    RetrievalV3DomainGateOptions,
    RetrievalV3PreflightStatus,
    run_retrieval_cli,
)


ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_gate_stops_before_provider_until_public_ci() -> None:
    result = run_retrieval_cli(
        RetrievalV3DomainGateOptions(confirm_real_call=False, preflight_only=True),
        repository_root=ROOT,
        environment_loader=lambda _root: (_ for _ in ()).throw(AssertionError()),
        provider_factory=lambda _settings: (_ for _ in ()).throw(AssertionError()),
    )
    assert isinstance(result, RetrievalV3PreflightStatus)
    assert result.status == "pending_public_ci"
    assert result.external_provider_calls == 0
    assert result.held_out_executed is False


def admitted_inputs():
    identity = assets.admit_retrieval_hardened_domain_v3_assets(project_root=ROOT, confirm_rules_frozen=True)
    dataset = load_domain_dataset(ROOT / assets.DATASET_PATH)
    plan = load_domain_case_input_plan(ROOT / assets.INPUT_PLAN_PATH, project_root=ROOT, dataset=dataset, expected_max_revisions=1)
    values = dict(
        experiment_id="0" * 64, implementation_sha="a" * 40, public_ci_sha="a" * 40,
        public_ci_scope="offline-test", asset_admission=identity,
        dataset_sha256=gate._digest_json(dataset.model_dump(mode="json")),
        dataset_file_sha256=identity.dataset_file_sha256,
        input_plan_file_sha256=identity.input_plan_file_sha256,
        prompt_context_snapshot_sha256=identity.snapshot_sha256,
        prompt_context_snapshot_file_sha256=identity.snapshot_file_sha256,
        execution_plan=plan.execution_plan, budget_report_sha256=identity.budget_report_sha256,
        budget_report_file_sha256=identity.budget_report_file_sha256,
        protocol_result_sha256="b" * 64, protocol_code_sha="a" * 40,
        protocol_input_tokens=0, protocol_output_tokens=0, protocol_total_tokens=0,
    )
    draft = gate.RetrievalV3DomainAdmission.model_construct(**values)
    values["experiment_id"] = gate._admission_identity(draft)
    return gate.RetrievalV3DomainAdmission(**values), dataset


def test_fresh_gate_executes_three_offline_cases_and_body_free_round_trip():
    admission, dataset = admitted_inputs()
    provider = ScriptedProvider()
    result = gate.run_retrieval_v3_domain_gate(
        admission=admission, dataset=dataset, provider=provider,
        case_executor=PassingExecutor(admission.execution_plan),
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    assert result.admitted
    assert len(provider.requests) == 9
    assert result.admission.case_max_tokens == 205_000
    assert result.resources.max_observed_tokens == 613_000
    assert not result.production_admitted
    encoded = gate.canonical_retrieval_v3_result_bytes(result)
    assert gate.RetrievalV3DomainGateResult.model_validate_json(encoded) == result
    assert b"CINDER_RETRIEVAL_INJECT_97" not in encoded


def test_runtime_dataset_mutation_stops_before_model():
    admission, dataset = admitted_inputs()
    mutated = dataset.model_copy(update={"dataset_version": "9.0.0"})
    provider = ScriptedProvider()
    with pytest.raises(ValueError, match="Dataset content"):
        gate.run_retrieval_v3_domain_gate(
            admission=admission, dataset=mutated, provider=provider,
            case_executor=PassingExecutor(admission.execution_plan),
        )
    assert provider.requests == []


def test_new_gate_rejects_disabled_retrieval_before_model():
    admission, dataset = admitted_inputs()
    provider = ScriptedProvider()
    with pytest.raises(ValueError, match="retrieval hardening"):
        gate.run_retrieval_v3_domain_gate(
            admission=admission, dataset=dataset, provider=provider,
            case_executor=PassingExecutor(admission.execution_plan, retrieval_hardening=False),
        )
    assert provider.requests == []


def test_new_gate_requires_new_protocol_without_reading_environment():
    result = run_retrieval_cli(
        RetrievalV3DomainGateOptions(
            confirm_real_call=False, preflight_only=True,
            implementation_sha="a" * 40, public_ci_sha="a" * 40,
            confirm_public_ci_success=True,
        ), repository_root=ROOT,
        environment_loader=lambda _: pytest.fail("must not read environment"),
        provider_factory=lambda _: pytest.fail("must not construct provider"),
    )
    assert isinstance(result, RetrievalV3PreflightStatus)
    assert result.status == "pending_protocol_evidence"
    assert result.external_provider_calls == 0
