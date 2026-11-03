"""Pre-dispatch adapter test. ALL native judgments here are synthetic."""
import json
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.full_chain_host_rehearsal import Rehearsal, ROOT, KEY, VERSION, no_network
from scripts.codex_review_event_source import CodexHostReviewEventSource


@pytest.mark.parametrize('profile', ['original', 'explicit', 'bound'])
def test_offline_adapter_three_stages_before_real_host_dispatch(tmp_path, profile):
    cls, key, version = Rehearsal, KEY, VERSION
    if profile == 'explicit':
        from scripts.full_chain_explicit_host_rehearsal import ExplicitRehearsal, driver
        cls, key, version = ExplicitRehearsal, driver.KEY, driver.VERSION
    if profile == 'bound':
        from scripts.full_chain_bound_fixture import BoundRehearsal, VERSION as bound_version, FIXTURE
        cls, key, version = BoundRehearsal, 'host-io-count:1', bound_version
    session = cls(directory=tmp_path/'run', answers=tmp_path/'authors', observations=tmp_path/'obs')
    plan = session.prepare(root_thread_id='test-root', independent_thread_id='test-child')
    assert plan['sequence'] == [key] and plan['kind'] == version
    assert not plan['paid_execution_enabled'] and not plan['execution_authorized']
    session.directory.mkdir()
    session.runner._write_json(session.directory/'plan.json', dict(preparation_plan=plan,
        plan_sha256=session.runner.canonical_sha(plan)))
    turns = []
    def native(method, params):
        if method == 'thread/read':
            return dict(thread=dict(id='test-child', parentThreadId='test-root',
                source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='test-root')))))
        return dict(data=turns, nextCursor=None)
    source = CodexHostReviewEventSource(SimpleNamespace(request=native), plan)
    def judge(path, remaining):
        required = session.evidence.read(path)
        bound, stage = required['binding'], required['binding']['stage']
        folder = path.parent
        if profile == 'bound' and stage == 'revision':
            bundle = session.evidence.read(ROOT / FIXTURE)
            actual = session.evidence.read(folder / 'stage.json')
            expected = bundle['responses']['revision']['tool_calls'][0]['arguments']
            assert json.loads(actual['journal']['raw']) == expected
            op = actual['journal']['operations'][0]
            assert {k: op[k] for k in ('before', 'after', 'reason')} == expected['edits']['block_4'][0]
            assert session.runner.digest(actual['report']) == bundle['revised_report_sha256']
            assert actual['journal']['semantic_approval'] is False
        pin = session.publish_task(path)
        task = json.loads((folder/'independent-task.json').read_text(encoding='utf-8'))
        assert task['instructions'].startswith('OFFLINE business-response rehearsal.')
        assert task['binding'] == bound
        def opinion(reviewer):
            return dict(binding=bound, stage_assessment=dict(stage=stage, stage_sha256=required['stage_sha256'],
                reviewer=reviewer, source_review='TEST ONLY synthetic judgment, no semantic evidence.',
                accepted=True, defects=[]), report_assessment=None if stage == 'initial' else dict(
                    report_sha256=bound['report_sha256'], reviewer=reviewer, source_review='TEST ONLY',
                    facts_and_sources_correct=True, correct_content_preserved=True,
                    identity_and_goal_preserved=True, true_errors_fixed=True))
        answer = dict(binding=bound, review=opinion('test-child'))
        target = session.workspace.answer_path(folder/'task-checkpoint.json', pin)
        with target.open('x', encoding='utf-8') as stream:
            json.dump(answer, stream, ensure_ascii=False, indent=2)
        checked = subprocess.run([sys.executable, '-m', 'scripts.host_review_task_checkpoint', 'check-answer',
            '--checkpoint', str(folder/'task-checkpoint.json'), '--checkpoint-sha', pin,
            '--answer-file', str(target)], cwd=ROOT, capture_output=True)
        assert checked.returncode == 0, checked.stderr.decode('utf-8')
        turns.insert(0, dict(id=stage, status='completed', itemsView='full', error=None, items=[
            dict(id='dispatch', type='userMessage', content=[dict(type='text',
                text=session.evidence.task(session.directory, key, stage))]),
            dict(id='final', type='agentMessage', phase='final_answer', text=target.read_text(encoding='utf-8'))]))
        notes = opinion('test-root'); notes.pop('binding')
        session.evidence.submit(session.directory, key, stage, notes, f'test-child/{stage}/final', source, pin)
        return session.evidence.read(folder/'review-submission.json')
    with no_network():
        result = session.runner.observe(session.offline_factory(), session.directory, plan,
            event_source=source, adjudicate=judge)
        assert result['scan_completed'] and result['diagnostic_accepted'], result
        assert result['provider_calls'] == 3  # synthetic receipt counter only
        before = session.snapshot()
        replay = session.evidence.replay(session.directory, event_source=source)
        assert session.snapshot() == before and len(replay['author_evidence']) == 3
        assert replay['new_qualification'] == 0
        session.evidence.seal(session.directory, tmp_path/'seal.json', event_source=source)
        with pytest.raises(FileExistsError):
            session.evidence.seal(session.directory, tmp_path/'seal.json', event_source=source)
    other = cls(directory=session.directory, answers=session.workspace.answers, observations=session.observations)
    assert other.evidence.load_plan(session.directory) == plan  # independently rebuilt plan
    for audit in session.observations.glob('*/parent-audit.json'):
        value = json.loads(audit.read_text(encoding='utf-8'))
        assert value['external_http_requests'] == 0 and 'OFFLINE' in value['fixture']


def test_network_guard_restores_after_failure():
    original = socket.socket.connect
    with pytest.raises(ValueError, match='network_forbidden'), no_network():
        socket.socket().connect(('127.0.0.1', 1))
    assert socket.socket.connect is original
