"""Durable reconstruction across processes; SCRIPTED model/native evidence."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import review_duty_replay as replay
from tests.test_review_duty_execution import sample, no_network, setup


def params(session):
    return dict(closure_sha256=session.closure_sha256,inputs=session.inputs,
        event_source=session.gate.event_source,observe=session.observe)


@pytest.mark.parametrize('fault,at',[
    (None,'facts-initial'),('both_pass','facts-initial'),('conflict','compatibility'),
    ('reject','edit'),('fresh_issue','completion-fresh'),('timeout','facts-fresh'),
    ('receipt','edit'),('bad_channel','facts-initial'),('bad_anchor','edit'),
    ('missing_observation','facts-initial'),
])
def test_closed_chain_reconstructs_without_any_write(tmp_path,sample,fault,at):
    session,_,_,_=setup(tmp_path,sample,fault=fault,at=at)
    result=session.run()
    assert hasattr(session,'closure_sha256'),repr(session.failure)
    before=session.snapshot()
    record=replay.replay(session.directory,**params(session))
    assert record['outcome']==result['outcome']
    assert record['known_tokens']==result['known_tokens']
    assert session.snapshot()==before
    assert record['http_requests'] is None  # SCRIPTED observation is not HTTP evidence.
    assert record['http_send_unknown_calls']==result['calls']
    assert record['first_stop_key']==(None if fault in (None,'both_pass') else at)
    sealed=replay.seal(tmp_path/'seal.json',directory=session.directory,**params(session))
    assert sealed==record and session.snapshot()==before
    with pytest.raises(FileExistsError):
        replay.seal(tmp_path/'seal.json',directory=session.directory,**params(session))


def test_replay_in_new_process_and_mutation_refusal(tmp_path,sample):
    session,_,_,turns=setup(tmp_path,sample,fault='both_pass')
    session.run()
    (tmp_path/'native.json').write_text(json.dumps(turns),encoding='utf-8')
    program=r'''
import json,sys
def guard(event,args):
    if event=='socket.connect': raise RuntimeError('offline_replay_network_forbidden')
sys.addaudithook(guard)
from pathlib import Path
from types import SimpleNamespace as NS
from scripts.review_duty_replay import replay
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.review_duty_host_gate import sha
from tests.test_coarse_revision_editor import cases
root=Path(sys.argv[1]);run=root/'run'
turns=json.loads((root/'native.json').read_bytes())
def native(method,params):
    if method=='thread/read':
        return dict(thread=dict(id='synthetic-child',parentThreadId='synthetic-root',
            source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='synthetic-root')))))
    return dict(data=turns,nextCursor=None)
def observe(folder,root,*,complete_required):
    path=root/(folder.name+'.json')
    assert json.loads(path.read_bytes())['request_sha256']==sha(folder/'issued-request.json')
    return {str(path):sha(path)}
source=CodexHostReviewEventSource(NS(request=native),json.loads((run/'plan.json').read_bytes()))
record=replay(run,closure_sha256=sys.argv[2],inputs=cases()['claim-scope:4'][1],event_source=source,observe=observe)
print(json.dumps(record,ensure_ascii=True))
'''
    before=session.snapshot()
    result=subprocess.run([sys.executable,'-B','-c',program,str(tmp_path),session.closure_sha256],
        capture_output=True,cwd=replay.execution.ROOT)
    assert result.returncode==0,result.stderr.decode('utf-8')
    assert json.loads(result.stdout)['outcome']=='initial_both_pass_no_edit'
    assert session.snapshot()==before
    for target in [session.directory/'result.json',session.directory/'closure.json',
            session.directory/'facts-initial/receipt.json',next(session.workspace.answers.iterdir())]:
        raw=target.read_bytes();target.write_bytes(raw+b' ')
        with pytest.raises(ValueError):replay.replay(session.directory,**params(session))
        target.write_bytes(raw)
    (session.directory/'facts-initial/unexpected.json').write_text('{}')
    with pytest.raises(ValueError):replay.replay(session.directory,**params(session))


@pytest.mark.parametrize('target',['request','ledger','material'])
def test_reconstruction_rejects_even_a_rehashed_corrupt_closure(tmp_path,sample,target):
    session,_,_,_=setup(tmp_path,sample,fault='both_pass')
    session.run()
    if target=='request':
        path=session.directory/'facts-initial/prepared-request.json'
        value=replay.read(path);value['messages'][0]['content']='changed'
    elif target=='ledger':
        path=session.directory/'result.json'
        value=replay.read(path);value['known_tokens']=0
    else:
        path=session.directory/'host-facts-initial/material.json'
        value=replay.read(path);value['report']='changed'
    path.write_text(json.dumps(value),encoding='utf-8')
    closure_path=session.directory/'closure.json';closure=replay.read(closure_path)
    closure['files'][str(path)]=replay.sha(path)
    closure_path.write_text(json.dumps(closure),encoding='utf-8')
    session.closure_sha256=replay.sha(closure_path)
    with pytest.raises(ValueError):replay.replay(session.directory,**params(session))
