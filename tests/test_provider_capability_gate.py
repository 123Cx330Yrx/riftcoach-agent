from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.provider_capability_gate import (
    CapabilityProbeCaseResult,
    CapabilityProbeReport,
    ExternalCallBudget,
    ExternalCallBudgetExceeded,
)
from app.evaluation.provider_adapter_protocol import AdapterProtocolSliceReport
from app.evaluation.provider_domain_skill import DomainSkillSliceReport
from app.evaluation.provider_domain_experiment import (
    ProviderDomainExperimentRecord,
)
from app.evaluation.provider_domain_readmission import (
    FreshProviderDomainExperimentRecord,
)
from app.evaluation.provider_protocol_experiment import (
    ProviderAdapterProtocolExperimentRecord,
)
from app.evaluation.provider_resource_calibration import (
    RealResourceCalibrationResult,
    ResourceCalibrationAdjudication,
    V3ResourceBudgetRecord,
)
from app.evaluation.glm53_flash_capability_matrix import (
    GLM53FlashCapabilityMatrixReport,
)
from app.evaluation.glm53_flash_tool_stream_followup import (
    ToolStreamFollowupReport,
)
from app.evaluation.glm53_domain_gate import GLM53FreshDomainResult


DEEPSEEK_V4_PRO_PROTOCOL_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)
DEEPSEEK_V4_PRO_PROTOCOL_RESULT_SHA256 = (
    "575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1"
)
DEEPSEEK_V4_PRO_DOMAIN_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_heldout.json"
)
DEEPSEEK_V4_PRO_DOMAIN_RESULT_SHA256 = (
    "fbd1251af98daa9e767de56a35100025807ce96026d6b3b3497e33dd30ad989e"
)


def passed_case(case_id: str) -> CapabilityProbeCaseResult:
    return CapabilityProbeCaseResult(
        case_id=case_id,
        capability="text_chat",
        status="passed",
        error_code=None,
        response_received=True,
        content_state="non_empty",
        reasoning_content_state="missing",
        latency_ms=12,
        input_tokens=3,
        output_tokens=2,
        finish_reason="stop",
        resolved_model="glm-test-resolved",
        request_id_sha256="c" * 64,
        tool_call_count=0,
        repair_count=0,
        output_sha256="a" * 64,
    )


def test_case_result_is_strict_and_rejects_inconsistent_status() -> None:
    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            **passed_case("P1_text_baseline").model_dump(),
            unknown="not-allowed",
        )

    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            case_id="P2_structured_pass",
            capability="structured_output",
            status="failed",
            error_code=None,
            latency_ms=1,
            input_tokens=0,
            output_tokens=0,
            tool_call_count=0,
            repair_count=0,
        )

    with pytest.raises(ValidationError):
        CapabilityProbeCaseResult(
            case_id="P2_structured_pass",
            capability="structured_output",
            status="passed",
            error_code="unexpected",
            latency_ms=-1,
            input_tokens=-1,
            output_tokens=0,
            tool_call_count=0,
            repair_count=0,
            output_sha256="bad",
        )


def test_probe_report_rejects_duplicate_cases_and_wrong_admission() -> None:
    cases = [passed_case(case_id) for case_id in (
        "P1_text_baseline",
        "P2_structured_pass",
        "P3_structured_issue",
        "P4_tool_request",
        "P5_tool_final",
    )]
    report = CapabilityProbeReport(
        provider_id="zhipu",
        requested_model="glm-test",
        code_sha="b" * 40,
        documentation_snapshot_date="2026-08-09",
        run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
        max_calls=5,
        calls_used=5,
        admitted=True,
        cases=cases,
    )
    assert report.admitted is True

    with pytest.raises(ValidationError):
        CapabilityProbeReport(
            provider_id="zhipu",
            requested_model="glm-test",
            code_sha="b" * 40,
            documentation_snapshot_date="2026-08-09",
            run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
            max_calls=5,
            calls_used=5,
            admitted=True,
            cases=[cases[0], cases[0]],
        )

    with pytest.raises(ValidationError):
        CapabilityProbeReport(
            provider_id="zhipu",
            requested_model="glm-test",
            code_sha="b" * 40,
            documentation_snapshot_date="2026-08-09",
            run_timestamp_utc=datetime(2026, 8, 9, tzinfo=timezone.utc),
            max_calls=5,
            calls_used=4,
            admitted=True,
            cases=cases[:-1],
        )


