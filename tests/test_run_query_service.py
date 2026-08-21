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
PLAYER_SUMMARY = {
    "schema_version": "1.0",
    "metadata": {
        "generated_at_utc": "2026-08-21T00:00:00+00:00",
        "source": "synthetic_fixture",
        "matches_requested": 2,
        "matches_received": 2,
        "matches_analyzed": 2,
    },
    "player": {
        "game_name": "PrivateName",
        "tag_line": "PRIVATE",
        "riot_id": "PrivateName#PRIVATE",
        "puuid_prefix": "private-puuid...",
    },
    "request": {"count": 2, "queue": 420, "region": "asia"},
    "recent_summary": {
        "games_analyzed": 2,
        "wins": 1,
        "losses": 1,
        "win_rate": 50.0,
        "main_role": "MIDDLE",
        "main_champions": ["ChampionA", "ChampionB"],
        "averages": {
            "kda": 3.0,
            "cs_per_min": 8.5,
            "gold_per_min": 430.0,
            "damage_per_min": 700.0,
            "vision_score": 20.0,
            "kill_participation_percent": 50.0,
            "damage_share_percent": 25.0,
            "gold_share_percent": 22.0,
            "deaths_before_15": 0.5,
        },
        "win_loss_comparison": {
            "wins": {
                "cs_per_min": 9.0,
                "gold_per_min": 460.0,
                "damage_per_min": 760.0,
                "vision_score": 24.0,
                "deaths_before_15": 0.0,
            },
            "losses": {
                "cs_per_min": 8.0,
                "gold_per_min": 400.0,
                "damage_per_min": 640.0,
                "vision_score": 16.0,
                "deaths_before_15": 1.0,
            },
        },
    },
    "matches": [
        {
            "match_id": "PRIVATE_MATCH_1",
            "game_duration_seconds": 1800,
            "champion_id": 1,
            "champion_name": "ChampionA",
            "role": "MIDDLE",
            "win": True,
            "timeline_status": "available",
            "included_in_aggregate": True,
        },
        {
            "match_id": "PRIVATE_MATCH_2",
            "game_duration_seconds": 1800,
            "champion_id": 2,
            "champion_name": "ChampionB",
            "role": "MIDDLE",
            "win": False,
            "timeline_status": "available",
            "included_in_aggregate": True,
        },
    ],
    "failed_matches": [],
    "excluded_matches": [],
}


