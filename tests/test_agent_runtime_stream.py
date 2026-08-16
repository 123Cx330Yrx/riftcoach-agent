from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from time import monotonic, sleep

import pytest
from pydantic import ValidationError

from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall
from app.runtime.models import (
    RuntimeStreamItem,
    RuntimeStatus,
)
from app.runtime.runtime import AgentRuntimeV1, RuntimeCompositionError
from app.runtime.signals import (
    RunCompletedSignal,
    RunFailedSignal,
)
from tests.test_agent_runtime import (
    FactoryProbe,
    RuntimeProvider,
    _catalog_with_fallback,
    _policy,
    _request,
    _runtime,
    _version_mismatch_request,
)


def test_stream_item_requires_exactly_one_payload():
    with pytest.raises(ValidationError, match="event item"):
        RuntimeStreamItem(kind="event")

    with pytest.raises(ValidationError, match="result item"):
        RuntimeStreamItem(kind="result")


def test_stream_does_not_start_worker_before_first_consumption(tmp_path):
    provider = RuntimeProvider()
    runtime = _runtime(tmp_path, provider)

    iterator = runtime.stream(_request("stream_lazy"))

    assert provider.requests == []
    first = next(iterator)
    assert first.kind == "event"
    assert first.event is not None
    assert first.event.signal.kind == "run_started"

    items = [first, *iterator]
    result_items = [item for item in items if item.kind == "result"]
    assert len(result_items) == 1
    assert result_items[0].result is not None
    assert result_items[0].result.runtime_status is RuntimeStatus.COMPLETED


@pytest.mark.parametrize("queue_size", [0, 1025])
def test_stream_rejects_unsafe_queue_size(tmp_path, queue_size):
    runtime = _runtime(tmp_path, RuntimeProvider())
    with pytest.raises(ValueError, match="queue_size"):
        runtime.stream(_request(f"stream_bad_queue_{queue_size}"), queue_size=queue_size)


def test_stream_events_are_in_order_and_result_follows_terminal(tmp_path):
    provider = RuntimeProvider()
    runtime = _runtime(tmp_path, provider)

    items = list(runtime.stream(_request("stream_order")))
    events = [item.event for item in items if item.kind == "event"]
    result_items = [item.result for item in items if item.kind == "result"]

    assert all(event is not None for event in events)
    assert [event.sequence for event in events if event is not None] == list(
        range(1, len(events) + 1)
    )
    assert isinstance(events[-1].signal, RunCompletedSignal)
    assert result_items == [result_items[0]]
    assert result_items[0] is not None
    assert result_items[0].runtime_status is RuntimeStatus.COMPLETED


def test_run_and_stream_share_signal_and_result_semantics(tmp_path):
    run_provider = RuntimeProvider()
    stream_provider = RuntimeProvider()
    run_result = _runtime(tmp_path / "run", run_provider).run(
        _request("parity_run")
    )
    stream_items = list(
        _runtime(tmp_path / "stream", stream_provider).stream(
            _request("parity_stream")
        )
    )
    stream_events = [
        item.event for item in stream_items if item.kind == "event"
    ]
    stream_result = next(
        item.result for item in stream_items if item.kind == "result"
    )

    from app.runtime.store import RuntimeTraceStore

    run_trace = RuntimeTraceStore(tmp_path / "run", "parity_run").read_trace(
        run_result.trace_reference
    )
    stream_trace = RuntimeTraceStore(
        tmp_path / "stream", "parity_stream"
    ).read_trace(stream_result.trace_reference)

    assert [event.signal.model_dump() for event in stream_events] == [
        event.signal.model_dump() for event in stream_trace.events
    ]
    assert [event.signal.kind for event in stream_trace.events] == [
        event.signal.kind for event in run_trace.events
    ]
    assert stream_result.runtime_status is run_result.runtime_status
    assert stream_result.publication_status is run_result.publication_status
    assert stream_result.terminal_reason == run_result.terminal_reason
    stream_output = stream_result.output.model_dump()
    run_output = run_result.output.model_dump()
    stream_output.pop("run_id", None)
    run_output.pop("run_id", None)
    assert stream_output == run_output


def test_small_queue_preserves_all_events_and_completes(tmp_path):
    provider = RuntimeProvider()
    items = list(
        _runtime(tmp_path, provider).stream(
            _request("stream_backpressure"),
            queue_size=1,
        )
    )
    events = [item.event for item in items if item.kind == "event"]
    assert len(events) > 1
    assert [event.sequence for event in events] == list(
        range(1, len(events) + 1)
    )
    assert items[-1].kind == "result"


