"""Bound the remaining scope and exercise the actual generated dispatch path."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

from scripts import document_full_report_diagnostic as original
from scripts import document_full_report_remaining_initial as remaining
from tests.dispatch_assertions import assert_dispatch_python


@pytest.fixture(scope='module')
def prepared():
    return remaining.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')


def test_only_never_sent_inputs_and_smaller_budget(prepared):
    plan, rows = prepared
    _, old = original.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    assert plan['sequence'] == ['report-H5:initial', 'report-S8:initial']
    assert rows == old[1:]
    assert plan['budget']['max_calls'] == 2
    assert plan['budget']['max_tokens'] == 193536
    assert plan['budget']['max_active_seconds'] == 1200
    assert plan['budget']['estimated_uncached_cny'] == '2.859008'
    assert plan['budget']['role_calls'] == {'glm-5.3': 2, 'glm-5.3-flash': 0}
    assert plan['omitted_uncertified_key'] == 'report-V2:initial'
    assert not plan['execution_authorized'] and not plan['prior_run_reopened']
    assert original.base.runner.checkpoint is not remaining.checkpoint


def test_old_authorization_and_mutated_evidence_rejected(prepared, monkeypatch):
    plan, _ = prepared
    now = datetime.now(timezone.utc)
    auth = dict(version='document-full-report-network-authorization-v1', authorized=True,
        user_instruction='OFFLINE ONLY', head='a' * 40, ci_run='ci', budget=deepcopy(plan['budget']),
        plan_sha256=remaining.base.sha(remaining.base.options.canonical(plan)),
        issued_at=now.isoformat(), expires_at=(now + timedelta(hours=24)).isoformat())
    with pytest.raises(ValueError, match='authorization'):
        remaining.base.check_authorization(auth, plan, 'a' * 40, 'ci', now=now)
    monkeypatch.setitem(remaining.EVIDENCE, next(iter(remaining.EVIDENCE)), '0' * 64)
    with pytest.raises(ValueError, match='remaining_initial_evidence_changed'):
        remaining.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')


@pytest.mark.parametrize('missing_directory', [False, True])
def test_real_observe_uses_explicit_dispatch_or_stops_before_host_wait(
        tmp_path, monkeypatch, prepared, missing_directory):
    helper = remaining.base.load_private(Path(__file__).with_name('test_document_full_report_diagnostic.py'),
                                         'tests._remaining_initial_setup')
    monkeypatch.setattr(helper, 'diagnostic', remaining)
    plan, rows, fixtures = helper.execution(tmp_path, monkeypatch, prepared)
    if missing_directory:
        monkeypatch.setattr(remaining, 'ROOT', tmp_path / 'missing-backend')
    provider = fixtures.OfflineProvider(None)
    host = fixtures.OfflineNativeHost(plan, tmp_path, None)

    def adjudicate(directory, key, seconds):
        # Keep the shared fixture's native event reader, but exercise the new
        # executable dispatch instead of its legacy literal "python" assertion.
        from scripts.verify_host_review_artifacts import verify
        from app.evaluation.role_task_outcome import stage_identity
        folder = directory / key.replace(':', '-')
        pin = remaining.checkpoint.digest((folder / 'task-checkpoint.json').read_bytes())
        _, task = remaining.checkpoint.read(folder / 'task-checkpoint.json', pin)
        stage = remaining.runner.read(folder / 'stage.json')
        assert verify(folder / 'task-checkpoint.json', pin)['stage_sha256'] == stage_identity(stage)
        bound = task['binding']
        index = len(host.turns) + 1
        def notes(role):
            return dict(stage_assessment=dict(stage='initial', stage_sha256=stage_identity(stage),
                reviewer=plan['review_principals'][role]['principal_id'],
                source_review='OFFLINE routing fixture, not semantic evidence',
                accepted=True, defects=[]), report_assessment=None)
        host.turns.insert(0, dict(id=f'turn-{index}', status='completed', itemsView='full',
            error=None, items=[dict(id=f'dispatch-{index}', type='userMessage',
                content=[dict(type='text', text=json.dumps(task))]),
                dict(id=f'final-{index}', type='agentMessage', phase='final_answer',
                     text=json.dumps(dict(binding=bound,
                         review=dict(binding=bound, **notes('independent')))))]))
        remaining.runner.submit(directory, key, notes('primary'),
            f'synthetic-child/turn-{index}/final-{index}', host.source,
            folder / 'task-checkpoint.json', pin)
        return remaining.runner.read(folder / 'review-submission.json')

    result = remaining.runner.observe(tmp_path, plan, rows, provider, host.source,
                                      adjudicate=adjudicate)
    first = tmp_path / 'report-H5-initial'
    if missing_directory:
        assert not result['scan_completed'] and len(provider.calls) == 1
        assert result['first_deviation']['phase'] == 'host'
        assert result['unexecuted'] == ['report-S8:initial']
        assert not (first / 'dispatch.txt').exists()
        assert not (first / 'review-wait-start.json').exists()
    else:
        assert result['scan_completed'] and len(provider.calls) == 2
        assert not (tmp_path / 'report-V2-initial').exists()
        for cell, _, _ in rows:
            folder = tmp_path / cell['key'].replace(':', '-')
            text = (folder / 'dispatch.txt').read_text(encoding='utf-8')
            assert str(remaining.ROOT.resolve()) in text
            assert str(Path(sys.executable).resolve()) in text
            assert_dispatch_python(text, Path(sys.executable).resolve(), sys.platform,
                                   command_count=2)
            assert 'scripts.verify_host_review_artifacts' in text
            assert 'check-answer' in text and 'do not append backend' in text
        before = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
                  for p in tmp_path.rglob('*') if p.is_file()}
        output = tmp_path.parent / (tmp_path.name + '-seal.json')
        assert remaining.runner.seal(tmp_path, output, event_source=host.source)['native_reviews'] == 2
        assert before == {p.relative_to(tmp_path).as_posix(): p.read_bytes()
                          for p in tmp_path.rglob('*') if p.is_file()}


def test_package_rebuild_and_no_original_entrypoint(tmp_path):
    package = remaining.Package(tmp_path / 'package')
    package.write(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    assert package.verify()['requests'] == 2
    with pytest.raises(ValueError, match='sampling_package_plan_changed'):
        original.Package(package.directory).verify()
