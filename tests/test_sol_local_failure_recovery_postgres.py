"""Real SQL lifecycle and Worker replay; external model receipts are scripted."""
import json
from pathlib import Path
from uuid import UUID

import pytest

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import CapacityBridgeObservation, RESPONSE
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, digest, tree
from app.harness.store import FileRunStore
from app.persistence.task_continuations import PostgresTaskContinuations
from app.product import sol_contract as product
from app.product.local_failure_recovery import prepare_local_failure_recovery, verify_local_failure_recovery
from app.runtime.sol_session_receipts import request_from_raw
from app.tasks.continuation import ContinuationError, ResumeContinuation
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, setup_worker


def receipt_stub(session, value):
    """The fake provider returns through the real journal/checkpoint boundary."""
    request = request_from_raw(value["issued_raw"])
    response = RESPONSE.validate_json(value["response_raw"])
    ordinal = value["budget"]["calls"]
    folder = session.transport_root / "generation"
    stream = folder / f"stream-{ordinal:03d}"
    stream.mkdir(parents=True, exist_ok=True)
    raw = product.request_bytes(request)
    (folder / f"request-{ordinal:03d}.json").write_bytes(raw)
    (folder / f"response-{ordinal:03d}.json").write_bytes(value["response_raw"].encode())
    attempt = value["budget"]["attempts"][-1]
    identity = dict(ordinal=ordinal, role="generation", provider=response.provider, model=response.model,
        thinking_profile_id=attempt["profile"], transport_id=attempt["transport_id"],
        request_sha256=digest(raw), raw_directory="generation")
    for name, data in (
        (f"call-{ordinal:03d}.json", dict(identity, state="reserved_before_io")),
        (f"call-result-{ordinal:03d}.json", dict(identity, state="complete",
            response_sha256=digest(value["response_raw"].encode()),
            input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))):
        path = session.transport_root / name
        # The routed stub may already have emitted the identical call receipt.
        if path.exists():
            assert json.loads(path.read_bytes()) == data
        else:
            write_new_json(path, data)
    write_new_json(stream / "reservation.json", dict(identity, stream_tool_arguments=bool(request.tools)))
    write_new_json(stream / "result.json", dict(state="complete", transport_id=attempt["transport_id"], elapsed_ms=1))
    write_new_json(stream / "progress.json", CapacityBridgeObservation(state="complete", close_state="closed",
        http_requests=1, eof_ms=1, close_ms=1, terminal_ms=1,
        input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens).model_dump())


