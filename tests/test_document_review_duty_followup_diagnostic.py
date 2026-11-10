"""Offline full/facts contract and real loopback SDK wiring, not quality proof."""
from copy import deepcopy
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from scripts import document_review_duty_followup_diagnostic as diagnostic
from scripts import document_review_duty_followup_request as identity
from scripts.diagnose_block_review_route import route_environment

@pytest.fixture(scope='module')
def prepared():
    return diagnostic.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')


def test_followup_exact_requests_scope_and_budget(prepared):
    plan,rows=prepared
    assert plan['sequence']==['duty-1-facts:initial','duty-2-full:initial','duty-2-facts:initial','duty-3-full:initial','duty-3-facts:initial']
    assert plan['budget']['max_calls']==5 and plan['budget']['max_tokens']==483840
    assert plan['budget']['max_active_seconds']==3000
    assert plan['budget']['estimated_uncached_cny']=='7.14752'
    old=diagnostic.ROOT/'data/evaluation/fixtures/document_review_duty_20261014'
    for cell,material,request in rows:
        folder=old/cell['key'].replace(':','-')
        assert identity.request_bytes(request)==(folder/'prepared-request.json').read_bytes()
        assert diagnostic.base.options.canonical(material)==(folder/'material.json').read_bytes()
        assert cell['stage']=='initial'
    assert rows[1][0]['source_stage']=='final'
    assert plan['run_id']=='document-review-duty-followup-20261014'
    assert not plan['execution_authorized'] and plan['new_qualification']==0
    assert 'No cross-batch' in plan['pair_policy']


@pytest.mark.parametrize('field',['policy','marker','schema','temperature','scope'])
def test_request_drift_rejected(prepared,field):
    request=prepared[1][0][2]
    if field=='policy':request=replace(request,messages=(replace(request.messages[0],content=request.messages[0].content+'changed'),*request.messages[1:]))
    elif field=='marker':request=replace(request,metadata={**request.metadata,identity.MARKER:{'version':identity.VERSION,'variant':'other'}})
    elif field=='schema':request=replace(request,tools=())
    elif field=='temperature':request=replace(request,temperature=.2)
    else:request=replace(request,metadata={**request.metadata,identity.MARKER:{'version':identity.VERSION,'variant':'full'}})
    with pytest.raises(ValueError):identity.request_bytes(request)


def test_package_create_only_and_authorized_input_pin(tmp_path,monkeypatch):
    package=diagnostic.Package(tmp_path/'package')
    package.write(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')
    assert package.verify()['requests']==5
    with pytest.raises(FileExistsError):package.write(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')
    path=package.directory/'duty-1-facts-initial/prepared-request.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='package_material_changed'):package.verify()
    original=Path.read_bytes
    target=diagnostic.ROOT/diagnostic.PROPOSAL/'01-facts.json'
    monkeypatch.setattr(Path,'read_bytes',lambda p:original(p)+b' ' if p==target else original(p))
    with pytest.raises(ValueError,match='authorized_input_changed'):diagnostic.controls()


def test_old_authorization_and_expiry_rejected(prepared):
    plan,_=prepared; now=datetime.now(timezone.utc)
    auth=dict(version=diagnostic.base.AUTH_VERSION,authorized=True,user_instruction='OFFLINE fixture',
        plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)),budget=plan['budget'],
        head='f'*40,ci_run='fixture',issued_at=now.isoformat(),expires_at=(now+timedelta(hours=24)).isoformat())
    diagnostic.base.check_authorization(auth,plan,'f'*40,'fixture',now=now)
    with pytest.raises(ValueError):diagnostic.base.check_authorization(auth,plan,'f'*40,'fixture',now=now+timedelta(hours=24))
    auth['version']='document-review-duty-authorization-v1'
    with pytest.raises(ValueError):diagnostic.base.check_authorization(auth,plan,'f'*40,'fixture',now=now)


def test_run_rechecks_original_authorization_bytes(tmp_path, monkeypatch):
    from types import SimpleNamespace
    path=tmp_path/'authorization.json';path.write_text('{}',encoding='utf-8')
    monkeypatch.setattr(diagnostic,'execution_paths_preflight',lambda: None)
    def changed(args):
        path.write_text('{"changed":true}',encoding='utf-8')
        diagnostic.base.check_authorization(None,None,None,None)
    monkeypatch.setattr(diagnostic,'_run',changed)
    with pytest.raises(ValueError,match='authorization_file_changed'):
        diagnostic.run(SimpleNamespace(authorization=path))
    assert diagnostic.base.check_authorization is diagnostic._check


