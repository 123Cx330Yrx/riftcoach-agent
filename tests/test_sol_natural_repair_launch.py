"""Launcher through strict seal with mock HTTP/native; no live quality claim."""
import json
from pathlib import Path
import socket

import pytest

from app.evaluation import sol_review_contract as candidate
from app.evaluation.sol_natural_session import digest
from app.evaluation.sol_session_review import SessionReviewGate
from app.runtime import sol_natural_provider
from scripts import sol_natural_launch as launch
from scripts.reviewer_profile_batch import inventory
from tests.test_sol_natural_candidate import application
from tests.test_sol_natural_launch import grant
from tests.test_sol_session_review import controls, author


def test_rejected_initial_repair_through_launcher_replay_and_seal(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('repair launcher cannot access network or real credentials')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(launch, 'continuation_credentials', deny)
    monkeypatch.setattr(launch, 'current_head', lambda: '1'*40)
    monkeypatch.setattr(launch, 'source', lambda: dict(head='1'*40, files={}))
    prepared = launch.prepare(tmp_path/'operator', 'repair-fixture', 'synthetic-root',
        'synthetic-child', candidate=candidate,
        initial_review_rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    pin = prepared['plan_sha256']
    p = launch.load(prepared['operator'], pin)
    opened, turns, _ = controls(tmp_path/'history')
    _, template = opened()
    native = launch.CodexHostReviewEventSource(template.native.event_source.client, p['review_plan'])
    keys, attempts, factories, receipts = [], [], [], []
    monkeypatch.setattr(launch, 'verify_ci', lambda *args: dict(conclusion='success'))
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *args: True)
    monkeypatch.setattr(launch, 'verify_preflight', lambda *args: True)
    def credentials(*args, **kwargs):
        keys.append('synthetic')
        return None, 'OFFLINE_SENTINEL'
    monkeypatch.setattr(launch, 'credentials', credentials)
    def factory(**kwargs):
        assert kwargs['contract_module'] is candidate
        _, value, _, calls = application(Path(p['operator'])/'execution', candidate=candidate)
        factories.append(value)
        attempts.append(calls)
        return value
    monkeypatch.setattr(sol_natural_provider, 'SolNaturalProviderFactory', factory)
    original_session_for = launch.session_for
    def session_for(*args, **kwargs):
        return original_session_for(*args, **dict(kwargs, sink=receipts.append))
    monkeypatch.setattr(launch, 'session_for', session_for)
    raw = json.dumps(grant(p, pin)).encode()
    authorization = tmp_path/'authorization.json'
    authorization.write_bytes(raw)
    auth = dict(authorization_sha=digest(raw))
    common = dict(**auth, authorization_file=authorization, ci_run='synthetic', preflight_proof={})
    def roots():
        return dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
    def primary_file(value, name):
        path = tmp_path/(name+'.json')
        path.write_text(json.dumps(value), encoding='utf-8')
        return path
    stages, host_only, saved_rejection, repaired_report = [], False, None, None
    journal = Path(p['operator'])/'execution/journal'
    current_roots = {}
    for _ in range(12):
        result = launch.execute(p, pin, native, **common, **current_roots, host_only=host_only)
        current_roots = roots()
        if result['phase'] == 'closed':
            break
        if result['reason'] == 'session_model_boundary':
            assert host_only and (journal/'application.json').exists()
            host_only = False
            continue
        assert result['reason'] == 'session_awaiting_native_review'
        current, gate = session_for(p, pin, native, read_only=True, **auth, **current_roots)
        with current:
            handle = list(gate.handles())[-1]
        key = handle['binding']['key']
        stages.append(key)
        accepted = key != 'completion-initial'
        primary, event = author(handle, turns, gate.native.workspace, accepted=accepted,
            defect_kind='missed_error')
        submitted = launch.submit(p, pin, native, key, primary_file(primary, key), event,
            **auth, **current_roots)
        assert submitted['accepted'] is accepted
        current_roots = roots()
        if not accepted:
            saved_rejection = inventory(Path(handle['folder']))
            count = len(keys), sum(map(len, attempts))
            pending = launch.execute(p, pin, native, **common, **current_roots)
            assert pending['reason'] == 'session_review_repair_required'
            assert count == (len(keys), sum(map(len, attempts)))
            current_roots = roots()
            dispatch = launch.repair_task(p, pin, native, key, **auth, **current_roots)
            current_roots = roots()
            current, gate = session_for(p, pin, native, read_only=True, **auth, **current_roots)
            with current:
                saved = json.loads(gate._repair_file(key).read_bytes())
                repair = saved['handle']
                assert dispatch == (Path(repair['folder'])/'dispatch.txt').read_text(encoding='utf-8')
                repaired_report = json.loads((Path(repair['folder'])/'material.json').read_bytes())['report']
            primary, event = author(repair, turns, gate.native.workspace)
            repaired = launch.repair_submit(p, pin, native, key, primary_file(primary, 'repair'), event,
                **auth, **current_roots)
            assert repaired == dict(repair_accepted=True, original_review_accepted=False,
                provider_requests=0, key_read=False)
            assert count == (len(keys), sum(map(len, attempts)))
            assert saved_rejection == inventory(Path(handle['folder']))
            current_roots = roots()
        host_only = key not in ('facts-initial', 'facts-fresh')
    else:
        pytest.fail('launcher repair never completed')
    assert stages == ['facts-initial', 'completion-initial', 'compatibility', 'edit',
                      'facts-fresh', 'completion-fresh']
    assert sum(map(len, attempts)) == 4
    assert sum(len(f.providers[p['run_id']].generator.requests) for f in factories) == 2
    applied = json.loads((journal/'application.json').read_bytes())
    assert applied['report_sha256'] == digest(repaired_report.encode())
    assert len(list(journal.glob('application.json'))) == 1
    for key in ('facts-fresh', 'completion-fresh'):
        material = json.loads((journal/'host'/key/'material.json').read_bytes())
        assert material['report'] == repaired_report
    originals, count = inventory(p['operator']), (len(keys), sum(map(len, attempts)))
    readback = launch.replay(p, pin, native, **auth, **current_roots)
    assert readback['strict_replay'] and readback['rejected_initial_reviews_retained'] == 1
    assert readback['native_repair_reviews'] == 1 and readback['native_reviews'] == 6
    assert originals == inventory(p['operator'])
    sealed = launch.seal(p, pin, native, **auth, **current_roots)
    assert sealed['sealed'] and sealed['strict_replay'] and sealed['accounting']['calls'] == 6
    assert not sealed['publication_allowed']
    assert count == (len(keys), sum(map(len, attempts)))
    assert saved_rejection == inventory(journal/'host/completion-initial')
    with pytest.raises(ValueError, match='seal_already_exists'):
        launch.seal(p, pin, native, **auth, **current_roots)
