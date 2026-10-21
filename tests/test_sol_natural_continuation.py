"""Actual launcher continuation with synthetic HTTP; no live model evidence."""
from copy import deepcopy
from pathlib import Path
import json
import socket
import sys
from unittest.mock import patch

import pytest

from app.evaluation.sol_natural_session import canonical, digest, SessionBlocked, tree
from scripts import sol_natural_launch as launch
from scripts import sol_natural_continuation as continuation
from tests.test_sol_natural_launch import grant
from tests.test_sol_natural_candidate import application
from tests.test_sol_session_review import controls, author


@pytest.fixture
def setup(tmp_path, monkeypatch):
    def deny(*a, **kw):
        pytest.fail('unexpected network/key/generation')
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(launch, 'current_head', lambda:'1'*40)
    monkeypatch.setattr(launch, 'source', lambda:dict(head='1'*40,files={},
        python=sys.executable,python_version=sys.version,packages={}))
    prepared = launch.prepare(tmp_path/'operator','launch-fixture','synthetic-root','synthetic-child')
    pin = prepared['plan_sha256']
    p = launch.load(prepared['operator'],pin)
    # Keep this history's event list for subsequent unique author imports.
    opened, turns, _ = controls(tmp_path/'native')
    _, gate = opened()
    native = launch.CodexHostReviewEventSource(gate.native.event_source.client, p['review_plan'])
    monkeypatch.setattr(launch, 'verify_ci', lambda *a: {'conclusion':'success'})
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *a: True)
    monkeypatch.setattr(launch, 'verify_preflight', lambda *a: True)
    monkeypatch.setattr(launch, 'credentials', lambda: (None, 'OFFLINE_SENTINEL'))
    monkeypatch.setattr(launch, 'continuation_credentials', lambda: (None, 'OFFLINE_SENTINEL'))
    state = dict(plan=p, mode='reasoning_conflict', factories=[], requests=[], statuses=())
    from app.runtime import sol_natural_provider
    state['real_factory'] = sol_natural_provider.SolNaturalProviderFactory
    def factory(**kwargs):
        _, value, _, calls = application(Path(state['plan']['operator'])/'execution',
            mode=state['mode'], statuses=state['statuses'])
        if state['plan'].get('continuation'):
            original = value.make
            def make(name):
                router = original(name)
                router.generator.chat = deny
                return router
            value.make = make
        state['factories'].append(value)
        state['requests'].append(calls)
        return value
    monkeypatch.setattr(sol_natural_provider, 'SolNaturalProviderFactory', factory)
    pins = []
    original_session = launch.session_for
    monkeypatch.setattr(launch, 'session_for', lambda *a, **kw:
        original_session(*a, **dict(kw, sink=pins.append)))
    raw = canonical(grant(p, pin))
    auth = tmp_path/'parent-grant.json'
    auth.write_bytes(raw)
    common = dict(authorization_file=auth, authorization_sha=digest(raw),
                  ci_run='synthetic', preflight_proof={})
    assert launch.execute(p, pin, native, **common)['phase'] == 'closed'
    roots = dict(guard=pins[-1]['guard_sha256'], checkpoint=pins[-1]['checkpoint_sha256'])
    sealed = launch.seal(p, pin, native, authorization_sha=common['authorization_sha'], **roots)
    assert sealed['accounting']['calls'] == 3
    state.update(native=native, turns=turns, pins=pins, parent=p, parent_pin=pin,
                 seal=sealed, parent_inventory=tree(Path(p['operator'])))
    return state


def prepare_child(state, tmp_path):
    p = state['parent']
    # Preparation uses its real offline factory; the test's sender factory is
    # safe too, but preview pauses before it can send or search.
    with patch('app.runtime.sol_natural_provider.SolNaturalProviderFactory',state['real_factory']):
        result = launch.prepare(tmp_path/'continued', p['run_id'], 'synthetic-root','synthetic-child',
            parent_operator=p['operator'], parent_seal_sha=state['seal']['seal_sha256'])
    child = launch.load(result['operator'], result['plan_sha256'])
    state.update(plan=child, mode='repair', factories=[], requests=[])
    value = grant(child, result['plan_sha256'])
    spec = child['continuation']
    value['continuation'] = dict(parent_seal_sha256=spec['seal_sha256'],
        max_new_attempts=4, max_new_tokens=321536, generation_requests=0)
    path = tmp_path/'child-grant.json'
    path.write_bytes(canonical(value))
    return child, result['plan_sha256'], dict(authorization_file=path,
        authorization_sha=digest(path.read_bytes()), ci_run='synthetic', preflight_proof={})