def test_external_call_budget_counts_attempts_and_stops_before_sixth() -> None:
    budget = ExternalCallBudget(max_calls=5)
    calls: list[int] = []

    for index in range(5):
        assert budget.run(lambda value: calls.append(value) or value, index) == index

    with pytest.raises(ExternalCallBudgetExceeded):
        budget.run(lambda: calls.append(99))

    assert calls == [0, 1, 2, 3, 4]
    assert budget.calls_used == 5


def test_executed_failure_consumes_budget_but_rejected_call_does_not() -> None:
    budget = ExternalCallBudget(max_calls=1)

    with pytest.raises(RuntimeError, match="upstream"):
        budget.run(lambda: (_ for _ in ()).throw(RuntimeError("upstream")))
    assert budget.calls_used == 1

    with pytest.raises(ExternalCallBudgetExceeded):
        budget.run(lambda: "never")
    assert budget.calls_used == 1


def test_v10_result_remains_readable_with_unknown_observation() -> None:
    result_path = Path(
        "data/evaluation/results/provider_capabilities/zhipu_glm52_p1_p5.json"
    )

    report = CapabilityProbeReport.model_validate_json(
        result_path.read_text(encoding="utf-8")
    )

    assert report.schema_version == "1.0"
    assert report.probe_scope == "p1_p5"
    assert report.cases[0].response_received is None
    assert report.cases[0].content_state == "not_observed"
    assert report.cases[0].reasoning_content_state == "not_observed"


def test_all_public_provider_capability_results_match_versioned_contract() -> None:
    result_root = Path("data/evaluation/results/provider_capabilities")
    result_paths = sorted(result_root.glob("*.json"))

    assert result_paths
    for result_path in result_paths:
        content = result_path.read_text(encoding="utf-8")
        payload = json.loads(content)
        if {
            "calibration_experiment_id",
            "calibration_result_sha256",
            "usage_complete",
        }.issubset(payload):
            model = ResourceCalibrationAdjudication
        elif {
            "calibration_experiment_id",
            "calibration_result_sha256",
            "decision",
        }.issubset(payload):
            model = V3ResourceBudgetRecord
        elif {
            "experiment_id",
            "admission",
            "request_set_sha256",
            "v3_budget_derivation_ready",
        }.issubset(payload):
            model = RealResourceCalibrationResult
        elif {
            "admission",
            "domain_result",
            "explicit_real_call_confirmed",
        }.issubset(payload):
            model = FreshProviderDomainExperimentRecord
        elif {
            "preparation",
            "protocol",
            "resources",
            "control",
        }.issubset(payload):
            model = ProviderAdapterProtocolExperimentRecord
        elif {
            "preparation",
            "prior_protocol",
            "execution_plan",
            "cases",
        }.issubset(payload):
            model = ProviderDomainExperimentRecord
        elif {
            "experiment_id",
            "admission",
            "resources",
            "control",
            "protocol_calls",
            "domain_calls_used",
            "cumulative_calls_used",
        }.issubset(payload):
            model = GLM53FreshDomainResult
        elif payload.get("experiment_name") == (
            "g53-5-fresh-flash-capability-matrix-v1"
        ):
            model = GLM53FlashCapabilityMatrixReport
        elif payload.get("experiment_name") == (
            "g53-5-fresh-flash-tool-stream-followup-v1"
        ):
            model = ToolStreamFollowupReport
        else:
            model = {
                "adapter_protocol": AdapterProtocolSliceReport,
                "recent_form_domain": DomainSkillSliceReport,
            }.get(payload.get("probe_scope", "p1_p5"), CapabilityProbeReport)
        model.model_validate_json(content)


