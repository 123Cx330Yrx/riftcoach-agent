"""Offline task execution and crash recovery through real publication files."""
import copy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import socket
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.evidence.publication import EvidencePublicationContext, canonical_bytes
from app.evidence.publication_store import FileEvidencePublicationStore
from app.tasks.fingerprint import (
    compute_conversation_review_task_fingerprint,
    compute_task_request_fingerprint,
)
from app.tasks.models import TaskPublicationMode, TaskTerminal
from app.tasks.recent_review_executor import (
    RecentReviewTaskExecutionError,
    RecentReviewTaskExecutor,
)
from app.tasks.reconciliation import (
    ExpiredReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
    ReviewTaskReconciler,
    TaskTerminalEvidenceError,
)
from app.tasks.reliable_runtime import TaskCheckpointPhase
from tests.test_coach_application_composition import product_request
from tests.test_evidence_publication_store import prepared
from tests.test_evidence_publication import sources
from tests.test_reliable_task_recovery import FakeRecoveryRepository
from tests.test_task_reconciliation import NOW, running_conversation_task, running_task


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("task recovery tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def bound_task(*, schema_version="1.0"):
    task = (
        running_task(payload=product_request().model_dump(mode="json"))
        if schema_version == "1.0" else running_conversation_task()
    )
    mode = TaskPublicationMode.EVIDENCE_BOUND_V1
    if schema_version == "1.0":
        fingerprint = compute_task_request_fingerprint(
            task_kind=task.task_kind, schema_version=task.schema_version,
            request_payload=task.request_payload, publication_mode=mode,
        )
    else:
        fingerprint = compute_conversation_review_task_fingerprint(
            owner_id=task.owner_id, binding=task.conversation_binding,
            request_payload=task.request_payload, publication_mode=mode,
        )
    return task.model_copy(update={
        "publication_mode": mode, "request_fingerprint": fingerprint,
        "checkpoint_reference": task.checkpoint_reference.model_copy(update={
            "phase": TaskCheckpointPhase.EXECUTION_STARTED, "safe_to_replay": False,
        }),
    })


def publication_context(task):
    return EvidencePublicationContext(
        task_id=task.task_id, owner_id=task.owner_id, run_id=task.run_id,
        request_fingerprint=task.request_fingerprint,
    )


def completed_files(tmp_path, *, rejected=False):
    task = bound_task()
    application, deps, store, _ = prepared(tmp_path, rejected=rejected)
    result = application.review(
        product_request(), run_id=task.run_id,
        publication_context=publication_context(task),
    )
    return task, deps, store, result


class EvidenceRecoveryRepository(FakeRecoveryRepository):
    def reconcile_expired_success_with_evidence(self, **kwargs):
        self.calls.append(("reconcile_with_evidence", kwargs))
        return self.accepted


def recover(task, repository, verifier, path):
    now = NOW + timedelta(minutes=10)
    if path == "single":
        return ReviewTaskReconciler(
            repository=repository, verifier=verifier,
        ).reconcile(task, now=now)
    return ExpiredReviewTaskRecovery(
        repository=repository, verifier=verifier,
    ).recover_batch(now=now)[0]


@pytest.mark.parametrize("schema_version", ["1.0", "2.0"])
def test_evidence_mode_fingerprint_reaches_application(schema_version):
    task = bound_task(schema_version=schema_version)
    calls = []
    def entered(request, **kwargs):
        calls.append((request, kwargs))
        raise RuntimeError("stop after task validation")
    application = SimpleNamespace(review=entered, review_by_puuid=entered)
    executor = RecentReviewTaskExecutor(
        application_service=application,
        evidence_verifier=SimpleNamespace(terminal_for=lambda task: None),
    )
    with pytest.raises(RecentReviewTaskExecutionError) as caught:
        executor.execute(task)
    assert caught.value.code == "application_failed"
    assert len(calls) == 1
    assert calls[0][1]["publication_context"] == publication_context(task)


@pytest.mark.parametrize("schema_version", ["1.0", "2.0"])
def test_evidence_mode_rejects_legacy_fingerprint_before_application(schema_version):
    task = bound_task(schema_version=schema_version)
    if schema_version == "1.0":
        fingerprint = compute_task_request_fingerprint(
            task_kind=task.task_kind, schema_version=task.schema_version,
            request_payload=task.request_payload,
        )
    else:
        fingerprint = compute_conversation_review_task_fingerprint(
            owner_id=task.owner_id, binding=task.conversation_binding,
            request_payload=task.request_payload,
        )
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(kwargs)
        raise AssertionError("invalid identity reached application")
    executor = RecentReviewTaskExecutor(
        application_service=SimpleNamespace(review=forbidden, review_by_puuid=forbidden),
        evidence_verifier=SimpleNamespace(terminal_for=forbidden),
    )
    with pytest.raises(RecentReviewTaskExecutionError) as caught:
        executor.execute(task.model_copy(update={"request_fingerprint": fingerprint}))
    assert caught.value.code == "task_fingerprint_mismatch"
    assert not calls


@pytest.mark.parametrize("rejected", [False, True])
def test_executor_returns_verified_file_payload_for_atomic_commit(tmp_path, rejected):
    task = bound_task()
    application, _, store, _ = prepared(tmp_path, rejected=rejected)
    result = RecentReviewTaskExecutor(
        application_service=application,
        evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        runs_root=tmp_path,
    ).execute(task)
    manifest = store.read(publication_context(task))
    assert result.summary_digest == manifest.summary_digest
    assert result.pending_snapshot == store.read_pending_snapshot(publication_context(task))
    assert result.artifact_reference == manifest.report
    assert result.report_available is not rejected
    assert result.terminal_turn is None


def test_executor_rebuilds_file_payload_when_verifier_returns_base_terminal(tmp_path):
    task, _, store, result = completed_files(tmp_path)
    verified = RecentReviewTerminalEvidenceVerifier(tmp_path).terminal_for(task)
    base = TaskTerminal.model_validate(
        verified.model_dump(mode="python", include=set(TaskTerminal.model_fields)),
    )
    output = RecentReviewTaskExecutor(
        application_service=SimpleNamespace(review=lambda *args, **kwargs: result),
        evidence_verifier=SimpleNamespace(terminal_for=lambda task: base),
        runs_root=tmp_path,
    ).execute(task)
    assert output.pending_snapshot == store.read_pending_snapshot(publication_context(task))
    assert output.summary_digest == verified.summary_digest


@pytest.mark.parametrize("field", ["summary_digest", "bundle"])
def test_executor_rejects_application_projection_different_from_verified_files(tmp_path, field):
    task, deps, _, result = completed_files(tmp_path)
    if field == "summary_digest":
        projection = replace(result.evidence_projection, summary_digest="f" * 64)
    else:
        summary = copy.deepcopy(deps["summary_builder"].summary)
        summary["matches"][0]["champion_id"] = 76
        projection = replace(result.evidence_projection,
            bundle=sources().project(summary, routing_region="asia").bundle)
    result = result.model_copy(update={"evidence_projection": projection})
    with pytest.raises(RecentReviewTaskExecutionError) as caught:
        RecentReviewTaskExecutor(
            application_service=SimpleNamespace(review=lambda *args, **kwargs: result),
            evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
            runs_root=tmp_path,
        ).execute(task)
    assert caught.value.code == "terminal_evidence_invalid"


@pytest.mark.parametrize("path", ["single", "batch"])
@pytest.mark.parametrize("rejected", [False, True])
@pytest.mark.parametrize("accepted", [False, True])
def test_files_ready_crash_recovers_atomic_payload_without_model_replay(
    tmp_path, path, rejected, accepted,
):
    task, deps, store, result = completed_files(tmp_path, rejected=rejected)
    requests = tuple(deps["provider"].requests)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in tmp_path.rglob("*") if p.is_file()}
    repository = EvidenceRecoveryRepository((task,), accepted=accepted)
    output = recover(task, repository, RecentReviewTerminalEvidenceVerifier(tmp_path), path)
    assert output.status.value == ("reconciled" if accepted else "ownership_lost")
    assert [name for name, _ in repository.calls] == (
        ["scan", "reconcile_with_evidence"] if path == "batch" else ["reconcile_with_evidence"]
    )
    payload = repository.calls[-1][1]
    manifest = store.read(publication_context(task))
    assert payload["task_id"] == task.task_id
    assert payload["worker_id"] == task.worker_id
    assert payload["lease_generation"] == task.lease.generation
    assert payload["lease_token"] == task.lease.private_token
    assert payload["pending_snapshot"] == store.read_pending_snapshot(publication_context(task))
    assert payload["publication_reference"] == {
        "context": publication_context(task).model_dump(mode="json"),
        "summary_digest": manifest.summary_digest,
    }
    assert payload["summary_digest"] == manifest.summary_digest
    assert payload["terminal"].trace_reference == result.trace_reference
    assert payload["terminal"].artifact_reference == manifest.report
    assert payload["terminal"].report_available is not rejected
    assert tuple(deps["provider"].requests) == requests
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("filename", [
    "evidence_publication_manifest.json", "evidence_bundle.json",
    "api_run_receipt.json", "runtime_trace.json", "manifest.json",
    "inputs/player_summary.json", "report",
])
@pytest.mark.parametrize("path", ["single", "batch"])
def test_damaged_files_cannot_publish_or_replay_model(tmp_path, filename, path):
    task, deps, store, _ = completed_files(tmp_path)
    requests = tuple(deps["provider"].requests)
    manifest = store.read(publication_context(task))
    target = tmp_path / task.run_id / (
        manifest.report.relative_path if filename == "report" else filename
    )
    target.write_bytes(b'{"private":')
    repository = EvidenceRecoveryRepository((task,))
    output = recover(task, repository, RecentReviewTerminalEvidenceVerifier(tmp_path), path)
    assert output.status.value == "recovery_required"
    assert [name for name, _ in repository.calls] == (["scan", "required"] if path == "batch" else [])
    assert tuple(deps["provider"].requests) == requests


