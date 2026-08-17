from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.harness.models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from app.harness.state_machine import advance
from app.harness.store import FileRunStore
from app.product.run_query import RunQueryError, RunQueryService
from app.product.run_receipts import ApiRunReceipt, FileRunReceiptStore
from app.runtime.models import (
    RuntimeArtifactReference,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
)
from app.runtime.recorder import RuntimeRecorder
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    ContextBuiltSignal,
    EvaluationCompletedSignal,
    ExecutionValidatedSignal,
    HarnessTransitionedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RunStartedSignal,
    RuntimeAgentStatus,
    RuntimeAgentStopReason,
    RuntimeEvaluationVerdict,
    RuntimeFailureStage,
    RuntimeHarnessStatus,
    RuntimePublicationStatus,
)
from app.runtime.store import RuntimeTraceStore
from app.runtime.models import RuntimeStatus


NOW = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)
REPORT = "# Verified coach report\n\nOnly these bytes may be returned.\n"


def _identity() -> RuntimeIdentitySnapshot:
    return RuntimeIdentitySnapshot(
        skill_name="recent-form-review",
        skill_version="0.2.0",
        context_contract_version="1.0.0",
        prompt_profile_id="recent-form-review-coach",
        prompt_profile_version="1.0.0",
        provider_id="private-provider",
        provider_model="private-model",
        harness_version="1.0.0",
    )


def _policy() -> RuntimePolicySnapshot:
    return RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=256,
        max_iterations=4,
        max_tool_calls=3,
        timeout_s=30,
        max_context_tokens=16000,
        publish_score_threshold=85,
        max_revisions=1,
        allow_deterministic_fallback=True,
    )


def _manifest(
    root: Path,
    run_id: str,
    publication: RuntimePublicationStatus,
) -> tuple[FileRunStore, dict | None]:
    store = FileRunStore(root, run_id)
    store.create_run(RunManifest.new(run_id, HarnessConfig()))
    final_record = None
    if publication is not RuntimePublicationStatus.REJECTED:
        final_record = store.write_artifact(
            kind=ArtifactKind.FINAL_REPORT,
            relative_path="output/final_report.md",
            content=REPORT,
            schema_version="1.0",
            producer="review_harness.publisher",
        )

    manifest = store.read_manifest()
    reason = {
        RuntimePublicationStatus.PUBLISHED: "quality_gate_passed",
        RuntimePublicationStatus.DEGRADED: "deterministic_fallback",
        RuntimePublicationStatus.REJECTED: "quality_gate_rejected",
    }[publication]
    if publication is RuntimePublicationStatus.PUBLISHED:
        for status in (
            RunStatus.FACTS_READY,
            RunStatus.KNOWLEDGE_READY,
            RunStatus.DRAFT_READY,
            RunStatus.EVALUATING,
            RunStatus.PASSED,
            RunStatus.PUBLISHED,
        ):
            advance(manifest, status, reason=reason if status.is_terminal else None)
        manifest.final_decision = "published"
    elif publication is RuntimePublicationStatus.DEGRADED:
        advance(manifest, RunStatus.FACTS_READY)
        advance(manifest, RunStatus.DEGRADED, reason=reason)
        manifest.final_decision = "deterministic_fallback"
    else:
        advance(manifest, RunStatus.REJECTED, reason=reason)
        manifest.final_decision = "rejected"
    store.write_manifest(manifest)
    return store, final_record


