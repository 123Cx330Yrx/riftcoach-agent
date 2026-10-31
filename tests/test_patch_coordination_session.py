"""Real session/gate/replay path with synthetic HTTP and native events only."""
import json
from pathlib import Path

import pytest

from app.evaluation import sol_original15_session as engine
from app.evaluation.sol_natural_session import SessionPaused, SessionBlocked
from scripts import review_duty_direct_patch as direct
from scripts import sol_original15_launch as launch
from scripts.reviewer_profile_batch import inventory
from tests.test_patch_coordination import selection, no_network
from tests.test_sol_original15_session import setup, router
from tests.test_sol_session_review import author


@pytest.mark.parametrize('reject', [None, 'patch-coordination', 'edit'])
def test_overlap_waits_for_selection_native_approval_edit_and_both_fresh(setup, reject):
    opened, turns, operator = setup
    previous, chosen = None, None
    calls, stages = [], []
    missing_selection_seen = False
    for _ in range(12):
        session, gate = opened(previous=previous)
        try:
            with session:
                result = launch.advance_case(session, router(session, calls, mode='overlap'),
                    patch_coordination=chosen)
                session.close(dict(result=result))
        except SessionPaused as error:
            if str(error) == 'session_awaiting_patch_coordination':
                assert chosen is None and calls == [200, 200]
                assert not session.status()['unresolved'] and not session.status()['closed']
                assert not (session.journal_root/'outcome.json').exists()
                missing_selection_seen = True
                conflict = json.loads((session.journal_root/'patch-conflicts.json').read_bytes())
                chosen = selection(conflict)
                previous = session
                continue
            assert str(error) == 'session_awaiting_native_review'
            importer, g = opened(previous=session)
            with importer:
                handle = list(g.handles())[-1]
                stage = handle['binding']['key']
                stages.append(stage)
                if stage not in ('facts-fresh', 'completion-fresh'):
                    assert not (importer.journal_root/'application.json').exists()
                if stage == 'patch-coordination':
                    assert missing_selection_seen and calls == [200, 200]
                    material = json.loads((Path(handle['folder'])/'material.json').read_bytes())
                    assert len(material['initial_requests_with_complete_policies']) == 2
                    assert len(material['patch_journal']['operations']) == 2
                    assert len(material['patch_journal']['selected_operations']) == 1
                    assert material['complete_source']['data_json'] and material['complete_source']['pack_json']
                primary, event = author(handle, turns, g.native.workspace, accepted=stage != reject)
                assert g.submit(stage, primary, event) is (stage != reject)
            previous = importer
            # Future segments must replay the committed choice, without an operator reselecting it.
            if stage == 'patch-coordination':
                chosen = None
            if stage == reject:
                assert calls == [200, 200] and not (importer.journal_root/'application.json').exists()
                return
        else:
            assert reject is None and result['matched'] is True
            break
    else:
        pytest.fail('coordination workflow never completed')
    assert stages == ['facts-initial', 'completion-initial', 'patch-coordination',
                      'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
    assert calls == [200]*4 and result['accounting']['calls'] == 4
    assert result['accounting']['logical'] == dict(generation=0, review=4)
    assert len(list(session.journal_root.glob('application.json'))) == 1
    before = inventory(operator), inventory(operator.with_name(operator.name+'-authors'))
    replay, _ = opened(previous=session, read_only=True)
    with replay:
        assert engine.run_case(replay, router(replay, [], mode='wrong_model')) == result
        assert replay.cursor == replay.status()['operations']
    assert before == (inventory(operator), inventory(operator.with_name(operator.name+'-authors')))
    replay, _ = opened(previous=session, read_only=True)
    with replay, pytest.raises(SessionBlocked, match='coordination_changed'):
        inventory_data = json.loads((replay.journal_root/'patch-conflicts.json').read_bytes())
        changed = selection(inventory_data, ['op_2'])
        engine.run_case(replay, router(replay, []), patch_coordination=changed)


def test_coordination_file_is_pinned_before_any_runtime_or_credentials(tmp_path, monkeypatch):
    from app.evaluation.sol_natural_session import digest
    path = tmp_path/'choice.json'
    raw = json.dumps({'version': direct.COORDINATION_VERSION}, ensure_ascii=True).encode('utf-8')
    path.write_bytes(raw)
    assert launch.load_patch_coordination(path, digest(raw)) == json.loads(raw)
    assert launch.load_patch_coordination(None, None) is None
    for file, pin in [(path, None), (None, digest(raw)), (path, '0'*64)]:
        with pytest.raises(ValueError, match='original15_patch_coordination_'):
            launch.load_patch_coordination(file, pin)
    # Reject duplicate JSON keys even if the entire malformed file is pinned.
    raw = b'{"resolutions":[],"resolutions":[]}'
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        launch.load_patch_coordination(path, digest(raw))
    raw = b'null'
    path.write_bytes(raw)
    with pytest.raises(ValueError, match='coordination_object_required'):
        launch.load_patch_coordination(path, digest(raw))
    def deny(*args, **kwargs):
        pytest.fail('an unpublished selection must not reach CI or credentials')
    monkeypatch.setattr(launch, 'verify_ci', deny)
    monkeypatch.setattr(launch.base, 'continuation_credentials', deny)
    with pytest.raises(ValueError, match='patch_conflicts_required'):
        launch.execute({'operator': str(tmp_path/'operator')}, '0'*64, None, 'observed:3', {},
            authorization_file=tmp_path/'missing.json', authorization_sha='0'*64,
            ci_run='0', preflight={}, patch_coordination={})
