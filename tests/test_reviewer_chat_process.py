"""Chat SDK, existing owned subprocess and durable receipts; sockets blocked."""
import json
import sys

import httpx
import pytest

from app.evaluation.golden_native_issues_review import build_inputs
from app.product import sol_contract as product
from app.product.review_purpose import bind_inputs
from scripts import reviewer_chat_stream as chat
from scripts import reviewer_responses_process as process
from scripts.prepare_reviewer_profile_screen import visible, json_value
from tests.test_natural_duty_candidate import Responses
from tests.test_reviewer_chat_contract import rows
from tests.test_reviewer_responses_nonstream import offline, PRIVATE, KEY


def request(duty='facts', stage='initial'):
    inputs = bind_inputs(build_inputs(Responses().req), 'observed')
    req = product.make_request(inputs, duty, stage)
    return visible(json_value(req)), req.metadata[product.CONTEXT]


CHILD = r'''
import json,socket,time
from pathlib import Path
import httpx
from scripts import reviewer_chat_stream as chat, reviewer_responses_process as process
from tests.test_reviewer_chat_contract import rows, chunk
from tests.test_reviewer_responses_nonstream import REVIEW, PRIVATE
def deny(*a,**k):raise AssertionError('network forbidden')
socket.socket = socket.create_connection = deny
original = chat.collect
def collect(business, **kwargs):
    folder = Path(kwargs['observation_dir']).parent
    context = process.read_json(folder/'validation-context.json')
    value = dict(REVIEW)
    if context['stage'] == 'fresh':value.pop('repairs')
    if MODE == 'business_invalid':value['verdict'] = 'needs_revision'
    events = rows(json.dumps(value))
    if MODE in ('conflict', 'conflict_hang'):
        events.append(chunk(usage=dict(prompt_tokens=13,completion_tokens=8,total_tokens=21)))
    if MODE == 'missing_usage':events.pop()
    class Bytes(httpx.SyncByteStream):
        def __iter__(self):
            if MODE == 'unknown_hang':
                process.write_json(folder/'blocked.json', True)
                time.sleep(60)
            for event in events:yield ('data: '+json.dumps(event)+'\n\n').encode()
            if MODE in ('known_hang', 'conflict_hang'):
                process.write_json(folder/'blocked.json', True)
                time.sleep(60)
            if MODE == 'read_error':raise httpx.ReadError(PRIVATE)
            yield b'data: [DONE]\n\n'
            if MODE == 'bad_tail':yield b'data: {"unexpected":true}\n\n'
        def close(self):
            if MODE == 'close_error':raise RuntimeError(PRIVATE)
            if MODE == 'close_hang':
                if not (folder/'blocked.json').exists():process.write_json(folder/'blocked.json', True)
                time.sleep(60)
    def handler(req):
        assert req.url.path == '/v1/chat/completions'
        assert json.loads(req.content) == chat.build_wire(business)
        return httpx.Response(524, content=b'{}') if MODE == '524' else httpx.Response(
            200, headers={'content-type':'text/event-stream'}, stream=Bytes())
    return original(business, **kwargs, transport=httpx.MockTransport(handler))
chat.collect = collect
process.worker()
'''


def run(tmp_path, mode='pass', *, duty='facts', stage='initial', cancel=lambda:False, timeout=30):
    business, context = request(duty, stage)
    # A short synthetic key equal to a valid schema value exercises sanitizing
    # accepted tool arguments, without adding an out-of-schema field first.
    return process.run_once(business, profile=product.REVIEW_PROFILE,
        api_key='pass' if mode == 'credential_echo' else KEY,
        directory=tmp_path/'call', response_mode=chat.MODE, validation_context=context,
        command=[sys.executable, '-c', 'MODE='+repr(mode)+'\n'+CHILD],
        cancel=cancel, timeout_s=timeout)


