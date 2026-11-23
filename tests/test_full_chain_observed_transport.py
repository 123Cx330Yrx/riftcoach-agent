"""Real subprocess/SDK/HTTP over loopback for both roles; no Provider traffic."""
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

from scripts import full_chain_observed_transport as subject
from scripts.diagnose_block_review_route import route_environment
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow
from scripts.run_full15_resumption_candidate import selected_controls
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
from scripts.full_chain_observed_transport import main
main()
'''


@pytest.fixture(scope='module')
def requests():
    _, variants = selected_controls(timing_mode='time600')
    _, _, inputs, initial = next(v for v in variants if v[0]['key']=='claim-scope:4')
    _, wire, _ = Workflow.validate_review(cases()['claim-scope:4'][3],inputs)
    return {'review':initial,'revision':Workflow.edit_request(inputs,wire)}


@pytest.mark.parametrize('role',['review','revision'])
@pytest.mark.parametrize('complete',[True,False])
def test_actual_observed_worker_for_both_roles(tmp_path,monkeypatch,requests,role,complete):
    captured=[]
    model='glm-5.3' if role=='review' else 'glm-5.3-flash'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            chunk=dict(id='offline',object='chat.completion.chunk',created=0,model=model,
                choices=[dict(index=0,delta=dict(reasoning_content='x'),finish_reason=None)])
            def send(): self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode());self.wfile.flush()
            for _ in range(65):send()
            if complete:
                chunk['choices']=[dict(index=0,delta=dict(content='OFFLINE transport fixture'),finish_reason='stop')];send()
                chunk['choices']=[];chunk['usage']=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2);send()
                self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    bridge=subject.isolated_bridge(observation_root=tmp_path/'observations')
    original=bridge.subprocess.Popen
    def start(command,**kwargs):
        at=command.index('-m')
        assert command[at+1]=='scripts.full_chain_observed_transport'
        return original([*command[:at],'-c',CHILD,*command[at+2:],str(server.server_port)],**kwargs)
    monkeypatch.setattr(bridge.subprocess,'Popen',start)
    from types import SimpleNamespace as NS
    transport=bridge.TIMED_REVIEW_TRANSPORT_ID if role=='review' else bridge.TIMED_FLASH_TRANSPORT_ID
    provider=bridge.GoldenProcessStreamProvider(settings=NS(model=model,api_key='OFFLINE',
        base_url='https://open.bigmodel.cn/api/paas/v4'),directory=tmp_path/'transport',transport_id=transport)
    request=replace(requests[role],timeout_s=15)
    from app.providers.errors import ProviderError
    try:
        with route_environment('direct'):
            if complete: assert provider.chat(request).content=='OFFLINE transport fixture'
            else:
                with pytest.raises(ProviderError):provider.chat(request)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    assert len(captured)==1 and captured[0]['model']==model
    assert captured[0]['messages']==[dict(role=m.role.value,content=m.content) for m in request.messages]
    raw=bridge.validate_request(request,transport_id=transport)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    record=subject.verify_observation(tmp_path/'transport/stream-001',raw,transport_id=transport,
        observation_root=tmp_path/'observations',complete_required=complete)
    assert record['state']=='valid'
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    side=next((tmp_path/'observations').iterdir())
    assert json.loads((side/'binding.json').read_text())['request_sha256']==hashlib.sha256(raw).hexdigest()
    snapshot=side/'sampling/observation.json'
    snapshot.write_bytes(snapshot.read_bytes()+b' ')
    with pytest.raises(ValueError,match='evidence_changed'):
        subject.verify_observation(tmp_path/'transport/stream-001',raw,transport_id=transport,
            observation_root=tmp_path/'observations',complete_required=complete)
