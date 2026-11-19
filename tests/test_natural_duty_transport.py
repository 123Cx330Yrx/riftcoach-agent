"""Actual serializer, worker, collector and receipts with socket-blocked SDK fixtures."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import sys
import subprocess
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.natural_duty_contract import CONTRACT, VERSION, NaturalDutyProvider, make_request, request_bytes
from app.providers.errors import ProviderError, ProviderResponseError, ProviderTimeoutError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage
from app.providers.zhipu import ZhipuProvider
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.natural_duty_provider_factory import NaturalDutyProviderFactory
from tests.test_coarse_revision_editor import cases
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a, **k):
        raise AssertionError('natural duty transport tests cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    # Only explicit fixture settings are passed into a real child below.
    system = {key: bridge.os.environ[key] for key in ('SystemRoot', 'SYSTEMROOT') if key in bridge.os.environ}
    system.update({key:'http://offline.invalid:9' for key in
        ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')})
    monkeypatch.setattr(bridge.os, 'environ', system)


def factory(tmp_path):
    def settings(model):
        return NS(model=model, api_key='OFFLINE_FIXTURE', base_url='https://open.bigmodel.cn/api/paas/v4')
    return NaturalDutyProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path)


def generation():
    return ChatRequest(messages=(ChatMessage(MessageRole.USER, 'Offline natural generation.'),),
        max_tokens=32768, timeout_s=300, temperature=1.0, top_p=.95,
        metadata={'agent_loop_iteration': 1, 'evaluation_policy_id': VERSION})


def review(name='facts', stage='initial'):
    return make_request(cases()['claim-scope:4'][1], name, stage)


@pytest.mark.parametrize('role', ['generation', 'review'])
def test_candidate_serializer_role_and_time_are_bidirectionally_isolated(role):
    request = generation() if role == 'generation' else review()
    transport = VERSION + ':' + role
    assert bridge.validate_request(request, transport_id=transport) == request_bytes(request)
    assert bridge.transport_limits(transport) == (32768, 300, 65536)
    assert bridge.transport_max_calls(transport) == 6
    profile = bridge.transport_profile(transport)
    assert profile.model == ('glm-5.3-flash' if role == 'generation' else 'glm-5.3')
    policy = bridge.transport_request_policy(transport)
    assert (policy.agent_timeout_s, policy.llm_tool_timeout_s, policy.transport_timeout_s) == (330, 330, 360)
    for old in (bridge.CAPACITY_TRANSPORT_ID, bridge.REVIEW_MODEL_TRANSPORT_ID,
                bridge.TIMED_FLASH_TRANSPORT_ID, bridge.TIMED_REVIEW_TRANSPORT_ID):
        with pytest.raises(ProviderResponseError, match='stream_transport_identity'):
            bridge.validate_request(request, transport_id=old)
    other = VERSION + (':review' if role == 'generation' else ':generation')
    with pytest.raises(ValueError, match='natural_duty_transport_identity'):
        bridge.validate_request(request, transport_id=other)
    for change in (dict(timeout_s=300.001), dict(timeout_s=0), dict(max_tokens=8192),
                   dict(temperature=.5), dict(metadata={})):
        with pytest.raises(ValueError):
            bridge.validate_request(replace(request, **change), transport_id=transport)


def test_factory_is_explicit_exact_and_has_no_startup_io(tmp_path):
    root = tmp_path/'absent'
    build = factory(root)
    assert type(build.descriptor) is NaturalDutyProvider
    router = build('natural')
    assert router is not build.descriptor and not root.exists()
    assert router.generator.transport_id == bridge.NATURAL_FLASH_TRANSPORT_ID
    assert router.reviewer.transport_id == bridge.NATURAL_REVIEW_TRANSPORT_ID
    assert router.generator.sdk_max_retries == router.reviewer.sdk_max_retries == 0
    with pytest.raises(ValueError):
        build('../escape')


def test_actual_child_worker_sdk_and_six_global_receipts(tmp_path, monkeypatch):
    real_child = bridge.run_child
    real_popen = subprocess.Popen
    sent = []
    def child(command, raw, **kwargs):
        assert command[command.index('-m') + 1] == 'app.evaluation.golden_stream_bridge'
        request = bridge.REQUEST.validate_json(raw)
        assert kwargs['environ']['NO_PROXY'] == kwargs['environ']['no_proxy'] == 'open.bigmodel.cn'
        assert all(k not in kwargs['environ'] for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'))
        model = bridge.transport_profile(kwargs['transport_id']).model
        sent.append((request, hashlib.sha256(raw).hexdigest(), kwargs['timeout_s']))
        # Replace only the network client inside the real child process. Parent
        # run_child, worker validation, SDK encoding, collect, close and receipts
        # all execute unchanged.
        code = """import sys,json,openai,socket