@pytest.mark.parametrize("field,value", [
    ("owner_id", "other-owner"),
    ("task_id", "70000000-0000-4000-8000-000000000001"),
    ("run_id", "other-run"),
    ("request_fingerprint", "f" * 64),
    ("summary_digest", "f" * 64),
    ("bundle_digest", "f" * 64),
])
def test_foreign_or_rehashed_manifest_cannot_recover(tmp_path, field, value):
    task, _, store, _ = completed_files(tmp_path)
    target = tmp_path / task.run_id / store.filename
    manifest = json.loads(target.read_bytes())
    if field == "summary_digest":
        manifest[field] = value
    elif field == "bundle_digest":
        manifest["bundle"][field] = value
    else:
        manifest["context"][field] = value
    target.write_bytes(canonical_bytes(manifest))
    with pytest.raises(TaskTerminalEvidenceError) as caught:
        RecentReviewTerminalEvidenceVerifier(tmp_path).terminal_for(task)
    assert caught.value.code == "terminal_evidence_invalid"


@pytest.mark.parametrize("field,value", [
    ("owner_id", "other-owner"),
    ("task_id", UUID("70000000-0000-4000-8000-000000000001")),
    ("run_id", "other-run"),
])
def test_pending_snapshot_identity_change_fails_closed(tmp_path, monkeypatch, field, value):
    task, _, _, _ = completed_files(tmp_path)
    original = FileEvidencePublicationStore.read_pending_snapshot
    def changed(store, context):
        return original(store, context).model_copy(update={field: value})
    monkeypatch.setattr(FileEvidencePublicationStore, "read_pending_snapshot", changed)
    with pytest.raises(TaskTerminalEvidenceError) as caught:
        RecentReviewTerminalEvidenceVerifier(tmp_path).terminal_for(task)
    assert caught.value.code == "terminal_evidence_invalid"


