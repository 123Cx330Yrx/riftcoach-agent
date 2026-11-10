"""Offline real worker/SDK fixture and native-import fixture, not live quality."""
from dataclasses import replace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from scripts import document_relation_diagnostic as diagnostic
from scripts import document_relation_request as identity
from scripts.document_sampling_screening import load_private
from scripts.report_relation_contrast import NEW


@pytest.fixture(scope='module')
def prepared():
    return diagnostic.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')


def test_four_new_requests_exact_pair_and_budget(prepared):
    plan, rows = prepared
    assert len(rows) == 4 and plan['budget']['role_calls'] == {'glm-5.3': 4, 'glm-5.3-flash': 0}
    assert plan['budget']['max_tokens'] == 387072 and plan['budget']['max_active_seconds'] == 2400
    assert plan['budget']['estimated_uncached_cny'] == '5.718016'
    assert not plan['execution_authorized'] and not plan['production_admitted']
    for a, b in ((rows[0], rows[1]), (rows[2], rows[3])):
        assert a[1]['report'] == b[1]['report']
        assert a[2].messages[1:] == b[2].messages[1:]
        assert a[2].tools == b[2].tools
        assert identity.projection(a[2]) == identity.projection(b[2])
        assert a[2].timeout_s == b[2].timeout_s == 600
        assert NEW in b[2].messages[0].content and NEW not in a[2].messages[0].content
    assert 'H5' not in json.dumps(plan['sequence'])


@pytest.mark.parametrize('fault', ['material_digest','audit_digest','report'])
def test_calibrated_full_sources_cannot_silently_change(monkeypatch, fault):
    if fault=='material_digest': monkeypatch.setattr(diagnostic,'CALIBRATION_SHA','0'*64)
    elif fault=='audit_digest': monkeypatch.setattr(diagnostic,'CALIBRATION_AUDIT_SHA','0'*64)
    else:
        original=diagnostic.reports
        monkeypatch.setattr(diagnostic,'reports',lambda:[(k,t+'\n\nchanged',v) for k,t,v in original()])
    with pytest.raises(ValueError,match='relation_calibrat'):
        diagnostic.controls()


@pytest.mark.parametrize('fault', ['policy', 'temperature', 'schema', 'timeout', 'marker'])
def test_identity_rejects_control_drift(prepared, fault):
    request = prepared[1][1][2]
    if fault == 'policy': request = replace(request, messages=(replace(request.messages[0], content=request.messages[0].content+'drift'), *request.messages[1:]))
    if fault == 'temperature': request = replace(request, temperature=.2)
    if fault == 'schema': request = replace(request, tools=())
    if fault == 'timeout': request = replace(request, timeout_s=601)
    if fault == 'marker': request = replace(request, metadata={**request.metadata, identity.MARKER: {'version':identity.VERSION,'variant':'other'}})
    with pytest.raises(ValueError): identity.request_bytes(request)


def test_actual_worker_sends_only_teaching_delta_to_sdk(tmp_path, monkeypatch, prepared):
    from tests.test_document_sampling_screening import _FAKE_SDK_CHILD
    child_text = _FAKE_SDK_CHILD.replace('from scripts.document_sampling_screening_request import main',
        'from scripts.document_relation_request import main')
    assert child_text != _FAKE_SDK_CHILD
    bridge = identity.isolated_bridge()
    original = bridge.subprocess.Popen
    def child(command, **kwargs):
        at = command.index('-m')
        assert command[at+1] == 'scripts.document_relation_request'
        return original([*command[:at], '-c', child_text, *command[at+2:]], **kwargs)
    monkeypatch.setattr(bridge.subprocess, 'Popen', child)
    provider = diagnostic.transport.SemanticProvider(NS(model='glm-5.3', api_key='OFFLINE',
        base_url='https://open.bigmodel.cn/api/paas/v4'), bridge=bridge)
    sent=[]
    for cell, _, request in prepared[1][:2]:
        directory = tmp_path/cell['key'].replace(':','-')
        provider.chat(request, directory)
        sdk = json.loads((directory/'stream-001/sdk-fixture.json').read_bytes())
        assert 'metadata' not in sdk
        assert sdk['messages'][0]['content'] == request.messages[0].content
        assert sdk['temperature'] == 1 and sdk['top_p'] == .95 and sdk['max_tokens'] == 32768
        sent.append(sdk)
        with pytest.raises(FileExistsError): provider.chat(request, directory)
    assert sent[0]['messages'][1:] == sent[1]['messages'][1:]
    # SDK timeout is the remaining wall-clock budget after child startup.
    # Both reserve 600 seconds; startup latency must not be mistaken for drift.
    assert all(0 < sdk['timeout'] <= 600 for sdk in sent)
    assert {k:v for k,v in sent[0].items() if k not in ('messages', 'timeout')} == {
        k:v for k,v in sent[1].items() if k not in ('messages', 'timeout')}