CHILD = r'''
import sys,json,traceback
from pathlib import Path
try:
    def guard(event,args):
        if event=='socket.connect' and args[1][0]!='127.0.0.1': raise RuntimeError('non_loopback_forbidden')
    sys.addaudithook(guard)
    import openai
    from scripts import document_review_duty_followup_request as module
    original_bridge=module.isolated_bridge
    def debug_bridge(*a,**kw):
        bridge=original_bridge(*a,**kw)
        call=bridge.worker
        def invoke(*a,**kw):
            try: return call(*a,**kw)
            except BaseException as e:
                p=Path(sys.argv[sys.argv.index('--worker')+1])/'offline-worker-error.json'
                p.write_text(json.dumps(dict(category=type(e).__name__,frames=[dict(file=Path(f.filename).name,
                    line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])))
                raise
        bridge.worker=invoke
        return bridge
    module.isolated_bridge=debug_bridge
    original=openai.OpenAI
    port=int(sys.argv.pop())
    def local(**kwargs):
        kwargs.update(api_key='OFFLINE',base_url=f'http://127.0.0.1:{port}/v1')
        return original(**kwargs)
    openai.OpenAI=local
    module.main()
except BaseException as e:
    p=Path(sys.argv[sys.argv.index('--worker')+1])/'offline-error.json'
    p.write_text(json.dumps(dict(category=type(e).__name__,frames=[dict(file=Path(f.filename).name,
        line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])))
    raise SystemExit(1)
'''


