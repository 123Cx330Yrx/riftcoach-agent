"""Real child + SDK + HTTP on loopback only; no paid or semantic evidence."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace as NS

import pytest

from scripts import review_duty_transport as subject
from scripts import review_duty_composition as duty
from scripts.review_duty_execution import request_bytes
from tests.test_coarse_revision_editor import cases

CHILD = r'''
import sys
def guard(event,args):
    if event=='socket.connect' and args[1][0]!='127.0.0.1':
        raise RuntimeError('non_loopback_forbidden')
sys.addaudithook(guard)
import openai
port=int(sys.argv.pop())
original=openai.OpenAI
def local(**kwargs):
    kwargs.update(api_key='OFFLINE',base_url=f'http://127.0.0.1:{port}/v1')
    return original(**kwargs)
openai.OpenAI=local
from scripts.review_duty_transport import main
main()
'''


@pytest.fixture(scope='module')
def requests():
    _,inputs,_,raw = cases()['claim-scope:4']
    opinions = [duty.bind(inputs,'facts','initial',raw),duty.bind(inputs,'completion','initial',
        json.dumps(dict(score=95,verdict='pass',issues=[],advisories=[],issue_resolutions=[])))]
    return dict(facts=duty.review_request(inputs,'facts'),completion=duty.review_request(inputs,'completion'),
        edit=duty.edit_request(inputs,opinions,conflict_status='clear'))


@pytest.mark.parametrize('role',['facts','completion','edit'])
@pytest.mark.parametrize('complete',[True,False])
def test_actual_child_sdk_loopback(tmp_path,monkeypatch,requests,role,complete):
    captured=[]
    model='glm-5.3-flash' if role=='edit' else 'glm-5.3'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
            chunk=dict(id='offline',object='chat.completion.chunk',created=0,model=model,
                choices=[dict(index=0,delta=dict(reasoning_content='PRIVATE_FIXTURE_DO_NOT_PERSIST'),finish_reason=None)])
            def send():
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode());self.wfile.flush()
            send()
            if complete:
                chunk['choices']=[dict(index=0,delta=dict(content='OFFLINE'),finish_reason='stop')];send()
                chunk['choices']=[];chunk['usage']=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2);send()
                self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    folder=tmp_path/role;folder.mkdir()
    prepared=requests[role]
    request=replace(prepared,timeout_s=20)
    (folder/'prepared-request.json').write_bytes(request_bytes(prepared))
    (folder/'issued-request.json').write_bytes(request_bytes(request))
    original=subject.legacy.subprocess.Popen
    def start(command,**kwargs):
        at=command.index('-m')
        assert command[at+1]=='scripts.review_duty_transport'
        assert not any(k.lower() in ('http_proxy','https_proxy','all_proxy') for k in kwargs['env'])
        return original([*command[:at],'-c',CHILD,*command[at+2:],str(server.server_port)],**kwargs)
    monkeypatch.setattr(subject.legacy.subprocess,'Popen',start)
    monkeypatch.setenv('HTTP_PROXY','http://invalid.invalid:1')
    sender=subject.Sender(settings_for_model=lambda name:NS(model=name,api_key='OFFLINE',
        base_url='https://open.bigmodel.cn/api/paas/v4'),observation_root=tmp_path/'observations')
    try:
        if complete:
            exchange=sender(request,folder)
            assert exchange.response.content=='OFFLINE'
            assert exchange.receipt_request_sha256==subject.sha(folder/'issued-request.json')
        else:
            from app.providers.errors import ProviderError
            with pytest.raises(ProviderError):sender(request,folder)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    assert len(captured)==1 and captured[0]['model']==model
    assert captured[0]['messages'][0]['content']==prepared.messages[0].content
    assert captured[0]['reasoning_effort']=='high'
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    files=subject.verify(folder,tmp_path/'observations',complete_required=complete)
    assert len(files)==4
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert all(b'PRIVATE_FIXTURE_DO_NOT_PERSIST' not in v for v in before.values())
    with pytest.raises(ValueError,match='no_restart'):sender(request,folder)
    side=next((tmp_path/'observations').iterdir())
    (side/'sampling/observation.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='evidence_changed'):
        subject.verify(folder,tmp_path/'observations',complete_required=complete)


def test_request_pin_and_legacy_isolation(tmp_path,requests):
    path=tmp_path/'prepared-request.json';path.write_bytes(request_bytes(requests['facts']))
    original=subject.legacy.validate_request
    bridge=subject.isolated_bridge(path,subject.sha(path))
    for bad in (replace(requests['facts'],temperature=.2),requests['completion'],requests['edit']):
        with pytest.raises(ValueError):bridge.validate_request(bad,transport_id=subject.REVIEW)
    assert subject.legacy.validate_request is original
    assert subject.REVIEW not in subject.legacy.TRANSPORTS
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='prepared_binding'):
        bridge.validate_request(requests['facts'],transport_id=subject.REVIEW)


def test_five_stage_chain_uses_real_worker_and_replays(tmp_path,monkeypatch):
    from tests.test_review_duty_execution import setup, PASS
    from tests.test_coarse_revision_editor import BEFORE, AFTER
    from scripts.review_duty_replay import replay
    import time
    _,inputs,_,raw=cases()['claim-scope:4']
    facts=json.loads(raw)
    session,_,_,_=setup(tmp_path,(inputs,facts),fault='SCRIPTED_NATIVE_WITH_REAL_LOOPBACK')
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            index=len(captured);captured.append(request)
            args=(facts if index==0 else dict(edits={'block_4':[dict(before=BEFORE,after=AFTER,
                reason='SCRIPTED edit witness')]}) if index==2 else PASS)
            name='submit_block_edits' if index==2 else 'submit_report_review'
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            chunk=dict(id='offline-chain',object='chat.completion.chunk',created=0,model=request['model'],
                choices=[dict(index=0,delta=dict(tool_calls=[dict(index=0,id='SCRIPTED',type='function',
                    function=dict(name=name,arguments=json.dumps(args,ensure_ascii=False)))]),finish_reason='tool_calls')])
            def send():
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode());self.wfile.flush()
            send();chunk['choices']=[];chunk['usage']=dict(prompt_tokens=20,completion_tokens=10,total_tokens=30);send()
            self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    original=subject.legacy.subprocess.Popen
    def start(command,**kwargs):
        at=command.index('-m')
        assert command[at+1]=='scripts.review_duty_transport'
        return original([*command[:at],'-c',CHILD,*command[at+2:],str(server.server_port)],**kwargs)
    monkeypatch.setattr(subject.legacy.subprocess,'Popen',start)
    session.send=subject.Sender(settings_for_model=lambda name:NS(model=name,api_key='OFFLINE',
        base_url='https://open.bigmodel.cn/api/paas/v4'),observation_root=session.observations)
    session.observe=subject.verify
    session.wall_clock=time.monotonic
    try:
        result=session.run()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    assert result['outcome']=='development_chain_pass',repr(session.failure)
    assert len(captured)==5 and result['known_tokens']==150
    assert captured[2]['model']=='glm-5.3-flash'
    assert AFTER in captured[3]['messages'][1]['content']
    before=session.snapshot()
    record=replay(session.directory,closure_sha256=session.closure_sha256,inputs=inputs,
        event_source=session.gate.event_source,observe=subject.verify)
    assert record['http_requests']==5 and record['reviewed_stages']==6
    assert record['receiptless_attempts']==0 and record['production_admitted'] is False
    assert session.snapshot()==before
