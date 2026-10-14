"""SCRIPTED responses/native fixtures, real author-file/CLI/import IO; zero model calls."""
from copy import deepcopy
from dataclasses import replace
import json
import socket

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from scripts import review_duty_patch_execution as execution
from scripts import review_duty_patch_replay as replay
from scripts import review_duty_execution as legacy
from scripts import review_duty_host_gate as legacy_gate
from scripts import review_duty_direct_patch as direct
from scripts.full_chain_modules import private_module
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER
from tests.test_review_duty_direct_patch import repaired

# Reuse the real author -> check-answer CLI -> native importer test harness
# without modifying its frozen source or any public module globals.
_fixture = private_module(execution.ROOT/'tests/test_review_duty_execution.py',
    {'scripts.review_duty_execution': execution})


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('offline fixture cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    monkeypatch.setattr(socket, 'create_connection', reject)


@pytest.fixture(scope='module')
def sample():
    _, inputs, _, raw = cases()['claim-scope:4']
    return inputs, json.loads(raw)


def setup(tmp_path, sample, *, fault=None, at='facts-initial'):
    session, sent, gates, turns = _fixture.setup(tmp_path, sample, fault=fault, at=at)
    sender = session.send
    def send(request, folder):
        exchange = sender(request, folder)
        tool = exchange.response.tool_calls[0]
        args = deepcopy(dict(tool.arguments))
        if folder.name.endswith('initial'):
            args = repaired(args) if args['verdict'] == 'needs_revision' else dict(args, repairs=[])
        if fault == 'bad_anchor' and folder.name == 'facts-initial':
            args['repairs'][0]['edits']['block_4'][0]['before'] = 'absent anchor'
        if fault == 'overlap' and folder.name == 'completion-initial':
            args = repaired(sample[1])
        if fault == 'terminal' and folder.name == at:
            args.update(score=0, verdict='fail', issues=[], repairs=[])
        response = replace(exchange.response, tool_calls=(replace(tool, arguments=args),))
        return Exchange(exchange.issued_request, response, exchange.receipt_request_sha256)
    session.send = send
    return session, sent, gates, turns


def replay_session(session):
    return replay.replay(session.directory, closure_sha256=session.closure_sha256,
        inputs=session.inputs, event_source=session.gate.event_source, observe=session.observe)


def test_four_requests_six_native_gates_author_cli_unique_application_and_readonly_seal(tmp_path, sample):
    original = (legacy.VERSION, deepcopy(legacy.LIMITS), legacy.SLOTS,
                legacy.DevelopmentChain, legacy_gate.NativeGate.publish)
    session, sent, gates, turns = setup(tmp_path, sample)
    result = session.run()
    assert result['outcome'] == 'development_chain_pass', repr(session.failure)
    assert sent == list(execution.SLOTS)
    assert gates == ['facts-initial', 'completion-initial', 'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
    assert result['calls'] == 4 and result['known_tokens'] == 120 and result['unknown_reserved_tokens'] == 0
    assert result['timing']['active_elapsed_seconds'] == 400
    assert result['timing']['host_elapsed_seconds'] == 30000
    assert session.budget.contract.descriptor() == execution.LIMITS
    application = json.loads((session.directory/'application.json').read_bytes())
    preview = json.loads((session.directory/'preview.json').read_bytes())
    assert application['report'] == sample[0].source.report.replace(BEFORE, AFTER) == preview['report']
    assert len(application['accepted_submissions']) == 4 and not (session.directory/'edit').exists()
    assert application['preview_sha256'] == execution.sha(session.directory/'preview.json')
    for name in ('facts', 'completion'):
        request = json.loads((session.directory/(name+'-fresh')/'prepared-request.json').read_bytes())
        assert AFTER in request['messages'][1]['content']
        assert 'repairs' not in request['tools'][0]['input_schema']['properties']
        assert 'OFFLINE authored replacement' not in ''.join(m['content'] for m in request['messages'])
        material = json.loads((session.directory/('host-'+name+'-fresh')/'material.json').read_bytes())
        assert material['report'] == application['report']
    instructions = (session.directory/'host-edit/independent-task.json').read_text(encoding='utf-8')
    assert 'reviewer-authored exact repairs' in instructions
    before = session.snapshot()
    record = replay_session(session)
    assert record['outcome'] == result['outcome'] and record['reviewed_stages'] == 6
    assert record['http_count_available'] is False  # SCRIPTED observations are not HTTP evidence.
    assert session.snapshot() == before
    seal = tmp_path/'seal.json'
    replay.seal(seal, directory=session.directory, closure_sha256=session.closure_sha256,
        inputs=session.inputs, event_source=session.gate.event_source, observe=session.observe)
    assert session.snapshot() == before
    with pytest.raises(FileExistsError):
        replay.seal(seal, directory=session.directory, closure_sha256=session.closure_sha256,
            inputs=session.inputs, event_source=session.gate.event_source, observe=session.observe)
    with pytest.raises(ValueError, match='already_started'):
        session.run()
    assert original == (legacy.VERSION, legacy.LIMITS, legacy.SLOTS, legacy.DevelopmentChain, legacy_gate.NativeGate.publish)
    turns[0]['items'][-1]['text'] = '{}'
    with pytest.raises(ValueError):
        replay_session(session)


@pytest.mark.parametrize('at,count', [(s, i+1) for i, s in enumerate(execution.SLOTS)])
@pytest.mark.parametrize('fault', ['missing_observation', 'receipt', 'elapsed', 'timeout', 'pollution'])
def test_hard_failure_stops_shared_budget_without_retry(tmp_path, sample, fault, at, count):
    session, sent, _, _ = setup(tmp_path, sample, fault=fault, at=at)
    result = session.run()
    assert result['outcome'] == 'hard_failure', repr(session.failure)
    assert len(sent) == count and session.budget.stopped
    if fault == 'timeout':
        assert result['unknown_reserved_tokens'] > 0
    if fault == 'receipt':
        assert result['known_tokens'] == 30*count and result['unknown_reserved_tokens'] == 0
    if fault in ('receipt', 'timeout'):
        assert replay_session(session)['outcome'] == 'hard_failure'
    if fault == 'missing_observation':
        record = replay_session(session)
        assert record['outcome'] == 'hard_failure' and record['http_count_available'] is False
        assert not result['attempts'][-1]['complete']
        assert result['attempts'][-1]['observation_verified'] is False
    with pytest.raises(ValueError):
        session.run()


@pytest.mark.parametrize('fault,at,count,outcome', [
    ('both_pass', 'facts-initial', 2, 'initial_both_pass_no_edit'),
    ('terminal', 'facts-initial', 1, 'initial_rejected'),
    ('reject', 'facts-initial', 1, 'initial_rejected'),
    ('reject', 'completion-initial', 2, 'initial_rejected'),
    ('conflict', 'compatibility', 2, 'incompatible_opinions'),
    ('reject', 'edit', 2, 'edit_rejected'),
    ('reject', 'facts-fresh', 3, 'fresh_rejected'),
    ('fresh_issue', 'completion-fresh', 4, 'fresh_rejected'),
    ('cancel', 'completion-initial', 2, 'hard_failure'),
    ('cancel', 'edit', 2, 'hard_failure'),
    ('author_changed', 'facts-initial', 1, 'hard_failure'),
    ('checkpoint', 'facts-initial', 1, 'hard_failure'),
    ('native_mutation', 'compatibility', 2, 'hard_failure'),
    ('bad_anchor', 'facts-initial', 2, 'hard_failure'),
    ('overlap', 'completion-initial', 2, 'hard_failure'),
    ('bad_channel', 'facts-initial', 1, 'hard_failure'),
    ('report_flag', 'edit', 2, 'hard_failure'),
    ('report_hash', 'edit', 2, 'hard_failure'),
    ('report_missing', 'edit', 2, 'hard_failure'),
    ('observation_orphan', 'facts-initial', 1, 'hard_failure'),
])
def test_semantic_and_protocol_stops(tmp_path, sample, fault, at, count, outcome):
    session, sent, _, _ = setup(tmp_path, sample, fault=fault, at=at)
    result = session.run()
    assert result['outcome'] == outcome, repr(session.failure)
    assert len(sent) == count
    if count <= 2:
        assert not (session.directory/'application.json').exists()
    if outcome != 'hard_failure':
        assert replay_session(session)['outcome'] == outcome


@pytest.mark.parametrize('artifact', ['preview.json', 'application.json'])
def test_artifact_mutation_prevents_fresh_and_closure_acceptance(tmp_path, sample, artifact):
    session, sent, _, _ = setup(tmp_path, sample, fault='mutation')
    before = session.before
    def mutate():
        before()
        path = session.directory/artifact
        if path.exists():
            path.write_text('{}', encoding='utf-8')
    session.before = mutate
    result = session.run()
    assert result['outcome'] == 'hard_failure' and len(sent) == 2
    assert not hasattr(session, 'closure_sha256')


def test_cancellation_at_last_boundary_after_application_prevents_fresh(tmp_path, sample):
    session, sent, _, _ = setup(tmp_path, sample, fault='last_boundary')
    def cancel():
        if (session.directory/'application.json').exists():
            raise ValueError('SCRIPTED cancelled after application')
    session.before = cancel
    result = session.run()
    assert result['outcome'] == 'hard_failure' and len(sent) == 2
    assert (session.directory/'application.json').exists()
    replayed = replay_session(session)
    assert replayed['outcome'] == 'hard_failure'
    assert replayed['first_stop_key'] is None and replayed['exact_failure_phase_available'] is False
    assert replayed['last_attempt_slot'] == 'completion-initial'


def test_candidate_identity_rejects_legacy_and_editor_requests(sample):
    from scripts import review_duty_composition as duty
    inputs, _ = sample
    with pytest.raises(ValueError, match='identity'):
        execution.model_for(duty.review_request(inputs, 'facts'))
    request = direct.review_request(inputs, 'facts')
    assert execution.model_for(request) == 'glm-5.3'


def test_tighter_active_budget_stops_before_legacy_2700_limit(tmp_path, sample):
    session, sent, _, _ = setup(tmp_path, sample, fault='tighter_budget')
    sender, wall = session.send, session.wall_clock
    extra = [0]
    session.wall_clock = lambda: wall() + extra[0]
    def slow(request, folder):
        extra[0] += 550
        return sender(request, folder)
    session.send = slow
    result = session.run()
    assert result['outcome'] == 'hard_failure' and len(sent) == 4
    assert result['timing']['active_elapsed_seconds'] == 2600
    assert result['known_tokens'] == 120 and session.budget.stopped
    assert replay_session(session)['outcome'] == 'hard_failure'


@pytest.mark.parametrize('artifact', ['preview.json', 'application.json', 'host-edit/submission.json'])
def test_closed_artifact_changes_are_rejected_by_external_trust_root(tmp_path, sample, artifact):
    session, _, _, _ = setup(tmp_path, sample, fault='closed_mutation')
    assert session.run()['outcome'] == 'development_chain_pass'
    (session.directory/artifact).write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError):
        replay_session(session)


def test_wrong_external_closure_digest_rejected(tmp_path, sample):
    session, _, _, _ = setup(tmp_path, sample, fault='both_pass')
    assert session.run()['outcome'] == 'initial_both_pass_no_edit'
    with pytest.raises(ValueError, match='closure_digest'):
        replay.replay(session.directory, closure_sha256='0'*64, inputs=session.inputs,
            event_source=session.gate.event_source, observe=session.observe)
