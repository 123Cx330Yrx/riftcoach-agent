"""A host interruption cannot lose already made judgments or approve late IO."""
import json
from pathlib import Path
import shutil

import pytest

from scripts import write_role_stage_decision as writer
from tests.test_role_observation_qualification import make_run, read


@pytest.mark.parametrize('event', ['review_ready', 'batch_closed', 'stage_changed', 'deadline'])
def test_explicit_judgment_survives_wait_without_inventing_acceptance(tmp_path, monkeypatch, event):
    arm = tmp_path/'claim-scope-4'
    arm.mkdir()
    stage = arm/'final.json'
    stage.write_text('{"stage":"final"}', encoding='utf-8')
    notes = dict(accepted=True, reason='Explicitly reviewed before waiting.')
    now, releases = [0.0], []

    def release(run, key, name, received, **kwargs):
        releases.append(received)
        return dict(accepted=True)

    def progress(seconds):
        saved = json.loads((arm/'primary-notes-final.json').read_bytes())
        assert saved['notes'] == notes
        assert not (arm/'decision-final.json').exists()
        now[0] += seconds
        if event == 'review_ready':
            (arm/'independent-final-review.json').write_text('{}', encoding='utf-8')
        elif event == 'batch_closed':
            (tmp_path/'result.json').write_text('{}', encoding='utf-8')
        elif event == 'stage_changed':
            stage.write_text('{}', encoding='utf-8')

    monkeypatch.setattr(writer, 'write_decision', release)
    args = dict(profile='correction-scope', max_wait_seconds=1,
        clock=lambda: now[0], sleep=progress)
    if event == 'review_ready':
        assert writer.wait_and_write_decision(tmp_path, 'claim-scope:4', 'final', notes, **args)['accepted']
        assert releases == [notes]
    else:
        code = {'batch_closed':'batch_closed', 'stage_changed':'stage_changed',
                'deadline':'independent_deadline'}[event]
        with pytest.raises(ValueError, match=code):
            writer.wait_and_write_decision(tmp_path, 'claim-scope:4', 'final', notes, **args)
        assert releases == []
    assert json.loads((arm/'primary-notes-final.json').read_bytes())['notes'] == notes


def test_already_closed_batch_gets_no_late_primary_file(tmp_path):
    arm = tmp_path/'claim-scope-4'
    arm.mkdir()
    (arm/'final.json').write_text('{}', encoding='utf-8')
    (tmp_path/'result.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='batch_closed'):
        writer.wait_and_write_decision(tmp_path, 'claim-scope:4', 'final', {},
            profile='correction-scope', max_wait_seconds=1)
    assert not (arm/'primary-notes-final.json').exists()


@pytest.mark.parametrize('event', ['ready', 'closed_during_read', 'stage_during_read',
                                  'deadline_during_read', 'closed_after_primary'])
def test_wait_uses_real_writer_with_interleaved_state_changes(make_run, tmp_path, monkeypatch, event):
    source, _ = make_run(('claim-scope:1',), profile='correction-scope')
    run = tmp_path/'pending-copy'
    shutil.copytree(source, run)
    arm = run/'claim-scope-1'
    primary = read(arm/'primary-initial-review.json')
    notes = {k: primary[k] for k in ('accepted','defects','reason',
        'target_and_correction_valid','final_report_checks','report_reason')}
    (run/'result.json').unlink()
    for name in ('primary-initial-review.json','decision-initial.json','initial-host.json',
                 'case-completed.json','task-observation.json'):
        (arm/name).unlink()
    independent = arm/'independent-initial-review.json'
    stage = arm/'initial.json'
    now, triggered = [0.0], [False]
    original_read, original_write = Path.read_bytes, writer.write_new_json

    def read_interleaved(path):
        raw = original_read(path)
        if path == independent and not triggered[0]:
            triggered[0] = True
            if event == 'closed_during_read':
                original_write(run/'result.json', {'closed':True})
            elif event == 'stage_during_read':
                stage.write_bytes(original_read(stage) + b' ')
            elif event == 'deadline_during_read':
                now[0] = 2.0
        return raw

    def write_interleaved(path, value):
        result = original_write(path, value)
        if event == 'closed_after_primary' and path.name == 'primary-initial-review.json':
            original_write(run/'result.json', {'closed':True})
        return result

    monkeypatch.setattr(Path, 'read_bytes', read_interleaved)
    monkeypatch.setattr(writer, 'write_new_json', write_interleaved)
    options = dict(profile='correction-scope', max_wait_seconds=1, clock=lambda: now[0])
    if event == 'ready':
        assert writer.wait_and_write_decision(run,'claim-scope:1','initial',notes,**options)['accepted']
        assert (arm/'decision-initial.json').exists()
    else:
        with pytest.raises(ValueError, match='host_writer_'):
            writer.wait_and_write_decision(run,'claim-scope:1','initial',notes,**options)
        assert not (arm/'decision-initial.json').exists()
    assert read(arm/'primary-notes-initial.json')['notes'] == notes
