"""Actual Application/Runtime with mock HTTP/native: repair is not opinion pass."""
import json
from pathlib import Path
import socket

import pytest

from app.evaluation.sol_natural_session import SessionPaused, SessionBlocked, tree
from app.evaluation.sol_session_review import SessionReviewGate
from tests.test_sol_session_review import controls, author
from tests.test_sol_natural_session import app_for, NoSearch
from tests.test_natural_duty_candidate import run


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('repair checks cannot access network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


@pytest.mark.parametrize('approve', [True, False])
def test_repair_review_preserves_rejection_and_resumes_exact_application(tmp_path, approve):
    opened, turns, workspace = controls(tmp_path, rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    previous = None
    stages, http, generation = [], 0, 0
    rejected = None
    repaired_report = None
    for segment in range(7):
        session, gate = opened(previous)
        app, factory, calls = app_for(tmp_path, session, segment)
        try:
            with session:
                result = run(app)
        except SessionPaused:
            assert segment < 6
        else:
            assert segment == 6 and result.publication_status.value == 'rejected'
        http += len(calls)
        generation += len(factory.providers['candidate'].generator.requests)
        previous = session
        if segment == 6:
            break
        importer, gate = opened(previous)
        with importer:
            handle = list(gate.handles())[-1]
            key = handle['binding']['key']
            stages.append(key)
            primary, event = author(handle, turns, workspace,
                accepted=key != 'completion-initial', defect_kind='missed_error')
            assert gate.submit(key, primary, event) is (key != 'completion-initial')
            if key == 'completion-initial':
                rejected = tree(Path(handle['folder']))
                assert not (importer.root/'terminal.json').exists()
                with pytest.raises(SessionPaused, match='repair_required'):
                    gate.verify_prior()
                repair = gate.prepare_repair(key)
                assert gate.prepare_repair(key) == repair  # Same task, no redispatch.
                material = json.loads((Path(repair['folder'])/'material.json').read_bytes())
                repaired_report = material['report']
                assert material['original_reviews']['completion']['primary']['decision']['accepted'] is False
                assert repaired_report != material['original_report']
                repair_primary, repair_event = author(repair, turns, workspace, accepted=approve)
                assert gate.submit_repair(key, repair_primary, repair_event) is approve
                assert tree(Path(handle['folder'])) == rejected
                assert not (importer.root/'terminal.json').exists()
                with pytest.raises(ValueError, match='already_submitted'):
                    gate.submit_repair(key, repair_primary, repair_event)
                if not approve:
                    with pytest.raises(SessionPaused, match='repair_required'):
                        gate.verify_prior()
                    with pytest.raises(SessionBlocked, match='selection_changed'):
                        gate.prepare_repair(key, coordination={'invalid': True})
                    assert not (importer.journal_root/'application.json').exists()
                    return
                gate.verify_prior()
                with pytest.raises(SessionBlocked, match='actual_report_changed'):
                    gate.verify_repair_report(repaired_report+' changed')
        previous = importer
    assert stages == ['facts-initial', 'completion-initial', 'compatibility', 'edit',
                      'facts-fresh', 'completion-fresh']
    assert http == 4 and generation == 2
    assert len(list((tmp_path/'journal').glob('application.json'))) == 1
    applied = json.loads((tmp_path/'journal/application.json').read_bytes())
    from app.evaluation.sol_natural_session import digest
    assert applied['report_sha256'] == digest(repaired_report.encode())
    for key in ('facts-fresh', 'completion-fresh'):
        material = json.loads((tmp_path/'journal/host'/key/'material.json').read_bytes())
        assert material['report'] == repaired_report
    before = tree(tmp_path/'session'), tree(tmp_path/'journal'), tree(tmp_path/'transport')
    replay, gate = opened(previous, read_only=True)
    with replay:
        app, factory, calls = app_for(tmp_path, replay, 'replay', knowledge=NoSearch())
        run(app)
        assert calls == [] and factory.providers['candidate'].generator.requests == []
    assert before == (tree(tmp_path/'session'), tree(tmp_path/'journal'), tree(tmp_path/'transport'))
    # Changing the coverage event blocks readback even though the old rejection remains.
    repair_turn = next(t for t in turns if t['id'] == 'completion-initial-repair')
    repair_turn['items'][-1]['text'] = '{}'
    verify, gate = opened(previous, read_only=True)
    with verify, pytest.raises(ValueError):
        gate.verify_prior()