def _trace_reference(
    root: Path,
    run_id: str,
    publication: RuntimePublicationStatus,
    final_record: dict | None,
):
    recorder = RuntimeRecorder(run_id=run_id)
    recorder.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    recorder.emit(
        ExecutionValidatedSignal(input_artifact_sha256s=("a" * 64, "b" * 64))
    )
    recorder.emit(
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=8000,
        )
    )
    reason = {
        RuntimePublicationStatus.PUBLISHED: "quality_gate_passed",
        RuntimePublicationStatus.DEGRADED: "deterministic_fallback",
        RuntimePublicationStatus.REJECTED: "quality_gate_rejected",
    }[publication]
    if publication is RuntimePublicationStatus.REJECTED:
        recorder.emit(
            HarnessTransitionedSignal(
                from_status=RuntimeHarnessStatus.CREATED,
                to_status=RuntimeHarnessStatus.REJECTED,
                revision_count=0,
            )
        )
    else:
        recorder.emit(
            HarnessTransitionedSignal(
                from_status=RuntimeHarnessStatus.CREATED,
                to_status=RuntimeHarnessStatus.FACTS_READY,
                revision_count=0,
            )
        )
        recorder.emit(
            AgentRunTerminatedSignal(
                status=RuntimeAgentStatus.COMPLETED,
                stop_reason=RuntimeAgentStopReason.FINAL_RESPONSE,
                iterations=1,
            )
        )
        if publication is RuntimePublicationStatus.DEGRADED:
            recorder.emit(
                HarnessTransitionedSignal(
                    from_status=RuntimeHarnessStatus.FACTS_READY,
                    to_status=RuntimeHarnessStatus.DEGRADED,
                    revision_count=0,
                )
            )
        else:
            for source, target in (
                (RuntimeHarnessStatus.FACTS_READY, RuntimeHarnessStatus.KNOWLEDGE_READY),
                (RuntimeHarnessStatus.KNOWLEDGE_READY, RuntimeHarnessStatus.DRAFT_READY),
                (RuntimeHarnessStatus.DRAFT_READY, RuntimeHarnessStatus.EVALUATING),
            ):
                recorder.emit(
                    HarnessTransitionedSignal(
                        from_status=source,
                        to_status=target,
                        revision_count=0,
                    )
                )
            recorder.emit(
                EvaluationCompletedSignal(
                    attempt=0,
                    score=91,
                    verdict=RuntimeEvaluationVerdict.PASS,
                )
            )
            for source, target in (
                (RuntimeHarnessStatus.EVALUATING, RuntimeHarnessStatus.PASSED),
                (RuntimeHarnessStatus.PASSED, RuntimeHarnessStatus.PUBLISHED),
            ):
                recorder.emit(
                    HarnessTransitionedSignal(
                        from_status=source,
                        to_status=target,
                        revision_count=0,
                    )
                )

    recorder.emit(
        PublicationDecidedSignal(
            publication_status=publication,
            terminal_reason=reason,
            artifact_sha256s=(
                () if final_record is None else (final_record["sha256"],)
            ),
        )
    )
    recorder.emit(
        RunCompletedSignal(
            publication_status=publication,
            terminal_reason=reason,
        )
    )
    artifacts = ()
    if final_record is not None:
        artifacts = (
            RuntimeArtifactReference(
                kind=final_record["kind"],
                schema_version=final_record["schema_version"],
                relative_path=final_record["path"],
                sha256=final_record["sha256"],
                producer=final_record["producer"],
            ),
        )
    trace = recorder.build_trace(
        identity=_identity(),
        policy=_policy(),
        artifacts=artifacts,
    )
    return RuntimeTraceStore(root, run_id).write_trace(trace)


def _create_terminal_run(
    root: Path,
    *,
    run_id: str = "query_demo",
    publication: RuntimePublicationStatus = RuntimePublicationStatus.PUBLISHED,
) -> tuple[FileRunStore, ApiRunReceipt]:
    store, final_record = _manifest(root, run_id, publication)
    reference = _trace_reference(root, run_id, publication, final_record)
    reason = {
        RuntimePublicationStatus.PUBLISHED: "quality_gate_passed",
        RuntimePublicationStatus.DEGRADED: "deterministic_fallback",
        RuntimePublicationStatus.REJECTED: "quality_gate_rejected",
    }[publication]
    receipt = ApiRunReceipt(
        run_id=run_id,
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=publication,
        terminal_reason=reason,
        trace_reference=reference,
        created_at_utc=NOW,
        report_available=(publication is not RuntimePublicationStatus.REJECTED),
    )
    FileRunReceiptStore(root).write_receipt(receipt)
    return store, receipt


def test_query_returns_allowlisted_run_view_and_verified_report(tmp_path: Path) -> None:
    _, receipt = _create_terminal_run(tmp_path)
    service = RunQueryService(tmp_path)

    view = service.get_run(receipt.run_id)

    assert view.run_id == receipt.run_id
    assert view.runtime_status is RuntimeStatus.COMPLETED
    assert view.publication_status is RuntimePublicationStatus.PUBLISHED
    assert view.skill_name == "recent-form-review"
    assert view.skill_version == "0.2.0"
    assert view.prompt_profile_id == "recent-form-review-coach"
    assert view.prompt_profile_version == "1.0.0"
    assert view.usage.token_observation.value == "not_applicable"
    assert view.report_available is True
    assert service.get_report(receipt.run_id) == REPORT
    public = view.model_dump(mode="json")
    forbidden = (
        "relative_path",
        "provider_id",
        "provider_model",
        "prompt_body",
        "tool_data",
        "artifacts",
    )
    assert not any(key in public for key in forbidden)
    serialized = json.dumps(public, ensure_ascii=False)
    assert "private-provider" not in serialized
    assert "private-model" not in serialized
    assert "final_report.md" not in serialized