@pytest.mark.parametrize('duty', ['facts','completion'])
@pytest.mark.parametrize('stage', ['initial','fresh'])
def test_owned_chat_call_validates_product_business_and_preserves_exact_wire(tmp_path, duty, stage):
    receipt = run(tmp_path, duty=duty, stage=stage)
    assert receipt['ok'], receipt
    assert receipt['reaped'] and receipt['worker_exit'] == 0 and receipt['http_requests'] == 1
    assert receipt['usage_state'] == 'known' and receipt['usage']['total_tokens'] == 20
    folder = tmp_path/'call'
    business, context = request(duty, stage)
    assert process.read_json(folder/'request.json') == business
    assert receipt['wire_sha256'] == chat.transport_contract.digest(chat.build_wire(business))
    assert receipt['validation_context_sha256'] == chat.transport_contract.digest(context)
    profile = process.read_json(folder/'profile.json')
    assert profile['api'] == 'chat.completions' and profile['max_output_tokens'] == 16384
    worker = process.read_json(folder/'worker-result.json')
    assert worker['business_validated'] and not worker['semantic_approval']
    assert not worker['publication_allowed']
    serialized = ''.join(p.read_text(encoding='utf-8') for p in folder.rglob('*.json'))
    assert KEY not in serialized and PRIVATE not in serialized
    before = {str(p):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):run(tmp_path, duty=duty, stage=stage)
    assert before == {str(p):p.read_bytes() for p in folder.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mode,code,usage', [
    ('business_invalid','business_contract_invalid','known'),
    ('credential_echo','credential_echo','known'),
    ('conflict','usage_conflict','unknown'), ('missing_usage','usage_unavailable','unknown'),
    ('read_error','request_failed','known'), ('bad_tail','request_failed','known'),
    ('close_error','close_failed','known'), ('524','http_status_524','unknown'),
])
def test_failures_are_receipted_once_without_becoming_accepted_reviews(tmp_path, mode, code, usage):
    receipt = run(tmp_path, mode)
    assert not receipt['ok'] and receipt['code'] == 'worker_rejected', receipt
    assert receipt['worker_code'] == code, receipt
    assert receipt['http_requests'] == 1 and receipt['reaped']
    assert receipt['usage_state'] == usage
    if mode not in ('524','missing_usage'):assert receipt['usage']['total_tokens'] == 20
    assert receipt['usage_conflict'] is (mode == 'conflict')
    worker = process.read_json(tmp_path/'call/worker-result.json')
    assert not worker['business_validated'] and not worker['semantic_approval']
    if mode != 'business_invalid':assert worker['public_tool_call'] is None
    assert KEY not in json.dumps(worker) and PRIVATE not in json.dumps(worker)


@pytest.mark.parametrize('mode,usage', [('known_hang','known'),('unknown_hang','unknown'),
                                      ('close_hang','known'),('conflict_hang','unknown')])
def test_cancel_reaps_real_child_and_preserves_usage_including_conflict(tmp_path, mode, usage):
    receipt = run(tmp_path, mode, cancel=lambda:(tmp_path/'call/blocked.json').exists())
    assert receipt['code'] == 'cancelled' and receipt['reaped'], receipt
    assert receipt['usage_state'] == usage
    # Immediate cancellation may precede the observer's next durable sample.
    # Such a started process is unknown, never falsely reported as not sent.
    assert receipt['http_requests'] in (None, 1) and receipt['usage_state'] != 'not_sent'
    assert receipt['usage_conflict'] is (mode == 'conflict_hang')
    assert receipt['usage'] is None if mode == 'unknown_hang' else receipt['usage']['total_tokens'] == 20
    assert not (tmp_path/'call/worker-result.json').exists()


def test_deadline_covers_stream_after_reported_usage(tmp_path):
    receipt = run(tmp_path, 'known_hang', timeout=10)
    assert receipt['code'] == 'deadline_exceeded' and receipt['reaped'], receipt
    assert receipt['usage_state'] == 'known' and receipt['usage']['total_tokens'] == 20
    assert receipt['elapsed_s'] < 16 and not receipt['ok']


def test_cancel_before_start_is_not_sent(tmp_path):
    receipt = run(tmp_path, cancel=lambda:True)
    assert receipt['code'] == 'cancelled' and receipt['reaped']
    assert receipt['http_requests'] == 0 and receipt['usage_state'] == 'not_sent'


@pytest.mark.parametrize('mutation', ['business','context','profile'])
def test_preflight_refuses_drift_before_process_or_directory_creation(tmp_path, mutation):
    business, context = request()
    profile = product.REVIEW_PROFILE
    if mutation == 'business':business['messages'][0]['content'] += ' drift'
    if mutation == 'context':context = dict(context, version='foreign')
    if mutation == 'profile':profile = chat.transport_contract.Profile(group='GPT-pro',route='proxy-12000')
    with pytest.raises(ValueError):
        process.run_once(business, profile=profile, api_key=KEY, directory=tmp_path/'call',
            response_mode=chat.MODE, validation_context=context)
    assert not (tmp_path/'call').exists()


def test_usage_checkpoint_write_failure_rejects_but_retains_observed_usage(tmp_path):
    business, _ = request()
    class Bytes(httpx.SyncByteStream):
        def __iter__(self):
            for row in rows():yield ('data: '+json.dumps(row)+'\n\n').encode()
            yield b'data: [DONE]\n\n'
    def fail(value):raise OSError(PRIVATE)
    result = chat.collect(business, profile=product.REVIEW_PROFILE, api_key=KEY,
        observation_dir=tmp_path/'observation', on_usage=fail,
        transport=httpx.MockTransport(lambda _:httpx.Response(200,
            headers={'content-type':'text/event-stream'},stream=Bytes())))
    assert result['code'] == 'usage_write_failed' and not result['ok']
    assert result['usage']['total_tokens'] == 20 and result['public_tool_call'] is None
    assert PRIVATE not in json.dumps(result)