def test_valid_alternative_bundle_between_reads_fails_closed(tmp_path, monkeypatch):
    task, deps, _, _ = completed_files(tmp_path)
    summary = copy.deepcopy(deps["summary_builder"].summary)
    summary["matches"][0]["champion_id"] = 76
    replacement = sources().project(summary, routing_region="asia").bundle
    assert replacement.has_valid_digest()
    original = FileEvidencePublicationStore.read_pending_snapshot
    def changed(store, context):
        return original(store, context).model_copy(update={"bundle": replacement})
    monkeypatch.setattr(FileEvidencePublicationStore, "read_pending_snapshot", changed)
    with pytest.raises(TaskTerminalEvidenceError) as caught:
        RecentReviewTerminalEvidenceVerifier(tmp_path).terminal_for(task)
    assert caught.value.code == "terminal_evidence_invalid"


def test_cancelled_expired_evidence_task_skips_files_and_atomic_commit(tmp_path):
    task, _, _, _ = completed_files(tmp_path)
    task = task.model_copy(update={
        "cancel_request_id": "cancel-1", "cancel_requested_at": task.claimed_at,
        "cancel_reason": "user_requested",
    })
    def forbidden(*args):
        raise AssertionError("cancelled task must not read files")
    repository = EvidenceRecoveryRepository((task,))
    output = recover(task, repository, SimpleNamespace(terminal_for=forbidden), "batch")
    assert output.status.value == "cancelled"
    assert [name for name, _ in repository.calls] == ["scan", "cancel"]