from pathlib import Path
from types import SimpleNamespace
from app.evaluation.golden_stream_bridge import worker
from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage,tool_fragment
def deny(*a,**k): raise AssertionError('No network allowed')
socket.socket.connect=deny
socket.create_connection=deny
model=MODEL
events=([chunk(tool_calls=[tool_fragment(index=0,call_id='fixture',name='submit_report_review',arguments=json.dumps(dict(score=95,verdict='pass',issues=[],issue_resolutions=[],advisories=[],repairs=[])))],finish_reason='tool_calls',model=model)] if model=='glm-5.3' else [chunk(content='Synthetic generation only.',finish_reason='stop',model=model)])
events.append(chunk(raw_usage=usage(10,20),model=model))
stream=ClosableStream(events)
client=FakeClient(stream)
def close():
 assert stream.closed
 payload=client.completions.calls[0]
 assert payload['extra_body']['reasoning_effort']=='high' and payload['max_tokens']==32768
 assert 0 < payload['timeout'] <= 300
 assert 'metadata' not in payload and 'natural-duty-direct-patch-time300-v1' not in json.dumps(payload)
client.close=close
def openai_client(**kwargs):
 assert kwargs['max_retries']==0 and 0 < kwargs['timeout'] <= 300
 assert kwargs['api_key']=='OFFLINE_FIXTURE'
 assert kwargs['http_client'].trust_env is False
 for hook in kwargs['http_client'].event_hooks['request']: hook(SimpleNamespace(extensions={}))
 return client
