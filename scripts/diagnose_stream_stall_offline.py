"""Loopback-only reproduction of stalled stream evidence, never a paid retry.

Uses the real relation worker, OpenAI SDK, HTTPX and process deadline. Only the
SDK destination/key/client are replaced. Synthetic SSE bodies stay in memory.
"""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=True, indent=2)


def child(directory, port, started, deadline, observe=False):
    import httpx
    import openai
    from scripts.document_relation_request import isolated_bridge, TRANSPORT

    # Fail before any non-loopback socket connection, even if SDK routing drifts.
    def network_guard(event, args):
        if event == 'socket.connect' and args[1][0] != '127.0.0.1':
            raise RuntimeError('offline_non_loopback_forbidden')
    sys.addaudithook(network_guard)
    main_id = threading.get_ident()

    def snapshot():
        frame = sys._current_frames().get(main_id)
        frames = []
        while frame:
            frames.append(dict(file=Path(frame.f_code.co_filename).name,
                               function=frame.f_code.co_name, line=frame.f_lineno))
            frame = frame.f_back
        write(directory / 'offline-stack.json', dict(frames=frames))
    timer = threading.Timer(max(.1, deadline - time.monotonic() - 1), snapshot)
    timer.daemon = True
    timer.start()
    real_openai = openai.OpenAI
    observer = None
    if observe:
        from scripts.stream_observation import StreamObservation
        observer = StreamObservation(directory / 'body-free-observation')

    def local_client(**kwargs):
        original_hooks = kwargs['http_client'].event_hooks['request']
        kwargs['http_client'].close()
        def record_timeout(request):
            write(directory / 'offline-timeout.json', request.extensions['timeout'])
        return real_openai(api_key='OFFLINE', base_url=f'http://127.0.0.1:{port}/v1',
            max_retries=0, timeout=kwargs['timeout'],
            http_client=httpx.Client(trust_env=False,
                event_hooks={'request': [*original_hooks, record_timeout,
                    *([observer.on_request] if observer else [])],
                    'response': [observer.on_response] if observer else []}))
    openai.OpenAI = local_client
    bridge = isolated_bridge()
    try:
        bridge.worker(directory, started, deadline, TRANSPORT)
    except BaseException as error:
        # Same bounded error fields as the real worker entrypoint.
        write(directory / 'failure.json', dict(
            category='assembly_rejected' if isinstance(error, bridge.StreamAdapterError) else 'worker_failed',
            assembly_code=error.code if isinstance(error, bridge.StreamAdapterError) else None,
            provider_code=error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None))
        raise SystemExit(1) from None
    finally:
        timer.cancel()
        if observer:
            observer.close()
            if observer.failure:
                write(directory / 'observation-failure.json', dict(code=observer.failure))