def test_continue_four_reviews_and_native_gates_without_rebuying_prefix(setup, tmp_path, monkeypatch):
    s = setup
    p, pin, common = prepare_child(s, tmp_path)
    spec = p['continuation']
    assert p['offline']['continuation_frontier']['generation_requests'] == 0
    assert spec['historical_budget']['calls'] == 3 and spec['remaining_attempts'] == 4
    assert p['estimated_uncached_cny'] == '0.233472'
    roots, stages = {}, []
    for n in range(7):
        result = launch.execute(p, pin, s['native'], **common, **roots)
        roots = dict(guard=s['pins'][-1]['guard_sha256'], checkpoint=s['pins'][-1]['checkpoint_sha256'])
        if result['phase'] == 'closed':
            break
        session, gate = launch.session_for(p, pin, s['native'], read_only=True,
            authorization_sha=common['authorization_sha'], **roots)
        with session:
            handle = list(gate.handles())[-1]
        stages.append(handle['binding']['key'])
        primary, event = author(handle, s['turns'], gate.native.workspace)
        path = tmp_path/f'primary-{n}.json'
        path.write_bytes(canonical(primary))
        launch.submit(p, pin, s['native'], stages[-1], path, event,
            authorization_sha=common['authorization_sha'], **roots)
        roots = dict(guard=s['pins'][-1]['guard_sha256'], checkpoint=s['pins'][-1]['checkpoint_sha256'])
    assert result['phase'] == 'closed'
    assert stages == ['facts-initial','completion-initial','compatibility','edit','facts-fresh','completion-fresh']
    assert sum(map(len,s['requests'])) == 4
    assert all(not f.providers[p['run_id']].generator.requests for f in s['factories'])
    sealed = launch.seal(p, pin, s['native'], authorization_sha=common['authorization_sha'], **roots)
    assert sealed['accounting']['calls'] == 7
    assert sealed['accounting']['tokens'] == spec['historical_budget']['tokens']+80
    assert sealed['continuation']['new_calls'] == 4
    assert sealed['continuation']['historical_failure_retained']
    assert len(list((Path(p['operator'])/'execution/journal').glob('application.json'))) == 1
    assert tree(Path(s['parent']['operator'])) == s['parent_inventory']
    assert not sealed['production_admitted'] and not sealed['publication_allowed']


def test_parent_tamper_and_unapproved_continuation_block_before_keys(setup, tmp_path, monkeypatch):
    s = setup
    p, pin, common = prepare_child(s, tmp_path)
    def deny(): pytest.fail('asked for key')
    monkeypatch.setattr(launch, 'continuation_credentials', deny)
    value = json.loads(common['authorization_file'].read_bytes())
    value.pop('continuation')
    common['authorization_file'].write_bytes(canonical(value))
    common['authorization_sha'] = digest(common['authorization_file'].read_bytes())
    with pytest.raises(ValueError, match='continuation_specific_authorization'):
        launch.execute(p, pin, s['native'], **common)
    assert not (Path(p['operator'])/'execution').exists()
    parent = Path(s['parent']['operator'])
    (parent/'execution/session/operations/0001-result.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError, match='parent_inventory'):
        continuation.verify_parent(p['continuation'])


def test_frontier_mismatch_blocks_new_claim_and_import_preserves_failed_cost(setup, tmp_path):
    s = setup
    p, pin, common = prepare_child(s, tmp_path)
    session, _ = launch.session_for(p, pin, s['native'],
        authorization_sha=common['authorization_sha'], before=lambda: pytest.fail('preflight reached'))
    with session:
        spec = p['continuation']
        for n in range(1,spec['prefix_operations']+1):
            i = json.loads((session.root/f'operations/{n:04d}-intent.json').read_bytes())
            value,replayed = session.operation(i['kind'],i['request'],lambda:pytest.fail('prefix rerun'))
            assert replayed
        assert value['budget']['tokens'] == spec['historical_budget']['tokens']
        assert value['budget']['attempts'][-1]['status'] == 'failed'
        with pytest.raises(SessionBlocked,match='frontier_changed'):
            session.operation('model',{'metadata':{}},lambda:pytest.fail('sent'))
        assert session.status()['operations'] == spec['prefix_operations']
        # Even if later runtime code tried to generate again, fail before IO.
        session.cursor += 1
        with pytest.raises(SessionBlocked,match='generation_forbidden'):
            session.operation('model',{'metadata':{}},lambda:pytest.fail('sent'))
        session.cursor -= 1


def test_review_only_credentials_do_not_read_generator_config(monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin,'isatty',lambda:True)
    prompts=[]
    def prompt(message):
        prompts.append(message)
        return 'OFFLINE_REVIEW_KEY'
    monkeypatch.setattr(launch.getpass,'getpass',prompt)
    settings,key=launch.continuation_credentials()
    assert key=='OFFLINE_REVIEW_KEY' and settings.api_key=='UNUSED_GENERATION_FORBIDDEN'
    assert prompts==['Tianjige GPT-pro API key (hidden): ']
    captured=capsys.readouterr()
    assert key not in captured.out+captured.err


def test_source_changes_cannot_hide_generation_or_prompt_changes():
    previous = dict(files={'app/generate.py':'old'}, python='py',python_version='v',packages={})
    spec = dict(source=previous)
    current = deepcopy(previous)
    current['files']['scripts/sol_natural_launch.py']='new'
    assert continuation.verify_source(spec,current)==['scripts/sol_natural_launch.py']
    current['files']['app/generate.py']='new'
    with pytest.raises(ValueError,match='unrelated_source'):
        continuation.verify_source(spec,current)
