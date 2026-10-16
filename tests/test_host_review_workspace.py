"""Actual author-file IO through an explicitly synthetic native transport.

These regressions are offline, not authentic native or Provider quality proof.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from scripts.document_sampling_screening import load_private
from scripts.host_review_workspace import HostReviewWorkspace
from app.evaluation.role_task_outcome import stage_identity
from tests.dispatch_assertions import assert_dispatch_python

ROOT = Path(__file__).resolve().parents[1]


def setup(tmp_path, monkeypatch):
    adapter = load_private(ROOT / 'scripts/document_full_report_workspace.py',
                           'scripts._test_workspace')
    work = adapter.workspace
    work.answers = tmp_path / 'author-answers'
    work.evidence_roots = (tmp_path / 'run',)
    directory = tmp_path / 'run'
    directory.mkdir()
    helper = load_private(ROOT / 'tests/test_document_full_report_diagnostic.py',
                          'tests._workspace_setup')
    helper.diagnostic = adapter
    prepared = adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    plan, rows, fixtures = helper.execution(directory, monkeypatch, prepared)
    provider = fixtures.OfflineProvider()
    host = fixtures.OfflineNativeHost(plan, directory)
    return adapter, directory, plan, rows, provider, host


def author_submit(adapter, directory, plan, host, key, *, fault=None):
    runner, work = adapter.runner, adapter.workspace
    folder = directory / key.replace(':', '-')
    path = folder / 'task-checkpoint.json'
    pin = runner.checkpoint.digest(path.read_bytes())
    _, task = runner.checkpoint.read(path, pin)
    stage = runner.read(folder / 'stage.json')
    index = len(host.turns) + 1
    def notes(role):
        return dict(stage_assessment=dict(stage='initial', stage_sha256=stage_identity(stage),
            reviewer=plan['review_principals'][role]['principal_id'],
            source_review='OFFLINE synthetic author fixture; no semantic evidence',
            accepted=True, defects=[]), report_assessment=None)
    answer = dict(binding=task['binding'], review=dict(binding=task['binding'], **notes('independent')))
    target = work.answer_path(path, pin)
    # Unlike earlier fixtures, write the author's file, execute the real CLI,
    # and populate the explicitly synthetic event from that exact checked file.
    with target.open('x', encoding='utf-8') as stream:
        json.dump(answer, stream, ensure_ascii=False, indent=2)
    checked = subprocess.run([sys.executable, '-m', 'scripts.host_review_task_checkpoint',
        'check-answer', '--checkpoint', str(path), '--checkpoint-sha', pin,
        '--answer-file', str(target)], cwd=ROOT, capture_output=True)
    assert checked.returncode == 0, checked.stderr
    native_text = target.read_text(encoding='utf-8')
    host.turns.insert(0, dict(id=f'turn-{index}', status='completed', itemsView='full', error=None,
        items=[dict(id=f'dispatch-{index}', type='userMessage',
                    content=[dict(type='text', text=json.dumps(task))]),
               dict(id=f'final-{index}', type='agentMessage', phase='final_answer', text=native_text)]))
    if fault == 'before_submit':
        (folder / 'independent-answer.json').write_text(native_text, encoding='utf-8')
    if fault == 'answer_drift':
        answer['review']['stage_assessment']['source_review'] = 'changed after native final'
        target.write_text(json.dumps(answer), encoding='utf-8')
    if fault == 'native_read_pollution':
        original = host.source.client.request
        def polluted(method, params):
            result = original(method, params)
            (folder / 'unexpected.json').write_text('{}')
            return result
        host.source.client.request = polluted
    runner.submit(directory, key, notes('primary'), f'synthetic-child/turn-{index}/final-{index}',
                  host.source, path, pin)
    if fault == 'after_submit':
        (folder / 'unexpected.json').write_text('{}')
    return runner.read(folder / 'review-submission.json')


@pytest.mark.parametrize('fault', [None, 'before_submit', 'after_submit',
                                  'native_read_pollution', 'answer_drift'])
def test_author_file_through_submit_next_request_and_strict_seal(tmp_path, monkeypatch, fault):
    a, directory, plan, rows, provider, host = setup(tmp_path, monkeypatch)
    result = a.runner.observe(directory, plan, rows, provider, host.source,
        adjudicate=lambda d, k, s: author_submit(a, d, plan, host, k, fault=fault))
    if fault:
        assert not result['scan_completed']
        assert len(provider.calls) == 1
        assert len(result['unexecuted']) == 2
        first = directory / rows[0][0]['key'].replace(':', '-')
        assert (first / 'review-submission.json').exists() == (fault == 'after_submit')
        assert result['first_deviation']['code'] == (
            'host_workspace_answer_native_mismatch' if fault == 'answer_drift'
            else 'semantic_unexpected_run_file')
        assert not (directory / rows[1][0]['key'].replace(':', '-')).exists()
        return
    assert result['scan_completed'] and len(provider.calls) == 3
    assert len(list(a.workspace.answers.glob('*.json'))) == 3
    for cell, _, _ in rows:
        folder = directory / cell['key'].replace(':', '-')
        text = (folder / 'dispatch.txt').read_text(encoding='utf-8')
        assert '--answer-file ' in text and str(a.workspace.answers) in text
        assert_dispatch_python(text, a.workspace.python, sys.platform, command_count=3)
    before = {p.relative_to(directory).as_posix(): p.read_bytes()
              for p in directory.rglob('*') if p.is_file()}
    output = tmp_path / 'OFFLINE-seal.json'
    assert a.runner.seal(directory, output, event_source=host.source)['native_reviews'] == 3
    assert before == {p.relative_to(directory).as_posix(): p.read_bytes()
                      for p in directory.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        a.runner.seal(directory, output, event_source=host.source)


@pytest.mark.parametrize('moment', ['before_send', 'transport_handoff'])
def test_pollution_after_successful_submission_never_sends_next(tmp_path, monkeypatch, moment):
    a, directory, plan, rows, provider, host = setup(tmp_path, monkeypatch)
    sends = 0
    def before():
        nonlocal sends
        sends += 1
        if sends == 2 and moment == 'before_send':
            (directory / 'unexpected.json').write_text('{}')
    original = a.runner.write_new_json
    def write(path, value):
        original(path, value)
        if Path(path).name == 'started.json' and sends == 2 and moment == 'transport_handoff':
            (directory / 'unexpected.json').write_text('{}')
    monkeypatch.setattr(a.runner, 'write_new_json', write)
    result = a.runner.observe(directory, plan, rows, provider, host.source, before_send=before,
        adjudicate=lambda d, k, s: author_submit(a, d, plan, host, k))
    assert len(provider.calls) == 1 and len(result['completed']) == 1
    assert len(result['unexecuted']) == 2
    assert result['first_deviation']['code'] == 'semantic_unexpected_run_file'


def test_paths_and_no_paid_entrypoint(tmp_path):
    with pytest.raises(ValueError, match='answer_inside_evidence'):
        HostReviewWorkspace(cwd=ROOT, python=sys.executable,
            answers=tmp_path / 'runs/answer', evidence_roots=(tmp_path / 'runs',))
    a = load_private(ROOT / 'scripts/document_full_report_workspace.py', 'scripts._no_paid_workspace')
    with pytest.raises(ValueError, match='paid_scope_not_selected'):
        a.base.run(None)
    original = load_private(ROOT / 'scripts/document_full_report_remaining_initial.py', 'scripts._old_workspace')
    assert not getattr(original.runner, '_host_workspace_installed', False)


def test_answer_alias_and_existing_file_are_rejected(tmp_path, monkeypatch):
    a, directory, plan, rows, provider, host = setup(tmp_path, monkeypatch)
    dispatch = a.runner.checkpoint.dispatch
    def existing(path, pin, **kw):
        target = a.workspace.answer_path(path, pin)
        target.parent.mkdir(parents=True)
        target.write_text('{}')
        with pytest.raises(ValueError, match='answer_already_exists'):
            dispatch(path, pin, **kw)
        raise ValueError('test_existing_answer_stopped')
    a.runner.checkpoint.dispatch = existing
    result = a.runner.observe(directory, plan, rows, provider, host.source)
    assert result['first_deviation']['code'] == 'test_existing_answer_stopped'
    assert len(provider.calls) == 1


def test_junction_in_answer_ancestor_is_rejected(tmp_path):
    target = tmp_path / 'run'
    target.mkdir()
    link = tmp_path / 'answers'
    if sys.platform == 'win32':
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        assert made.returncode == 0, made.stderr
    else:
        link.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match='redirected_answer_path'):
            HostReviewWorkspace(cwd=ROOT, python=sys.executable, answers=link / 'new',
                                evidence_roots=(target,))
    finally:
        if sys.platform == 'win32':
            link.rmdir()
        else:
            link.unlink()


def test_native_rehearsal_fixture_is_complete_before_real_dispatch(tmp_path, monkeypatch):
    harness = load_private(ROOT / 'tests/host_workspace_native_rehearsal.py',
                           'tests._native_rehearsal_contract')
    a = harness.adapter
    a.workspace.answers = tmp_path / 'answers'
    a.workspace.evidence_roots = (tmp_path / 'run',)
    directory = tmp_path / 'run'
    directory.mkdir()
    helper = load_private(ROOT / 'tests/test_document_full_report_diagnostic.py',
                          'tests._native_rehearsal_setup')
    helper.diagnostic = a
    plan, rows, fixtures = helper.execution(directory, monkeypatch,
        harness.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child'))
    assert plan['synthetic_transport'] and plan['actual_project_provider_calls'] == 0
    assert [r[0]['key'] for r in rows] == ['workspace-probe:initial']
    host = fixtures.OfflineNativeHost(plan, directory)
    result = a.runner.observe(directory, plan, rows, fixtures.OfflineProvider(), host.source,
        adjudicate=lambda d, k, s: author_submit(a, d, plan, host, k))
    assert result['scan_completed'], result['first_deviation']
    assert a.runner.seal(directory, tmp_path / 'OFFLINE-seal.json',
                         event_source=host.source)['native_reviews'] == 1


@pytest.mark.parametrize('fault', ['unsubmitted_pollution', 'submit_native_failure'])
def test_waiting_observer_stops_independently_of_submit_caller(tmp_path, monkeypatch, fault):
    a, directory, plan, rows, provider, host = setup(tmp_path, monkeypatch)
    results = []
    worker = threading.Thread(target=lambda: results.append(a.runner.observe(
        directory, plan, rows, provider, host.source)), daemon=True)
    worker.start()
    first = directory / rows[0][0]['key'].replace(':', '-')
    deadline = time.monotonic() + 15
    while not (first / 'review-wait-start.json').exists() and worker.is_alive():
        assert time.monotonic() < deadline
        time.sleep(.05)
    assert worker.is_alive()
    if fault == 'unsubmitted_pollution':
        (first / 'unexpected-answer.json').write_text('{}')
    else:
        def unavailable(**kwargs):
            raise ValueError('test_native_unavailable')
        monkeypatch.setattr(host.source, 'fetch', unavailable)
        # This exception occurs in the submitting caller, outside observe's
        # stack. The waiting observer must notice the abort on its own.
        with pytest.raises(ValueError, match='test_native_unavailable'):
            author_submit(a, directory, plan, host, rows[0][0]['key'])
        assert (first / 'operator-abort.json').exists()
    worker.join(timeout=10)
    assert not worker.is_alive()
    assert len(results) == 1 and len(provider.calls) == 1
    assert len(results[0]['unexecuted']) == 2
    assert results[0]['first_deviation']['code'] == (
        'semantic_unexpected_run_file' if fault == 'unsubmitted_pollution'
        else 'semantic_operator_abort')
    assert not (first / 'review-submission.json').exists()


def test_wait_polling_does_not_reject_protected_atomic_publication(tmp_path, monkeypatch):
    a, directory, plan, rows, provider, host = setup(tmp_path, monkeypatch)
    original = a.runner.os.link
    def delayed_link(source, target, **kwargs):
        if Path(source).name.startswith('.submission-'):
            time.sleep(.4)  # Longer than the supervisor poll interval.
        return original(source, target, **kwargs)
    monkeypatch.setattr(a.runner.os, 'link', delayed_link)
    results = []
    worker = threading.Thread(target=lambda: results.append(a.runner.observe(
        directory, plan, rows, provider, host.source)), daemon=True)
    worker.start()
    for cell, _, _ in rows:
        folder = directory / cell['key'].replace(':', '-')
        deadline = time.monotonic() + 15
        while not (folder / 'review-wait-start.json').exists() and worker.is_alive():
            assert time.monotonic() < deadline
            time.sleep(.05)
        assert worker.is_alive(), results
        author_submit(a, directory, plan, host, cell['key'])
    worker.join(timeout=10)
    assert not worker.is_alive() and results[0]['scan_completed'], results
    assert len(provider.calls) == 3
    assert a.runner.seal(directory, tmp_path / 'OFFLINE-concurrent-seal.json',
                         event_source=host.source)['native_reviews'] == 3
