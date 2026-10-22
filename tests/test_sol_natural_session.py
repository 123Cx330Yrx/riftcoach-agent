"""Restart actual candidate application without buying completed stages twice."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.evaluation import sol_natural_contract as contract
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, tree
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.store import RuntimeTraceStore
from tests.test_native_editor_product_budget import SummaryBuilder
from tests.test_sol_natural_candidate import application
from tests.test_natural_duty_candidate import run


def session(tmp, previous=None, **kwargs):
    return CandidateSession(tmp/'session', binding=dict(run_id='candidate', fixture_only=True),
        transport_root=tmp/'transport/candidate', journal_root=tmp/'journal',
        guard_sha=previous.guard_sha if previous else None,
        checkpoint_sha=previous.checkpoint_sha if previous else None,
        before_new_model=lambda: None, **kwargs)


def app_for(tmp, sess, segment, *, statuses=(), mode='repair', knowledge=None):
    _, factory, _, calls = application(tmp, statuses=statuses, mode=mode)
    app = build_natural_duty_candidate(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory,
        knowledge_provider=knowledge or LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp/f'derived-{segment}', candidate=contract, execution_session=sess)
    return app, factory, calls


class NoSearch:
    provider_name = 'forbidden-on-replay'
    def search(self, query):
        pytest.fail('committed tool result was searched again')


@pytest.mark.parametrize('interrupt', [False, True])
def test_credential_wait_excludes_human_time_and_preserves_active_time(tmp_path, interrupt):
    now = [100.0]
    first = session(tmp_path, clock=lambda: now[0])
    with first:
        now[0] += 17
        def prompt():
            with first.waiting_for_credentials():
                now[0] += 7200
                assert first.active_seconds == 17
                if interrupt:
                    raise KeyboardInterrupt()
        if interrupt:
            with pytest.raises(KeyboardInterrupt):
                prompt()
        else:
            prompt()
        assert first.active_seconds == 17
        now[0] += 23
        assert first.active_seconds == 40
    now[0] += 5000
    resumed = session(tmp_path, first, clock=lambda: now[0])
    with resumed:
        assert resumed.active_seconds == 40
        now[0] += 5
        assert resumed.active_seconds == 45


def test_application_resume_preserves_tools_budget_and_single_application(tmp_path):
    first = session(tmp_path, max_new_models=3)
    with pytest.raises(SessionPaused), first:
        app, factory, calls = app_for(tmp_path, first, 1)
        run(app)
    assert calls == [200]
    old_transport, old_journal = tree(first.transport_root), tree(first.journal_root)
    assert 'facts-initial.json' in old_journal and 'application.json' not in old_journal
    assert not (first.journal_root/'outcome.json').exists()
    second = session(tmp_path, first)
    with second:
        app, factory, calls = app_for(tmp_path, second, 2, knowledge=NoSearch())
        result = run(app)
        assert result.publication_status.value == 'rejected'
        router = factory.providers['candidate']
        assert router.candidate_budget.calls == 6
        assert router._logical == {'generation': 2, 'review': 4}
        assert router.generator.requests == []
        assert calls == [200, 200, 200]
        trace = RuntimeTraceStore(tmp_path/'derived-2', 'candidate').read_trace(result.trace_reference)
        assert trace.usage.provider_calls_attempted == 3  # new IO only
        second.close(dict(outcome=json.loads((second.journal_root/'outcome.json').read_bytes())['outcome']))
    assert all(tree(second.transport_root)[p] == sha for p, sha in old_transport.items())
    assert all(tree(second.journal_root)[p] == sha for p, sha in old_journal.items())
    assert len(list(second.journal_root.glob('application.json'))) == 1
    before = tree(tmp_path/'session'), tree(tmp_path/'transport'), tree(tmp_path/'journal')
    replay = session(tmp_path, second, read_only=True)
    with replay:
        app, factory, calls = app_for(tmp_path, replay, 3, knowledge=NoSearch())
        result = run(app)
        assert result.publication_status.value == 'rejected'
        assert calls == [] and factory.providers['candidate'].generator.requests == []
        trace = RuntimeTraceStore(tmp_path/'derived-3', 'candidate').read_trace(result.trace_reference)
        assert trace.usage.provider_calls_attempted == 0
    assert before == (tree(tmp_path/'session'), tree(tmp_path/'transport'), tree(tmp_path/'journal'))


def test_retry_state_and_unknown_reservation_survive_resume(tmp_path):
    first = session(tmp_path, max_new_models=3)
    with pytest.raises(SessionPaused), first:
        app, factory, calls = app_for(tmp_path, first, 1, statuses=(524, 200))
        run(app)
    assert calls == [524, 200]
    budget = factory.providers['candidate'].candidate_budget
    assert budget.calls == 4 and budget.reserved_tokens > 0
    unknown = budget.reserved_tokens
    second = session(tmp_path, first)
    with second:
        app, factory, calls = app_for(tmp_path, second, 2, statuses=(524,), knowledge=NoSearch())
        run(app)
        budget = factory.providers['candidate'].candidate_budget
        assert calls == [524]  # task retry was already spent before restart
        assert budget.calls == 5 and budget.reserved_tokens > unknown
        assert factory.providers['candidate']._retries == 1


def test_pending_intent_never_reinvokes_action(tmp_path):
    first = session(tmp_path)
    def crash():
        raise KeyboardInterrupt()
    with pytest.raises(SessionPaused), first:
        first.operation('model', {'request': 'fixture'}, crash)
    second = session(tmp_path, first)
    with pytest.raises(SessionBlocked, match='unresolved_intent'), second:
        second.operation('model', {'request': 'fixture'}, lambda: pytest.fail('duplicate IO'))


@pytest.mark.parametrize('change', ['request', 'result', 'transport', 'checkpoint', 'binding'])
def test_tampering_or_identity_drift_blocks_before_io(tmp_path, change):
    first = session(tmp_path)
    with first:
        first.operation('tool', {'query': 'fixture'}, lambda: {'chunks': []})
    if change == 'result':
        (first.root/'operations/0001-result.json').write_text('{}', encoding='utf-8')
    elif change == 'transport':
        first.transport_root.mkdir(parents=True)
        (first.transport_root/'unexpected.json').write_text('{}', encoding='utf-8')
    elif change == 'checkpoint':
        (first.root/'checkpoints/0001.json').write_text('{}', encoding='utf-8')
    second = session(tmp_path, first)
    if change == 'binding':
        second.binding['run_id'] = 'wrong'
    with pytest.raises((SessionBlocked, ValueError, KeyError)):
        with second:
            second.operation('tool', {'query': 'changed' if change == 'request' else 'fixture'},
                             lambda: pytest.fail('unexpected replay action'))


def test_kernel_lock_blocks_second_executor_and_releases_after_exit(tmp_path):
    first = session(tmp_path)
    with first:
        second = session(tmp_path, first)
        with pytest.raises(ValueError, match='executor_active'):
            with second:
                pytest.fail('concurrent executor')
    with session(tmp_path, first) as second:
        assert second.status()['operations'] == 0


def test_new_send_requires_preflight_and_closed_session_cannot_append(tmp_path):
    first = session(tmp_path)
    with first:
        first.before_new_model = None
        with pytest.raises(SessionBlocked, match='preflight'):
            first.operation('model', {}, lambda: pytest.fail('sent without preflight'))
        first.close({'fixture': True})
    with session(tmp_path, first) as second:
        with pytest.raises(SessionBlocked, match='closed'):
            second.operation('model', {}, lambda: pytest.fail('reopened'))


def test_real_process_restart_replays_committed_operation(tmp_path):
    # The child has no key/network code. Separate interpreters prove that the
    # completion and its trust roots do not depend on surviving Python objects.
    child = '''
import json,sys
from pathlib import Path
from app.evaluation.sol_natural_session import CandidateSession
p=Path(sys.argv[1]); old=json.loads((p/'pins.json').read_text()) if (p/'pins.json').exists() else {}
with CandidateSession(p/'state',binding={'fixture_only':True},transport_root=p/'transport',
 journal_root=p/'journal',guard_sha=old.get('guard'),checkpoint_sha=old.get('checkpoint')) as s:
 value,replay=s.operation('tool',{'query':'fixture'},lambda:{'value':'original'})
 assert replay == bool(old)
(p/'pins.json').write_text(json.dumps({'guard':s.guard_sha,'checkpoint':s.checkpoint_sha}))
print(json.dumps({'replayed':replay,'value':value}))
'''
    for expected in (False, True):
        value = json.loads(subprocess.check_output([sys.executable, '-c', child, str(tmp_path)], text=True))
        assert value == {'replayed': expected, 'value': {'value': 'original'}}


def crash_after_model(session, ordinal):
    operation = session.operation
    def wrapped(kind, request, action):
        def execute():
            value = action()
            if kind == 'model' and value['budget']['calls'] == ordinal:
                raise KeyboardInterrupt('fixture parent loss after complete response')
            return value
        return operation(kind, request, execute)
    session.operation = wrapped


def test_original_sol_response_is_reconciled_without_another_http(tmp_path):
    first = session(tmp_path)
    crash_after_model(first, 3)
    with pytest.raises(SessionPaused), first:
        app, factory, calls = app_for(tmp_path, first, 1)
        run(app)
    assert calls == [200]
    original = tree(first.transport_root)
    recovered = session(tmp_path, first, reconcile=True)
    with recovered:
        result = recovered.reconcile_completed()
        assert result['provider_requests'] == 0 and result['reconciled_ordinal'] == 3
    assert tree(first.transport_root) == original
    resumed = session(tmp_path, recovered)
    with resumed:
        app, factory, calls = app_for(tmp_path, resumed, 2, knowledge=NoSearch())
        result = run(app)
        assert calls == [200, 200, 200]
        assert factory.providers['candidate'].candidate_budget.calls == 6
        assert result.publication_status.value == 'rejected'


def test_original_flash_response_recovery_is_read_only(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.evaluation import golden_stream_bridge as bridge
    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
    from app.runtime.sol_session_runtime import SessionBudget
    from app.runtime.observed_provider import ObservedLLMProvider
    from tests.test_runtime_execution_factory_combined import _NoopObserver
    from tests.test_natural_duty_transport import generation, scripted_child
    sent = []
    child = scripted_child(sent)
    def timed_child(command, raw, **kwargs):
        response = child(command, raw, **kwargs)
        path = kwargs['directory']/'result.json'
        value = json.loads(path.read_bytes())
        path.write_text(json.dumps(dict(value, elapsed_ms=1)), encoding='utf-8')
        return response
    monkeypatch.setattr(bridge, 'run_child', timed_child)
    factory = SolNaturalProviderFactory(generator_settings=SimpleNamespace(model='glm-5.3-flash',
        api_key='OFFLINE_SENTINEL', base_url='https://open.bigmodel.cn/api/paas/v4'),
        api_key='OFFLINE_SENTINEL', transport_root=tmp_path/'transport')
    first = session(tmp_path)
    crash_after_model(first, 1)
    with pytest.raises(SessionPaused), first:
        provider = ObservedLLMProvider(delegate=factory('candidate'), observer=_NoopObserver(),
                                       request_identity=contract.request_identity)
        budget = SessionBudget(provider, session=first, coach_contract=contract.CONTRACT)
        budget.chat(generation())
    assert len(sent) == 1
    original = tree(first.transport_root)
    recovered = session(tmp_path, first, reconcile=True)
    with recovered:
        assert recovered.reconcile_completed()['reconciled_ordinal'] == 1
    assert original == tree(first.transport_root)
    with session(tmp_path, recovered) as resumed:
        provider = ObservedLLMProvider(delegate=factory('candidate'), observer=_NoopObserver(),
                                       request_identity=contract.request_identity)
        budget = SessionBudget(provider, session=resumed, coach_contract=contract.CONTRACT)
        response = budget.chat(generation())
        assert response.model == 'glm-5.3-flash' and budget.calls == 1
        assert len(sent) == 1


def test_abrupt_process_exit_recovers_uncommitted_complete_transport(tmp_path):
    child = '''
import json,os,sys
from pathlib import Path
from app.evaluation.sol_natural_session import CandidateSession
from tests.test_sol_natural_session import app_for
from tests.test_natural_duty_candidate import run
p=Path(sys.argv[1])
def pins(value): (p/'last-pins.json').write_text(json.dumps(value),encoding='utf-8')
with CandidateSession(p/'session',binding={'run_id':'candidate','fixture_only':True},
 transport_root=p/'transport/candidate',journal_root=p/'journal',checkpoint_sink=pins,
 before_new_model=lambda:None) as s:
 operation=s.operation
 def wrapped(kind,request,action):
  def invoke():
   value=action()
   if kind=='model' and value['budget']['calls']==3: os._exit(79)
   return value
  return operation(kind,request,invoke)
 s.operation=wrapped
 app,_,_=app_for(p,s,'killed')
 run(app)
'''
    result = subprocess.run([sys.executable, '-c', child, str(tmp_path)], timeout=90)
    assert result.returncode == 79
    from types import SimpleNamespace
    pins = json.loads((tmp_path/'last-pins.json').read_bytes())
    previous = SimpleNamespace(guard_sha=pins['guard_sha256'], checkpoint_sha=pins['checkpoint_sha256'])
    with pytest.raises(SessionBlocked, match='uncommitted'):
        with session(tmp_path, previous):
            pytest.fail('uncommitted IO accepted without reconciliation')
    before = tree(tmp_path/'transport')
    recovered = session(tmp_path, previous, reconcile=True)
    with recovered:
        assert recovered.reconcile_completed()['provider_requests'] == 0
    assert before == tree(tmp_path/'transport')
    with session(tmp_path, recovered) as resumed:
        app, factory, calls = app_for(tmp_path, resumed, 'after-kill', knowledge=NoSearch())
        run(app)
        assert calls == [200, 200, 200]
        assert factory.providers['candidate'].candidate_budget.calls == 6
