"""Real launcher/worker/native import paths with mock HTTP and synthetic authors."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

from app.evaluation import original15_patch_recovery as engine, sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import digest
from scripts import original15_patch_recovery_launch as launch, sol_original15_launch as old
from scripts.reviewer_profile_batch import inventory
from tests.test_original15_patch_recovery import make_parent
from tests.test_patch_coordination import selection, no_network
from tests.test_sol_original15_session import setup, WORKER
from scripts.reviewer_responses_process import run_once
from tests.test_sol_session_review import author


@pytest.mark.parametrize('reject,timeout', [(False, False), (True, False), (False, True)])
def test_launcher_preserves_original_grant_and_waits_for_real_io(setup,tmp_path,monkeypatch,reject,timeout):
    extra = dict(head='3'*40, contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        limits=old.ENVELOPE, review_profile=old.profile(), estimated_maximum_uncached_cny='8.7552')
    now = datetime.now(timezone.utc)
    grant = dict(old.grant_binding(extra,'1'*64),issued_at=(now-timedelta(hours=25)).isoformat(),
        expires_at=(now-timedelta(hours=1)).isoformat(),user_authorization_evidence='synthetic historical grant')
    grant_file=tmp_path/'authorization.json';write_new_json(grant_file,grant)
    parent,spec,events,turns,previous,historical,before = make_parent(setup,tmp_path,monkeypatch,extra,
        authorization_sha=digest(grant_file.read_bytes()))
    parent_plan = engine.read(parent/'plan.json')
    continuation = dict(version=launch.AUTH_VERSION,original_authorization_sha256=digest(grant_file.read_bytes()),
        original_plan_sha256='1'*64,original_operator=str(parent),
        original_envelope=old.grant_binding(parent_plan,'1'*64),scope='remaining_original_batch',
        reset_accounting=False,rewrite_original_authorization=False,automatic_retries=False,
        qualified=False,publication_allowed=False,issued_at=(now-timedelta(minutes=30)).isoformat(),
        expires_at=(now+timedelta(hours=23)).isoformat(),user_authorization_evidence='synthetic continuation')
    continuation_file=tmp_path/'continuation.json';write_new_json(continuation_file,continuation)
    _,inputs=engine.original.case_for(spec['proof']['key'])
    proposals=[engine.direct.bind(inputs,d,engine.read(parent/'cases'/engine.original.case_slug(spec['proof']['key'])/'journal'/f'{d}-initial.json')['raw']) for d in ('facts','completion')]
    choice_file=tmp_path/'choice.json'
    write_new_json(choice_file,selection(engine.direct.conflict_inventory(inputs,proposals)))
    monkeypatch.setattr(launch,'current_head',lambda:'4'*40)
    monkeypatch.setattr(launch,'source',lambda:dict(synthetic='pinned'))
    monkeypatch.setattr(launch,'verify_native_principals',lambda *a:None)
    ci=[];reads=[];calls=[]
    def check(run,head): ci.append((run,head));return dict(run_id=run,head_sha=head,conclusion='success')
    monkeypatch.setattr(launch,'verify_ci',check)
    original_router=old.router_for
    def fixture_router(session,key,sender=None):
        if sender is not None: return original_router(session,key,sender)
        def send(business,**kwargs):
            status=524 if timeout and not calls else 200
            calls.append(status)
            return run_once(business,**kwargs,command=[sys.executable,'-c',
                "MODE='repair'\nSTATUS="+str(status)+"\n"+WORKER])
        return original_router(session,key,send)
    monkeypatch.setattr(old,'router_for',fixture_router)
    operator=tmp_path/'launch-operator'
    prepared=launch.prepare(operator,spec['proof_file'],spec['proof_sha256'],choice_file,
        digest(choice_file.read_bytes()),grant_file,digest(grant_file.read_bytes()),
        continuation_file,digest(continuation_file.read_bytes()))
    pin=prepared['plan_sha256'];plan,_=launch.load(operator,pin)
    launch.validate_authorization(plan,now=now)
    with pytest.raises(ValueError,match='unexpired'):
        launch.validate_authorization(plan,now=now+timedelta(days=2))
    roots={};emitted=[];stages=[]
    def key(): reads.append('read');return 'OFFLINE_SENTINEL'
    def advance(**kwargs):
        value=launch.execute(plan,pin,events,**roots,ci_run='fixture',sink=emitted.append,key_reader=key,**kwargs)
        roots.update(guard=emitted[-1]['guard_sha256'],checkpoint=emitted[-1]['checkpoint_sha256'])
        return value
    retry=False
    for _ in range(9):
        value=advance(manual_retry=retry)
        retry=False
        if value['phase']=='closed':
            assert not reject and value['result']['matched']
            assert value['result']['cumulative_batch_accounting']['calls']==4+int(timeout)
            break
        if value.get('reason')=='session_timeout_awaiting_manual_retry':
            counts=len(ci),len(reads),len(calls)
            assert advance()['reason']=='patch_launch_awaiting_manual_retry'
            assert counts==(len(ci),len(reads),len(calls))
            retry=True
            continue
        assert value['reason']=='session_awaiting_native_review'
        # Repeating a local/native wait must not query CI or read any key.
        count=len(ci),len(reads),len(calls)
        assert advance(host_only=True)['reason']=='session_awaiting_native_review'
        assert count==(len(ci),len(reads),len(calls))
        session,gate=launch.session_for(plan,pin,events,**roots,sink=emitted.append)
        with session:
            assert gate.native.workspace.answers == operator.with_name(operator.name+'-authors')
            assert not gate.native.workspace.answers.is_relative_to(operator)
            handle=list(gate.handles())[-1];stage=handle['binding']['key'];stages.append(stage)
            primary,event=author(handle,turns,gate.native.workspace,accepted=not reject)
            assert gate.submit(stage,primary,event) is (not reject)
        roots.update(guard=emitted[-1]['guard_sha256'],checkpoint=emitted[-1]['checkpoint_sha256'])
        if reject:
            assert reads==calls==ci==[]
            break
        if stage=='edit':
            boundary=advance(host_only=True)
            assert boundary['reason']=='session_model_boundary' and reads==calls==ci==[]
            # An expired grant stops before CI/Key and does not close good work.
            valid=launch.validate_authorization
            def expire(*args,**kwargs):
                if kwargs.get('active',True): raise ValueError('expired_fixture')
                return valid(*args,**kwargs)
            with monkeypatch.context() as expired:
                expired.setattr(launch,'validate_authorization',expire)
                assert advance()['phase']=='stopped'
            assert reads==calls==ci==[]
    else:
        pytest.fail('launch did not finish')
    assert reads==['read']*(2+int(timeout)) if not reject else reads==[]
    assert calls==([524] if timeout else [])+[200]*2 if not reject else calls==[]
    snapshot=inventory(operator),inventory(operator.with_name(operator.name+'-authors'))
    replay=launch.replay(plan,pin,events,**roots)
    assert replay['strict_replay'] and replay['transport']['http_requests_known']==(2 if reject else 4+int(timeout))
    assert snapshot==(inventory(operator),inventory(operator.with_name(operator.name+'-authors')))
    assert before==(inventory(parent),inventory(parent.with_name(parent.name+'-authors')))
    assert stages==(['patch-coordination'] if reject else ['patch-coordination','compatibility','edit','facts-fresh','completion-fresh'])