@pytest.mark.parametrize('mode',['complete','silent','comments','eof'])
def test_real_observed_worker_sdk_and_parent_path(tmp_path,monkeypatch,prepared,mode):
    from app.providers.errors import ProviderError
    captured=[]; stop=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args): pass
        def do_POST(self):
            self.close_connection=True
            captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200); self.send_header('Content-Type','text/event-stream')
            self.send_header('Transfer-Encoding','chunked'); self.end_headers()
            def send(raw):
                self.wfile.write(f'{len(raw):x}\r\n'.encode()+raw+b'\r\n'); self.wfile.flush()
            chunk=dict(id='offline',object='chat.completion.chunk',created=0,model='glm-5.3',
                choices=[dict(index=0,delta=dict(reasoning_content='x'),finish_reason=None)])
            try:
                for _ in range(65): send(('data: '+json.dumps(chunk)+'\n\n').encode())
                if mode=='complete':
                    chunk['choices']=[dict(index=0,delta=dict(content='offline-answer'),finish_reason='stop')]
                    send(('data: '+json.dumps(chunk)+'\n\n').encode())
                    chunk['choices']=[]; chunk['usage']=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2)
                    send(('data: '+json.dumps(chunk)+'\n\n').encode());send(b'data: [DONE]\n\n')
                if mode in ('complete','eof'):
                    self.wfile.write(b'0\r\n\r\n');self.wfile.flush();return
                while not stop.wait(.1):
                    if mode=='comments': send(b': keepalive\n\n')
            except (ConnectionError,OSError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    bridge=identity.isolated_bridge(observation_root=tmp_path/'observations')
    original=bridge.subprocess.Popen
    def start(command,**kw):
        at=command.index('-m')
        assert command[at+1]=='scripts.document_review_duty_followup_request'
        return original([*command[:at],'-c',CHILD,*command[at+2:],str(server.server_port)],**kw)
    monkeypatch.setattr(bridge.subprocess,'Popen',start)
    from types import SimpleNamespace as NS
    provider=diagnostic.transport.SemanticProvider(NS(model='glm-5.3',api_key='OFFLINE',
        base_url='https://open.bigmodel.cn/api/paas/v4'),bridge=bridge)
    request=replace(prepared[1][1][2],timeout_s=15)
    try:
        with route_environment('direct'):
            if mode=='complete': assert provider.chat(request,tmp_path/'transport').content=='offline-answer'
            else:
                with pytest.raises(ProviderError):provider.chat(request,tmp_path/'transport')
    finally:
        stop.set();server.shutdown();server.server_close();thread.join(timeout=2)
    assert len(captured)==1
    assert captured[0]['messages'][0]['content']==request.messages[0].content
    assert [m['content'] for m in captured[0]['messages'][1:]]==[m.content for m in request.messages[1:]]
    assert captured[0]['temperature']==1 and captured[0]['max_tokens']==32768
    assert 'metadata' not in captured[0] and 'expected_verdict' not in json.dumps(captured)
    directory=next((tmp_path/'observations').iterdir())
    binding=json.loads((directory/'binding.json').read_text())
    assert binding['request_sha256']==hashlib.sha256(identity.request_bytes(request)).hexdigest()
    audit=json.loads((directory/'parent-audit.json').read_text())
    observation=json.loads((directory/'sampling/observation.json').read_text())
    assert audit['observation_valid'] and observation['http_requests']==1
    assert not (tmp_path/'transport/sampling').exists()
    if mode in ('silent','comments'):
        assert json.loads((tmp_path/'transport/stream-001/result.json').read_text())['state']=='deadline'
        gap=observation['observed_ms']-observation['last_bytes_ms']
        assert gap>2000 if mode=='silent' else gap<2000
    if mode=='eof': assert json.loads((tmp_path/'transport/stream-001/failure.json').read_text())['assembly_code']=='missing_terminal'
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    verified=identity.verify_observation(tmp_path/'transport/stream-001',identity.request_bytes(request),
        observation_root=tmp_path/'observations',complete_required=mode=='complete')
    assert verified['state']=='valid'
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    snapshot=directory/'sampling/observation.json'
    snapshot.write_bytes(snapshot.read_bytes()+b' ')
    with pytest.raises(ValueError,match='evidence_changed'):
        identity.verify_observation(tmp_path/'transport/stream-001',identity.request_bytes(request),
            observation_root=tmp_path/'observations')
    with route_environment('direct'):
        with pytest.raises(FileExistsError):provider.chat(request,tmp_path/'transport')


@pytest.mark.parametrize('fault',[None,'missing','tamper','transport'])
def test_observation_binding_through_host_next_send_and_readonly_seal(tmp_path,monkeypatch,prepared,fault):
    from pathlib import Path
    from scripts.document_sampling_screening import load_private
    from tests.test_host_review_workspace import author_submit
    directory=tmp_path/'run';directory.mkdir()
    root=tmp_path/'observations'
    monkeypatch.setattr(identity,'OBSERVATION_ROOT',root)
    plan,rows=deepcopy(prepared);plan['observation_root']=str(root.absolute())
    helper=load_private(Path(__file__).with_name('test_document_full_report_diagnostic.py'),'tests._joint_execution')
    helper.diagnostic=diagnostic
    plan,rows,fixtures=helper.execution(directory,monkeypatch,(plan,rows))
    monkeypatch.setattr(diagnostic.workspace,'answers',tmp_path/'answers')
    monkeypatch.setattr(diagnostic.workspace,'evidence_roots',(directory,))
    class Provider(fixtures.OfflineProvider):
        def chat(self,request,folder):
            response=super().chat(request,folder)
            stream=(folder/'stream-001').resolve()
            dest=root/hashlib.sha256(str(stream).encode()).hexdigest();dest.mkdir(parents=True)
            if fault=='missing':return response
            # Explicit synthetic sidecar for wiring only; real SDK observation
            # is tested separately above. No fake record is production evidence.
            fixtures.runner.write_new_json(dest/'binding.json',dict(version=identity.VERSION,
                transport_id=identity.TRANSPORT,request_sha256=identity.request_sha(request),
                worker_directory=str(stream),route=dict(route='direct',destination_host='open.bigmodel.cn',
                process_proxy_present=False,no_proxy_matches_host=True,system_network_path_proven=False)))
            files={p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
            fixtures.runner.write_new_json(dest/'parent-audit.json',dict(transport_complete=True,
                observation_valid=True,files=files,synthetic_fixture=True))
            if fault=='tamper':(dest/'binding.json').write_bytes((dest/'binding.json').read_bytes()+b' ')
            return response
    provider=Provider('transport' if fault=='transport' else None)
    host=fixtures.OfflineNativeHost(plan,directory)
    result=diagnostic.runner.observe(directory,plan,rows,provider,host.source,
        adjudicate=lambda d,k,s:author_submit(diagnostic,d,plan,host,k))
    if fault:
        assert not result['scan_completed'] and len(provider.calls)==(2 if fault=='transport' else 1)
        if fault=='transport':
            replay=diagnostic.runner.replay(directory,event_source=host.source)
            assert replay['body_free_observations'][-1]['state']=='unavailable'
        return
    assert result['scan_completed'] and len(provider.calls)==5
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    sealed=tmp_path.parent/(tmp_path.name+'-seal.json')
    assert diagnostic.runner.seal(directory,sealed,event_source=host.source)['native_reviews']==5
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert len(json.loads(sealed.read_text())['body_free_observations'])==5