@pytest.fixture
def failed_local(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo,
        contract=product, profile=product.WORKER_PROFILE)
    operation = CandidateSession.operation
    def observed(self, kind, request, action):
        def wrapped():
            value = action()
            if kind == "model":
                receipt_stub(self, value)
            return value
        return operation(self, kind, request, wrapped)
    write = FileRunStore.write_artifact
    def fail_storage(self, **kwargs):
        if str(kwargs["relative_path"]) == "knowledge/retrieval_evidence.json":
            raise FileNotFoundError("scripted local artifact write failure")
        return write(self, **kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(CandidateSession, "operation", observed)
        scoped.setattr(FileRunStore, "write_artifact", fail_storage)
        worker, _ = make()
        result = worker.run_once()
        assert result.status.value == "failed", result
    store = PostgresTaskContinuations(repo)
    reference = store.load(owner_id="owner-1", task_id=UUID(task))
    assert requests == [[]] and summary.reads == 1
    assert reference["accounting"]["known_tokens"] == 40
    yield dict(task=UUID(task), run=run, repo=repo, store=store, reference=reference,
               parent=tmp_path / run, root=tmp_path / "recovered", original=tree(tmp_path / run))


def prepare(case):
    return prepare_local_failure_recovery(parent_run=case["parent"],
        destination_root=case["root"], reference=case["reference"])


def adopt(case, proof, sha, owner="owner-1"):
    return case["store"].recover_local_failure(owner_id=owner, task_id=case["task"],
        proof_path=proof, proof_sha256=sha, runs_root=str(case["root"]))


@pytest.fixture
def draft_rejected(continued_api, tmp_path, monkeypatch):
    from app.product import sol_chat_contract as chat
    from app.report_validation import ReportValidationError
    from app.tasks.service import ReviewTaskService, CreateReviewTaskCommand
    from app.product.recent_review import RecentReviewProductRequest
    from app.tasks.models import TaskPublicationMode
    owner, _, repo, _ = continued_api
    created = ReviewTaskService(repository=repo).create(CreateReviewTaskCommand(
        owner_id="owner-1", idempotency_key="draft-heading-evidence",
        request=RecentReviewProductRequest(riot_id="DemoPlayer#TEST", routing_region="asia", focus="overall"),
        publication_mode=TaskPublicationMode.EVIDENCE_BOUND_V1))
    task, run = str(created.task.task_id), created.task.run_id
    make, _, _, requests = setup_worker(tmp_path, monkeypatch, repo,
        contract=chat, profile=chat.WORKER_PROFILE)
    original = CandidateSession.operation
    def observed(self, kind, request, action):
        def wrapped():
            value = action()
            if kind == "model":
                receipt_stub(self, value)
            return value
        return original(self, kind, request, wrapped)
    def reject(*args):
        raise ReportValidationError("report_missing_headings", "scripted old heading guard")
    with monkeypatch.context() as patch:
        patch.setattr(CandidateSession, "operation", observed)
        patch.setattr("app.runtime.runtime.guard_coach_draft", reject)
        worker, _ = make()
        assert worker.run_once().status.value == "succeeded"
    store = PostgresTaskContinuations(repo)
    reference = store.load(owner_id="owner-1", task_id=UUID(task))
    assert requests == [[]]
    assert repo.get_by_task_id(owner_id="owner-1", task_id=UUID(task)).terminal_reason == "draft_safety_failed"
    return dict(task=UUID(task), run=run, repo=repo, store=store, reference=reference,
                parent=tmp_path / run, root=tmp_path / "draft-recovered", original=tree(tmp_path / run))


def adopt_draft(c, proof, sha, owner="owner-1"):
    return c["store"].recover_draft_guard_rejection(owner_id=owner, task_id=c["task"],
        proof_path=proof, proof_sha256=sha, runs_root=str(c["root"]))


def test_draft_recovery_replays_success_to_first_review_and_keeps_terminal(draft_rejected, monkeypatch):
    from app.product import draft_guard_recovery as recovery, sol_chat_contract as chat
    c = draft_rejected
    proof, sha = recovery.prepare(parent_run=c["parent"], destination_root=c["root"], reference=c["reference"])
    with pytest.raises(ContinuationError, match="task_not_found"):
        adopt_draft(c, proof, sha, "owner-2")
    assert adopt_draft(c, proof, sha)["status"] == "recovery_required"
    assert adopt_draft(c, proof, sha)["replayed"]
    saved = c["store"].load(owner_id="owner-1", task_id=c["task"])
    assert saved["draft_guard_recovery"]["terminal_reason"] == "draft_safety_failed"
    with pytest.raises(ContinuationError, match="conflict"):
        c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="stale",
            command=ResumeContinuation(checkpoint_sha256=c["reference"]["checkpoint_sha256"]))
    c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="recovered",
        command=ResumeContinuation(checkpoint_sha256=saved["checkpoint_sha256"]))
    make, source, factories, requests = setup_worker(c["root"], monkeypatch, c["repo"],
        contract=chat, profile=chat.WORKER_PROFILE)
    worker, executor = make()
    executor.candidate.max_new_models = 0
    assert worker.run_once().status.value == "paused"
    at_boundary = c["store"].load(owner_id="owner-1", task_id=c["task"])
    assert at_boundary["accounting"] == c["reference"]["accounting"]
    assert requests == [[]] and source.reads == 0
    assert all(not p.generator.requests for f in factories for p in f.providers.values())
    c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="scripted-reviews",
        command=ResumeContinuation(checkpoint_sha256=at_boundary["checkpoint_sha256"]))
    worker, _ = make()
    assert worker.run_once().status.value == "succeeded"
    assert requests == [[], [200, 200]]
    assert c["repo"].get_by_task_id(owner_id="owner-1", task_id=c["task"]).report_available
    from sqlalchemy import text
    with c["repo"]._session_factory() as session:
        snapshots = session.execute(text("SELECT refresh_id FROM evidence_bundle_snapshots WHERE run_id=:run"),
                                    {"run": c["run"]}).scalars().all()
    assert set(snapshots) == {"publication-1", "publication-recovery-" + sha}
    assert tree(c["parent"]) == c["original"]
    assert adopt_draft(c, proof, sha)["replayed"]


