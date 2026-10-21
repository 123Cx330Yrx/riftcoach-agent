"""Launch boundaries, entirely offline; no semantic or real-provider claim."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_natural_contract as contract
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, SessionPaused, digest
from scripts import sol_natural_launch as launch
from scripts.prepare_sol_natural import capture, CaptureFactory
from tests.test_sol_session_review import controls, author


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('unexpected network/key access')
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(launch, 'credentials', deny)


def test_actual_application_entry_passes_persistent_session_before_first_io(tmp_path):
    first, _ = capture('launch-offline-check')
    session = CandidateSession(tmp_path/'session',
        binding=dict(fixture_only=True, first_request_sha256=launch.first_pin(first)),
        transport_root=tmp_path/'transport'/'launch-offline-check', journal_root=tmp_path/'journal',
        before_new_model=lambda: pytest.fail('offline preparation sent'), max_new_models=0)
    factory = CaptureFactory()
    # CaptureFactory's reviewer directory must bind the actual session transport.
    from app.runtime.sol_natural_provider import SolReviewProvider, SolNaturalProvider
    old_make = factory.make
    def make():
        old = old_make()
        return SolNaturalProvider(old.generator, SolReviewProvider(api_key='',
            directory=session.transport_root/'review', task_directory=session.transport_root))
    factory.make = make
    factory.descriptor = factory.make()
    with pytest.raises(SessionPaused, match='model_boundary'), session:
        app = launch.base.build_application(provider_factory=factory, output_root=tmp_path/'derived',
            run_id='launch-offline-check', candidate=contract, execution_session=session)
        app.run()
    assert factory.first is None
    assert session.status()['operations'] == 0
    assert not session.transport_root.exists()


def test_first_request_change_is_rejected_before_intent_or_send(tmp_path):
    session = CandidateSession(tmp_path/'session', binding=dict(first_request_sha256='0'*64),
        transport_root=tmp_path/'transport', journal_root=tmp_path/'journal',
        before_new_model=lambda: pytest.fail('preflight should not be reached'))
    with session:
        with pytest.raises(SessionBlocked, match='first_request_changed'):
            session.operation('model', {'changed': True}, lambda: pytest.fail('sent'))
        assert session.status()['operations'] == 0


def plan(tmp_path, monkeypatch):
    monkeypatch.setattr(launch, 'current_head', lambda: '1'*40)
    monkeypatch.setattr(launch, 'source', lambda: dict(head='1'*40, files={}))
    operator = tmp_path/'operator'
    roots = launch.prepare(operator, 'launch-fixture', 'synthetic-root', 'synthetic-child')
    return launch.load(operator, roots['plan_sha256']), roots['plan_sha256']


def grant(p, pin):
    now = datetime.now(timezone.utc)
    return dict(version=launch.VERSION+'-authorization', issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat(), plan_sha256=pin, head=p['head'],
        run_id=p['run_id'], limits=p['limits'], estimated_uncached_cny=p['estimated_uncached_cny'],
        retry_authorized=True, production_admitted=False, user_authorization_evidence='Synthetic test only')


def test_preparation_create_only_pinned_and_no_run(tmp_path, monkeypatch):
    p, pin = plan(tmp_path, monkeypatch)
    assert not (Path(p['operator'])/'execution').exists()
    assert p['offline']['provider_requests'] == 0 and not p['execution_authorized']
    assert launch.load(p['operator'], pin, frozen=True) == p
    with pytest.raises(ValueError, match='already_exists'):
        launch.prepare(p['operator'], p['run_id'], 'synthetic-root', 'synthetic-child')
    with pytest.raises(ValueError, match='original_plan'):
        launch.load(p['operator'], '0'*64)
    monkeypatch.setattr(launch, 'source', lambda: {'different': True})
    with pytest.raises(ValueError, match='frozen_source'):
        launch.load(p['operator'], pin, frozen=True)


@pytest.mark.parametrize('change', ['expired', 'extra_budget', 'old_authorization', 'no_retry_consent'])
def test_invalid_grant_rejects_before_credentials(tmp_path, monkeypatch, change):
    p, pin = plan(tmp_path, monkeypatch)
    value = grant(p, pin)
    if change == 'expired':
        value['expires_at'] = value['issued_at']
    elif change == 'extra_budget':
        value['limits'] = dict(value['limits'], max_calls=8)
    elif change == 'old_authorization':
        value['version'] = 'old-six-call-grant'
    else:
        value['retry_authorized'] = False
    raw = json.dumps(value).encode()
    path = tmp_path/'authorization.json'
    path.write_bytes(raw)
    with pytest.raises(ValueError, match='authorization_required'):
        launch.execute(p, pin, None, authorization_file=path, authorization_sha=digest(raw),
                       ci_run='synthetic', preflight_proof={})
    assert not (Path(p['operator'])/'execution').exists()


def test_native_preflight_authors_import_and_exact_dispatch(tmp_path, monkeypatch):
    p, pin = plan(tmp_path, monkeypatch)
    open_session, turns, _ = controls(tmp_path/'history')
    _, example_gate = open_session()
    native = launch.CodexHostReviewEventSource(example_gate.native.event_source.client, p['review_plan'])
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *a: {'verified': True})
    receipts = []
    monkeypatch.setattr(launch, 'emit', receipts.append)
    # session_for's default sink is fixed at definition time; capture independently.
    original = launch.session_for
    def session_for(*a, **kw):
        return original(*a, **dict(kw, sink=receipts.append))
    monkeypatch.setattr(launch, 'session_for', session_for)
    launch.native_task(p, pin, native)
    roots = receipts[-1]
    kw = dict(preflight=True, guard=roots['guard_sha256'], checkpoint=roots['checkpoint_sha256'])
    dispatch = launch.inspect_task(p, pin, native, **kw)
    assert str(Path(sys.executable).absolute()) in dispatch
    session, gate = session_for(p, pin, native, read_only=True, **kw)
    with session:
        handle = list(gate.handles())[-1]
    primary, event = author(handle, turns, gate.native.workspace)
    primary_path = tmp_path/'primary.json'
    primary_path.write_text(json.dumps(primary), encoding='utf-8')
    assert launch.submit(p, pin, native, 'startup-preflight', primary_path, event, **kw)['accepted']
    roots = receipts[-1]
    assert launch.verify_preflight(p, pin, native, roots)
    turns[0]['items'][-1]['text'] += '\n'
    with pytest.raises(ValueError):
        launch.verify_preflight(p, pin, native, roots)
    assert not (Path(p['operator'])/'execution').exists()


@pytest.mark.parametrize('failing_check', ['ci', 'lineage', 'preflight'])
def test_execution_checks_fail_before_claim_and_keys(tmp_path, monkeypatch, failing_check):
    from types import SimpleNamespace
    p, pin = plan(tmp_path, monkeypatch)
    raw = json.dumps(grant(p, pin)).encode()
    path = tmp_path/'authorization.json'
    path.write_bytes(raw)
    for name, selected in [('verify_ci', 'ci'), ('verify_native_principals', 'lineage'),
                           ('verify_preflight', 'preflight')]:
        def check(*args, selected=selected):
            if selected == failing_check:
                raise ValueError('synthetic_'+selected+'_unavailable')
            return {'verified': True}
        monkeypatch.setattr(launch, name, check)
    with pytest.raises(ValueError, match='synthetic_'+failing_check):
        launch.execute(p, pin, SimpleNamespace(client=None), authorization_file=path,
            authorization_sha=digest(raw), ci_run='synthetic', preflight_proof={})
    assert not (Path(p['operator'])/'execution').exists()


def test_launcher_runs_real_application_resumes_gates_and_never_rebuys(tmp_path, monkeypatch):
    from tests.test_sol_natural_candidate import application
    from app.runtime import sol_natural_provider
    p, pin = plan(tmp_path, monkeypatch)
    open_history, turns, _ = controls(tmp_path/'history')
    _, example_gate = open_history()
    native = launch.CodexHostReviewEventSource(example_gate.native.event_source.client, p['review_plan'])
    monkeypatch.setattr(launch, 'verify_ci', lambda *a: {'conclusion': 'success'})
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *a: {'verified': True})
    monkeypatch.setattr(launch, 'verify_preflight', lambda *a: True)  # exercised separately above
    keys = []
    def credentials():
        keys.append('synthetic')
        return None, 'OFFLINE_SENTINEL'
    monkeypatch.setattr(launch, 'credentials', credentials)
    factories, requests = [], []
    def factory(**kwargs):
        _, value, _, calls = application(Path(p['operator'])/'execution')
        factories.append(value)
        requests.append(calls)
        return value
    monkeypatch.setattr(sol_natural_provider, 'SolNaturalProviderFactory', factory)
    receipts = []
    original = launch.session_for
    def session_for(*a, **kw):
        return original(*a, **dict(kw, sink=receipts.append))
    monkeypatch.setattr(launch, 'session_for', session_for)
    raw = json.dumps(grant(p, pin)).encode()
    path = tmp_path/'authorization.json'
    path.write_bytes(raw)
    authorization_sha = digest(raw)
    common = dict(authorization_file=path, authorization_sha=authorization_sha,
                  ci_run='synthetic', preflight_proof={})
    roots, stages = {}, []
    for index in range(7):
        result = launch.execute(p, pin, native, **common, **roots)
        roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
        if result['phase'] == 'closed':
            break
        assert result['reason'] == 'session_awaiting_native_review'
        # Re-running at the same unsatisfied gate must not even ask for a key.
        key_count = len(keys)
        again = launch.execute(p, pin, native, **common, **roots)
        assert again['phase'] == 'paused' and len(keys) == key_count
        roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
        session, gate = session_for(p, pin, native, authorization_sha=authorization_sha,
                                   read_only=True, **roots)
        with session:
            handle = list(gate.handles())[-1]
        key = handle['binding']['key']
        stages.append(key)
        primary, event = author(handle, turns, gate.native.workspace)
        primary_path = tmp_path/f'primary-{index}.json'
        primary_path.write_text(json.dumps(primary), encoding='utf-8')
        launch.submit(p, pin, native, key, primary_path, event,
                      authorization_sha=authorization_sha, **roots)
        roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
    assert result['phase'] == 'closed'
    assert stages == ['facts-initial', 'completion-initial', 'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
    assert sum(map(len, requests)) == 4
    assert sum(len(f.providers[p['run_id']].generator.requests) for f in factories) == 2
    assert len(list((Path(p['operator'])/'execution/journal').glob('application.json'))) == 1
    calls_before = sum(map(len, requests))
    replayed = launch.replay(p, pin, native, authorization_sha=authorization_sha, **roots)
    assert replayed['strict_replay'] and replayed['accounting']['calls'] == 6
    assert replayed['native_reviews'] == 6
    assert sum(map(len, requests)) == calls_before
    sealed = launch.seal(p, pin, native, authorization_sha=authorization_sha, **roots)
    assert sealed['sealed'] and not sealed['production_admitted']
    with pytest.raises(ValueError, match='seal_already_exists'):
        launch.seal(p, pin, native, authorization_sha=authorization_sha, **roots)
    with pytest.raises(SessionBlocked, match='closed'):
        launch.execute(p, pin, native, **common, **roots)