def audit(output, *, observe=False):
    from scripts import document_relation_diagnostic as diagnostic
    from scripts.document_relation_request import request_bytes
    from app.evaluation import golden_stream_bridge as parent_bridge
    from app.providers.errors import ProviderError
    output = output.resolve()
    if output.is_relative_to(ROOT / 'data/runs'):
        raise ValueError('offline_output_must_not_be_run_evidence')
    output.mkdir(parents=True, exist_ok=False)
    _, rows = diagnostic.prepare(root_thread_id='offline', independent_thread_id='offline-child')
    request = replace(rows[3][2], timeout_s=15)
    results = []
    for mode in ('silent', 'comments', 'eof_without_terminal', 'complete'):
        directory = output / mode
        directory.mkdir()
        stop = threading.Event()
        sent = dict(http_requests=0, events=0, comments=0, bytes=0)

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.close_connection = True
                self.rfile.read(int(self.headers['Content-Length']))
                sent['http_requests'] += 1
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Transfer-Encoding', 'chunked')
                self.end_headers()
                def send(data):
                    self.wfile.write(f'{len(data):x}\r\n'.encode() + data + b'\r\n')
                    self.wfile.flush()
                    sent['bytes'] += len(data)
                try:
                    for _ in range(65):
                        chunk = dict(id='offline', object='chat.completion.chunk', created=0,
                            model='glm-5.3', choices=[dict(index=0,
                            delta=dict(reasoning_content='x'), finish_reason=None)])
                        send(('data: ' + json.dumps(chunk) + '\n\n').encode())
                        sent['events'] += 1
                    if mode == 'complete':
                        chunk['choices'] = [dict(index=0, delta=dict(content='offline-answer'), finish_reason='stop')]
                        send(('data: ' + json.dumps(chunk) + '\n\n').encode())
                        chunk['choices'] = []
                        chunk['usage'] = dict(prompt_tokens=1, completion_tokens=1, total_tokens=2)
                        send(('data: ' + json.dumps(chunk) + '\n\n').encode())
                        send(b'data: [DONE]\n\n')
                    if mode in ('eof_without_terminal', 'complete'):
                        self.wfile.write(b'0\r\n\r\n')
                        self.wfile.flush()
                        return
                    while not stop.wait(.1):
                        if mode == 'comments':
                            send(b': synthetic keepalive\n\n')
                            sent['comments'] += 1
                except (ConnectionError, OSError):
                    pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        environ = dict(os.environ, LLM_PROVIDER='zhipu', LLM_MODEL='glm-5.3',
            LLM_BASE_URL='https://open.bigmodel.cn/api/paas/v4', LLM_API_KEY='OFFLINE')
        try:
            response = parent_bridge.run_child([sys.executable, '-B', '-m', 'scripts.diagnose_stream_stall_offline',
                '--child', str(directory), '--port', str(server.server_port),
                *(['--observe'] if observe else [])],
                request_bytes(request), directory=directory, timeout_s=15,
                environ=environ, transport_id=parent_bridge.TIMED_REVIEW_TRANSPORT_ID)
            assert mode == 'complete' and response.content == 'offline-answer'
            error_type = None
        except ProviderError as error:
            error_type = type(error).__name__
        finally:
            stop.set()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        def read(name):
            path = directory / name
            return json.loads(path.read_text()) if path.exists() else None
        value = dict(mode=mode, synthetic=True, server=sent, error_type=error_type,
            progress=read('progress.json'), result=read('result.json'),
            failure=read('failure.json'), sdk_timeout=read('offline-timeout.json'),
            stack=read('offline-stack.json'), observation=read('body-free-observation/observation.json'))
        assert sent['http_requests'] == 1 and sent['events'] == 65
        if mode in ('silent', 'comments'):
            assert value['result']['state'] == 'deadline'
            assert value['progress']['state'] == 'reading' and value['progress']['events'] == 64
            assert value['failure'] is None
            assert any(f['file'] == 'sync.py' and f['function'] == 'read'
                       for f in value['stack']['frames'])
            if observe:
                obs = value['observation']
                assert obs['phase'] == 'waiting_for_raw_bytes' and obs['raw_chunks'] >= 65
                gap = obs['observed_ms'] - obs['last_bytes_ms']
                assert (gap > 2000) if mode == 'silent' else (gap < 2000)
        elif mode == 'eof_without_terminal':
            assert value['result']['state'] == 'failed' and value['failure'] is not None
            assert value['progress']['events'] == 65
        else:
            assert value['result']['state'] == 'complete' and value['failure'] is None
            assert value['progress']['state'] == 'complete'
        if observe:
            assert value['observation']['http_requests'] == 1
            assert value['observation']['response_status'] == 200
            assert read('observation-failure.json') is None
            assert 'offline-answer' not in json.dumps(value['observation'])
        results.append(value)
    summary = dict(scope='offline loopback only; no provider quality or historical root-cause proof',
        external_http_requests=0, observer_enabled=observe,
        versions={n: version(n) for n in ('openai', 'httpx', 'httpcore', 'h11')},
        cases=results)
    write(output / 'summary.json', summary)
    print(json.dumps(dict(cases=len(results), checks='passed', external_http_requests=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', type=Path)
    parser.add_argument('--port', type=int)
    parser.add_argument('--started', type=float)
    parser.add_argument('--deadline', type=float)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    if args.child:
        child(args.child, args.port, args.started, args.deadline, args.observe)
    elif args.output:
        audit(args.output, observe=args.observe)
    else:
        parser.error('--output is required')