@pytest.mark.parametrize("mutation", ["parent", "child", "proof"])
def test_draft_recovery_rejects_changed_evidence(draft_rejected, mutation):
    from app.product import draft_guard_recovery as recovery
    c = draft_rejected
    proof, sha = recovery.prepare(parent_run=c["parent"], destination_root=c["root"], reference=c["reference"])
    path = {"parent": c["parent"] / "api_run_receipt.json", "proof": proof,
            "child": c["root"] / c["run"] / ".continuation/session/draft-guard-parent.zip"}[mutation]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ContinuationError, match="invalid"):
        adopt_draft(c, proof, sha)
    assert c["repo"].get_by_task_id(owner_id="owner-1", task_id=c["task"]).terminal_reason == "draft_safety_failed"


@pytest.mark.parametrize("mutation", ["other_rejection", "cancelled"])
def test_draft_recovery_does_not_reopen_other_failures(draft_rejected, mutation):
    from app.product import draft_guard_recovery as recovery
    c = draft_rejected
    if mutation == "other_rejection":
        for path in [c["parent"] / "manifest.json", *list((c["parent"] / ".continuation/segments").glob("*/" + c["run"] + "/manifest.json"))]:
            value = json.loads(path.read_bytes())
            value["failure_code"] = "unknown_report_citation"
            path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ValueError, match="not_heading_rejection"):
            recovery.prepare(parent_run=c["parent"], destination_root=c["root"], reference=c["reference"])
        assert not c["root"].exists()
    else:
        from app.tasks.service import ReviewTaskService
        proof, sha = recovery.prepare(parent_run=c["parent"], destination_root=c["root"], reference=c["reference"])
        adopt_draft(c, proof, sha)
        ReviewTaskService(repository=c["repo"]).request_cancel(owner_id="owner-1", task_id=c["task"], request_id="cancel-recovered-draft")
        assert adopt_draft(c, proof, sha)["status"] == "cancelled"
        saved = c["store"].load(owner_id="owner-1", task_id=c["task"])
        with pytest.raises(ContinuationError, match="conflict"):
            c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="after-cancel",
                command=ResumeContinuation(checkpoint_sha256=saved["checkpoint_sha256"]))


@pytest.mark.parametrize("mutation", ["generation", "cap", "timeout", "read_error", "valid"])
def test_recovery_new_request_scope_precedes_intent_and_boundary(draft_rejected, mutation, monkeypatch):
    from app.product import draft_guard_recovery as recovery, sol_chat_contract as chat
    from app.evaluation.sol_natural_session import SessionPaused
    from tests.test_reviewer_chat_process import request
    c = draft_rejected
    proof_path, _ = recovery.prepare(parent_run=c["parent"], destination_root=c["root"], reference=c["reference"])
    proof = json.loads(proof_path.read_bytes())
    _, context = request()
    pending = json.loads(chat.request_bytes(chat.make_request(product.restore_context(context), "facts")))
    if mutation == "generation":
        pending = json.loads(next((c["parent"] / ".continuation/session/operations").glob("attempt-*.json")).read_bytes())["issued_raw"]
        pending = json.loads(pending)
    elif mutation == "cap":
        pending["max_tokens"] = 32768
    elif mutation == "timeout":
        pending["timeout_s"] = 301
    child = c["root"] / c["run"]
    with recovery.session_at(child, dict(binding=proof["binding"], **proof["child_checkpoint"]), read_only=False) as session:
        if mutation == "read_error":
            def unreadable(path):
                raise PermissionError("scripted marker read failure")
            monkeypatch.setattr(recovery, "read", unreadable)
        session.cursor = proof["operations"]
        before = tree(session.root / "operations")
        def no_send():
            pytest.fail("request guard called provider")
        with pytest.raises(SessionPaused if mutation == "valid" else SessionBlocked,
                           match="session_model_boundary" if mutation == "valid" else "session_new_request_scope_rejected"):
            session.operation("model", pending, no_send)
        assert tree(session.root / "operations") == before


