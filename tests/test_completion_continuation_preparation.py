"""Synthetic HTTP/native fixtures: continuation integrity, never model quality."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_necessity_contract as candidate
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, canonical, digest, tree
from app.evaluation.sol_session_review import SessionReviewGate
from scripts import prepare_completion_continuation as preparation
from scripts.host_review_workspace import HostReviewWorkspace
from tests.test_sol_session_review import controls, author
from tests.test_sol_natural_session import app_for, NoSearch
from tests.test_natural_duty_candidate import run


@pytest.fixture
def parent(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('unexpected network')
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket.socket, 'connect', deny)
    opened, turns, _ = controls(tmp_path/'native')
    _, template = opened()
    plan, source = template.plan, template.native.event_source
    root = tmp_path/'parent'
    workspace = HostReviewWorkspace(cwd=Path.cwd(), python=sys.executable,
        answers=tmp_path/'parent-authors', evidence_roots=[root])

    def session(previous=None):
        value = CandidateSession(root/'execution/session',
            binding=dict(fixture_only=True, candidate_contract=candidate.VERSION,
                         review_plan_sha256=digest(canonical(plan))),
            transport_root=root/'execution/transport/candidate', journal_root=root/'execution/journal',
            guard_sha=previous.guard_sha if previous else None,
            checkpoint_sha=previous.checkpoint_sha if previous else None,
            before_new_model=lambda: None, contract_module=candidate)
        gate = SessionReviewGate(value, plan=plan, workspace=workspace, event_source=source)
        return value, gate

    first, gate = session()
    with pytest.raises(SessionPaused, match='awaiting_native'), first:
        app, _, _ = app_for(root/'execution', first, 1, candidate=candidate)
        run(app)
    importer, gate = session(first)
    with importer:
        primary, event = author(list(gate.handles())[-1], turns, workspace)
        assert gate.submit('facts-initial', primary, event)
    failed, gate = session(importer)
    with failed:
        with pytest.raises(SessionPaused, match='format_awaiting_manual_retry'):
            app, factory, calls = app_for(root/'execution', failed, 2,
                candidate=candidate, mode='non_tool', knowledge=NoSearch())
            run(app)
        assert calls == [200] and factory.providers['candidate'].generator.requests == []
        # Model a historical v1 failure, whose code was non_tool_output. The
        # mock v2 text-only reply above uses single_tool_required. These are
        # explicitly synthetic receipt bytes, not a real closed-task rewrite.
        folder = failed.transport_root/'review/call-004'
        for name, key in (('receipt.json', 'worker_code'), ('worker-result.json', 'code')):
            path = folder/name
            value = json.loads(path.read_bytes())
            value[key] = 'non_tool_output'
            path.write_bytes(canonical(value))
        # Refresh only the fixture's checkpoint inventory after the modeled v1
        # receipt is installed; production always reads an external pinned seal.
        failed.expected = failed._inventory()
        failed._checkpoint('synthetic_legacy_receipt')
        failed.operation('journal', dict(name='outcome', data=dict(outcome='candidate_execution_failed')),
            lambda: dict(recorded=True))
        failed.close(dict(synthetic=True))
    (root/'plan.json').write_bytes(canonical(dict(run_id='candidate', review_plan=plan)))
    return dict(root=root, source=source, workspace=workspace, turns=turns,
                spec=preparation.prefix_state(root))


def test_actual_runtime_replays_success_and_original_native_with_all_failed_cost(parent):
    state = parent
    before = tree(state['root']), tree(state['workspace'].answers)
    spec = state['spec']
    assert spec['historical_budget']['calls'] == 4
    assert spec['derived_budget']['calls'] == 4
    assert spec['derived_budget']['logical'] == {'generation': 2, 'review': 1}
    assert spec['derived_budget']['attempts'][-1]['status'] == 'failed'
    assert spec['derived_budget']['tokens'] == spec['historical_budget']['tokens']

    def build(scratch, session):
        app, factory, calls = app_for(scratch, session, 3, candidate=candidate, knowledge=NoSearch())
        try:
            run(app)
        finally:
            assert calls == [] and factory.providers['candidate'].generator.requests == []
            budget = factory.providers['candidate'].candidate_budget
            assert budget.snapshot() == spec['derived_budget']
    proof = preparation.preview_prefix(state['root'], spec, candidate,
        state['workspace'], state['source'], builder=build)
    assert proof['frontier'] == spec['frontier']
    assert proof['original_native_review_replayed'] is True
    assert proof['provider_requests'] == proof['key_reads'] == 0
    assert before == (tree(state['root']), tree(state['workspace'].answers))


@pytest.mark.parametrize('fault', ['native', 'author', 'frontier', 'operation'])
def test_changed_trust_or_request_stops_before_any_new_io(parent, fault):
    state, spec = parent, deepcopy(parent['spec'])
    if fault == 'native':
        state['turns'][0]['items'][-1]['text'] += '\n'
    elif fault == 'author':
        path = next(state['workspace'].answers.glob('*.json'))
        path.write_bytes(path.read_bytes()+b'\n')
    elif fault == 'frontier':
        spec['frontier_sha256'] = '0'*64
    else:
        path = state['root']/'execution/session/operations/0001-result.json'
        row = json.loads(path.read_bytes())
        row['value']['response_raw'] = '{}'
        path.write_bytes(canonical(row))
    with pytest.raises((ValueError, SessionPaused)):
        preparation.preview_prefix(state['root'], spec, candidate, state['workspace'], state['source'],
            builder=lambda scratch, session: run(app_for(scratch, session, 4,
                candidate=candidate, knowledge=NoSearch())[0]))


@pytest.mark.parametrize('fault', ['accepted', 'accounting', 'receipt', 'stage'])
def test_unsupported_parent_cannot_become_completion_continuation(parent, fault):
    root = parent['root']
    paths = sorted((root/'execution/session/operations').glob('*-result.json'))
    if fault == 'receipt':
        path = root/'execution/transport/candidate/review/call-004/receipt.json'
        row = json.loads(path.read_bytes())
        row['usage_state'] = 'unknown'
    else:
        index = -3 if fault == 'accepted' else -2
        path = paths[index]
        row = json.loads(path.read_bytes())
        if fault == 'accepted':
            row['value']['accepted'] = False
        elif fault == 'accounting':
            row['value']['budget']['tokens'] -= 1
        else:
            path = path.with_name(path.name.replace('-result', '-intent'))
            row = json.loads(path.read_bytes())
            row['request']['metadata'][candidate.CONTEXT]['stage'] = 'fresh'
    path.write_bytes(canonical(row))
    with pytest.raises(ValueError, match='completion_parent_'):
        preparation.prefix_state(root)


def test_unpinned_parent_never_launches_its_named_interpreter(tmp_path, monkeypatch):
    root = tmp_path/'untrusted'
    root.mkdir()
    (root/'plan.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(preparation.subprocess, 'run', lambda *a, **kw: pytest.fail('unverified process'))
    with pytest.raises(ValueError, match='original_seal_required'):
        preparation.prepare(root, '0'*64, tmp_path/'output')


@pytest.mark.parametrize('fault', ['edited_plan', 'existing_output', 'author_output'])
def test_controls_and_output_checked_before_starting_worker(tmp_path, monkeypatch, fault):
    root, frozen = tmp_path/'parent', tmp_path/'frozen'
    root.mkdir()
    frozen.mkdir()
    raw = canonical(dict(cwd=str(frozen), python=sys.executable))
    (root/'plan.json').write_bytes(raw)
    seal = canonical(dict(plan_sha256=digest(raw), inventory={'plan.json':digest(raw)}))
    (root/'seal.json').write_bytes(seal)
    output = tmp_path/'output'
    if fault == 'edited_plan':
        (root/'plan.json').write_bytes(raw+b'\n')
    elif fault == 'existing_output':
        output.mkdir()
    else:
        output = tmp_path/'parent-authors'/'child'
    monkeypatch.setattr(preparation.subprocess, 'run', lambda *a, **kw: pytest.fail('unverified worker'))
    with pytest.raises(ValueError, match='completion_parent_inventory_changed|completion_output_must_be_new_external'):
        preparation.prepare(root, digest(seal), output)
