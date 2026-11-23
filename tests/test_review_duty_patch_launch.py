"""Prospective launch tests. Grants, CI and native content are SCRIPTED, never authority."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

from app.evaluation.golden_journal import write_new_json
from scripts import review_duty_patch_launch as candidate
from scripts import review_duty_patch_replay  # Bind Reader before test constructor substitution.
from scripts.full_chain_modules import private_module
from scripts.review_duty_host_gate import sha
from tests.test_review_duty_patch_execution import setup

launch = candidate._launch
_fixture = private_module(launch.ROOT/'tests/test_review_duty_launch.py',
    {'scripts.review_duty_launch': launch})
prepared = _fixture.prepared
kwargs, install_preflights = _fixture.kwargs, _fixture.install_preflights

# Unchanged launch invariants are executed against the candidate's own globals.
test_preflight_failures_precede_secret_and_run = _fixture.test_preflight_failures_precede_secret_and_run
test_claim_survives_failure_and_blocks_second_secret_access = _fixture.test_claim_survives_failure_and_blocks_second_secret_access
test_package_source_and_control_path_pins = _fixture.test_package_source_and_control_path_pins
test_actual_absolute_python_startup_and_wrong_identity = _fixture.test_actual_absolute_python_startup_and_wrong_identity
test_competing_launches_claim_before_single_secret_read = _fixture.test_competing_launches_claim_before_single_secret_read
test_dangling_run_link_refused_before_credentials = _fixture.test_dangling_run_link_refused_before_credentials


def install_chain(p, monkeypatch, fault=None, *, real_transport=False):
    install_preflights(p, monkeypatch)
    session, sent, gates, turns = setup(p['operator'], (p['inputs'], p['facts']), fault='SCRIPTED_LAUNCH')
    original_judge = session.judge
    if fault == 'after_submit':
        original_submit = session.gate.submit
        def submit(handle, *args):
            accepted = original_submit(handle, *args)
            (p['operator']/'host-controls'/(handle['binding']['key']+'.pending.json')).write_text('{}')
            return accepted
        monkeypatch.setattr(session.gate, 'submit', submit)
    original_check = launch.HostMailbox.check_controls
    @contextmanager
    def client(exe):
        yield session.gate.event_source.client
    monkeypatch.setattr(launch, 'CodexReadOnlyClient', client)
    monkeypatch.setattr(launch, 'load_role_settings', lambda p: (object(), object()))
    if not real_transport:
        monkeypatch.setattr(launch.transport, 'Sender', lambda **kw: session.send)
        monkeypatch.setattr(launch.transport, 'verify', session.observe)
    def factory(**kw):
        from scripts.host_review_workspace import HostReviewWorkspace
        session.directory, session.observations = kw['directory'], kw['observations']
        session.workspace = HostReviewWorkspace(cwd=launch.ROOT, python=sys.executable,
            answers=kw['answers'], evidence_roots=(launch.RUN,))
        session.gate.workspace = session.workspace
        session.judge, session.before = kw['judge'], kw['before_send']
        if real_transport:
            import time
            session.send, session.observe, session.wall_clock = kw['send'], kw['observe'], time.monotonic
        return session
    monkeypatch.setattr(launch.execution, 'DevelopmentChain', factory)
    processed = set()
    def check_controls(mailbox, allowed=()):
        original_check(mailbox, allowed)
        for pending in mailbox.root.glob('*.pending.json'):
            if pending in processed:
                continue
            processed.add(pending)
            handle = launch.read(pending)
            key = handle['binding']['key']
            guard_sha = sha(p['operator']/'worker-guard.json')
            task = launch.host_command(p['operator'], key, guard_sha=guard_sha, action='task')
            assert task == (Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8')
            assert str(session.workspace.answers) in task and str(launch.ROOT) in task
            if fault == 'abort' or fault == 'abort_edit' and key == 'edit':
                launch.host_command(p['operator'], key, guard_sha=guard_sha, action='abort',
                    checkpoint_sha=handle['checkpoint_sha256'])
                return
            primary, event = original_judge(handle, 86400)
            notes = p['operator']/(key+'.primary.json')
            write_new_json(notes, primary)
            launch.host_command(p['operator'], key, guard_sha=guard_sha, action='submit',
                checkpoint_sha=handle['checkpoint_sha256'], notes=notes,
                event_id='missing' if fault == 'wrong_event' else event)
            if fault == 'pending_changed':
                pending.write_text('{}')
            if fault == 'author_changed':
                session.workspace.answer_path(Path(handle['folder'])/'task-checkpoint.json',
                    handle['checkpoint_sha256']).write_text('{}')
            if fault == 'late_source':
                monkeypatch.setattr(launch, 'source_inventory', lambda: {})
    monkeypatch.setattr(launch.HostMailbox, 'check_controls', check_controls)
    return session, sent, gates, turns


@pytest.mark.parametrize('fault', [None, 'abort', 'abort_edit', 'pending_changed',
    'author_changed', 'wrong_event', 'late_source', 'after_submit'])
def test_mailbox_native_import_closed_audit_and_stop(prepared, monkeypatch, fault):
    p = prepared
    session, sent, gates, turns = install_chain(p, monkeypatch, fault)
    result = launch.execute(**kwargs(p))
    assert result['outcome'] == ('development_chain_pass' if fault is None else 'hard_failure'), repr(session.failure)
    assert len(sent) == (4 if fault is None else 2 if fault == 'abort_edit' else 1)
    closed = p['operator']/'execution-exit.json'
    assert launch.read(closed)['closure_sha256'] == getattr(session, 'closure_sha256', None)
    if fault is None:
        assert len(gates) == 6
        original_auth = launch.authorization
        def expired(*a, **kw):
            if kw.get('now') is None:
                raise ValueError('expired')
            return original_auth(*a, **kw)
        monkeypatch.setattr(launch, 'authorization', expired)
        params = dict(guard_sha=sha(p['operator']/'worker-guard.json'), exit_sha=sha(closed), codex_executable=launch.CODEX)
        before = session.snapshot()
        record = launch.audit(p['operator'], **params, output=p['operator']/'seal.json')
        assert record['calls'] == 4 and record['reviewed_stages'] == 6
        assert record['kind'] == 'direct-patch-readonly-replay-v1' and session.snapshot() == before
        with pytest.raises(FileExistsError):
            launch.audit(p['operator'], **params, output=p['operator']/'seal.json')
        turns[0]['items'][-1]['text'] = '{}'
        with pytest.raises(ValueError):
            launch.audit(p['operator'], **params)


def test_new_grant_and_budget_do_not_accept_closed_batch_authorization(prepared, monkeypatch):
    from scripts import review_duty_launch as old
    p = prepared
    calls = install_preflights(p, monkeypatch)
    assert p['saved']['budget']['maximum_calls'] == 4 and p['saved']['budget']['flash_high'] == 0
    assert p['saved']['plan']['limits']['execution_timeout_s'] == 2400
    grant = {**p['grant'], 'kind': old.AUTH_VERSION}
    p['authorization'].write_text(__import__('json').dumps(grant), encoding='utf-8')
    with pytest.raises(ValueError):
        launch.execute(**kwargs(p))
    assert not calls and not launch.RUN.exists()


def test_inventory_pins_candidate_and_frozen_dependencies():
    paths = launch.source_inventory()
    for name in ('review_duty_patch_execution', 'review_duty_patch_replay',
                 'review_duty_patch_transport', 'review_duty_patch_launch', 'review_duty_launch'):
        assert 'scripts/'+name+'.py' in paths
