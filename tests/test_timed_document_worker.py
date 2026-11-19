"""Real Worker thread + candidate factory/budget; offline transport and DB."""
from datetime import timedelta
from threading import Event, current_thread, enumerate as threads

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.document_review_timing_adapter import TimedDocumentBudget
from app.providers.models import ChatResponse, TokenUsage
from app.tasks.models import TaskPublicationMode
from app.tasks.reliable_runtime import TaskHeartbeatDisposition, TaskLeasePolicy
from app.workers.review_worker import ReviewWorker, ReviewWorkerError, WorkerIterationStatus
from tests.test_document_review_timed_budget import review, no_network
from tests.test_document_review_timed_transport import factory
from tests.test_reliable_review_worker import NOW, Repository, EvidenceExecutor, TOKEN


class Clock:
    now = 0

    def __call__(self):
        return self.now

    def worker_time(self):
        # Compress elapsed time, but keep the actual independent heartbeat
        # thread. No 600-second sleep or manually invoked maintainer.
        if current_thread().name.startswith("riftcoach-lease-"):
            self.now += 190
        return NOW + timedelta(seconds=self.now)


class RenewingRepository(Repository):
    def __init__(self, fault):
        super().__init__(succeed_result=fault not in ("cas_cancel", "cas_lost"),
                         cancel_result=fault != "cas_lost")
        self.fault = fault
        self.ready = Event()
        self.expires = NOW + timedelta(seconds=360)
        self.claim = self.claim.model_copy(update={
            "publication_mode": TaskPublicationMode.EVIDENCE_BOUND_V1,
            "lease": self.claim.lease.model_copy(update={"expires_at": self.expires}),
        })

    def heartbeat(self, **kwargs):
        assert kwargs["lease_generation"] == 1 and kwargs["lease_token"] == TOKEN
        assert kwargs["now"] < self.expires, "renewal must precede expiry"
        self.expires = kwargs["now"] + timedelta(seconds=kwargs["lease_seconds"])
        if len(self.heartbeats) == 2:
            self.dispositions = [{
                "cancel": TaskHeartbeatDisposition.CANCEL_REQUESTED,
                "lost": TaskHeartbeatDisposition.LOST,
            }.get(self.fault, TaskHeartbeatDisposition.ACTIVE)]
            self.ready.set()
            if self.fault == "heartbeat_error":
                raise RuntimeError("synthetic database unavailable")
        return super().heartbeat(**kwargs)


@pytest.mark.parametrize("fault,expected", [
    (None, WorkerIterationStatus.SUCCEEDED),
    ("cancel", WorkerIterationStatus.CANCELLED),
    ("lost", WorkerIterationStatus.OWNERSHIP_LOST),
    ("heartbeat_error", None),
    ("task_deadline", WorkerIterationStatus.FAILED),
    ("cas_cancel", WorkerIterationStatus.CANCELLED),
    ("cas_lost", WorkerIterationStatus.OWNERSHIP_LOST),
])
def test_timed_send_renews_lease_but_cannot_publish_after_fence_or_deadline(
    tmp_path, monkeypatch, no_network, fault, expected
):
    clock = Clock()
    repository = RenewingRepository(fault)
    sent = []

    def child(command, raw, *, directory, transport_id, **kwargs):
        request = bridge.REQUEST.validate_json(raw)
        sent.append(request)
        assert repository.ready.wait(10), "background renewals did not arrive"
        clock.now = 901 if fault == "task_deadline" else 590
        bridge.write_new_json(directory / "result.json", {
            "state": "complete", "elapsed_ms": 0, "transport_id": transport_id,
        })
        return ChatResponse(provider="zhipu", model="glm-5.3",
                            content="Synthetic response, no quality proof", usage=TokenUsage(20, 10))

    monkeypatch.setattr(bridge, "run_child", child)
    budget = TimedDocumentBudget(factory(tmp_path)("worker-timed"), clock=clock)

    class Executor(EvidenceExecutor):
        def execute(self, task):
            budget.chat(review())
            return super().execute(task)

    worker = ReviewWorker(repository=repository, executor=Executor(),
        worker_id="worker-reliable-1", clock=clock.worker_time,
        lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=1))
    if expected is None:
        with pytest.raises(ReviewWorkerError, match="task_lease_update_failed"):
            worker.run_once()
    else:
        assert worker.run_once().status is expected
    assert len(sent) == budget.calls == 1 and sent[0].timeout_s == 600
    assert budget.tokens == 30 and budget.reserved_tokens == 0
    assert [h["now"] for h in repository.heartbeats[:2]] == [
        NOW + timedelta(seconds=190), NOW + timedelta(seconds=380)]
    assert repository.succeed_calls == []  # evidence mode never uses legacy commit
    assert len(repository.succeed_with_evidence_calls) == int(fault in (None, "cas_cancel", "cas_lost"))
    assert len(repository.fail_calls) == int(fault == "task_deadline")
    assert len(repository.cancel_calls) == int(fault in ("cancel", "cas_cancel", "cas_lost"))
    if fault == "task_deadline":
        assert budget.stopped and budget.last_exchange is None
    assert not any(t.name.startswith("riftcoach-lease-") for t in threads())