def test_deepseek_v4_pro_real_protocol_result_is_immutable_and_admitted() -> None:
    raw = DEEPSEEK_V4_PRO_PROTOCOL_RESULT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        DEEPSEEK_V4_PRO_PROTOCOL_RESULT_SHA256
    )

    record = ProviderAdapterProtocolExperimentRecord.model_validate_json(raw)

    assert record.preparation.code_sha == (
        "076a5e3558cd68abb545cebdc2542c973b020768"
    )
    assert record.protocol.admitted is True
    assert record.protocol.calls_used == 3
    assert [case.status for case in record.protocol.cases] == ["passed", "passed"]
    assert record.resources.total_tokens == 1428
    assert str(record.resources.estimated_cost) == "0.00221496"
    assert record.control.global_stop is None
    assert record.control.provider_stops == ()
    assert record.held_out_executed is False


def test_deepseek_v4_pro_real_domain_result_is_immutable_and_rejected() -> None:
    raw = DEEPSEEK_V4_PRO_DOMAIN_RESULT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        DEEPSEEK_V4_PRO_DOMAIN_RESULT_SHA256
    )
    serialized = raw.decode("utf-8")
    for forbidden in (
        "DEEPSEEK_API_KEY",
        "USER_INJECTION_ACCEPTED",
        "KNOWLEDGE_INJECTION_ACCEPTED",
        "忽略既有规则",
        "deepseek-request-",
    ):
        assert forbidden not in serialized

    record = ProviderDomainExperimentRecord.model_validate_json(raw)

    assert record.preparation.code_sha == (
        "205397f0bd87a53291b8a2c62487a8b6d966fdb1"
    )
    assert record.held_out_executed is True
    assert record.admitted is False
    assert record.domain_calls_used == 1
    assert record.domain_total_tokens == 0
    assert str(record.domain_estimated_cost) == "0.00"
    assert record.resources.calls_used == 4
    assert record.resources.total_tokens == 1428
    assert record.control.global_stop is None
    assert [
        (row.provider_id, row.failure_code.value)
        for row in record.control.provider_stops
    ] == [("deepseek", "provider_response_invalid")]
    assert [row.status for row in record.cases] == [
        "executed",
        "skipped",
        "skipped",
    ]
    first = record.cases[0]
    assert first.observation is not None
    assert first.observation.safe_provider_error_code == (
        "unsupported_parallel_tool_calls"
    )
    assert first.observation.normalized_response_count == 0
    assert first.observation.agent_status == "failed"
    assert first.observation.agent_stop_reason == "provider_error"
    assert first.observation.proposed_tool_names == ()
    assert first.observation.successful_tool_names == ()
    assert first.observation.evidence_source_ids == ()
    assert first.observation.terminal_status == "degraded"
    assert first.observation.terminal_reason == "draft_preparation_failed"
    assert record.candidate is None
    assert record.evaluation is None


def test_v11_requires_explicit_consistent_response_observation() -> None:
    case = passed_case("P1_text_baseline").model_dump()
    case.pop("response_received")
    case.pop("content_state")
    case.pop("reasoning_content_state")

    with pytest.raises(ValidationError, match="response_received"):
        CapabilityProbeReport(
            schema_version="1.1",
            probe_scope="p1_diagnostic",
            provider_id="zhipu",
            requested_model="glm-test",
            code_sha="b" * 40,
            documentation_snapshot_date="2026-08-10",
            run_timestamp_utc=datetime(2026, 8, 10, tzinfo=timezone.utc),
            max_calls=1,
            calls_used=1,
            admitted=False,
            cases=[case],
        )

    case.update(
        response_received=True,
        content_state="non_empty",
        reasoning_content_state="missing",
    )
    report = CapabilityProbeReport(
        schema_version="1.1",
        probe_scope="p1_diagnostic",
        provider_id="zhipu",
        requested_model="glm-test",
        code_sha="b" * 40,
        documentation_snapshot_date="2026-08-10",
        run_timestamp_utc=datetime(2026, 8, 10, tzinfo=timezone.utc),
        max_calls=1,
        calls_used=1,
        admitted=False,
        cases=[case],
    )
    assert report.admitted is False


def test_skipped_case_rejects_claimed_response_observation() -> None:
    with pytest.raises(ValidationError, match="skipped"):
        CapabilityProbeCaseResult(
            case_id="P2_structured_pass",
            capability="structured_output",
            status="skipped",
            error_code="p1_baseline_failed",
            response_received=True,
            content_state="null",
            reasoning_content_state="missing",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            tool_call_count=0,
            repair_count=0,
        )
