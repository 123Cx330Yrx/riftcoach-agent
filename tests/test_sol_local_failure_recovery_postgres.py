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
