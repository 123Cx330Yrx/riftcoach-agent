"""Synthetic HTTP/native only: sealed pair -> coverage -> fresh-only tail."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from app.evaluation import sol_review_contract as candidate
from app.evaluation.sol_natural_session import canonical, digest, SessionBlocked, SessionPaused
from app.evaluation.sol_session_review import SessionReviewGate
from app.runtime import sol_natural_provider
from scripts import natural_review_repair_continuation as repair
from scripts import sol_natural_launch as launch
from scripts.reviewer_profile_batch import inventory
from tests.test_sol_natural_candidate import application
from tests.test_sol_natural_launch import grant
from tests.test_sol_session_review import controls, author


def test_sealed_rejection_inherits_exact_pair_and_budgets_without_rebuying(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('inheritance test attempted network or real credentials')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(launch, 'continuation_credentials', deny)
    monkeypatch.setattr(launch, 'current_head', lambda: '1'*40)
    monkeypatch.setattr(launch, 'source', lambda: dict(head='1'*40, files={}))
    monkeypatch.setattr(launch, 'verify_ci', lambda *a: dict(conclusion='success'))
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *a: True)
    monkeypatch.setattr(launch, 'verify_preflight', lambda *a: True)
    keys, calls, generators, receipts = [], [], [], []
    def credentials(*args, **kwargs):
        keys.append('synthetic')
        return None, 'OFFLINE_SENTINEL'
    monkeypatch.setattr(launch, 'credentials', credentials)
    # The continuation must select only the reviewer credential, never GLM.
    from scripts import windows_reviewer_credentials as stored
    def install(target, **kwargs):
        target.continuation_credentials = lambda **kw: credentials()
    monkeypatch.setattr(stored, 'install', install)
    run_roots = {}
    timeout_injected = False
    def factory(**kwargs):
        nonlocal timeout_injected
        root = run_roots['operator']
        statuses = ()
        if root.name == 'parent' and not timeout_injected:
            statuses, timeout_injected = (524,), True
        _, value, _, attempts = application(root/'execution', candidate=candidate, statuses=statuses)
        calls.append(attempts)
        generators.append(value)
        return value
    monkeypatch.setattr(sol_natural_provider, 'SolNaturalProviderFactory', factory)
    original_session_for = launch.session_for
    def session_for(*args, **kwargs):
        return original_session_for(*args, **dict(kwargs, sink=receipts.append))
    monkeypatch.setattr(launch, 'session_for', session_for)
    opened, turns, _ = controls(tmp_path/'history')
    _, template = opened()
    def prepare(name, **kwargs):
        prepared = launch.prepare(tmp_path/name, 'inheritance-fixture', 'synthetic-root',
            'synthetic-child', candidate=candidate, **kwargs)
        p = launch.load(prepared['operator'], prepared['plan_sha256'])
        events = launch.CodexHostReviewEventSource(template.native.event_source.client, p['review_plan'])
        return p, prepared['plan_sha256'], events
    def roots():
        return dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
    def authorization(p, pin, name):
        value = grant(p, pin)
        if p.get('continuation'):
            scope = p['continuation']
            value.update(new_logical_reviews=2, initial_reviews_reused_without_revote=True,
                continuation=dict(parent_seal_sha256=scope['seal_sha256'],
                    max_new_attempts=scope['remaining_attempts'], max_new_tokens=scope['max_new_tokens'],
                    generation_requests=0))
        raw = canonical(value)
        path = tmp_path/(name+'-authorization.json')
        path.write_bytes(raw)
        return dict(authorization_file=path, authorization_sha=digest(raw),
            ci_run='synthetic', preflight_proof={})
    def submit(p, pin, events, handle, accepted=True):
        primary, event = author(handle, turns, workspace=gate.native.workspace,
            accepted=accepted, defect_kind='missed_error')
        path = tmp_path/(Path(p['operator']).name+'-'+handle['binding']['key']+'.json')
        path.write_bytes(canonical(primary))
        return launch.submit(p, pin, events, handle['binding']['key'], path, event,
            authorization_sha=common['authorization_sha'], **roots())
    p, pin, events = prepare('parent')
    common = authorization(p, pin, 'parent')
    run_roots['operator'] = Path(p['operator'])
    current_roots = {}
    for expected in ('facts-initial', 'completion-initial'):
        result = launch.execute(p, pin, events, **common, **current_roots)
        if result.get('reason') == 'session_timeout_awaiting_manual_retry':
            assert expected == 'facts-initial'
            current_roots = roots()
            # Explicit synthetic operator action, never an automatic resume.
            result = launch.execute(p, pin, events, **common, **current_roots, manual_retry=True)
        assert result['reason'] == 'session_awaiting_native_review'
        current_roots = roots()
        session, gate = session_for(p, pin, events, read_only=True,
            authorization_sha=common['authorization_sha'], **current_roots)
        with session:
            handle = list(gate.handles())[-1]
        assert handle['binding']['key'] == expected
        submit(p, pin, events, handle, accepted=expected == 'facts-initial')
        current_roots = roots()
    parent_seal = launch.seal(p, pin, events, authorization_sha=common['authorization_sha'], **current_roots)
    parent = Path(p['operator'])
    proof = repair.audit(parent, parent_seal['seal_sha256'], events)
    proof_file = tmp_path/'repair-proof.json'
    proof_file.write_bytes(canonical(proof))
    proof_sha = digest(proof_file.read_bytes())
    bound = repair.bind(proof_file, proof_sha)
    assert bound['historical_budget']['reserved_tokens'] > 0
    assert bound['historical_budget']['retries'] == 1
    bad = deepcopy(bound)
    bad['historical_budget']['reserved_tokens'] += 1
    with pytest.raises(SessionBlocked, match='scope_changed'):
        repair.verify_parent(bad)
    parent_before = inventory(parent), inventory(parent.with_name(parent.name+'-authors'))
    p, pin, events = prepare('child', repair_proof=proof_file, repair_proof_sha=proof_sha,
        initial_review_rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    common = authorization(p, pin, 'child')
    # An old or narrower grant cannot accidentally become a repair authorization.
    old_grant = json.loads(common['authorization_file'].read_bytes())
    old_grant.pop('initial_reviews_reused_without_revote')
    with pytest.raises(ValueError, match='repair_specific_authorization'):
        launch.validate_grant(old_grant, p, pin)
    run_roots['operator'] = Path(p['operator'])
    count = sum(map(len, calls)), len(keys)
    result = launch.execute(p, pin, events, **common)
    assert result['reason'] == 'session_review_repair_required'
    assert count == (sum(map(len, calls)), len(keys))
    current_roots = roots()
    journal = Path(p['operator'])/'execution/journal'
    operations = Path(p['operator'])/'execution/session/operations'
    for name in proof['parent_inventory']:
        if name.startswith('execution/session/operations/') and name.endswith(('-intent.json','-result.json')):
            assert (operations/Path(name).name).read_bytes() == (parent/name).read_bytes()
    launch.repair_task(p, pin, events, 'completion-initial',
        authorization_sha=common['authorization_sha'], **current_roots)
    current_roots = roots()
    session, gate = session_for(p, pin, events, read_only=True,
        authorization_sha=common['authorization_sha'], **current_roots)
    with session:
        handle = json.loads(gate._repair_file('completion-initial').read_bytes())['handle']
    primary, event = author(handle, turns, gate.native.workspace)
    primary_file = tmp_path/'repair-primary.json'
    primary_file.write_bytes(canonical(primary))
    accepted = launch.repair_submit(p, pin, events, 'completion-initial', primary_file, event,
        authorization_sha=common['authorization_sha'], **current_roots)
    assert accepted['repair_accepted'] and not accepted['original_review_accepted']
    current_roots, host_only, stages = roots(), True, []
    for _ in range(9):
        result = launch.execute(p, pin, events, **common, **current_roots, host_only=host_only)
        current_roots = roots()
        if result['phase'] == 'closed':
            break
        if result['reason'] == 'session_model_boundary':
            assert host_only
            host_only = False
            continue
        assert result['reason'] == 'session_awaiting_native_review'
        session, gate = session_for(p, pin, events, read_only=True,
            authorization_sha=common['authorization_sha'], **current_roots)
        with session:
            handle = list(gate.handles())[-1]
        stages.append(handle['binding']['key'])
        submit(p, pin, events, handle)
        current_roots = roots()
        host_only = stages[-1] != 'facts-fresh'
    else:
        pytest.fail('inherited repair did not finish')
    assert stages == ['compatibility','edit','facts-fresh','completion-fresh']
    assert sum(map(len, calls))-count[0] == 2
    assert sum(len(f.providers[p['run_id']].generator.requests) for f in generators) == 2
    assert len(list(journal.glob('application.json'))) == 1
    outcome = launch.seal(p, pin, events, authorization_sha=common['authorization_sha'], **current_roots)
    assert outcome['strict_replay'] and outcome['rejected_initial_reviews_retained'] == 1
    assert outcome['native_repair_reviews'] == 1 and outcome['continuation']['new_calls'] == 2
    assert outcome['accounting']['calls'] == bound['historical_budget']['calls']+2
    assert outcome['accounting']['reserved_tokens'] == bound['historical_budget']['reserved_tokens']
    assert outcome['accounting']['retries'] == bound['historical_budget']['retries']
    assert parent_before == (inventory(parent), inventory(parent.with_name(parent.name+'-authors')))