openai.OpenAI=openai_client
worker(Path(DIRECTORY),float(sys.argv[-3]),float(sys.argv[-1]),TRANSPORT)
"""
        for marker, value in (('MODEL',model),('DIRECTORY',str(kwargs['directory'])),('TRANSPORT',kwargs['transport_id'])):
            code = code.replace(marker, repr(value))
        stderr_path = kwargs['directory']/'offline-stderr.txt'
        with stderr_path.open('wb') as stderr:
            def popen(*args, **options):
                return real_popen(*args, **dict(options, stderr=stderr))
            with monkeypatch.context() as patch:
                patch.setattr(bridge.subprocess, 'Popen', popen)
                try:
                    return real_child([sys.executable, '-B', '-c', code], raw, **kwargs)
                except ProviderError as error:
                    stderr.flush()
                    raise AssertionError(stderr_path.read_text(encoding='utf-8',errors='replace')) from error
    monkeypatch.setattr(bridge, 'run_child', child)
    router = factory(tmp_path)('six')
    budget = CoachBudgetedProvider(router, coach_contract=CONTRACT)
    requests = [generation(), generation(), review(), review('completion'),
                review(stage='fresh'), review('completion','fresh')]
    for ordinal, request in enumerate(requests, 1):
        response = budget.chat(request)
        assert router.last_exchange.response is response
        assert router.last_exchange.receipt_request_sha256 == sent[-1][1]
        task = tmp_path/'six'
        claim = json.loads((task/f'call-{ordinal:03d}.json').read_bytes())
        terminal = json.loads((task/f'call-result-{ordinal:03d}.json').read_bytes())
        folder = task/claim['raw_directory']
        reservation = json.loads((folder/f'stream-{ordinal:03d}/reservation.json').read_bytes())
        progress = json.loads((folder/f'stream-{ordinal:03d}/progress.json').read_bytes())
        assert claim['ordinal'] == reservation['ordinal'] == ordinal
        assert claim['model'] == reservation['model'] == response.model
        assert claim['thinking_profile_id'] == reservation['thinking_profile_id']
        assert claim['transport_id'] == reservation['transport_id'] == VERSION+':'+claim['role']
        assert claim['request_sha256'] == reservation['request_sha256'] == sent[-1][1]
        assert terminal['response_sha256'] == hashlib.sha256((folder/f'response-{ordinal:03d}.json').read_bytes()).hexdigest()
        assert progress['schema_version'] == '1.3' and progress['state'] == 'complete'
        assert json.loads((folder/f'stream-{ordinal:03d}/result.json').read_bytes())['state'] == 'complete'
    assert budget.calls == len(sent) == 6 and budget.tokens == 180 and budget.reserved_tokens == 0
    with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
        budget.chat(generation())
    assert len(sent) == 6


def test_collect_uses_remaining_deadline_and_includes_close(tmp_path):
    request = generation()
    transport = bridge.NATURAL_FLASH_TRANSPORT_ID
    now = [250.0]
    stream = ClosableStream([chunk(content='Synthetic',finish_reason='stop'),chunk(raw_usage=usage(10,20))])
    client = FakeClient(stream)
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3-flash',
        profile=bridge.transport_profile(transport))
    def opener(req, hook):
        session = provider.stream_adapter(evaluation_request_policy=bridge.transport_request_policy(transport)).stream_session(req, include_usage_tail=True)
        close = session.close
        def delayed():
            close(); now[0] = 301
        session.close = delayed
        return session
    with pytest.raises(ProviderTimeoutError, match='stream_deadline'):
        bridge.collect(request, opener, directory=tmp_path, started=0, deadline=300,
            clock=lambda:now[0], transport_id=transport)
    assert stream.closed and client.completions.calls[0]['timeout'] == 50
    assert json.loads((tmp_path/'progress.json').read_bytes())['state'] == 'failed'
    with pytest.raises(ValueError, match='stream_worker_deadline'):
        bridge.collect(request, opener, directory=tmp_path, started=0, deadline=301,
            clock=lambda:0, transport_id=transport)


def scripted_child(sent, fault=None):
    def child(command, raw, *, directory, transport_id, **kwargs):
        sent.append(raw)
        if fault == 'unknown':
            write_new_json(directory/'result.json',dict(state='deadline',transport_id=transport_id))
            raise ProviderTimeoutError(provider='zhipu',code='stream_deadline')
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        write_new_json(directory/'progress.json',bridge.CapacityBridgeObservation(
            state='complete',close_state='closed',eof_ms=1,close_ms=1,terminal_ms=1,
            http_requests=1,input_tokens=10,output_tokens=20).model_dump(mode='json'))
        if fault in ('receipt','model_binding'):
            path = directory/('result.json' if fault == 'receipt' else 'reservation.json')
            value = json.loads(path.read_bytes())
            value['transport_id' if fault == 'receipt' else 'model'] = 'wrong'
            path.write_text(json.dumps(value),encoding='utf-8')
        return ChatResponse(provider='zhipu',model='wrong' if fault == 'wrong_model' else bridge.transport_profile(transport_id).model,
            content='Synthetic',finish_reason='stop',usage=TokenUsage(10,20))
    return child


@pytest.mark.parametrize('fault', ['unknown','receipt','model_binding','wrong_model'])
def test_failures_preserve_usage_attribution_and_poison_task(tmp_path, monkeypatch, fault):
    sent = []
    monkeypatch.setattr(bridge,'run_child',scripted_child(sent,fault))
    router = factory(tmp_path)('failure')
    budget = CoachBudgetedProvider(router,coach_contract=CONTRACT)
    with pytest.raises(ProviderError):
        budget.chat(generation())
    assert budget.calls == len(sent) == 1 and budget.stopped and router.last_exchange is None
    if fault in ('receipt','model_binding'):
        assert budget.tokens == 30 and budget.reserved_tokens == 0
    else:
        assert budget.tokens == 0 and budget.reserved_tokens > 0
    with pytest.raises(ProviderResponseError):
        budget.chat(review())
    assert len(sent) == 1


@pytest.mark.parametrize('ordinal', [0,7,True])
def test_invalid_global_ordinal_rejected_before_any_claim(tmp_path, ordinal):
    router = factory(tmp_path)('ordinal')
    with pytest.raises(ProviderResponseError,match='role_transport_ordinal_invalid'):
        router.generator.chat_at_ordinal(generation(),ordinal=ordinal,role='generation')
    assert not (tmp_path/'ordinal').exists()


def test_shared_claim_blocks_duplicate_even_through_other_model(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge,'run_child',scripted_child(sent))
    build = factory(tmp_path)
    first = build('duplicate')
    first.generator.chat_at_ordinal(generation(),ordinal=1,role='generation')
    second = build('duplicate')
    with pytest.raises(FileExistsError):
        second.reviewer.chat_at_ordinal(review(),ordinal=1,role='review')
    assert len(sent) == 1 and second.reviewer.last_exchange is None and second.reviewer._failed
    with pytest.raises(ProviderResponseError,match='stream_bridge_exhausted'):
        second.reviewer.chat_at_ordinal(review(),ordinal=2,role='review')


def test_candidate_has_no_revision_transport(tmp_path):
    router = factory(tmp_path)('revision')
    with pytest.raises(ProviderResponseError,match='role_transport_identity_mismatch'):
        router.generator.chat_at_ordinal(generation(),ordinal=1,role='revision')
    assert not (tmp_path/'revision').exists()


@pytest.mark.parametrize('fault', ['missing','schema','open','eof','http','usage','state','coercion'])
def test_complete_response_without_exact_terminal_observation_is_not_a_receipt(tmp_path, monkeypatch, fault):
    sent = []
    child = scripted_child(sent)
    def corrupt(command, raw, *, directory, **kwargs):
        response = child(command,raw,directory=directory,**kwargs)
        path = directory/'progress.json'
        if fault == 'missing':
            path.unlink()
        else:
            value = json.loads(path.read_bytes())
            key, replacement = {'schema':('schema_version','1.4'), 'open':('close_state','unknown'),
                'eof':('eof_ms',None),'http':('http_requests',2),'usage':('output_tokens',21),
                'state':('state','failed'),'coercion':('http_requests','1')}[fault]
            value[key] = replacement
            path.write_text(json.dumps(value),encoding='utf-8')
        return response
    monkeypatch.setattr(bridge,'run_child',corrupt)
    router = factory(tmp_path)('observation')
    budget = CoachBudgetedProvider(router,coach_contract=CONTRACT)
    with pytest.raises(ProviderResponseError,match='integrated_transport_receipt_invalid'):
        budget.chat(generation())
    assert router.last_exchange is None and budget.stopped
    assert budget.calls == len(sent) == 1 and budget.tokens == 30 and budget.reserved_tokens == 0
    assert not (tmp_path/'observation/call-result-001.json').exists()


def test_parent_timeout_closes_real_child_and_never_retries(tmp_path):
    with pytest.raises(ProviderTimeoutError,match='stream_deadline'):
        bridge.run_child([sys.executable,'-c','import time; time.sleep(10)'],request_bytes(generation()),
            directory=tmp_path,timeout_s=1,transport_id=bridge.NATURAL_FLASH_TRANSPORT_ID)
    terminal = json.loads((tmp_path/'result.json').read_bytes())
    assert terminal['state'] == 'deadline' and terminal['body_free']
    with pytest.raises(ValueError,match='stream_ipc_budget'):
        bridge.run_child([],request_bytes(generation()),directory=tmp_path,
            timeout_s=300.1,transport_id=bridge.NATURAL_FLASH_TRANSPORT_ID)
