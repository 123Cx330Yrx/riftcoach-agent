"""Real Worker/observation boundary, synthetic DB/Provider; no model calls."""
from threading import Event, Thread, enumerate as threads

import pytest

from app.runtime.dispatch_control import (
    DispatchStopped, bind_dispatch_guard, require_dispatch_allowed,
)
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.signals import ProviderCallStartedSignal
from app.tasks.models import TaskPublicationMode
from app.tasks.reliable_runtime import TaskHeartbeatDisposition as State, TaskLeasePolicy
from app.workers.review_worker import ReviewWorkerError, WorkerIterationStatus as Outcome
from tests.test_reliable_review_worker import Repository, EvidenceExecutor, worker
from tests.test_runtime_observed_provider import (
    RecordingObserver, ScriptedProvider, ReceiptProvider, Receipt, _request, _response,
)
from tests.test_document_review_timed_budget import no_network
from tests.test_correction_scope_runtime import coarse_script_sources


class SwitchingRepository(Repository):
    def __init__(self, fault, *, initially=False):
        super().__init__()
        self.fault = fault
        self.armed = initially
        self.observed = Event()
        self.claim = self.claim.model_copy(update={
            "publication_mode": TaskPublicationMode.EVIDENCE_BOUND_V1,
        })

    def heartbeat(self, **kwargs):
        if self.armed and self.fault:
            self.observed.set()
            if self.fault == "error":
                raise RuntimeError("private database failure must not escape")
            self.dispositions = [{"cancel": State.CANCEL_REQUESTED, "lost": State.LOST}[self.fault]]
        return super().heartbeat(**kwargs)


@pytest.mark.parametrize("fault,expected", [
    (None, Outcome.SUCCEEDED), ("cancel", Outcome.CANCELLED),
    ("lost", Outcome.OWNERSHIP_LOST), ("error", None),
])
@pytest.mark.parametrize("after", [0, 1, 2])
def test_each_stage_checks_current_fence_before_provider_start(no_network, fault, expected, after):
    repo = SwitchingRepository(fault, initially=after == 0)
    events = RecordingObserver()

    class Provider(ScriptedProvider):
        def chat(self, request):
            result = super().chat(request)
            if len(self.requests) >= after:
                repo.armed = True
            return result

    delegate = Provider([_response() for _ in range(3)])
    observed = ObservedLLMProvider(delegate=delegate, observer=events)

    class Executor(EvidenceExecutor):
        def execute(self, task):
            for phase in ("evaluate", "revise", "evaluate"):
                observed.chat(_request(harness_step=phase))
            return super().execute(task)

    execution = worker(repo, Executor())
    if expected is None:
        with pytest.raises(ReviewWorkerError, match="^task_lease_update_failed$"):
            execution.run_once()
    else:
        assert execution.run_once().status is expected
    sent = 3 if fault is None else after
    assert len(delegate.requests) == sent
    assert len([e for e in events.signals if isinstance(e, ProviderCallStartedSignal)]) == sent
    assert len(repo.succeed_with_evidence_calls) == int(fault is None)
    assert len(repo.cancel_calls) == int(fault == "cancel")
    assert not repo.fail_calls and not repo.succeed_calls
    assert not any(t.name.startswith("riftcoach-lease-") for t in threads())
    # The next job in this execution thread must not inherit a cancelled lease.
    require_dispatch_allowed()


@pytest.mark.parametrize("fault,expected", [
    ("cancel", Outcome.CANCELLED), ("lost", Outcome.OWNERSHIP_LOST), ("error", None),
])
def test_background_fence_during_inflight_call_blocks_next_stage(no_network, fault, expected):
    repo = SwitchingRepository(fault)

    class Provider(ScriptedProvider):
        def chat(self, request):
            repo.armed = True
            assert repo.observed.wait(5), "real heartbeat thread did not check the lease"
            return super().chat(request)

    delegate = Provider([_response(), _response()])
    observed = ObservedLLMProvider(delegate=delegate, observer=RecordingObserver())

    class Executor(EvidenceExecutor):
        def execute(self, task):
            observed.chat(_request(harness_step="evaluate"))
            observed.chat(_request(harness_step="revise"))
            return super().execute(task)

    execution = worker(repo, Executor(), policy=TaskLeasePolicy(lease_seconds=15, heartbeat_seconds=1))
    if expected is None:
        with pytest.raises(ReviewWorkerError, match="^task_lease_update_failed$"):
            execution.run_once()
    else:
        assert execution.run_once().status is expected
    assert len(delegate.requests) == 1  # preserve the in-flight outcome, no next call
    assert not repo.succeed_with_evidence_calls and not repo.fail_calls


def test_cancel_cannot_be_cleared_by_later_active_reply(no_network):
    repo = Repository([State.CANCEL_REQUESTED, State.ACTIVE])
    delegate = ScriptedProvider([_response()])
    observed = ObservedLLMProvider(delegate=delegate, observer=RecordingObserver())

    class Executor(EvidenceExecutor):
        def execute(self, task):
            observed.chat(_request(harness_step="evaluate"))
            return super().execute(task)

    assert worker(repo, Executor()).run_once().status is Outcome.CANCELLED
    assert not delegate.requests and len(repo.cancel_calls) == 1
    assert len(repo.heartbeats) == 2  # CANCEL at preflight, ACTIVE at final fence


