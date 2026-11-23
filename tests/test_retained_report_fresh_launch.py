"""Fresh-only orchestration against the real owned worker with offline HTTP.

Native authors here are explicit test fixtures, never semantic evidence.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import socket
import sys

import pytest

from scripts import retained_report_fresh_launch as launch
from app.evaluation import sol_original15_session as original_engine
from app.evaluation.sol_natural_session import SessionPaused, SessionBlocked
from tests.test_sol_session_review import controls, author
from tests.test_sol_original15_session import router, WORKER
from scripts.reviewer_responses_process import run_once


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a,**k): raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)


@pytest.fixture
def setup(tmp_path):
    opened,turns,_=controls(tmp_path/'native')
    _,template=opened()
    plan=dict(operator=str(tmp_path/'operator'),python=sys.executable,review_plan=template.plan)
    _,fixed=original_engine.case_for('claim-scope:4')
    def open_session(previous=None,**kwargs):
        return launch.open_session(plan,'1'*64,template.native.event_source,authorization_sha='2'*64,
            guard=previous.guard_sha if previous else None,
            checkpoint=previous.checkpoint_sha if previous else None,before=lambda:None,
            sink=lambda value:None,**kwargs)
    return open_session,turns,fixed,plan,template.native.event_source


def import_current(open_session,turns,previous,*,accepted=True):
    session,gate=open_session(previous)
    with session:
        handle=list(gate.handles())[-1]
        primary,event=author(handle,turns,gate.native.workspace,accepted=accepted)
        assert gate.submit(handle['binding']['key'],primary,event) is accepted
    return session,handle


def test_two_fresh_real_worker_resume_and_readonly_replay(setup):
    open_session,turns,fixed,_,_=setup
    previous=None;calls=[];keys=[]
    for _ in range(2):
        session,gate=open_session(previous)
        with pytest.raises(SessionPaused,match='awaiting_native_review'),session:
            launch.run_reviews(session,router(session,calls,mode='pass'),fixed)
        previous,handle=import_current(open_session,turns,session)
        keys.append(handle['binding']['key'])
        material=launch.read(Path(handle['folder'])/'material.json')
        assert material['stage']=='fresh' and material['report']==fixed.source.report
        assert 'old_opinions' not in material
    final,_=open_session(previous)
    with final:
        result=launch.run_reviews(final,router(final,calls,mode='pass'),fixed)
        final.close(dict(result=result))
    assert keys==['facts-fresh','completion-fresh'] and len(calls)==2
    assert result['both_fresh_pass'] and not result['qualified']
    assert not (final.journal_root/'application.json').exists()
    readonly,_=open_session(final,read_only=True)
    with readonly:
        assert launch.run_reviews(readonly,router(readonly,calls,mode='pass'),fixed)==result
        accounting=launch.original.audit_transport(readonly)
    assert len(calls)==2 and accounting['http_requests_known']==2


def test_timeout_pauses_success_prefix_and_manual_retry_only(setup):
    open_session,turns,fixed,_,_=setup
    calls=[]
    first,_=open_session()
    with pytest.raises(SessionPaused,match='awaiting_native_review'),first:
        launch.run_reviews(first,router(first,calls,mode='pass'),fixed)
    accepted,_=import_current(open_session,turns,first)
    failed,_=open_session(accepted)
    with pytest.raises(SessionPaused,match='timeout_awaiting_manual_retry'),failed:
        launch.run_reviews(failed,router(failed,calls,status=524),fixed)
    assert len(calls)==2 and not (failed.root/'terminal.json').exists()
    idle,_=open_session(failed)
    with pytest.raises(SessionPaused,match='timeout_awaiting_manual_retry'),idle:
        launch.run_reviews(idle,router(idle,calls),fixed)
    assert len(calls)==2
    retried,_=open_session(idle,manual_retry=True)
    with pytest.raises(SessionPaused,match='awaiting_native_review'),retried:
        launch.run_reviews(retried,router(retried,calls,mode='pass'),fixed)
    final_import,_=import_current(open_session,turns,retried)
    final,_=open_session(final_import)
    with final:
        result=launch.run_reviews(final,router(final,calls,mode='pass'),fixed)
        accounting=launch.original.audit_transport(final)
    assert len(calls)==3 and result['accounting']['retries']==1
    assert accounting['unknown_usage_calls']==1 and accounting['unknown_reserved_tokens']>0
    assert [launch.read(p)['request']['metadata']['sol_review_validation']['duty']
            for p in sorted((final.root/'operations').glob('*-intent.json'))
            if launch.read(p)['kind']=='model']==['facts','completion','completion']


def test_semantic_rejection_preserves_output_and_prevents_next_call(setup):
    open_session,turns,fixed,_,_=setup
    calls=[]
    first,_=open_session()
    with pytest.raises(SessionPaused),first:
        launch.run_reviews(first,router(first,calls,mode='pass'),fixed)
    rejected,_=import_current(open_session,turns,first,accepted=False)
    resumed,_=open_session(rejected)
    with pytest.raises(SessionBlocked,match='semantic_rejected'),resumed:
        launch.run_reviews(resumed,router(resumed,calls,mode='pass'),fixed)
    assert len(calls)==1 and (rejected.transport_root/'review/call-001/receipt.json').exists()


@pytest.mark.parametrize('fault',['expired','wrong_report','old_limits','empty_evidence'])
def test_authorization_exact_scope_and_time(fault):
    now=datetime.now(timezone.utc)
    plan=dict(head='1'*40,review_profile=launch.original.profile(),estimated_envelope_cny='0.43776')
    grant=dict(launch.grant_binding(plan,'2'*64),issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=24)).isoformat(),user_authorization_evidence='Explicit fixture consent')
    if fault=='expired': grant['expires_at']=(now-timedelta(seconds=1)).isoformat()
    if fault=='wrong_report': grant['report_sha256']='0'*64
    if fault=='old_limits': grant['limits']={**launch.LIMITS,'max_requests':10}
    if fault=='empty_evidence': grant['user_authorization_evidence']=''
    with pytest.raises(ValueError,match='specific_unexpired_authorization'):
        launch.validate_grant(grant,plan,'2'*64,now=now)


def test_one_new_request_boundary_never_repeats_success(setup):
    open_session,turns,fixed,_,_=setup
    calls=[]
    first,_=open_session(max_new_models=1)
    with pytest.raises(SessionPaused,match='awaiting_native_review'),first:
        launch.run_reviews(first,router(first,calls,mode='pass'),fixed)
    imported,_=import_current(open_session,turns,first)
    host_only,_=open_session(imported,max_new_models=0)
    with pytest.raises(SessionPaused,match='model_boundary'),host_only:
        launch.run_reviews(host_only,router(host_only,calls,mode='pass'),fixed)
    assert len(calls)==1


def test_actual_launcher_preflight_key_boundary_resume_and_timeout(setup,tmp_path,monkeypatch):
    open_session,turns,fixed,plan,events=setup
    plan.update(head='1'*40,review_profile=launch.original.profile(),estimated_envelope_cny='0.43776',
                historical_accounting=dict(http_requests=5,known_tokens=67065,unknown_reserved_tokens=73756,retries=1))
    monkeypatch.setattr(launch,'load',lambda *a,**k:plan)
    monkeypatch.setattr(launch,'inputs',lambda p:fixed)
    monkeypatch.setattr(launch,'verify_preflight',lambda *a:None)
    monkeypatch.setattr(launch,'verify_native_principals',lambda *a:None)
    ci_reads=[];keys=[];statuses=[];roots=[]
    def ci(run,head):
        ci_reads.append((run,head));return dict(run_id=run,head_sha=head,status='completed',conclusion='success')
    monkeypatch.setattr(launch.base,'verify_ci',ci)
    now=datetime.now(timezone.utc)
    grant=dict(launch.grant_binding(plan,'1'*64),issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=24)).isoformat(),user_authorization_evidence='Synthetic consent')
    grant_file=tmp_path/'grant.json';grant_file.write_text(json.dumps(grant),encoding='utf-8')
    def key_reader(): keys.append(True);return 'OFFLINE_SENTINEL'
    status=[200]
    def sender(business,**kwargs):
        statuses.append(status[0])
        return run_once(business,**kwargs,command=[sys.executable,'-c',
            "MODE='pass'\nSTATUS="+str(status[0])+'\n'+WORKER])
    def run(*,manual=False,host=False):
        saved=dict(guard=roots[-1]['guard_sha256'],checkpoint=roots[-1]['checkpoint_sha256']) if roots else {}
        return launch.execute(plan,'1'*64,events,authorization_file=grant_file,
            authorization_sha=launch.pin(grant_file),preflight_proof={},ci_run='123',
            manual_retry=manual,host_only=host,key_reader=key_reader,sender=sender,
            sink=roots.append,**saved)
    assert run()['reason']=='session_awaiting_native_review'
    assert len(statuses)==len(keys)==len(ci_reads)==1
    # Awaiting a Host review is a zero-key and zero-CI path.
    assert run()['reason']=='session_awaiting_native_review'
    assert len(statuses)==len(keys)==len(ci_reads)==1
    def submit():
        current=roots[-1]
        session,gate=launch.open_session(plan,'1'*64,events,authorization_sha=launch.pin(grant_file),
            guard=current['guard_sha256'],checkpoint=current['checkpoint_sha256'],sink=roots.append)
        with session:
            handle=list(gate.handles())[-1]
            primary,event=author(handle,turns,gate.native.workspace)
            assert gate.submit(handle['binding']['key'],primary,event)
    submit()
    class Later(datetime):
        @classmethod
        def now(cls,tz=None): return now+timedelta(days=2)
    monkeypatch.setattr(launch,'datetime',Later)
    assert run(host=True)['reason']=='session_model_boundary'
    assert len(statuses)==1
    with pytest.raises(ValueError,match='specific_unexpired_authorization'):
        run()
    assert len(keys)==1 and len(statuses)==1
    # The failed preflight is before a model intent; original session roots
    # remain sufficient, with no new charge or automatic renewal.
    monkeypatch.setattr(launch,'datetime',datetime)
    ci_reads.clear()
    status[0]=524
    assert run()['reason']=='session_timeout_awaiting_manual_retry'
    assert run()['reason']=='fresh_awaiting_manual_retry'
    assert len(statuses)==2
    status[0]=200
    assert run(manual=True)['reason']=='session_awaiting_native_review'
    submit()
    assert run(host=True)['phase']=='completed'
    assert statuses==[200,524,200] and len(keys)==3 and len(ci_reads)==2
    with pytest.raises(SessionBlocked,match='closed_or_unresolved'):
        run()
    assert len(statuses)==3
    current=roots[-1]
    kw=dict(authorization_sha=launch.pin(grant_file),guard=current['guard_sha256'],
            checkpoint=current['checkpoint_sha256'])
    sealed=launch.seal(plan,'1'*64,events,**kw)
    assert sealed['result']['both_fresh_pass'] and sealed['accounting']['actual_attempts']==3
    assert launch.read(Path(plan['operator'])/'seal.json')['historical_accounting']==plan['historical_accounting']
    with pytest.raises(ValueError,match='already_sealed'):
        launch.seal(plan,'1'*64,events,**kw)
    assert launch.replay(plan,'1'*64,events,**kw)['accounting']==sealed['accounting']
    (Path(plan['operator'])/'unexpected.txt').write_text('fixture',encoding='utf-8')
    with pytest.raises(ValueError,match='seal_changed'):
        launch.replay(plan,'1'*64,events,**kw)
    assert len(statuses)==3
