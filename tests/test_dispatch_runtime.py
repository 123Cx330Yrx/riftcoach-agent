"""Actual V1 recorder/adapter IO with scripted Providers; no model requests."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from app.runtime.dispatch_control import DispatchStopped, bind_dispatch_guard
from app.runtime.dispatch_runtime import DispatchAwareRuntime
from app.runtime.identity import LegacyRuntimeIdentityResolver
from app.runtime.observer import RuntimeObservationError
from app.runtime.recorder import RuntimeRecorder, RuntimeRecorderError
from app.runtime.signals import ProviderCallCompletedSignal
from app.runtime.store import RuntimeTraceStore
from tests.test_agent_runtime import FactoryProbe, RuntimeProvider, _request, _runtime, _trace
from tests.test_document_review_timed_budget import no_network


@pytest.mark.parametrize("after", [0, 1, 3, 4])
def test_trusted_stop_seals_exact_observed_events_and_resolves_identity_once(
    tmp_path, no_network, after,
):
    provider = RuntimeProvider()
    runtime = DispatchAwareRuntime.from_core(_runtime(tmp_path, provider, FactoryProbe(revision=True)))

    class Resolver(LegacyRuntimeIdentityResolver):
        calls = 0

        def resolve(self, *args, **kwargs):
            self.calls += 1
            assert self.calls == 1, "stop must use the identity captured at startup"
            return super().resolve(*args, **kwargs)

    resolver = Resolver()
    runtime._prompt_program_resolver = resolver
    seen = []

    def guard():
        if len(provider.requests) >= after:
            raise DispatchStopped("private lease details")

    with bind_dispatch_guard(guard):
        result = runtime._run_with_sink(_request(f"stop_{after}"), event_sink=seen.append)
    trace = _trace(tmp_path, result)
    assert result.runtime_status.value == "failed"
    assert result.terminal_reason == "task_dispatch_stopped"
    assert result.output is None and result.publication_status is None
    assert tuple(seen) == trace.events  # same sequence, timestamps and signals
    assert [e.sequence for e in trace.events] == list(range(1, len(seen) + 1))
    assert len(provider.requests) == after
    assert trace.usage.provider_calls_attempted == after
    assert trace.usage.provider_responses_observed == after
    assert trace.usage.observed_input_tokens == sum([11, 17, 7, 7][:after])
    assert trace.usage.observed_output_tokens == sum([5, 8, 3, 3][:after])
    assert trace.events[-1].signal.failure_code == "task_dispatch_stopped"
    assert resolver.calls == 1
    assert not list(tmp_path.rglob("final_report.md"))
    assert "private" not in repr(trace) and "private" not in repr(result)


@pytest.mark.parametrize("error_type", [RuntimeObservationError, RuntimeRecorderError, DispatchStopped])
def test_real_observer_fault_does_not_create_trusted_trace(tmp_path, no_network, monkeypatch, error_type):
    provider = RuntimeProvider()
    runtime = DispatchAwareRuntime.from_core(_runtime(tmp_path, provider))
    emit = RuntimeRecorder.emit

    def broken(self, signal):
        if isinstance(signal, ProviderCallCompletedSignal):
            raise error_type("private recorder fault")
        return emit(self, signal)

    monkeypatch.setattr(RuntimeRecorder, "emit", broken)
    result = runtime.run(_request("observer_fault"))
    assert result.terminal_reason == "observation_failed"
    assert result.trace_reference is None and result.output is None
    assert len(provider.requests) == 1
    assert not list(tmp_path.rglob("trace.json"))
    assert "private" not in repr(result)


def test_delegate_cannot_turn_unbound_dispatch_exception_into_trusted_trace(tmp_path, no_network):
    class Provider(RuntimeProvider):
        def chat(self, request):
            self.requests.append(request)
            raise DispatchStopped("private delegate fault")

    provider = Provider()
    result = DispatchAwareRuntime.from_core(_runtime(tmp_path, provider)).run(_request("delegate_fault"))
    assert result.terminal_reason == "observation_failed"
    assert result.trace_reference is None and result.output is None
    assert len(provider.requests) == 1


def test_trace_write_failure_stays_failed_without_reference(tmp_path, no_network, monkeypatch):
    provider = RuntimeProvider()
    runtime = DispatchAwareRuntime.from_core(_runtime(tmp_path, provider))

    def guard():
        if provider.requests:
            raise DispatchStopped("private fence")

    def broken_write(*args):
        raise OSError("private disk fault")

    monkeypatch.setattr(RuntimeTraceStore, "write_trace", broken_write)
    with bind_dispatch_guard(guard):
        result = runtime.run(_request("write_fault"))
    assert result.terminal_reason == "trace_persistence_failed"
    assert result.runtime_status.value == "failed"
    assert result.trace_reference is None and result.output is None
    assert len(provider.requests) == 1


def test_failed_call_usage_remains_unknown_when_next_send_is_stopped(tmp_path, no_network, monkeypatch):
    from app.providers.errors import ProviderAuthenticationError
    provider = RuntimeProvider(behavior="agent_failure")
    runtime = DispatchAwareRuntime.from_core(_runtime(tmp_path, provider))

    # Exercise the adapter after a real failed observation, without inventing
    # completion/usage. A diagnostic preparer attempts a second call inside
    # the actual Harness lifecycle; the guard must stop that second start.
    original_build = runtime._execution_factory.build
    def build(*, provider, observer):
        bundle = original_build(provider=provider, observer=observer)
        class Preparer:
            def prepare(self, execution, context):
                from tests.test_runtime_observed_provider import _request as chat_request
                request = chat_request(agent_loop_iteration=1)
                with pytest.raises(ProviderAuthenticationError):
                    provider.chat(request)
                provider.chat(request)
                raise AssertionError("second send was not fenced")
        return replace(bundle, draft_preparer=Preparer())

    monkeypatch.setattr(runtime._execution_factory, "build", build)

    def guard():
        if provider.requests:
            raise DispatchStopped("private fence")

    with bind_dispatch_guard(guard):
        result = runtime.run(_request("unknown_usage"))
    trace = _trace(tmp_path, result)
    assert trace.usage.provider_calls_attempted == 1
    assert trace.usage.provider_responses_observed == 0
    assert trace.usage.token_observation.value == "unknown"
    assert trace.usage.input_tokens is None and trace.usage.output_tokens is None
    assert trace.usage.cost is None
    assert len(provider.requests) == 1


def test_same_runtime_concurrent_runs_and_later_run_do_not_share_identity_or_stop(tmp_path, no_network):
    barrier = Barrier(2)
    runtime = DispatchAwareRuntime.from_core(_runtime(tmp_path, RuntimeProvider()))

    class Resolver(LegacyRuntimeIdentityResolver):
        def resolve(self, *args, **kwargs):
            identity = super().resolve(*args, **kwargs)
            barrier.wait(timeout=5)
            return identity

    runtime._prompt_program_resolver = Resolver()

    def execute(index):
        def guard():
            raise DispatchStopped("private fence")
        with bind_dispatch_guard(guard):
            return runtime.run(_request(f"parallel_{index}", single=bool(index)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, (0, 1)))
    for index, result in enumerate(results):
        trace = _trace(tmp_path, result)
        assert trace.identity.skill_name == ("single-match-review" if index else "recent-form-review")
        assert {e.run_id for e in trace.events} == {f"parallel_{index}"}
        assert result.terminal_reason == "task_dispatch_stopped"
        assert trace.usage.provider_calls_attempted == 0
    runtime._prompt_program_resolver = LegacyRuntimeIdentityResolver()
    normal = runtime.run(_request("later_run"))
    assert normal.runtime_status.value == "completed"
    assert _trace(tmp_path, normal).usage.provider_calls_attempted == 3


def test_adapter_refuses_unknown_runtime_subclasses(tmp_path):
    adapter = DispatchAwareRuntime.from_core(_runtime(tmp_path, RuntimeProvider()))
    with pytest.raises(TypeError, match="exact V1 core"):
        DispatchAwareRuntime.from_core(adapter)


def test_default_composition_uses_dispatch_adapter(tmp_path, no_network):
    from app.runtime.composition import RuntimeCompositionRoot
    core = _runtime(tmp_path, RuntimeProvider())
    root = RuntimeCompositionRoot.from_directories(skills_root="skills", prompt_programs_root="prompt_programs")
    runtime = root.build_runtime(runs_root=tmp_path, provider=core._provider,
        execution_factory=core._execution_factory)

    def guard():
        raise DispatchStopped("private stop")

    with bind_dispatch_guard(guard):
        result = runtime.run(_request("default_stop"))
    assert result.terminal_reason == "task_dispatch_stopped"
    assert _trace(tmp_path, result).usage.provider_calls_attempted == 0


def test_application_adapter_preserves_dependencies_and_original_runtime(tmp_path, no_network):
    from app.product.dispatch_trace import with_dispatch_trace
    from app.runtime.runtime import AgentRuntimeV1
    from tests.test_role_coach_application import application
    original, factory, _ = application(tmp_path)
    adapted = with_dispatch_trace(original)
    assert adapted is not original
    assert type(original._runtime) is AgentRuntimeV1
    assert type(adapted._runtime) is DispatchAwareRuntime
    for name, value in vars(original).items():
        if name != "_runtime":
            assert getattr(adapted, name) is value
    for name, value in vars(original._runtime).items():
        # The constructor normalizes the root Path but keeps every dependency.
        if name == "_runs_root":
            assert getattr(adapted._runtime, name) == value
        else:
            assert getattr(adapted._runtime, name) is value
    assert not factory.providers