def execution(tmp_path, monkeypatch, prepared):
    directory=tmp_path/'run'; directory.mkdir()
    monkeypatch.setattr(diagnostic.workspace, 'answers', tmp_path/'answers')
    monkeypatch.setattr(diagnostic.workspace, 'evidence_roots', (directory,))
    helper=load_private(Path(__file__).with_name('test_document_full_report_diagnostic.py'), 'tests._relation_setup')
    helper.diagnostic=diagnostic
    plan, rows, fixtures=helper.execution(directory,monkeypatch,prepared)
    return directory, plan, rows, fixtures


@pytest.mark.parametrize('fault', [None, 'before_submit', 'transport', 'native'])
def test_four_once_author_workspace_hard_stop_and_strict_replay(tmp_path, monkeypatch, prepared, fault):
    from tests.test_host_review_workspace import author_submit
    directory,plan,rows,fixtures=execution(tmp_path,monkeypatch,prepared)
    provider=fixtures.OfflineProvider(fault)
    host=fixtures.OfflineNativeHost(plan,directory)
    if fault=='native':
        def unavailable(*args): raise ValueError('OFFLINE_native_unavailable')
        host.source.client.request=unavailable
    result=diagnostic.runner.observe(directory,plan,rows,provider,host.source,
        adjudicate=lambda d,k,s: author_submit(diagnostic,d,plan,host,k,
            fault='before_submit' if fault=='before_submit' else None))
    if fault:
        assert not result['scan_completed']
        assert len(provider.calls)==(2 if fault=='transport' else 1)
        if fault=='transport':
            assert result['accounting']['unknown_usage_calls']==1
            assert result['accounting']['receiptless_calls']==1
    else:
        assert result['scan_completed'] and len(provider.calls)==4
        # T9's scripted pass is intentionally NOT semantic success: expectation
        # mismatches remain visible without retrying or skipping an independent arm.
        assert not result['completed'][2]['semantic_accepted']
        before={p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        seal=tmp_path/'OFFLINE-seal.json'
        assert diagnostic.runner.seal(directory,seal,event_source=host.source)['native_reviews']==4
        assert before=={p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        with pytest.raises(FileExistsError): diagnostic.runner.seal(directory,seal,event_source=host.source)


def test_package_create_only_and_tampering(tmp_path):
    package=diagnostic.Package(tmp_path/'package')
    package.write(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')
    assert package.verify()['requests']==4
    with pytest.raises(FileExistsError): package.write(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')
    path=next(package.directory.glob('*/prepared-request.json'))
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='material_changed'): package.verify()


def authorization(plan, now):
    return dict(version=diagnostic.base.AUTH_VERSION, authorized=True,
        user_instruction='OFFLINE authorization fixture',
        plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)),
        budget=deepcopy(plan['budget']), head='f'*40, ci_run='ci',
        issued_at=now.isoformat(), expires_at=(now+timedelta(hours=24)).isoformat())


@pytest.mark.parametrize('field,value', [('version','old'), ('budget',{}),
    ('head','e'*40), ('plan_sha256','0'*64), ('ci_run','other'), ('authorized',False),
    ('expires_at','2000-01-01T00:00:00+00:00')])
def test_authorization_cannot_reuse_other_scope(prepared, field, value):
    plan,_=prepared
    now=datetime.now(timezone.utc)
    auth=authorization(plan,now)
    diagnostic.base.check_authorization(auth,plan,'f'*40,'ci',now=now)
    auth[field]=value
    with pytest.raises(ValueError,match='authorization_invalid_or_expired'):
        diagnostic.base.check_authorization(auth,plan,'f'*40,'ci',now=now)


@pytest.mark.parametrize('fault', ['paths','package','authorization','native','existing_run'])
def test_execution_gates_precede_credentials_and_run_creation(tmp_path, monkeypatch, prepared, fault):
    from app.evaluation.golden_journal import write_new_json
    plan,rows=deepcopy(prepared)
    monkeypatch.setattr(diagnostic.base,'prepare',lambda **kw:(deepcopy(plan),rows))
    package=diagnostic.Package(tmp_path/'package')
    package.write(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')
    auth=authorization(plan,datetime.now(timezone.utc))
    if fault=='paths': monkeypatch.setattr(diagnostic.workspace,'cwd',tmp_path/'absent')
    elif fault=='package':
        (package.directory/rows[0][0]['key'].replace(':','-')/'material.json').write_text('{}')
    elif fault=='authorization': auth['budget']={}
    write_new_json(tmp_path/'authorization.json',auth)
    monkeypatch.setattr(diagnostic.base,'ROOT',tmp_path)
    monkeypatch.setattr(diagnostic.base,'verify_public_ci',lambda ci:'f'*40)
    monkeypatch.setattr(diagnostic.base,'require_unchanged_checkout',lambda head:None)
    class Reader:
        def __init__(self,*args): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
    monkeypatch.setattr(diagnostic.base,'CodexReadOnlyClient',Reader)
    def native(*args): raise ValueError('fixture_native_unavailable')
    monkeypatch.setattr(diagnostic.base,'verify_native_principals',native)
    def secret(*args): raise AssertionError('credentials_must_not_be_read')
    monkeypatch.setattr(diagnostic.base,'load_role_settings',secret)
    directory=tmp_path/'data/runs/model_comparison'/plan['run_id']
    if fault=='existing_run': directory.mkdir(parents=True)
    args=NS(package=package.directory,authorization=tmp_path/'authorization.json',ci_run='ci',
        codex_executable='OFFLINE_NOT_LAUNCHED',env_file='OFFLINE_NOT_READ')
    expected=dict(paths='host_workspace_execution_paths',package='sampling_package_material_changed',
        authorization='semantic_authorization_invalid_or_expired',native='fixture_native_unavailable',
        existing_run='sampling_run_already_exists')
    with pytest.raises(ValueError,match=expected[fault]): diagnostic.run(args)
    assert directory.exists() == (fault=='existing_run')
    assert not directory.exists() or not list(directory.iterdir())


def test_exact_interpreter_startup_and_wrong_existing_cwd(tmp_path, monkeypatch):
    value=diagnostic.execution_paths_preflight()
    assert Path(value['cwd'])==diagnostic.ROOT
    monkeypatch.setattr(diagnostic.workspace,'cwd',tmp_path)
    # Existing directory is insufficient: importing the actual helper must work.
    import subprocess
    with pytest.raises((ValueError,subprocess.CalledProcessError)):
        diagnostic.execution_paths_preflight()


def test_valid_host_rejection_continues_independent_cells(tmp_path, monkeypatch, prepared):
    from tests.test_host_review_workspace import author_submit
    directory,plan,rows,fixtures=execution(tmp_path,monkeypatch,prepared)
    provider=fixtures.OfflineProvider()
    host=fixtures.OfflineNativeHost(plan,directory)
    # Change the synthetic author's judgment BEFORE writing/checking its file
    # and generating the synthetic event; never mock the real import validator.
    original_dump=json.dump
    def dump(value, stream, **kwargs):
        if len(host.turns)==1 and 'review' in value:
            assessment=value['review']['stage_assessment']
            assessment.update(accepted=False,defects=[dict(kind='false_positive',detail='OFFLINE semantic rejection')])
        return original_dump(value,stream,**kwargs)
    monkeypatch.setattr(json,'dump',dump)
    result=diagnostic.runner.observe(directory,plan,rows,provider,host.source,
        adjudicate=lambda d,k,s:author_submit(diagnostic,d,plan,host,k))
    assert result['scan_completed'] and len(provider.calls)==4
    rejected=result['completed'][1]
    assert not rejected['semantic_accepted'] and rejected['host_disagreement']
    assert rejected['primary_accepted'] and not rejected['independent_accepted']
    assert result['completed'][2]['key']==rows[2][0]['key']
    assert diagnostic.runner.seal(directory,tmp_path/'OFFLINE-seal.json',event_source=host.source)['native_reviews']==4
