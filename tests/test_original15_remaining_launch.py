"""Successor uses the real session/worker/native import, with synthetic IO."""
from pathlib import Path
import sys

import pytest

from app.evaluation import sol_original15_session as engine
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import digest
from scripts import original15_remaining_launch as launch, sol_original15_launch as old
from scripts.reviewer_profile_batch import inventory
from scripts.reviewer_responses_process import run_once
from tests.test_sol_original15_session import setup, offline, WORKER
from tests.test_sol_session_review import author


@pytest.mark.parametrize('failure', [None, 'timeout', 'reject'])
def test_remaining_cases_preserve_success_and_require_manual_recovery(setup,tmp_path,monkeypatch,failure):
    opened,turns,_=setup
    _,template=opened()
    events=template.native.event_source
    operator=tmp_path/'successor';operator.mkdir()
    plan=dict(operator=str(operator),review_plan=template.plan,python=sys.executable,keys=launch.KEYS,
        limits=old.ENVELOPE,head='3'*40,parent_recovery_seal_sha256='4'*64,
        coverage=dict(cases=[dict(key=k) for k in launch.KEYS]),
        historical_accounting=dict(calls=45,tokens=810780,reserved_tokens=195578,retries=3),historical_active_seconds=28000.0)
    monkeypatch.setattr(launch,'load',lambda *a,**k:plan)
    monkeypatch.setattr(launch,'verify_parents',lambda *a:dict(authorization_sha256='2'*64))
    monkeypatch.setattr(launch,'verify_native_principals',lambda *a:None)
    monkeypatch.setattr(launch,'verify_parent_native',lambda *a:None)
    ci=[];keys=[];calls=[]
    def authorization(*a,active=True):
        return dict(expires_at='fixture')
    monkeypatch.setattr(launch,'authorization',authorization)
    def verify(run,head): ci.append(run);return dict(run_id=run,head_sha=head,conclusion='success')
    monkeypatch.setattr(launch,'verify_ci',verify)
    actual_router=old.router_for
    def router(session,key,sender=None):
        if sender is not None:return actual_router(session,key,sender)
        def send(business,**kwargs):
            status=524 if failure=='timeout' and not calls else 200
            calls.append(status)
            mode='pass' if engine.case_for(session.binding['key'])[0]['expected_initial']=='accept' else 'repair'
            return run_once(business,**kwargs,command=[sys.executable,'-c',
                'MODE='+repr(mode)+'\nSTATUS='+str(status)+'\n'+WORKER])
        return actual_router(session,key,send)
    monkeypatch.setattr(old,'router_for',router)
    emitted=[];roots={};stages=[]
    def key():keys.append('read');return 'OFFLINE_SENTINEL'
    def update(k):
        roots[k]=dict(guard_sha256=emitted[-1]['guard_sha256'],checkpoint_sha256=emitted[-1]['checkpoint_sha256'])
    def advance(k,**options):
        value=launch.execute(plan,'1'*64,events,k,roots,ci_run='fixture',sink=emitted.append,key_reader=key,**options)
        update(k)
        return value
    with pytest.raises(ValueError):
        launch.prefix(plan,'1'*64,events,'observed:5',roots)
    totals=[]
    for k in launch.KEYS:
        retry=False
        for _ in range(8):
            value=advance(k,manual_retry=retry);retry=False
            if value['phase']=='case_closed':
                # Synthetic worker exercises the runtime, not the real labels.
                totals.append(value['result']['accounting']['calls'])
                break
            if value.get('reason')=='session_timeout_awaiting_manual_retry':
                count=len(calls),len(keys),len(ci)
                assert advance(k)['reason']=='original15_remaining_awaiting_manual_retry'
                assert count==(len(calls),len(keys),len(ci))
                retry=True;continue
            assert value.get('reason')=='session_awaiting_native_review'
            count=len(calls),len(keys),len(ci)
            assert advance(k,host_only=True)['reason']=='session_awaiting_native_review'
            assert count==(len(calls),len(keys),len(ci))
            session,gate=launch.session_for(plan,'1'*64,events,k,sink=emitted.append,**old.roots_for(roots,k))
            with session:
                h=list(gate.handles())[-1];stage=h['binding']['key'];stages.append(stage)
                primary,event=author(h,turns,gate.native.workspace,accepted=failure!='reject')
                turns[0]['id']=k+'-'+stage
                event='synthetic-child/'+turns[0]['id']+'/final'
                assert gate.submit(stage,primary,event) is (failure!='reject')
            update(k)
            if failure=='reject':
                count=len(calls),len(keys)
                assert advance(k)['phase']=='stopped'
                assert count==(len(calls),len(keys))
                snap=inventory(operator)
                with launch.recovery.native_view(events):
                    assert launch.replay_case(plan,'1'*64,events,k,roots)['result']['reason']=='session_semantic_rejected'
                assert snap==inventory(operator)
                return
        else:pytest.fail('successor did not finish')
        snap=inventory(operator),inventory(operator.with_name(operator.name+'-authors'))
        with launch.recovery.native_view(events):
            replay=launch.replay_case(plan,'1'*64,events,k,roots)
        assert replay['strict_replay'] and replay['transport']['actual_attempts']==totals[-1]
        assert snap==(inventory(operator),inventory(operator.with_name(operator.name+'-authors')))
        assert replay['result']['matched'] is True
    expected=sum(2 if engine.case_for(k)[0]['expected_initial']=='accept' else 4 for k in launch.KEYS)
    assert sum(totals)==expected+int(failure=='timeout')
    assert len(keys)==len(calls)==len(ci)==sum(totals)
    write_new_json(operator/'seal.json',dict(test_only=True))
    with pytest.raises(launch.SessionBlocked,match='sealed_no_run'):
        advance('observed:5')


