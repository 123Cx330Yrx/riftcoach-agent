"""Offline launch boundary tests; SCRIPTED native/Provider bodies are not reviews."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

from scripts import review_duty_launch as launch
from scripts.review_duty_host_gate import sha
from app.evaluation.golden_journal import write_new_json
from tests.test_review_duty_execution import setup
from tests.test_coarse_revision_editor import cases


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    def no_network(*a,**kw): raise AssertionError('offline test cannot connect')
    monkeypatch.setattr(socket.socket,'connect',no_network)
    _,inputs,_,raw=cases()['claim-scope:4']
    monkeypatch.setattr(launch,'PACKAGE',tmp_path/'package')
    monkeypatch.setattr(launch,'RUN',tmp_path/'run')
    monkeypatch.setattr(launch,'PRIMARY','synthetic-root')
    monkeypatch.setattr(launch,'INDEPENDENT','synthetic-child')
    monkeypatch.setattr(launch,'load_inputs',lambda:inputs)
    # Freeze a small real source set here; full conservative inventory is tested separately.
    monkeypatch.setattr(launch,'source_inventory',lambda:{'scripts/review_duty_launch.py':sha(Path(launch.__file__))})
    launch.create_package()
    operator=tmp_path/'operator';operator.mkdir()
    saved=launch.proposal(operator,sys.executable)
    path=operator/'preparation.json';write_new_json(path,saved)
    now=datetime.now(timezone.utc)
    grant=dict(kind=launch.AUTH_VERSION,authorized=True,preparation_sha256=sha(path),
        execution_head='a'*40,ci_run='123',issued_at=(now-timedelta(seconds=1)).isoformat(),
        expires_at=(now+timedelta(hours=23)).isoformat())
    auth=operator/'authorization.json';write_new_json(auth,grant)
    return dict(operator=operator,saved=saved,preparation=path,grant=grant,authorization=auth,
        inputs=inputs,facts=json.loads(raw))


def kwargs(p):
    return dict(preparation=p['preparation'],preparation_sha=sha(p['preparation']),
        authorization_path=p['authorization'],authorization_sha=sha(p['authorization']),
        env_file=p['operator']/'NEVER_READ_SECRET',codex_executable=launch.CODEX)


def install_preflights(p,monkeypatch):
    calls=[]
    monkeypatch.setattr(launch,'verify_public_ci',lambda run:calls.append('ci') or 'a'*40)
    monkeypatch.setattr(launch,'startup',lambda saved:calls.append('startup') or {'SCRIPTED':True})
    monkeypatch.setattr(launch,'require_unchanged_checkout',lambda head:calls.append('checkout'))
    @contextmanager
    def client(exe):
        calls.append('native_client')
        yield object()
    monkeypatch.setattr(launch,'CodexReadOnlyClient',client)
    monkeypatch.setattr(launch,'verify_native_principals',lambda c,plan:calls.append('native') or {'SCRIPTED':True})
    monkeypatch.setattr(launch,'require_execution_event_source',lambda *a:None)
    def secret(path):
        calls.append('secret')
        assert (p['operator']/'execution.json').is_file()
        assert (p['operator']/'worker-guard.json').is_file()
        raise RuntimeError('SCRIPTED secret boundary failure')
    monkeypatch.setattr(launch,'load_role_settings',secret)
    return calls


@pytest.mark.parametrize('fault',['missing','expired','binding','ci','startup','native','head','run','answers','observations','claim'])
def test_preflight_failures_precede_secret_and_run(prepared,monkeypatch,fault):
    p=prepared;calls=install_preflights(p,monkeypatch);args=kwargs(p)
    def reject(*a,**kw): raise ValueError('SCRIPTED '+fault)
    if fault=='missing':p['authorization'].unlink()
    elif fault in ('expired','binding'):
        grant=dict(p['grant'])
        if fault=='expired':grant['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat()
        else:grant['preparation_sha256']='0'*64
        p['authorization'].write_text(json.dumps(grant))
        args['authorization_sha']=sha(p['authorization'])
    elif fault in ('ci','startup','native','head'):
        name={'ci':'verify_public_ci','startup':'startup','native':'verify_native_principals','head':'require_unchanged_checkout'}[fault]
        monkeypatch.setattr(launch,name,reject)
    else:
        path=launch.RUN if fault=='run' else p['operator']/{'answers':'author-answers','observations':'observations','claim':'execution.json'}[fault]
        path.mkdir() # Empty evidence also prevents a restart.
    with pytest.raises((ValueError,OSError)):launch.execute(**args)
    assert 'secret' not in calls
    assert not launch.RUN.exists() or fault=='run'


def test_claim_survives_failure_and_blocks_second_secret_access(prepared,monkeypatch):
    p=prepared;calls=install_preflights(p,monkeypatch)
    with pytest.raises(RuntimeError):launch.execute(**kwargs(p))
    assert calls.index('secret')>calls.index('native')>calls.index('startup')>calls.index('ci')
    record=launch.read(p['operator']/'execution-failure.json')
    assert record==dict(error_type='RuntimeError',calls=0,restart_allowed=False)
    before=(p['operator']/'execution.json').read_bytes()
    with pytest.raises(ValueError,match='already_started'):launch.execute(**kwargs(p))
    assert calls.count('secret')==1 and (p['operator']/'execution.json').read_bytes()==before


def test_package_source_and_control_path_pins(prepared,monkeypatch):
    p=prepared
    assert launch.packaged_inputs()==p['inputs']
    launch.validate_preparation(p['preparation'],sha(p['preparation']))
    for name in ('author-answers','observations','host-controls'):
        with pytest.raises(ValueError):launch.control_path(p['operator']/name/'preparation.json',p['saved'])
    monkeypatch.setattr(launch,'source_inventory',lambda:{'changed.py':'0'*64})
    with pytest.raises(ValueError,match='preparation_changed'):
        launch.validate_preparation(p['preparation'],sha(p['preparation']))
    path=launch.PACKAGE/'facts-initial.json';path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='initial_binding'):launch.packaged_inputs()


def test_actual_absolute_python_startup_and_wrong_identity(prepared,monkeypatch):
    monkeypatch.chdir(launch.ROOT)
    proof=launch.startup(prepared['saved'])
    assert Path(proof['python']).resolve()==Path(sys.executable).resolve()
    monkeypatch.chdir(prepared['operator'])
    with pytest.raises(ValueError,match='interpreter_or_cwd'):launch.startup(prepared['saved'])


@pytest.mark.parametrize('fault',[None,'abort','pending_changed','author_changed','wrong_event','late_source','after_submit'])
def test_mailbox_native_import_closed_audit_and_stop(prepared,monkeypatch,fault):
    from scripts import review_duty_replay  # Bind Reader before replacing the constructor.
    p=prepared;install_preflights(p,monkeypatch)
    session,sent,gates,turns=setup(p['operator'],(p['inputs'],p['facts']),fault='SCRIPTED_LAUNCH')
    original_judge=session.judge
    if fault=='after_submit':
        original_submit=session.gate.submit
        def submit(handle,*a):
            accepted=original_submit(handle,*a)
            (p['operator']/'host-controls'/(handle['binding']['key']+'.pending.json')).write_text('{}')
            return accepted
        monkeypatch.setattr(session.gate,'submit',submit)
    original_check=launch.HostMailbox.check_controls
    native_client=session.gate.event_source.client
    @contextmanager
    def client(exe):yield native_client
    monkeypatch.setattr(launch,'CodexReadOnlyClient',client)
    monkeypatch.setattr(launch,'load_role_settings',lambda p:(object(),object()))
    monkeypatch.setattr(launch.transport,'Sender',lambda **kw:session.send)
    monkeypatch.setattr(launch.transport,'verify',session.observe)
    def factory(**kw):
        from scripts.host_review_workspace import HostReviewWorkspace
        session.directory=kw['directory'];session.observations=kw['observations']
        session.workspace=HostReviewWorkspace(cwd=launch.ROOT,python=sys.executable,
            answers=kw['answers'],evidence_roots=(launch.RUN,))
        session.gate.workspace=session.workspace
        session.judge=kw['judge'];session.before=kw['before_send']
        return session
    monkeypatch.setattr(launch.execution,'DevelopmentChain',factory)
    processed=set()
    def check_controls(mailbox,allowed=()):
        original_check(mailbox,allowed)
        for pending in mailbox.root.glob('*.pending.json'):
            if pending in processed:continue
            processed.add(pending)
            handle=launch.read(pending);key=handle['binding']['key']
            guard_sha=sha(p['operator']/'worker-guard.json')
            task=launch.host_command(p['operator'],key,guard_sha=guard_sha,action='task')
            assert task==(Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8')
            assert str(session.workspace.answers) in task and str(launch.ROOT) in task
            if fault=='abort':
                launch.host_command(p['operator'],key,guard_sha=guard_sha,action='abort',checkpoint_sha=handle['checkpoint_sha256'])
                return
            primary,event=original_judge(handle,86400)
            notes=p['operator']/(key+'.primary.json');write_new_json(notes,primary)
            launch.host_command(p['operator'],key,guard_sha=guard_sha,action='submit',
                checkpoint_sha=handle['checkpoint_sha256'],notes=notes,event_id='missing' if fault=='wrong_event' else event)
            if fault=='pending_changed':pending.write_text('{}')
            if fault=='author_changed':
                session.workspace.answer_path(Path(handle['folder'])/'task-checkpoint.json',handle['checkpoint_sha256']).write_text('{}')
            if fault=='late_source':monkeypatch.setattr(launch,'source_inventory',lambda:{})
    monkeypatch.setattr(launch.HostMailbox,'check_controls',check_controls)
    result=launch.execute(**kwargs(p))
    assert result['outcome']==('development_chain_pass' if fault is None else 'hard_failure'),repr(session.failure)
    assert len(sent)==(5 if fault is None else 1)
    closed=p['operator']/'execution-exit.json'
    assert launch.read(closed)['closure_sha256']==getattr(session,'closure_sha256',None)
    if fault is None:
        assert len(gates)==6
        # Replay must validate the original grant at claim time, even after expiry.
        original_auth=launch.authorization
        def expired(*a,**kw):
            if kw.get('now') is None:raise ValueError('expired')
            return original_auth(*a,**kw)
        monkeypatch.setattr(launch,'authorization',expired)
        params=dict(guard_sha=sha(p['operator']/'worker-guard.json'),exit_sha=sha(closed),codex_executable=launch.CODEX)
        record=launch.audit(p['operator'],**params,output=p['operator']/'seal.json')
        assert record['calls']==5 and record['reviewed_stages']==6
        with pytest.raises(FileExistsError):launch.audit(p['operator'],**params,output=p['operator']/'seal.json')
        turns[0]['items'][-1]['text']='{}'
        with pytest.raises(ValueError):launch.audit(p['operator'],**params)


def test_full_source_inventory_includes_dynamic_modules():
    inventory=launch.source_inventory()
    assert all(name in inventory for name in ('scripts/review_duty_launch.py',
        'scripts/full_chain_execution.py','app/providers/config.py','app/evaluation/golden_stream_bridge.py','pyproject.toml'))


def test_competing_launches_claim_before_single_secret_read(prepared,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    calls=install_preflights(prepared,monkeypatch)
    original=launch.unused
    barrier=Barrier(2)
    def unused(saved):
        original(saved)
        barrier.wait(timeout=20)
    monkeypatch.setattr(launch,'unused',unused)
    def attempt():
        try:launch.execute(**kwargs(prepared))
        except Exception as error:return type(error).__name__
        raise AssertionError('must stop at mocked secret boundary')
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda _:attempt(),range(2)))
    assert sorted(outcomes)==['FileExistsError','RuntimeError']
    assert calls.count('secret')==1 and not launch.RUN.exists()


def test_dangling_run_link_refused_before_credentials(prepared):
    try:launch.RUN.symlink_to(launch.RUN.parent/'absent-target',target_is_directory=True)
    except OSError:pytest.skip('directory symlinks unavailable')
    with pytest.raises(ValueError,match='already_started'):launch.unused(prepared['saved'])