def test_rejected_run_never_exposes_a_report(tmp_path: Path) -> None:
    _, receipt = _create_terminal_run(
        tmp_path,
        publication=RuntimePublicationStatus.REJECTED,
    )
    service = RunQueryService(tmp_path)

    assert service.get_run(receipt.run_id).report_available is False
    with pytest.raises(RunQueryError) as caught:
        service.get_report(receipt.run_id)
    assert caught.value.code == "report_not_available"
    assert caught.value.to_public_dict() == {"code": "report_not_available"}


def test_missing_or_unsafe_run_id_is_body_free_not_found(tmp_path: Path) -> None:
    service = RunQueryService(tmp_path)

    for run_id in ("missing_run", "../private", "C:secret"):
        with pytest.raises(RunQueryError) as caught:
            service.get_run(run_id)
        assert caught.value.code == "run_not_found"
        assert str(caught.value) == "run_not_found"
        assert caught.value.__context__ is None


def test_failed_run_without_trace_returns_only_minimal_safe_view(tmp_path: Path) -> None:
    receipt = ApiRunReceipt(
        run_id="failed_before_harness",
        runtime_status=RuntimeStatus.FAILED,
        publication_status=None,
        terminal_reason="context_build_failed",
        trace_reference=None,
        created_at_utc=NOW,
        report_available=False,
    )
    FileRunReceiptStore(tmp_path).write_receipt(receipt)

    view = RunQueryService(tmp_path).get_run(receipt.run_id)

    assert view.runtime_status is RuntimeStatus.FAILED
    assert view.skill_name is None
    assert view.prompt_profile_id is None
    assert view.started_at_utc is None
    assert view.usage is None
    assert view.report_available is False


@pytest.mark.parametrize(
    "tamper",
    (
        "receipt_terminal",
        "trace_bytes",
        "manifest_publication",
        "manifest_reason",
        "duplicate_final",
        "report_bytes",
        "report_utf8",
    ),
)
def test_any_cross_store_tampering_fails_closed(
    tmp_path: Path,
    tamper: str,
) -> None:
    store, receipt = _create_terminal_run(tmp_path)
    receipt_path = tmp_path / receipt.run_id / "api_run_receipt.json"
    trace_path = tmp_path / receipt.run_id / "runtime_trace.json"
    manifest_path = store.manifest_path
    report_path = store.run_directory / "output/final_report.md"

    if tamper == "receipt_terminal":
        payload = json.loads(receipt_path.read_bytes())
        payload["terminal_reason"] = "different_safe_reason"
        receipt_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif tamper == "trace_bytes":
        trace_path.write_text('{"tampered": true}\n', encoding="utf-8")
    elif tamper == "manifest_publication":
        payload = json.loads(manifest_path.read_bytes())
        payload["status"] = "degraded"
        payload["final_decision"] = "deterministic_fallback"
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif tamper == "manifest_reason":
        payload = json.loads(manifest_path.read_bytes())
        payload["transitions"][-1]["reason"] = "different_safe_reason"
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif tamper == "duplicate_final":
        payload = json.loads(manifest_path.read_bytes())
        payload["artifacts"].append(dict(payload["artifacts"][-1]))
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif tamper == "report_bytes":
        report_path.write_text("tampered body", encoding="utf-8")
    else:
        report_path.write_bytes(b"\xff\xfe\x00")

    service = RunQueryService(tmp_path)
    with pytest.raises(RunQueryError) as caught:
        service.get_run(receipt.run_id)
    assert caught.value.code == "run_integrity_failed"
    assert caught.value.to_public_dict() == {"code": "run_integrity_failed"}
    assert "private" not in str(caught.value)
    assert caught.value.__context__ is None


def test_failed_trace_with_no_manifest_is_a_valid_non_report_run(tmp_path: Path) -> None:
    run_id = "failed_trace_no_manifest"
    recorder = RuntimeRecorder(run_id=run_id)
    recorder.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    recorder.emit(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.BOUNDARY,
            failure_code="execution_validation_failed",
            publication_status=None,
        )
    )
    trace = recorder.build_trace(identity=_identity(), policy=_policy())
    reference = RuntimeTraceStore(tmp_path, run_id).write_trace(trace)
    receipt = ApiRunReceipt(
        run_id=run_id,
        runtime_status=RuntimeStatus.FAILED,
        publication_status=None,
        terminal_reason="execution_validation_failed",
        trace_reference=reference,
        created_at_utc=NOW,
        report_available=False,
    )
    FileRunReceiptStore(tmp_path).write_receipt(receipt)

    view = RunQueryService(tmp_path).get_run(run_id)

    assert view.runtime_status is RuntimeStatus.FAILED
    assert view.skill_name == "recent-form-review"
    assert view.report_available is False