def _identity(
    skill_name: str = "recent-form-review",
) -> RuntimeIdentitySnapshot:
    skill_version = "0.1.0" if skill_name == "single-match-review" else "0.2.0"
    return RuntimeIdentitySnapshot(
        skill_name=skill_name,
        skill_version=skill_version,
        context_contract_version="1.0.0",
        prompt_profile_id=f"{skill_name}-coach",
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
    *,
    player_summary: dict | None = None,
) -> tuple[FileRunStore, dict | None, dict | None]:
    store = FileRunStore(root, run_id)
    store.create_run(RunManifest.new(run_id, HarnessConfig()))
    player_record = None
    if player_summary is not None:
        player_record = store.write_artifact(
            kind=ArtifactKind.PLAYER_SUMMARY,
            relative_path="inputs/player_summary.json",
            content=(
                json.dumps(
                    player_summary,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            ),
            schema_version="1.0",
            producer="review_harness.input",
        )
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
    return store, final_record, player_record


def _trace_reference(
    root: Path,
    run_id: str,
    publication: RuntimePublicationStatus,
    final_record: dict | None,
    *,
    player_record: dict | None = None,
    skill_name: str = "recent-form-review",
    validated_player_digest: str | None = None,
):
    recorder = RuntimeRecorder(run_id=run_id)
    recorder.emit(
        RunStartedSignal(
            skill_name=skill_name,
            skill_version=(
                "0.1.0" if skill_name == "single-match-review" else "0.2.0"
            ),
            runtime_policy_version="1.0.0",
        )
    )
    input_digests = (
        (validated_player_digest or player_record["sha256"], "b" * 64)
        if player_record is not None
        else ("a" * 64, "b" * 64)
    )
    recorder.emit(ExecutionValidatedSignal(input_artifact_sha256s=input_digests))
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
    artifact_records = tuple(
        record for record in (player_record, final_record) if record is not None
    )
    artifacts = tuple(
        RuntimeArtifactReference(
            kind=record["kind"],
            schema_version=record["schema_version"],
            relative_path=record["path"],
            sha256=record["sha256"],
            producer=record["producer"],
        )
        for record in artifact_records
    )
    trace = recorder.build_trace(
        identity=_identity(skill_name),
        policy=_policy(),
        artifacts=artifacts,
    )
    return RuntimeTraceStore(root, run_id).write_trace(trace)


def _create_terminal_run(
    root: Path,
    *,
    run_id: str = "query_demo",
    publication: RuntimePublicationStatus = RuntimePublicationStatus.PUBLISHED,
    player_summary: dict | None = None,
    skill_name: str = "recent-form-review",
    validated_player_digest: str | None = None,
) -> tuple[FileRunStore, ApiRunReceipt]:
    store, final_record, player_record = _manifest(
        root,
        run_id,
        publication,
        player_summary=player_summary,
    )
    reference = _trace_reference(
        root,
        run_id,
        publication,
        final_record,
        player_record=player_record,
        skill_name=skill_name,
        validated_player_digest=validated_player_digest,
    )
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


def test_query_projects_verified_recent_summary_without_private_identity(
    tmp_path: Path,
) -> None:
    _, receipt = _create_terminal_run(
        tmp_path,
        player_summary=PLAYER_SUMMARY,
    )

    view = RunQueryService(tmp_path).get_recent_summary(receipt.run_id)

    assert view.run_id == receipt.run_id
    assert view.skill_name == "recent-form-review"
    assert view.publication_status is RuntimePublicationStatus.PUBLISHED
    assert view.games_analyzed == 2
    assert view.wins == 1
    assert view.losses == 1
    assert view.win_rate == 50.0
    assert view.main_role == "MIDDLE"
    assert view.main_champions == ("ChampionA", "ChampionB")
    assert view.averages.kda == 3.0
    assert view.win_loss_comparison.wins.cs_per_min == 9.0
    serialized = view.model_dump_json()
    for forbidden in (
        "PrivateName",
        "PRIVATE",
        "private-puuid",
        "PRIVATE_MATCH",
        "player",
        "relative_path",
        "final_report",
    ):
        assert forbidden not in serialized


def test_query_projects_single_match_publication_identity_without_report_body(
    tmp_path: Path,
) -> None:
    _, receipt = _create_terminal_run(
        tmp_path,
        skill_name="single-match-review",
    )

    view = RunQueryService(tmp_path).get_single_match_review(receipt.run_id)

    assert view.run_id == receipt.run_id
    assert view.skill_name == "single-match-review"
    assert view.skill_version == "0.1.0"
    assert view.publication_status is RuntimePublicationStatus.PUBLISHED
    assert view.review_available is True
    assert len(view.review_sha256) == 64
    serialized = view.model_dump_json()
    assert REPORT.strip() not in serialized
    assert "final_report.md" not in serialized


@pytest.mark.parametrize(
    ("method_name", "skill_name"),
    (
        ("get_recent_summary", "single-match-review"),
        ("get_single_match_review", "recent-form-review"),
    ),
)
def test_safe_business_projection_rejects_skill_identity_mismatch(
    tmp_path: Path,
    method_name: str,
    skill_name: str,
) -> None:
    _, receipt = _create_terminal_run(
        tmp_path,
        player_summary=PLAYER_SUMMARY,
        skill_name=skill_name,
    )

    with pytest.raises(RunQueryError) as caught:
        getattr(RunQueryService(tmp_path), method_name)(receipt.run_id)
    assert caught.value.code == "run_integrity_failed"


def test_recent_summary_requires_publication_and_verified_player_artifact(
    tmp_path: Path,
) -> None:
    _, rejected = _create_terminal_run(
        tmp_path,
        run_id="query_rejected_summary",
        publication=RuntimePublicationStatus.REJECTED,
        player_summary=PLAYER_SUMMARY,
    )
    service = RunQueryService(tmp_path)
    with pytest.raises(RunQueryError) as unavailable:
        service.get_recent_summary(rejected.run_id)
    assert unavailable.value.code == "report_not_available"

    store, published = _create_terminal_run(
        tmp_path,
        run_id="query_tampered_summary",
        player_summary=PLAYER_SUMMARY,
    )
    (store.run_directory / "inputs" / "player_summary.json").write_text(
        '{"schema_version":"1.0","player":{"puuid":"leaked"}}',
        encoding="utf-8",
    )
    with pytest.raises(RunQueryError) as tampered:
        service.get_recent_summary(published.run_id)
    assert tampered.value.code == "run_integrity_failed"


def test_degraded_recent_summary_remains_explicit_and_available(tmp_path: Path) -> None:
    _, receipt = _create_terminal_run(
        tmp_path,
        publication=RuntimePublicationStatus.DEGRADED,
        player_summary=PLAYER_SUMMARY,
    )

    view = RunQueryService(tmp_path).get_recent_summary(receipt.run_id)

    assert view.publication_status is RuntimePublicationStatus.DEGRADED
    assert view.terminal_reason == "deterministic_fallback"


@pytest.mark.parametrize("tamper", ("manifest_identity", "input_commitment"))
def test_recent_summary_rejects_manifest_trace_or_input_binding_drift(
    tmp_path: Path,
    tamper: str,
) -> None:
    store, receipt = _create_terminal_run(
        tmp_path,
        player_summary=PLAYER_SUMMARY,
        validated_player_digest=("c" * 64 if tamper == "input_commitment" else None),
    )
    if tamper == "manifest_identity":
        payload = json.loads(store.manifest_path.read_bytes())
        summary_record = next(
            record
            for record in payload["artifacts"]
            if record["kind"] == ArtifactKind.PLAYER_SUMMARY.value
        )
        summary_record["producer"] = "untrusted.writer"
        store.manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    with pytest.raises(RunQueryError) as caught:
        RunQueryService(tmp_path).get_recent_summary(receipt.run_id)
    assert caught.value.code == "run_integrity_failed"


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