def test_closed_stream_does_not_cancel_runtime_execution(tmp_path):
    provider = BlockingProvider()
    runtime = _runtime(tmp_path, provider)
    iterator = runtime.stream(_request("stream_closed"), queue_size=1)

    while True:
        item = next(iterator)
        if (
            item.kind == "event"
            and item.event is not None
            and item.event.signal.kind == "provider_call_started"
        ):
            break
    assert provider.entered.wait(timeout=2)
    iterator.close()
    provider.release.set()

    assert provider.finished.wait(timeout=5)
    deadline = monotonic() + 5
    trace_path = tmp_path / "stream_closed" / "runtime_trace.json"
    while not trace_path.exists() and monotonic() < deadline:
        sleep(0.02)
    assert trace_path.exists()


def test_unexpected_worker_error_matches_run_error_semantics(tmp_path, monkeypatch):
    provider = RuntimeProvider()
    runtime = _runtime(tmp_path, provider)

    def explode(self, request, *, event_sink=None):
        raise RuntimeCompositionError("private composition detail")

    monkeypatch.setattr(AgentRuntimeV1, "_execute", explode)
    with pytest.raises(RuntimeCompositionError):
        runtime.run(_request("stream_worker_error_run"))

    with pytest.raises(RuntimeCompositionError):
        list(runtime.stream(_request("stream_worker_error_stream")))


@dataclass
class BlockingProvider(RuntimeProvider):
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)
    finished: Event = field(default_factory=Event)

    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.metadata.get("agent_loop_iteration") == 1:
            self.entered.set()
            if not self.release.wait(timeout=5):
                raise TimeoutError("test provider release timed out")
        try:
            return super().chat(request)
        finally:
            self.finished.set()


def test_stream_delivers_provider_started_before_provider_completes(tmp_path):
    provider = BlockingProvider()
    runtime = _runtime(tmp_path, provider)
    iterator = runtime.stream(_request("stream_live"))

    seen = []
    while True:
        item = next(iterator)
        seen.append(item)
        if (
            item.kind == "event"
            and item.event is not None
            and item.event.signal.kind == "provider_call_started"
        ):
            break

    assert provider.entered.wait(timeout=1)
    assert not any(
        item.kind == "event"
        and item.event is not None
        and item.event.signal.kind == "provider_call_completed"
        for item in seen
    )

    provider.release.set()
    remaining = list(iterator)
    assert any(item.kind == "result" for item in remaining)


def test_stream_trace_write_failure_never_emits_completed_terminal(tmp_path, monkeypatch):
    provider = RuntimeProvider()

    def fail_write(self, trace):
        raise OSError("private trace persistence failure")

    monkeypatch.setattr("app.runtime.runtime.RuntimeTraceStore.write_trace", fail_write)
    items = list(_runtime(tmp_path, provider).stream(_request("stream_trace_failure")))

    events = [item.event for item in items if item.kind == "event"]
    result = next(item.result for item in items if item.kind == "result")
    assert result is not None
    assert result.runtime_status is RuntimeStatus.FAILED
    assert isinstance(events[-1].signal, RunFailedSignal)
    assert not any(
        event is not None and isinstance(event.signal, RunCompletedSignal)
        for event in events
    )


@pytest.mark.parametrize("behavior", ["agent_failure", "evaluation_failure"])
def test_stream_preserves_degraded_publication_for_expected_provider_failure(
    tmp_path,
    behavior,
):
    items = list(
        _runtime(tmp_path, RuntimeProvider(behavior=behavior)).stream(
            _request(f"stream_{behavior}")
        )
    )
    result = next(item.result for item in items if item.kind == "result")
    assert result is not None
    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status.value == "degraded"
    assert isinstance(
        [item.event for item in items if item.kind == "event"][-1].signal,
        RunCompletedSignal,
    )


def test_stream_preserves_rejected_publication_without_report(tmp_path):
    request = _request("stream_rejected")
    request = request.model_copy(
        update={"policy": _policy(allow_deterministic_fallback=False)}
    )
    items = list(
        _runtime(
            tmp_path,
            RuntimeProvider(behavior="evaluation_failure"),
            catalog=_catalog_with_fallback(False),
        ).stream(request)
    )
    result = next(item.result for item in items if item.kind == "result")
    assert result is not None
    assert result.publication_status.value == "rejected"
    assert result.output.status == "rejected"
    assert result.output.report is None


def test_stream_boundary_failure_has_failed_terminal_and_no_provider_io(tmp_path):
    provider = RuntimeProvider()
    items = list(
        _runtime(tmp_path, provider)
        .stream(_version_mismatch_request("stream_boundary_failure"))
    )
    result = next(item.result for item in items if item.kind == "result")
    events = [item.event for item in items if item.kind == "event"]
    assert result is not None
    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "execution_validation_failed"
    assert isinstance(events[-1].signal, RunFailedSignal)
    assert provider.requests == []
