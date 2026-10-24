"""Launcher controls with real session/worker and synthetic HTTP/native only."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

from app.evaluation.sol_natural_session import canonical, digest
from scripts import completion_diagnostic_launch as launch
from scripts.reviewer_responses_process import run_once
from tests.test_completion_diagnostic_session import setup, WORKER
from tests.test_sol_session_review import author


@pytest.fixture
def ready(setup,monkeypatch):
    monkeypatch.setattr(launch,'current_head',lambda:'a'*40)
    monkeypatch.setattr(launch,'source',lambda:dict(offline=True))
    controls=launch.prepare(setup['root'],setup['spec']['proof_file'],setup['spec']['proof_sha256'])
    pin=controls['plan_sha256']
    plan,_=launch.load(setup['root'],pin,frozen=True)
    now=datetime.now(timezone.utc)
    grant=dict(launch.grant_binding(plan,pin),issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat(),user_authorization_evidence='SYNTHETIC TEST ONLY')
    auth=setup['root'].parent/'synthetic-authorization.json'
    auth.write_bytes(canonical(grant))
    reads=[]
    monkeypatch.setattr(launch.base,'continuation_credentials',lambda **kwargs:(None,reads.append('hidden') or 'OFFLINE'))
    monkeypatch.setattr(launch,'verify_ci',lambda *args:dict(synthetic=True))
    monkeypatch.setattr(launch,'verify_native_principals',lambda *args:None)
    monkeypatch.setattr(launch,'verify_preflight',lambda *args:None)
    return dict(setup,plan=plan,pin=pin,auth=auth,grant=grant,key_reads=reads)


def execute(state,monkeypatch,*,status=200,mode='valid',guard=None,checkpoint=None,retry=False):
    original=launch.router_for
    def sender(business,**kwargs):
        state['http'].append(status)
        command=[sys.executable,'-X','utf8','-c','STATUS='+str(status)+'\nMODE='+repr(mode)+'\n'+WORKER]
        return run_once(business,**kwargs,command=command)
    monkeypatch.setattr(launch,'router_for',lambda session,key,override=None:original(session,key,override or sender))
    return launch.execute(state['plan'],state['pin'],state['source'],authorization_file=state['auth'],
        authorization_sha=digest(state['auth'].read_bytes()),ci_run='OFFLINE',preflight={},
        guard=guard,checkpoint=checkpoint,manual_retry=retry)


@pytest.mark.parametrize('mode', ['valid','timeout','identity'])
def test_real_worker_pause_or_hard_stop_preserves_cost_and_plain_resume_does_not_prompt(ready,monkeypatch,mode):
    result=execute(ready,monkeypatch,status=524 if mode=='timeout' else 200,
                   mode='identity' if mode=='identity' else 'valid')
    assert len(ready['http'])==len(ready['key_reads'])==1
    assert result['phase']==('closed' if mode=='identity' else 'paused')
    root=ready['root']/'execution/session'
    guard=digest((root/'guard.json').read_bytes())
    checkpoint=digest(sorted((root/'checkpoints').glob('*.json'))[-1].read_bytes())
    if mode=='identity':
        before=launch.inventory(ready['root'])
        replayed=launch.replay(ready['plan'],ready['pin'],ready['source'],guard=guard,checkpoint=checkpoint,
            authorization_sha=digest(ready['auth'].read_bytes()))
        assert replayed['strict_replay'] and replayed['accounting']['calls']==5
        assert replayed['accounting']['tokens']==66591 and replayed['accounting']['reserved_tokens']>0
        assert launch.inventory(ready['root'])==before
    else:
        # The first argument remains an actual owner guard, not a recomputed replacement.
        result=launch.execute(ready['plan'],ready['pin'],ready['source'],authorization_file=ready['auth'],
            authorization_sha=digest(ready['auth'].read_bytes()),ci_run='OFFLINE',preflight={},
            guard=guard,checkpoint=checkpoint)
        assert result['phase']=='paused'
        assert len(ready['http'])==len(ready['key_reads'])==1


@pytest.mark.parametrize('change', ['expired','budget','parent_proof','head'])
def test_invalid_specific_grant_never_reads_key_or_sends(ready,monkeypatch,change):
    grant=ready['grant']
    if change=='expired':
        now=datetime.now(timezone.utc)-timedelta(days=2)
        grant.update(issued_at=now.isoformat(),expires_at=(now+timedelta(hours=1)).isoformat())
    elif change=='budget':
        grant['limits']={**grant['limits'],'max_new_attempts':11}
    elif change=='parent_proof':
        grant['parent_proof_sha256']='0'*64
    else:
        grant['head']='0'*40
    ready['auth'].write_bytes(canonical(grant))
    with pytest.raises(ValueError,match='completion_specific_unexpired_authorization_required'):
        execute(ready,monkeypatch)
    assert ready['key_reads']==ready['http']==[]
    assert not (ready['root']/'execution').exists()


def test_prepared_paths_and_source_are_checked_without_key(ready,monkeypatch):
    monkeypatch.setattr(launch,'source',lambda:dict(changed=True))
    with pytest.raises(ValueError,match='completion_frozen_source_changed'):
        launch.load(ready['root'],ready['pin'],frozen=True)
    assert ready['key_reads']==ready['http']==[]


def test_native_semantic_rejection_seals_at_actual_stage_without_resend(ready,monkeypatch):
    assert execute(ready,monkeypatch)['phase']=='paused'
    root=ready['root']/'execution/session'
    guard=digest((root/'guard.json').read_bytes())
    checkpoint=digest(sorted((root/'checkpoints').glob('*.json'))[-1].read_bytes())
    auth_sha=digest(ready['auth'].read_bytes())
    session,gate=launch.session_for(ready['plan'],ready['pin'],ready['source'],
        before_new_model=None,guard=guard,checkpoint=checkpoint,authorization_sha=auth_sha)
    with session:
        handle=list(gate.handles())[-1]
        primary,event=author(handle,ready['turns'],gate.native.current.workspace,accepted=False)
        assert gate.submit('control-b',primary,event) is False
    before=launch.inventory(ready['root'])
    result=launch.replay(ready['plan'],ready['pin'],ready['source'],guard=guard,
        checkpoint=session.checkpoint_sha,authorization_sha=auth_sha)
    assert result['replay_mode']=='native-rejection-frontier'
    assert result['result']==dict(reason='session_semantic_rejected',key='control-b')
    assert result['accounting']['calls']==5 and result['accounting']['tokens']==66611
    assert before==launch.inventory(ready['root'])
    assert len(ready['http'])==len(ready['key_reads'])==1
