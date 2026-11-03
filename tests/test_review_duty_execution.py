"""Scripted IO and native-host fixtures: no actual model or semantic certification."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from scripts import review_duty_execution as execution
from scripts import review_duty_composition as duty
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.review_duty_host_gate import sha
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER

PASS = dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('offline fixture cannot connect')
    monkeypatch.setattr(socket.socket,'connect',reject)
    monkeypatch.setattr(socket,'create_connection',reject)


@pytest.fixture(scope='module')
def sample():
    _,inputs,_,raw = cases()['claim-scope:4']
    return inputs,json.loads(raw)


def setup(tmp_path,sample,*,fault=None,at='facts-initial'):
    inputs, facts = sample
    plan = execution.preparation(inputs,primary='synthetic-root',independent='synthetic-child')
    turns, sent, gates = [], [], []
    wall = NS(now=0)
    def native(method,params):
        if fault == 'native_mutation' and gates and gates[-1] == at:
            (session.directory/'plan.json').write_text('{}')
        if method == 'thread/read':
            return dict(thread=dict(id='synthetic-child',parentThreadId='synthetic-root',
                source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='synthetic-root')))))
        return dict(data=turns,nextCursor=None)
    source = CodexHostReviewEventSource(NS(request=native),plan)
    def send(request,folder):
        slot=folder.name;sent.append(slot);wall.now += 100
        if fault=='timeout' and slot==at: raise TimeoutError('scripted unknown result')
        if fault=='elapsed' and slot==at: wall.now += 2700
        model=execution.model_for(request)
        if slot=='edit':
            args=dict(edits={'block_4':[dict(before=BEFORE,after=AFTER,reason='Scripted edit witness')]})
            if fault=='bad_anchor': args['edits']['block_4'][0]['before']='absent anchor'
            name='submit_block_edits'
        else:
            args=deepcopy(facts if slot=='facts-initial' and fault!='both_pass' else PASS)
            if fault=='fresh_issue' and slot==at: args=deepcopy(facts)
            name='submit_report_review'
        if fault=='bad_channel' and slot==at: name='unexpected_tool'
        response=ChatResponse(provider='zhipu',model=model,content=None,finish_reason='tool_calls',
            tool_calls=(ToolCall(id='SCRIPTED',name=name,arguments=args),),usage=TokenUsage(20,10))
        raw=execution.request_bytes(request)
        if not (fault=='missing_observation' and slot==at):
            record=dict(fixture='SCRIPTED body-free observation, not HTTP proof',
                request_sha256=hashlib.sha256(raw).hexdigest(),complete=True)
            (session.observations/(slot+'.json')).write_text(json.dumps(record),encoding='utf-8')
        if fault=='pollution' and slot==at: (session.directory/'unexpected.json').write_text('{}')
        if fault=='observation_orphan' and slot==at: (session.observations/'orphan.json').write_text('{}')
        receipt='0'*64 if fault=='receipt' and slot==at else hashlib.sha256(raw).hexdigest()
        return Exchange(request,response,receipt)
    def observe(folder,root,*,complete_required):
        path=root/(folder.name+'.json')
        record=json.loads(path.read_bytes())
        assert record['request_sha256']==sha(folder/'issued-request.json')
        assert record['complete'] is True
        return {str(path):sha(path)}
    def judge(handle,remaining):
        key=handle['binding']['key'];gates.append(key)
        if fault=='cancel' and key==at: stop.value=True
        wall.now += 5000
        def decision(role):
            accepted=not (fault in ('reject','conflict') and key==at and role=='independent')
            reviewer=plan['review_principals'][role]['principal_id']
            report = dict(report_sha256=handle['binding']['report_sha256'],reviewer=reviewer,
                source_review='SCRIPTED actual-report assessment',facts_and_sources_correct=True,
                correct_content_preserved=True,identity_and_goal_preserved=True,true_errors_fixed=True
            ) if handle['kind']=='edit' else None
            if key==at and role=='independent':
                if fault=='report_flag': report['true_errors_fixed']=False
                if fault=='report_hash': report['report_sha256']='0'*64
                if fault=='report_missing': report=None
            return dict(kind=handle['kind'],reviewer=reviewer,
                material_sha256=handle['material_sha256'],source_review='SCRIPTED fixture, no actual semantic review',
                accepted=accepted,defects=[] if accepted else [dict(kind='wrong_correction',detail='Scripted rejection')],
                compatibility=('clear' if accepted else 'conflict') if handle['kind']=='compatibility' else None,
                actual_report_checked=True,report_assessment=report)
        folder=Path(handle['folder']);bound=handle['binding']
        answer=dict(binding=bound,review=dict(binding=bound,decision=decision('independent')))
        path=session.workspace.answer_path(folder/'task-checkpoint.json',handle['checkpoint_sha256'])
        with path.open('x',encoding='utf-8') as f: json.dump(answer,f,ensure_ascii=False,indent=2)
        if fault is None:
            checked=subprocess.run([sys.executable,'-B','-m','scripts.host_review_task_checkpoint','check-answer',
                '--checkpoint',str(folder/'task-checkpoint.json'),'--checkpoint-sha',handle['checkpoint_sha256'],
                '--answer-file',str(path)],cwd=execution.ROOT,capture_output=True)
            assert checked.returncode==0,checked.stderr.decode('utf-8')
        else:
            from scripts.host_review_task_checkpoint import check_answer
            check_answer(folder/'task-checkpoint.json',handle['checkpoint_sha256'],path.read_bytes())
        text=path.read_text(encoding='utf-8')
        turns.insert(0,dict(id=key,status='completed',itemsView='full',error=None,items=[
            dict(id='dispatch',type='userMessage',content=[dict(type='text',text=(folder/'independent-task.json').read_text(encoding='utf-8'))]),
            dict(id='final',type='agentMessage',phase='final_answer',text=text)]))
        if fault=='author_changed' and key==at: path.write_text('{}')
        if fault=='checkpoint' and key==at: (folder/'task-checkpoint.json').write_text('{}')
        return decision('primary'),'synthetic-child/'+key+'/final'
    stop=NS(value=False)
    def before():
        if stop.value: raise ValueError('scripted_cancelled')
    session=execution.DevelopmentChain(directory=tmp_path/'run',answers=tmp_path/'answers',
        observations=tmp_path/'observations',inputs=inputs,plan=plan,event_source=source,
        send=send,observe=observe,judge=judge,before_send=before,wall_clock=lambda:wall.now)
    return session,sent,gates,turns


def test_full_chain_actual_author_io_native_import_and_single_budget(tmp_path,sample):
    session,sent,gates,turns=setup(tmp_path,sample)
    result=session.run()
    assert result['outcome']=='development_chain_pass',repr(session.failure)
    assert sent==list(execution.SLOTS)
    assert gates==['facts-initial','completion-initial','compatibility','edit','facts-fresh','completion-fresh']
    assert result['calls']==5 and result['known_tokens']==150 and result['unknown_reserved_tokens']==0
    assert result['timing']['active_elapsed_seconds']==500
    assert result['timing']['host_elapsed_seconds']==30000
    assert result['production_admitted'] is False
    before=session.snapshot()
    assert session.replay()==result and session.snapshot()==before
    with pytest.raises(ValueError,match='already_started'): session.run()
    fresh=json.loads((session.directory/'facts-fresh/prepared-request.json').read_bytes())
    assert AFTER in fresh['messages'][1]['content']
    assert 'duty_reviews' not in ''.join(m['content'] for m in fresh['messages'])
    turns[0]['items'][-1]['text']='{}'
    with pytest.raises(ValueError): session.replay()


@pytest.mark.parametrize('at,count',[(s,i+1) for i,s in enumerate(execution.SLOTS)])
@pytest.mark.parametrize('fault',['missing_observation','receipt','elapsed','timeout','pollution'])
def test_hard_fault_never_sends_next_request(tmp_path,sample,at,count,fault):
    session,sent,_,_=setup(tmp_path,sample,fault=fault,at=at)
    result=session.run()
    assert result['outcome']=='hard_failure'
    assert len(sent)==count,repr(session.failure)
    assert session.budget.stopped
    if fault=='timeout': assert result['unknown_reserved_tokens']>0
    if fault=='receipt':
        assert result['known_tokens']==30*count and result['unknown_reserved_tokens']==0
        assert (session.directory/at/'response.json').is_file()
        assert result['attempts'][-1]['response_present'] and result['attempts'][-1]['observation_verified']
    with pytest.raises(ValueError):session.run()


@pytest.mark.parametrize('fault,at,count,outcome',[
    ('both_pass','facts-initial',2,'initial_both_pass_no_edit'),
    ('reject','facts-initial',1,'initial_rejected'),
    ('reject','completion-initial',2,'initial_rejected'),
    ('conflict','compatibility',2,'incompatible_opinions'),
    ('reject','edit',3,'edit_rejected'),
    ('reject','facts-fresh',4,'fresh_rejected'),
    ('fresh_issue','completion-fresh',5,'fresh_rejected'),
    ('cancel','completion-initial',2,'hard_failure'),
    ('author_changed','facts-initial',1,'hard_failure'),
    ('checkpoint','facts-initial',1,'hard_failure'),
    ('native_mutation','compatibility',2,'hard_failure'),
    ('bad_anchor','edit',3,'hard_failure'),
    ('bad_channel','facts-initial',1,'hard_failure'),
    ('report_flag','edit',3,'hard_failure'),
    ('report_hash','edit',3,'hard_failure'),
    ('report_missing','edit',3,'hard_failure'),
    ('observation_orphan','facts-initial',1,'hard_failure'),
    ('observation_orphan','completion-fresh',5,'hard_failure'),
])
def test_semantic_and_handoff_stops_are_not_retried(tmp_path,sample,fault,at,count,outcome):
    session,sent,_,_=setup(tmp_path,sample,fault=fault,at=at)
    result=session.run()
    assert result['outcome']==outcome,repr(session.failure)
    assert len(sent)==count


def test_exact_request_identity_rejects_changed_policy_schema_and_expanded_timeout(sample):
    inputs,_=sample
    prepared=duty.review_request(inputs,'facts')
    issued=replace(prepared,timeout_s=20,metadata={**prepared.metadata,'coach_budget_contract':'coach-bounded-review-v2'})
    assert execution.check_issued(prepared,issued)
    for bad in [replace(issued,timeout_s=601),replace(issued,temperature=.2),
            replace(issued,messages=(replace(issued.messages[0],content='changed'),*issued.messages[1:])),
            replace(issued,tools=())]:
        with pytest.raises(ValueError): execution.check_issued(prepared,bad)


def test_empty_evidence_root_redirect_is_rejected_before_send(tmp_path,sample):
    session,sent,_,_=setup(tmp_path,sample)
    target=tmp_path/'elsewhere';target.mkdir()
    try:
        session.observations.symlink_to(target,target_is_directory=True)
    except OSError:
        pytest.skip('This host cannot create directory symlinks')
    with pytest.raises(ValueError,match='linked_evidence_root'):
        session.snapshot()
    assert not sent
