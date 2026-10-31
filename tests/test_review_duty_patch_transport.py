"""Real worker/SDK/loopback HTTP with synthetic grants and native judgments only."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
from types import SimpleNamespace as NS

import pytest

from scripts import review_duty_patch_transport as candidate
from scripts import review_duty_patch_execution as execution
from scripts import review_duty_composition as duty
from scripts import review_duty_transport as old
from tests.test_review_duty_patch_launch import prepared, launch, install_chain, kwargs
from tests.test_review_duty_direct_patch import repaired
from tests.test_review_duty_execution import PASS

subject = candidate._transport
CONNECT = socket.socket.connect
CHILD = r'''
import sys,json
from pathlib import Path
def network_guard(event,args):
    if event=='socket.connect' and args[1][0]!='127.0.0.1':
        raise RuntimeError('non_loopback_forbidden')
sys.addaudithook(network_guard)
config=json.loads(Path(sys.argv.pop()).read_bytes())
port=int(sys.argv.pop())
from scripts.review_duty_patch_launch import _launch as launch
launch.RUN=Path(config['run']); launch.PACKAGE=Path(config['package'])
launch.PRIMARY='synthetic-root'; launch.INDEPENDENT='synthetic-child'
launch.source_inventory=lambda:{p:launch.sha(launch.ROOT/p) for p in config['source']}
launch.require_unchanged_checkout=lambda head:None  # Synthetic HEAD; real guard/pins still execute.
import openai
original=openai.OpenAI
def local(**kwargs):
    kwargs.update(api_key='OFFLINE',base_url=f'http://127.0.0.1:{port}/v1')
    return original(**kwargs)
openai.OpenAI=local
from scripts.review_duty_patch_transport import main
main()
'''


@pytest.mark.parametrize('broken_at', [None, 0, 3])
def test_full_launch_real_guard_child_sdk_http_and_outer_seal(prepared, monkeypatch, broken_at):
    p = prepared
    session, _, gates, _ = install_chain(p, monkeypatch, real_transport=True)
    captured = []
    def local_connect(sock, address):
        if address[0] != '127.0.0.1':
            raise AssertionError('non_loopback_forbidden')
        return CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', local_connect)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            index = len(captured)
            captured.append(request)
            args = repaired(p['facts']) if index == 0 else dict(PASS, repairs=[]) if index == 1 else PASS
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            chunk = dict(id='offline-chain', object='chat.completion.chunk', created=0, model='glm-5.3',
                choices=[dict(index=0, delta=dict(reasoning_content='PRIVATE_FIXTURE_DO_NOT_PERSIST'), finish_reason=None)])
            def send():
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                self.wfile.flush()
            send()
            if index == broken_at:
                return
            chunk['choices'] = [dict(index=0, delta=dict(tool_calls=[dict(index=0, id='SCRIPTED', type='function',
                function=dict(name='submit_report_review', arguments=json.dumps(args, ensure_ascii=False)))]), finish_reason='tool_calls')]
            send()
            chunk['choices'] = []
            chunk['usage'] = dict(prompt_tokens=20, completion_tokens=10, total_tokens=30)
            send()
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = p['operator']/'SCRIPTED-child-config.json'
    config.write_text(json.dumps(dict(run=str(launch.RUN), package=str(launch.PACKAGE),
        source=p['saved']['source_sha256'])), encoding='utf-8')
    original = subject.legacy.subprocess.Popen
    def start(command, **options):
        at = command.index('-m')
        assert command[at+1] == 'scripts.review_duty_patch_transport'
        assert '--execution-guard' in command and '--execution-guard-sha' in command
        assert not any(k.lower() in ('http_proxy', 'https_proxy', 'all_proxy') for k in options['env'])
        return original([*command[:at], '-c', CHILD, *command[at+2:], str(server.server_port), str(config)], **options)
    monkeypatch.setattr(subject.legacy.subprocess, 'Popen', start)
    monkeypatch.setenv('HTTP_PROXY', 'http://invalid.invalid:1')
    settings = NS(model='glm-5.3', api_key='OFFLINE', base_url='https://open.bigmodel.cn/api/paas/v4')
    monkeypatch.setattr(launch, 'load_role_settings', lambda p: (object(), settings))
    try:
        result = launch.execute(**kwargs(p))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    count = 4 if broken_at is None else broken_at+1
    assert result['outcome'] == ('development_chain_pass' if broken_at is None else 'hard_failure'), repr(session.failure)
    assert len(captured) == result['calls'] == count
    assert all(r['model'] == 'glm-5.3' and r['reasoning_effort'] == 'high' for r in captured)
    assert 'repairs' in captured[0]['tools'][0]['function']['parameters']['properties']
    assert result['known_tokens'] == (4 if broken_at is None else broken_at)*30
    if broken_at is None:
        assert len(gates) == 6
        applied = launch.read(launch.RUN/'application.json')['report']
        for name in ('facts', 'completion'):
            assert launch.read(launch.RUN/('host-'+name+'-fresh')/'material.json')['report'] == applied
    else:
        assert result['unknown_reserved_tokens'] > 0
    before = session.snapshot()
    record = launch.audit(p['operator'], guard_sha=subject.sha(p['operator']/'worker-guard.json'),
        exit_sha=subject.sha(p['operator']/'execution-exit.json'), codex_executable=launch.CODEX,
        output=p['operator']/'seal.json')
    assert record['http_requests'] == count and record['http_count_available'] is True
    assert session.snapshot() == before
    if broken_at is not None:
        assert record['first_stop_key'] == 'request:'+execution.SLOTS[broken_at]
    assert all(b'PRIVATE_FIXTURE_DO_NOT_PERSIST' not in f.read_bytes()
        for root in (launch.RUN, session.observations) for f in root.rglob('*') if f.is_file())


@pytest.mark.parametrize('boundary', ['parent', 'child'])
def test_guard_failure_precedes_credentials_or_http(prepared, monkeypatch, boundary):
    p = prepared
    folder = p['operator']/'facts'
    folder.mkdir()
    request = execution.direct.review_request(p['inputs'], 'facts')
    issued = replace(request, timeout_s=20)
    (folder/'prepared-request.json').write_bytes(execution.request_bytes(request))
    (folder/'issued-request.json').write_bytes(execution.request_bytes(issued))
    guard = p['operator']/'invalid-guard.json'
    guard.write_text('{}')
    launched, secrets = [], []
    original = subject.legacy.subprocess.Popen
    def start(command, **options):
        launched.append(command)
        at = command.index('-m')
        child = "import sys; sys.addaudithook(lambda e,a: (_ for _ in ()).throw(RuntimeError('NETWORK_FORBIDDEN')) if e=='socket.connect' else None); from scripts.review_duty_patch_transport import main; main()"
        return original([*command[:at], '-c', child, *command[at+2:]], **options)
    monkeypatch.setattr(subject.legacy.subprocess, 'Popen', start)
    if boundary == 'child':
        monkeypatch.setattr(subject, 'check_execution_guard', lambda *a: None)
    def settings(model):
        secrets.append(model)
        return NS(model=model, api_key='OFFLINE', base_url='https://open.bigmodel.cn/api/paas/v4')
    sender = subject.Sender(settings_for_model=settings, observation_root=p['operator']/'observations',
        execution_guard=(guard, '0'*64))
    from app.providers.errors import ProviderError
    with pytest.raises((ValueError, ProviderError)):
        sender(issued, folder)
    assert len(launched) == len(secrets) == (1 if boundary == 'child' else 0)
    assert not list((p['operator']/'observations').rglob('observation.json'))


def test_guard_required_candidate_identity_and_public_modules_unchanged(prepared):
    p = prepared
    with pytest.raises(ValueError, match='guard_required'):
        candidate.check_execution_guard(None, p['preparation'])
    request = execution.direct.review_request(p['inputs'], 'facts')
    path = p['operator']/'prepared-request.json'
    path.write_bytes(execution.request_bytes(request))
    bridge = subject.isolated_bridge(path, subject.sha(path))
    for bad in (replace(request, temperature=.2), duty.review_request(p['inputs'], 'facts')):
        with pytest.raises(ValueError):
            bridge.validate_request(bad, transport_id=subject.REVIEW)
    assert subject.REVIEW not in old.TRANSPORTS
    assert old.Sender is not subject.Sender and old.VERSION == 'review-duty-observed-v1'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='prepared_binding'):
        bridge.validate_request(request, transport_id=subject.REVIEW)