def test_recovered_failure_resumes_without_regeneration_and_keeps_failure(failed_local, monkeypatch):
    c = failed_local
    proof, sha = prepare(c)
    with pytest.raises(ContinuationError, match="task_not_found"):
        adopt(c, proof, sha, "owner-2")
    with pytest.raises(ContinuationError, match="invalid"):
        adopt(c, proof, "0" * 64)
    assert adopt(c, proof, sha)["status"] == "recovery_required"
    assert adopt(c, proof, sha)["replayed"]
    saved = c["store"].load(owner_id="owner-1", task_id=c["task"])
    assert saved["local_failure_recovery"]["terminal_reason"] == "worker_execution_failed"
    assert saved["local_failure_recovery"]["runtime_terminal_reason"] == "harness_execution_failed"
    for pin, manual in [(c["reference"]["checkpoint_sha256"], False), (saved["checkpoint_sha256"], True)]:
        with pytest.raises(ContinuationError, match="conflict"):
            c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="bad",
                command=ResumeContinuation(checkpoint_sha256=pin, manual_retry=manual))
    c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="resume-recovered",
        command=ResumeContinuation(checkpoint_sha256=saved["checkpoint_sha256"]))
    make, summary, factories, requests = setup_worker(c["root"], monkeypatch, c["repo"],
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make()
    result = worker.run_once()
    assert result.status.value == "succeeded", result
    assert summary.reads == 0 and all(not p.generator.requests for f in factories for p in f.providers.values())
    assert requests == [[200, 200]]
    final = c["store"].load(owner_id="owner-1", task_id=c["task"])
    assert final["accounting"]["known_tokens"] == 80
    assert final["accounting"]["requests_observed"] == 4
    stored = c["repo"].get_by_task_id(owner_id="owner-1", task_id=c["task"])
    assert stored.report_available
    assert tree(c["parent"]) == c["original"]
    from sqlalchemy import text
    with c["repo"]._session_factory() as session:
        statuses = session.execute(text("SELECT status_after FROM review_task_events WHERE task_id=:task ORDER BY task_sequence"),
                                   dict(task=c["task"])).scalars().all()
    assert "failed" in statuses and statuses[-1] == "succeeded"
    assert adopt(c, proof, sha)["replayed"]


@pytest.mark.parametrize("mutation", ["parent", "child", "proof", "pending"])
def test_changed_evidence_cannot_enable_failed_retry(failed_local, mutation):
    c = failed_local
    if mutation == "pending":
        path = c["parent"] / ".continuation/session/operations/0003-result.json"
        path.unlink()  # disposable fixture only, simulating a lost committed result
        with pytest.raises(SessionBlocked, match="changed|uncommitted"):
            prepare(c)
        return
    proof, sha = prepare(c)
    if mutation == "proof":
        proof.write_bytes(proof.read_bytes() + b" ")
    else:
        path = (c["parent"] / "api_run_receipt.json" if mutation == "parent"
                else c["root"] / c["run"] / ".continuation/failed-parent.zip")
        path.write_bytes(b"changed")
    with pytest.raises(ContinuationError, match="invalid"):
        adopt(c, proof, sha)
    assert c["repo"].get_by_task_id(owner_id="owner-1", task_id=c["task"]).status.value == "failed"


def test_cancel_after_recovery_never_dispatches(failed_local):
    c = failed_local
    proof, sha = prepare(c)
    adopt(c, proof, sha)
    from app.tasks.service import ReviewTaskService
    # Use the same public service as the cancel endpoint.
    service = ReviewTaskService(repository=c["repo"])
    service.request_cancel(owner_id="owner-1", task_id=c["task"], request_id="cancel-recovered")
    saved = c["store"].load(owner_id="owner-1", task_id=c["task"])
    with pytest.raises(ContinuationError, match="conflict"):
        c["store"].resume(owner_id="owner-1", task_id=c["task"], request_id="after-cancel",
            command=ResumeContinuation(checkpoint_sha256=saved["checkpoint_sha256"]))