def test_disabling_observation_cannot_bypass_dispatch_fence():
    from app.runtime.observer import observe_runtime_signal
    from app.runtime.signals import RuntimeProviderPhase
    def stop():
        raise DispatchStopped("task_dispatch_fenced")
    start = ProviderCallStartedSignal(provider_id="zhipu", model="glm-5.3",
        ordinal=1, phase=RuntimeProviderPhase.EVALUATION, iteration=None)
    with bind_dispatch_guard(stop):
        with pytest.raises(DispatchStopped):
            observe_runtime_signal(None, start)


def test_dispatch_fence_clears_receipt_and_does_not_leak_across_contexts(no_network):
    first, second = Receipt(), Receipt()
    delegate = ReceiptProvider([_response(), _response()], [first, second])
    observer = RecordingObserver()
    observed = ObservedLLMProvider(delegate=delegate, observer=observer)
    observed.chat(_request(harness_step="evaluate"))
    assert observed.last_exchange is first

    def stop():
        raise DispatchStopped("task_dispatch_fenced")

    isolated = Event()
    with bind_dispatch_guard(stop):
        with pytest.raises(DispatchStopped):
            observed.chat(_request(harness_step="evaluate"))
        assert observed.last_exchange is None
        with pytest.raises(RuntimeError, match="already bound"):
            with bind_dispatch_guard(lambda: None):
                pass
        def independent_execution():
            require_dispatch_allowed()
            isolated.set()
        thread = Thread(target=independent_execution)
        thread.start()
        thread.join(2)
        assert isolated.is_set() and not thread.is_alive()
    observed.chat(_request(harness_step="evaluate"))
    assert observed.last_exchange is second
    # A cancelled execution ends here in production; reusing this wrapper only
    # checks scope cleanup. Its rejected start already consumed local ordinal 2.
    assert [e.ordinal for e in observer.signals if isinstance(e, ProviderCallStartedSignal)] == [1, 3]


def test_actual_coach_budget_stops_with_only_one_delegate_send(no_network, coarse_script_sources):
    from app.runtime.coach_budget import CoachBudgetedProvider as Budget
    from app.runtime.coach_contract import CORRECTION_SCOPE_COACH_CONTRACT as CONTRACT
    from app.runtime.reviewer_roles import RoleRoutedProvider
    from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as Workflow
    from app.evaluation.golden_coarse_source_projection import VERSION
    from tests.test_reviewer_role_proposal import providers
    repo = SwitchingRepository("cancel")
    roles = RoleRoutedProvider(*providers(), source_projection=VERSION)
    events = RecordingObserver()
    observed = ObservedLLMProvider(delegate=roles, observer=events,
                                  request_identity=CONTRACT.request_identity)
    budget = Budget(observed, clock=lambda: 0, coach_contract=CONTRACT)
    request = Workflow.make_request(Workflow.build_inputs(roles.generator.req))

    class Executor(EvidenceExecutor):
        def execute(self, task):
            budget.chat(request)
            repo.armed = True
            budget.chat(request)
            return super().execute(task)

    assert worker(repo, Executor()).run_once().status is Outcome.CANCELLED
    assert len(roles.attempts) == 1 and len(roles.reviewer.requests) == 1
    assert len([e for e in events.signals if isinstance(e, ProviderCallStartedSignal)]) == 1
    assert budget.stopped and observed.last_exchange is None
    # The unchanged outer budget reserves before the observed-provider boundary.
    # Keep that conservative attempted-call reservation; do not invent usage or
    # count it as another actual Provider/HTTP dispatch.
    assert budget.calls == 2 and budget.tokens > 0 and budget.reserved_tokens > 0
    assert not repo.succeed_with_evidence_calls and not repo.fail_calls


@pytest.mark.parametrize("after", [1, 3, 4, 6])
def test_real_application_path_blocks_next_generation_edit_or_fresh(
    tmp_path, no_network, coarse_script_sources, after,
):
    from pathlib import Path
    from app.product.native_coach_composition import build_correction_scope_coach_application
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from app.runtime.reviewer_roles import RoleRoutedProvider
    from app.evaluation.golden_coarse_source_projection import VERSION
    from tests.test_reviewer_role_proposal import providers
    from tests.test_native_editor_product_budget import SummaryBuilder
    from tests.test_role_coach_application import run

    repo = SwitchingRepository("cancel")

    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=VERSION)
            self.created = None

        def __call__(self, run_id):
            self.created = RoleRoutedProvider(*providers(), source_projection=VERSION)
            delegate = self.created.chat
            def chat(request):
                response = delegate(request)
                if len(self.created.attempts) == after:
                    repo.armed = True
                return response
            self.created.chat = chat
            return self.created

    factory = Factory()
    app = build_correction_scope_coach_application(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs")),
        runs_root=tmp_path,
    )

    class Executor(EvidenceExecutor):
        def execute(self, task):
            run(app, task.run_id)
            return super().execute(task)

    assert worker(repo, Executor()).run_once().status is (Outcome.CANCELLED if after < 5 else Outcome.SUCCEEDED)
    expected = ["generation", "generation", "review", "revision", "review"][:after]
    assert [a["role"] for a in factory.created.attempts] == expected
    assert len(repo.succeed_with_evidence_calls) == int(after > 5)
    assert len(repo.cancel_calls) == int(after < 5)
    assert len(list(tmp_path.rglob("final_report.md"))) == int(after > 5)
