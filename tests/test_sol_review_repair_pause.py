"""Prospective pause preserves real rejected native evidence and prevents IO."""
from pathlib import Path

import pytest

from app.evaluation.sol_natural_session import SessionPaused, tree
from app.evaluation.sol_session_review import SessionReviewGate
from tests.test_sol_session_review import controls, author


@pytest.mark.parametrize('stage', ['facts-initial', 'completion-initial'])
def test_missed_error_pause_survives_restart_without_repeat_or_send(tmp_path, stage):
    opened, turns, workspace = controls(tmp_path, rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    first, gate = opened()
    with pytest.raises(SessionPaused), first:
        gate.require(stage, 'opinion', {'responses': []}, 'fixture')
    second, gate = opened(first)
    with second:
        handle = list(gate.handles())[-1]
        primary, event = author(handle, turns, workspace, accepted=False, defect_kind='missed_error')
        assert gate.submit(stage, primary, event) is False
        assert not (second.root/'terminal.json').exists()
    originals = tree(second.journal_root)
    third, gate = opened(second)
    with third:
        with pytest.raises(SessionPaused, match='review_repair_required'):
            gate.require(stage, 'opinion', {'responses': []}, 'fixture')
        assert len(list(gate.handles())) == 1
        # A different new model operation must still fail before intent/action.
        third.cursor = len(list((third.root/'operations').glob('*-intent.json')))
        with pytest.raises(SessionPaused, match='review_repair_required'):
            third.operation('model', {'new': True}, lambda: pytest.fail('unresolved rejection sent'))
        with pytest.raises(SessionPaused, match='review_repair_required'):
            gate.submit(stage, primary, event)
        assert tree(third.journal_root) == originals
        # Tampered native evidence is an integrity failure, never a repair pause.
        turns[0]['items'][-1]['text'] = '{}'
        with pytest.raises(ValueError):
            gate.verify_prior()


@pytest.mark.parametrize('stage,defect', [
    ('facts-fresh', 'missed_error'), ('completion-initial', 'wrong_correction')])
def test_pause_policy_does_not_relax_other_rejections(tmp_path, stage, defect):
    opened, turns, workspace = controls(tmp_path, rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    first, gate = opened()
    with pytest.raises(SessionPaused), first:
        gate.require(stage, 'opinion', {'responses': []}, 'fixture')
    second, gate = opened(first)
    with second:
        primary, event = author(list(gate.handles())[-1], turns, workspace,
                                accepted=False, defect_kind=defect)
        assert not gate.submit(stage, primary, event)
        assert (second.root/'terminal.json').exists()


def test_unknown_policy_cannot_create_session(tmp_path):
    opened, _, _ = controls(tmp_path, rejection_policy='skip-rejection')
    with pytest.raises(ValueError, match='unknown_review_rejection_policy'):
        opened()
    assert not (tmp_path/'session').exists()


def test_prepare_pins_policy_and_run_cannot_override_it(tmp_path, monkeypatch):
    import sys
    from scripts import sol_natural_launch as launch
    monkeypatch.setattr(launch, 'current_head', lambda: '1'*40)
    monkeypatch.setattr(launch, 'source', lambda: dict(head='1'*40, files={}))
    monkeypatch.setattr(launch, 'capture', lambda run_id: (None, dict(estimated_uncached_cny='0')))
    monkeypatch.setattr(launch, 'first_pin', lambda first: '2'*64)
    prepared = launch.prepare(tmp_path/'operator', 'fixture', 'synthetic-root', 'synthetic-child',
        initial_review_rejection_policy=SessionReviewGate.PAUSE_INITIAL)
    plan = launch.load(prepared['operator'], prepared['plan_sha256'])
    assert plan['review_plan'][SessionReviewGate.REJECTION_POLICY] == SessionReviewGate.PAUSE_INITIAL
    assert not (Path(prepared['operator'])/'execution').exists()
    monkeypatch.setattr(sys, 'argv', ['sol_natural_launch', 'run', '--operator', str(tmp_path/'absent'),
        '--initial-review-rejection-policy', SessionReviewGate.PAUSE_INITIAL])
    with pytest.raises(SystemExit):
        launch.main()