def test_remaining_parent_root_and_inventory_reject_tampering(tmp_path,monkeypatch):
    """Minimal sealed history: account/proof/root checks all use original bytes."""
    parent=tmp_path/'repaired';parent.mkdir()
    original=tmp_path/'old';original.mkdir()
    session=parent/'execution/session';session.mkdir(parents=True)
    budget=dict(calls=45,tokens=810780,reserved_tokens=195578,retries=3)
    result=dict(key='observed:3',matched=True,cumulative_batch_accounting=budget)
    old=dict(parent_operator=str(original),parent_plan_sha256='a'*64,proof_file='fixture',proof_sha256='b'*64,
        review_plan={},limits=old_limits(),contract={},source={})
    write_new_json(parent/'plan.json',old)
    write_new_json(session/'terminal.json',dict(value=dict(result=result)))
    write_new_json(session/'guard.json',dict(binding=dict(control_binding=dict(plan_sha256=digest((parent/'plan.json').read_bytes())))))
    guard=digest((session/'guard.json').read_bytes())
    write_new_json(session/'checkpoint.json',dict(guard_sha256=guard,inventory={'session':{'terminal.json':digest((session/'terminal.json').read_bytes())}}))
    write_new_json(original/'plan.json',dict(coverage=dict(cases=[dict(key=k,input_sha256='c'*64,report_sha256='d'*64) for k in launch.KEYS])))
    old['parent_plan_sha256']=digest((original/'plan.json').read_bytes())
    # Rebind originals before sealing; no live record is rewritten by this fixture.
    (parent/'plan.json').write_bytes(launch.canonical(old))
    guard_value=dict(binding=dict(control_binding=dict(plan_sha256=digest((parent/'plan.json').read_bytes()))))
    (session/'guard.json').write_bytes(launch.canonical(guard_value));guard=digest((session/'guard.json').read_bytes())
    (session/'checkpoint.json').write_bytes(launch.canonical(dict(guard_sha256=guard,inventory={'session':{'terminal.json':digest((session/'terminal.json').read_bytes())}})))
    write_new_json(parent/'seal.json',dict(plan_sha256=digest((parent/'plan.json').read_bytes()),
        inventory=inventory(parent),result=dict(strict_replay=True,result=result)))
    plan=dict(parent_recovery=str(parent),parent_recovery_plan_sha256=digest((parent/'plan.json').read_bytes()),
        parent_recovery_seal_sha256=digest((parent/'seal.json').read_bytes()),
        parent_recovery_inventory=inventory(parent),parent_recovery_author_inventory={},
        historical_accounting=budget,parent_recovery_roots=dict(guard_sha256=guard,
            checkpoint=str(session/'checkpoint.json'),checkpoint_sha256=digest((session/'checkpoint.json').read_bytes())),
        review_plan={},limits=old_limits(),profile=launch.original.profile(),contract={},parent_runtime_source={},
        inputs={k:dict(input_sha256='c'*64,report_sha256='d'*64) for k in launch.KEYS})
    monkeypatch.setattr(launch.recovery.engine,'binding',lambda *a:None)
    monkeypatch.setattr(engine,'case_for',lambda k:(dict(input_sha256='c'*64,report_sha256='d'*64),None))
    assert launch.verify_parents(plan)==old
    plan['historical_accounting']=dict(budget,calls=0)
    with pytest.raises(ValueError,match='parent_changed'):launch.verify_parents(plan)
    plan['historical_accounting']=budget
    (parent/'unexpected').write_bytes(b'changed')
    with pytest.raises(ValueError,match='parent_changed'):launch.verify_parents(plan)


def old_limits():
    return old.ENVELOPE


def test_batch_replay_retains_first_rejection_and_forbids_skipped_case(tmp_path,monkeypatch):
    plan=dict(operator=str(tmp_path),historical_accounting=dict(calls=45,tokens=810780,reserved_tokens=195578,retries=3))
    (tmp_path/'cases/observed-4').mkdir(parents=True)
    row=dict(strict_replay=True,result=dict(reason='session_semantic_rejected',key='observed:4'),
        accounting=dict(calls=1,tokens=100,reserved_tokens=0,retries=0))
    monkeypatch.setattr(launch,'replay_case',lambda *a:row)
    result=launch.replay_batch(plan,'fixture',None,{'observed:4':{}})
    assert result['terminal_boundary'] and not result['complete']
    assert result['first_stopped_case']=='observed:4' and result['cumulative_accounting']['calls']==46
    (tmp_path/'cases/observed-5').mkdir()
    with pytest.raises(ValueError,match='out_of_order'):
        launch.replay_batch(plan,'fixture',None,{'observed:4':{},'observed:5':{}})
