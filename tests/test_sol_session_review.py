"""Synthetic native history checks only, never actual semantic acceptance."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.review_independence_contract import freeze_v2_identity
from scripts.host_review_task_checkpoint import check_answer
from tests.test_sol_natural_session import app_for
from tests.test_natural_duty_candidate import run


def controls(tmp_path):
    plan = freeze_v2_identity({'host_review_submission_mode': 'independent-drafts-v2'},
        root_thread_id='synthetic-root', primary_id='synthetic-root', independent_id='synthetic-child')
    turns = []
    def read(method, params):
        if method == 'thread/read':
            return dict(thread=dict(id='synthetic-child', parentThreadId='synthetic-root',
                source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='synthetic-root')))))
        return dict(data=turns, nextCursor=None)
    source = CodexHostReviewEventSource(SimpleNamespace(request=read), plan)
    workspace = HostReviewWorkspace(cwd=Path.cwd(), python=sys.executable,
        answers=tmp_path/'authors', evidence_roots=[tmp_path/'journal'])
    def open_session(previous=None, **kwargs):
        session = CandidateSession(tmp_path/'session',
            binding=dict(fixture_only=True, review_plan_sha256=digest(canonical(plan))),
            transport_root=tmp_path/'transport/candidate', journal_root=tmp_path/'journal',
            guard_sha=previous.guard_sha if previous else None,
            checkpoint_sha=previous.checkpoint_sha if previous else None,
            before_new_model=lambda: None, **kwargs)
        gate = SessionReviewGate(session, plan=plan, workspace=workspace, event_source=source)
        return session, gate
    return open_session, turns, workspace


def author(handle, turns, workspace, *, accepted=True):
    folder = Path(handle['folder'])
    key, bound = handle['binding']['key'], handle['binding']
    def decision(reviewer):
        assessment = dict(report_sha256=bound['report_sha256'], reviewer=reviewer,
            source_review='Synthetic fixture only', facts_and_sources_correct=True,
            correct_content_preserved=True, identity_and_goal_preserved=True, true_errors_fixed=True)
        return dict(kind=handle['kind'], reviewer=reviewer, material_sha256=handle['material_sha256'],
            source_review='Synthetic fixture only, not a business review', accepted=accepted,
            defects=[] if accepted else [dict(kind='wrong_correction', detail='Synthetic rejection')],
            compatibility='clear' if handle['kind']=='compatibility' else None,
            actual_report_checked=True, report_assessment=assessment if handle['kind']=='edit' else None)
    value = dict(binding=bound, review=dict(binding=bound, decision=decision('synthetic-child')))
    path = workspace.answer_path(folder/'task-checkpoint.json', handle['checkpoint_sha256'])
    raw = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    path.write_bytes(raw)
    check_answer(folder/'task-checkpoint.json', handle['checkpoint_sha256'], raw)
    turns.insert(0, dict(id=key, status='completed', itemsView='full', error=None, items=[
        dict(id='dispatch', type='userMessage', content=[dict(type='text',
             text=(folder/'independent-task.json').read_text(encoding='utf-8'))]),
        dict(id='final', type='agentMessage', phase='final_answer', text=raw.decode('utf-8'))]))
    return decision('synthetic-root'), 'synthetic-child/'+key+'/final'


def test_review_pause_native_import_and_readback(tmp_path):
    open_session, turns, workspace = controls(tmp_path)
    first, gate = open_session()
    with pytest.raises(SessionPaused), first:
        gate.require('facts-initial', 'opinion', {'responses': [], 'report': 'fixture'}, 'fixture')
    second, gate = open_session(first)
    with second:
        handle = list(gate.handles())[-1]
        primary, event = author(handle, turns, workspace)
        assert gate.submit('facts-initial', primary, event)
    third, gate = open_session(second)
    with third:
        gate.require('facts-initial', 'opinion', {'responses': [], 'report': 'fixture'}, 'fixture')
        # Changing an original native event remains a failure on readback.
        turns[0]['items'][-1]['text'] = '{}'
        with pytest.raises(ValueError):
            gate.verify_prior()


def test_native_rejection_closes_without_another_send(tmp_path):
    open_session, turns, workspace = controls(tmp_path)
    first, gate = open_session()
    with pytest.raises(SessionPaused), first:
        gate.require('facts-initial', 'opinion', {'responses': []}, 'fixture')
    second, gate = open_session(first)
    with second:
        primary, event = author(list(gate.handles())[-1], turns, workspace, accepted=False)
        assert not gate.submit('facts-initial', primary, event)
    third, gate = open_session(second)
    with third:
        with pytest.raises(SessionBlocked, match='closed|replay_request_changed'):
            third.operation('model', {}, lambda: pytest.fail('send after rejection'))


def test_equal_json_with_different_author_bytes_is_rejected(tmp_path):
    open_session, turns, workspace = controls(tmp_path)
    first, gate = open_session()
    with pytest.raises(SessionPaused), first:
        gate.require('facts-initial', 'opinion', {'responses': []}, 'fixture')
    second, gate = open_session(first)
    with second:
        handle = list(gate.handles())[-1]
        primary, event = author(handle, turns, workspace)
        turns[0]['items'][-1]['text'] += '\n'
        with pytest.raises(ValueError, match='bytes_mismatch'):
            gate.submit('facts-initial', primary, event)
        assert not (Path(handle['folder'])/'submission.json').exists()


def test_actual_application_waits_for_each_gate_and_applies_once(tmp_path):
    open_session, turns, workspace = controls(tmp_path)
    previous = None
    stages, http, generation = [], 0, 0
    for segment in range(7):
        session, gate = open_session(previous)
        app, factory, calls = app_for(tmp_path, session, segment)
        try:
            with session:
                result = run(app)
        except SessionPaused:
            assert segment < 6
        else:
            assert segment == 6 and result.publication_status.value == 'rejected'
            assert factory.providers['candidate'].candidate_budget.calls == 6
        http += len(calls)
        generation += len(factory.providers['candidate'].generator.requests)
        previous = session
        if segment == 6:
            break
        importer, gate = open_session(previous)
        with importer:
            handle = list(gate.handles())[-1]
            key = handle['binding']['key']
            stages.append(key)
            if key in ('facts-initial', 'completion-initial', 'compatibility', 'edit'):
                assert not (importer.journal_root/'application.json').exists()
            material = json.loads((Path(handle['folder'])/'material.json').read_bytes())
            assert material['source_checkpoint_sha256'] and material['session_guard_sha256']
            primary, event = author(handle, turns, workspace)
            assert gate.submit(key, primary, event)
        previous = importer
    assert stages == ['facts-initial', 'completion-initial', 'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
    assert http == 4 and generation == 2
    assert len(list((tmp_path/'journal').glob('application.json'))) == 1
