"""Actual fixed-source worker/session/gate path with synthetic HTTP/native data."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_original15_session as engine, sol_review_contract as contract
from app.evaluation.sol_natural_session import SessionPaused, SessionBlocked, canonical, digest
from scripts import sol_original15_launch as launch
from scripts.reviewer_responses_process import run_once
from scripts.reviewer_profile_batch import inventory
from scripts.prepare_reviewer_profile_screen import visible, json_value
from tests.test_sol_session_review import controls, author


WORKER = r'''
import json,socket,httpx
from pathlib import Path
from scripts import reviewer_responses_process as process, reviewer_responses_nonstream as codec
from tests.test_reviewer_responses_nonstream import response
from tests.test_sol_original15_session import opinion
def deny(*a,**k): raise AssertionError('network forbidden')
socket.socket=socket.create_connection=deny
original=codec.collect
def collect(business,**kwargs):
    context=process.read_json(Path(kwargs['observation_dir']).parent/'validation-context.json')
    value=response(opinion(context,MODE))
    if MODE=='bad_json': value['output'][0]['arguments']='{'
    if MODE=='wrong_model': value['model']='different-model'
    return original(business,**kwargs,transport=httpx.MockTransport(lambda request:httpx.Response(STATUS,
        stream=httpx.ByteStream(json.dumps(value if STATUS==200 else {'error':'timeout'}).encode()),
        headers={'content-type':'application/json'})))
codec.collect=collect
process.worker()
'''


def opinion(context, mode='repair'):
    inputs=contract.restore_context(context)
    value=dict(score=100,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
    if context['stage']=='fresh': return value
    value['repairs']=[]
    if mode=='pass' or (context['duty']=='completion' and mode!='overlap'): return value
    request=contract.make_request(inputs,context['duty'])
    content=next(m.content for m in request.messages if (m.content or '').startswith('[UNTRUSTED DATA]\n'))
    root=json.loads(content.split('\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])['source_roots']['roots'][0][0]
    before=inputs.source.blocks[0][1][-10:]
    value.update(score=70,verdict='needs_revision',issues=[dict(block=1,source_ids=[root],
        severity='medium',category='fact_error',explanation='Synthetic test only.',
        suggested_correction='Synthetic exact change.')],repairs=[dict(issue_ids=[1],edits={
            'block_1':[dict(before=before,after=before+' OFFLINE fixture.',reason='Synthetic test only.') ]})])
    if mode=='overlap' and context['duty']=='completion':
        value['repairs'][0]['edits']['block_1'][0]['after'] = before+' OFFLINE alternative.'
    contract.validate_business(visible(json_value(request)),context)(json.dumps(value))
    return value


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a,**k): raise AssertionError('original15 test cannot connect')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)


@pytest.fixture
def setup(tmp_path):
    opened,turns,_=controls(tmp_path/'native')
    _,template=opened()
    plan=template.plan
    operator=tmp_path/'operator'
    def open_case(key='claim-scope:4', previous=None, **kwargs):
        return engine.open_case(operator,key,plan,template.native.event_source,plan_sha='1'*64,
            authorization_sha='2'*64,python=sys.executable,before=lambda:None,
            guard=previous.guard_sha if previous else None,
            checkpoint=previous.checkpoint_sha if previous else None,**kwargs)
    return open_case,turns,operator


def router(session,attempts,*,mode='repair',status=200):
    def sender(business,**kwargs):
        attempts.append(status)
        return run_once(business,**kwargs,command=[sys.executable,'-c',
            'MODE='+repr(mode)+'\nSTATUS='+str(status)+'\n'+WORKER])
    return launch.router_for(session,'OFFLINE_SENTINEL',sender)


def consume(open_case,turns,*,key='claim-scope:4',previous=None,mode='repair',reject_at=None):
    calls=[];stages=[]
    while True:
        session,gate=open_case(key,previous)
        try:
            with session:
                value=engine.run_case(session,router(session,calls,mode=mode))
                session.close(dict(result=value))
        except SessionPaused:
            importer,g=open_case(key,session)
            with importer:
                handle=list(g.handles())[-1]
                stage=handle['binding']['key'];stages.append(stage)
                material=json.loads((Path(handle['folder'])/'material.json').read_bytes())
                assert 'expected_initial' not in json.dumps(material)
                primary,event=author(handle,turns,g.native.workspace,accepted=stage!=reject_at)
                assert g.submit(stage,primary,event) is (stage!=reject_at)
            previous=importer
            if stage==reject_at: return importer,calls,stages,None
        else:
            return session,calls,stages,value


@pytest.mark.parametrize('key,mode,expected_count', [('claim-scope:1','pass',2),('claim-scope:4','repair',4)])
def test_native_gated_whole_case_has_no_generation_and_replays_readonly(setup,key,mode,expected_count):
    opened,turns,operator=setup
    final,calls,stages,result=consume(opened,turns,key=key,mode=mode)
    assert len(calls)==expected_count and result['matched'] is True
    assert result['accounting']['logical']==dict(generation=0,review=expected_count)
    if expected_count==4:
        assert stages==['facts-initial','completion-initial','compatibility','edit','facts-fresh','completion-fresh']
        contexts=[json.loads(p.read_bytes()) for p in sorted(final.transport_root.glob('review/call-*/validation-context.json'))]
        fresh=[c for c in contexts if c['stage']=='fresh']
        assert fresh[0]['report']==fresh[1]['report']
        assert digest(fresh[0]['report'].encode())==result['actual_report_sha256']
        assert len(list(final.journal_root.glob('application.json')))==1
    else:
        assert stages==['facts-initial','completion-initial']
        assert not (final.journal_root/'application.json').exists()
    before=inventory(operator),inventory(operator.with_name(operator.name+'-authors'))
    replay,g=opened(key,final,read_only=True)
    with replay:
        replayed=engine.run_case(replay,router(replay,[],mode='wrong_model'))
        assert replayed==result and replay.cursor==replay.status()['operations']
        receipts=launch.audit_transport(replay)
        assert receipts['completed_calls']==expected_count and receipts['http_requests_known']==expected_count
        assert receipts['known_tokens']==result['accounting']['tokens']
    assert before==(inventory(operator),inventory(operator.with_name(operator.name+'-authors')))


@pytest.mark.parametrize('failure',['timeout','format'])
def test_current_failure_pauses_not_whole_batch_and_manual_retry_is_same_request(setup,failure):
    opened,turns,operator=setup
    first,g=opened()
    calls=[]
    with pytest.raises(SessionPaused,match='awaiting_manual_retry'),first:
        engine.run_case(first,router(first,calls,status=524 if failure=='timeout' else 200,
            mode='bad_json' if failure=='format' else 'repair'))
    assert not first.status()['closed'] and len(calls)==1
    retained=inventory(first.transport_root)
    second,g=opened(previous=first)
    with pytest.raises(SessionPaused,match='awaiting_manual_retry'),second:
        engine.run_case(second,router(second,calls))
    assert len(calls)==1 and retained==inventory(second.transport_root)
    approved,g=opened(previous=second,manual_retry=True)
    with pytest.raises(SessionPaused,match='awaiting_native_review'),approved:
        engine.run_case(approved,router(approved,calls))
    assert len(calls)==2
    assert all(inventory(approved.transport_root)[p]==pin for p,pin in retained.items())
    requests=sorted(approved.transport_root.glob('review/call-*/request.json'))
    assert requests[0].read_bytes()==requests[1].read_bytes()
    # Native submission and remaining stages continue from the successful retry.
    importer,g=opened(previous=approved)
    with importer:
        primary,event=author(list(g.handles())[-1],turns,g.native.workspace)
        assert g.submit('facts-initial',primary,event)
    final,more,_,value=consume(opened,turns,previous=importer)
    assert len(more)==3 and value['accounting']['calls']==5 and value['matched']
    assert (value['accounting']['reserved_tokens']>0) is (failure=='timeout')
    replay,_=opened(previous=final,read_only=True)
    with replay:
        receipts=launch.audit_transport(replay)
        assert receipts['actual_attempts']==5 and receipts['failed_calls']==1
        assert receipts['http_requests_known']==5 and receipts['http_requests_unknown']==0
        assert receipts['unknown_usage_calls']==int(failure=='timeout')
        assert receipts['unknown_reserved_tokens']==value['accounting']['reserved_tokens']
    assert not (operator/'seal.json').exists()


def test_native_rejection_is_retained_and_never_sends_next_case(setup):
    opened,turns,operator=setup
    final,calls,stages,value=consume(opened,turns,reject_at='facts-initial')
    assert calls==[200] and stages==['facts-initial'] and value is None
    assert json.loads((final.root/'terminal.json').read_bytes())['reason']=='semantic_rejected'
    assert not (operator/'cases/claim-scope-3').exists()


def test_wrong_model_stop_closes_once_and_reproduces_earliest_failure(setup):
    opened,turns,operator=setup
    current,g=opened()
    calls=[]
    with current,pytest.raises(Exception):
        launch.advance_case(current,router(current,calls,mode='wrong_model'))
    assert calls==[200] and current.status()['closed']
    terminal=json.loads((current.root/'terminal.json').read_bytes())
    assert terminal['value']['reason']=='case_execution_failed'
    replay,g=opened(previous=current,read_only=True)
    with replay,pytest.raises(Exception) as caught:
        engine.run_case(replay,router(replay,[]))
    assert type(caught.value).__name__==terminal['value']['error_type']
    replay,_=opened(previous=current,read_only=True)
    with replay:
        receipt=launch.audit_transport(replay)
        assert receipt['failed_calls']==1 and receipt['unknown_usage_calls']==1


def test_plan_grant_and_current_key_rejected_before_credentials_or_execution(tmp_path,monkeypatch):
    monkeypatch.setattr(launch,'current_head',lambda:'3'*40)
    prepared=launch.prepare(tmp_path/'operator','synthetic-root','synthetic-child')
    plan=launch.load(tmp_path/'operator',prepared['plan_sha256'])
    assert len(plan['coverage']['cases'])==15 and plan['limits']['max_requests']==120
    assert plan['coverage']['initial_request_count']==30 and not plan['execution_authorized']
    now=datetime.now(timezone.utc)
    grant=dict(launch.grant_binding(plan,prepared['plan_sha256']),issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat(),user_authorization_evidence='fixture only')
    launch.validate_grant(grant,plan,prepared['plan_sha256'],now=now)
    with pytest.raises(ValueError):
        launch.validate_grant(grant,plan,prepared['plan_sha256'],now=now+timedelta(hours=2))
    grant['limits']={}
    with pytest.raises(ValueError): launch.validate_grant(grant,plan,prepared['plan_sha256'],now=now)
    def deny(*a,**k): pytest.fail('credentials/CI must not be reached')
    monkeypatch.setattr(launch.base,'continuation_credentials',deny)
    monkeypatch.setattr(launch,'verify_ci',deny)
    bad=tmp_path/'wrong-grant.json';bad.write_text('{}')
    with pytest.raises(ValueError):
        launch.execute(plan,prepared['plan_sha256'],None,'claim-scope:1',{},authorization_file=bad,
            authorization_sha='0'*64,ci_run='0',preflight={})
    assert not (tmp_path/'operator/cases').exists()


def test_all_15_sources_are_fixed_and_new_source_scanner_excludes_untracked_script():
    for cell,source in engine.frozen.frozen_cases()[0]:
        restored,inputs=engine.case_for(cell['key'])
        assert restored==cell and inputs.source.report==source.report
        assert digest(inputs.data_json.encode())==cell['input_sha256']
        context=contract.make_request(inputs,'facts').metadata[contract.CONTEXT]
        assert 'expected_initial' not in context and 'control_case' not in context
    assert 'scripts/reviewer_responses_nonstream_probe.py' not in launch.source()


def test_actual_launcher_prompts_only_at_new_io_and_stops_on_wrong_label(tmp_path,monkeypatch):
    # Fixture CI/principals only; every business review still traverses the real
    # native task/author/check-answer/event import and actual owned HTTP worker.
    monkeypatch.setattr(launch,'current_head',lambda:'3'*40)
    monkeypatch.setattr(launch,'verify_ci',lambda run,head:dict(run_id=run,head_sha=head))
    monkeypatch.setattr(launch,'verify_native_principals',lambda *a:None)
    opened,turns,_=controls(tmp_path/'native-live')
    _,g=opened()
    prepared=launch.prepare(tmp_path/'operator','synthetic-root','synthetic-child')
    pin=prepared['plan_sha256'];plan=launch.load(tmp_path/'operator',pin)
    from scripts.codex_review_event_source import CodexHostReviewEventSource
    events=CodexHostReviewEventSource(g.native.event_source.client,plan['review_plan'])
    emitted=[]
    monkeypatch.setattr(launch.base,'emit',lambda v:emitted.append(v))
    launch.native_task(plan,pin,events)
    def proof():
        value=emitted[-1]
        return {k:value[k] for k in ('guard_sha256','checkpoint_sha256')}
    pre=proof()
    s,gate=launch.open_case(plan,pin,events,'claim-scope:1',preflight=True,
        guard=pre['guard_sha256'],checkpoint=pre['checkpoint_sha256'],sink=launch.base.emit)
    with s:
        primary,event=author(list(gate.handles())[-1],turns,gate.native.workspace)
        assert gate.submit('startup-preflight',primary,event)
    pre=proof()
    now=datetime.now(timezone.utc)
    grant=dict(launch.grant_binding(plan,pin),issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat(),user_authorization_evidence='fixture only')
    grant_file=tmp_path/'grant.json';grant_file.write_text(json.dumps(grant),encoding='utf-8')
    auth=digest(grant_file.read_bytes());roots={};prompts=[];attempts=[]
    def credentials(**kwargs): prompts.append(kwargs);return None,'OFFLINE_SENTINEL'
    monkeypatch.setattr(launch.base,'continuation_credentials',credentials)
    original=launch.router_for
    def offline_router(session,key,sender=None):
        if sender is not None: return original(session,key,sender)
        def send(business,**kwargs):
            attempts.append(session.binding['key'])
            return run_once(business,**kwargs,command=[sys.executable,'-c',"MODE='pass'\nSTATUS=200\n"+WORKER])
        return original(session,key,send)
    monkeypatch.setattr(launch,'router_for',offline_router)
    def advance(key,**kwargs):
        result=launch.execute(plan,pin,events,key,roots,authorization_file=grant_file,
            authorization_sha=auth,ci_run='fixture',preflight=pre,**kwargs)
        roots[key]=proof()
        return result
    def submit(key):
        p=roots[key]
        s,gate=launch.open_case(plan,pin,events,key,authorization_sha=auth,
            guard=p['guard_sha256'],checkpoint=p['checkpoint_sha256'],sink=launch.base.emit)
        with s:
            handle=list(gate.handles())[-1]
            primary,event=author(handle,turns,gate.native.workspace)
            # Real native turns are globally unique even when another case
            # uses the same stage name. The single-case helper uses stage IDs.
            turns[0]['id']='case-turn-'+str(len(turns))
            event='synthetic-child/'+turns[0]['id']+'/final'
            assert gate.submit(handle['binding']['key'],primary,event)
        roots[key]=proof()
    for key in ('claim-scope:1','claim-scope:4'):
        assert advance(key)['reason']=='session_awaiting_native_review'
        count=len(prompts)
        assert advance(key)['reason']=='session_awaiting_native_review'
        assert len(prompts)==count
        submit(key)
        assert advance(key)['reason']=='session_awaiting_native_review'
        submit(key)
        closed=advance(key,host_only=True)
        assert closed['phase']=='case_closed'
        assert closed['result']['matched'] is (key=='claim-scope:1')
    assert attempts==['claim-scope:1']*2+['claim-scope:4']*2 and len(prompts)==4
    before=inventory(plan['operator'])
    status=launch.frontier(plan,pin,events,roots,auth)
    assert status['next_key'] is None and not status['all_cases_matched']
    assert status['accounting']['calls']==4
    assert sum(r['transport']['http_requests_known'] for r in status['completed'])==4
    assert before==inventory(plan['operator'])
    with pytest.raises(ValueError,match='current_case_only'):
        advance('claim-scope:3')
    value=launch.seal(plan,pin,events,roots,auth,'4'*64)
    assert value['seal_sha256'] and not value['qualified']
    with pytest.raises(ValueError,match='seal_already_exists'):
        launch.seal(plan,pin,events,roots,auth,'4'*64)


def test_inventory_excludes_only_protocol_locks_and_unresolved_intent_never_resends(setup):
    opened,turns,operator=setup
    current,_=opened()
    with current,pytest.raises(SessionBlocked,match='injected_interrupt'):
        def stop(): raise SessionBlocked('injected_interrupt')
        current.operation('model',{'fixture':'pending'},stop)
    resumed,_=opened(previous=current)
    with resumed,pytest.raises(SessionBlocked,match='unresolved_intent_no_resend'):
        resumed.operation('model',{'fixture':'pending'},lambda:pytest.fail('cannot repeat IO'))
    plan=dict(operator=str(operator),coverage=dict(cases=[dict(key='claim-scope:4')]))
    arbitrary=operator/'unexpected.lock';arbitrary.write_text('evidence',encoding='utf-8')
    with resumed:
        files=launch.evidence_inventory(plan)
        assert 'unexpected.lock' in files and 'cases/claim-scope-4/session.lock' not in files
