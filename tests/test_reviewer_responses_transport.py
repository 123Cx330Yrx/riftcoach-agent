"""Real OpenAI SDK + HTTPX mock SSE. No network, credentials or model claims."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import sys

import httpx
import pytest

from scripts import reviewer_responses_transport as transport
from scripts.reviewer_responses_process import screen_validator
from scripts.reviewer_responses_process import run_once

PACKAGE = Path(__file__).resolve().parents[1]/'data/evaluation/fixtures/reviewer_profile_screen_20261015'
PRIVATE = 'PRIVATE_REASONING_SENTINEL_DO_NOT_RETAIN'
KEY = 'TEST_CREDENTIAL_DO_NOT_RETAIN'
REVIEW = dict(score=100, verdict='pass', issues=[], issue_resolutions=[], advisories=[], repairs=[])
USAGE = dict(input_tokens=125, output_tokens=70, total_tokens=195,
    input_tokens_details=dict(cached_tokens=20), output_tokens_details=dict(reasoning_tokens=30))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline Responses test attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def business():
    return json.loads((PACKAGE/'requests/r01-facts.json').read_text(encoding='utf-8'))


def events(arguments=None):
    raw = json.dumps(REVIEW) if arguments is None else arguments
    reasoning = dict(id='rs_1', type='reasoning', summary=[dict(type='summary_text', text=PRIVATE)])
    added = dict(id='fc_1', type='function_call', name=transport.TOOL,
        call_id='call_1', arguments='', status='in_progress')
    done = {**added, 'arguments': raw, 'status': 'completed'}
    response = dict(id='resp_1', object='response', created_at=1, model=transport.MODEL,
        status='in_progress', output=[], usage=None, error=None, incomplete_details=None)
    rows = [dict(type='response.created', response=response),
        dict(type='response.in_progress', response=response),
        dict(type='response.output_item.added', output_index=0, item=reasoning),
        dict(type='response.reasoning_summary_text.delta', output_index=0,
            item_id='rs_1', summary_index=0, delta=PRIVATE),
        dict(type='response.output_item.done', output_index=0, item=reasoning),
        dict(type='response.output_item.added', output_index=1, item=added),
        dict(type='response.function_call_arguments.delta', output_index=1,
            item_id='fc_1', delta=raw[:len(raw)//2]),
        dict(type='response.function_call_arguments.delta', output_index=1,
            item_id='fc_1', delta=raw[len(raw)//2:]),
        dict(type='response.function_call_arguments.done', output_index=1,
            item_id='fc_1', name=transport.TOOL, arguments=raw),
        dict(type='response.output_item.done', output_index=1, item=done),
        dict(type='response.completed', response={**response, 'status': 'completed',
            'output': [reasoning, done], 'usage': deepcopy(USAGE)})]
    return [dict(row, sequence_number=i) for i, row in enumerate(rows)]


class Bytes(httpx.SyncByteStream):
    def __init__(self, rows, *, after_error=False, close_error=False, done=True, tail=b''):
        self.rows, self.after_error, self.close_error = rows, after_error, close_error
        self.done, self.closed = done, False
        self.tail = tail

    def __iter__(self):
        for row in self.rows:
            # Splitting each SSE frame exercises the actual SDK byte decoder.
            raw = ('event: ' + row['type'] + '\ndata: ' + json.dumps(row) + '\n\n').encode()
            yield raw[:17]
            yield raw[17:]
        if self.after_error:
            raise httpx.ReadError(PRIVATE)
        if self.done:
            yield b'data: [DONE]\n\n'
        if self.tail:
            yield self.tail

    def close(self):
        self.closed = True
        if self.close_error:
            raise OSError(PRIVATE)


def run(business, tmp_path, rows, **kwargs):
    body = Bytes(rows, **kwargs)
    requests, saved_usage = [], []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=body,
            headers={'content-type': 'text/event-stream', 'x-request-id': 'req-offline'})
    result = transport.collect(business, profile=transport.Profile(group='GPT-pro'), api_key=KEY,
        observation_dir=tmp_path/'observation', on_usage=saved_usage.append,
        transport=httpx.MockTransport(handler))
    return result, requests, saved_usage, body


@pytest.mark.parametrize('case', ['r01-facts', 'r01-completion', 'r02-facts', 'r02-completion'])
def test_actual_sdk_wire_preserves_full_business_and_optional_schema(tmp_path, case):
    business = json.loads((PACKAGE/'requests'/f'{case}.json').read_text(encoding='utf-8'))
    before = deepcopy(business)
    result, requests, saved, body = run(business, tmp_path, events())
    assert result['ok'], result['code']
    assert body.closed and len(requests) == 1
    assert requests[0].url == 'https://yujianwudi.top/v1/responses'
    wire = json.loads(requests[0].content)
    assert wire == transport.build_wire(business)
    assert wire['input'] == business['messages'] and business == before
    assert wire['tools'][0]['parameters'] == business['tools'][0]['input_schema']
    assert wire['tools'][0]['strict'] is False
    assert wire['reasoning'] == {'effort': 'high'}
    assert wire['max_output_tokens'] == 32768 and wire['tool_choice'] == 'auto'
    assert wire['parallel_tool_calls'] is False and wire['store'] is False
    assert not {'temperature', 'top_p', 'max_tokens', 'response_format', 'metadata'} & wire.keys()
    assert result['public_tool_call']['arguments'] == json.dumps(REVIEW)
    assert saved == [result['usage']]
    assert result['usage']['output_tokens'] == 70  # Already includes 30 reasoning tokens.
    assert result['usage']['total_tokens'] == 195
    assert not result['business_validated'] and not result['semantic_approval']
    assert not result['upstream_identity_verified']
    public = json.dumps(result) + ''.join(p.read_text() for p in (tmp_path/'observation').glob('*.json'))
    assert PRIVATE not in public and KEY not in public


@pytest.mark.parametrize('status', ['incomplete', 'failed'])
def test_rejected_terminal_keeps_known_usage(tmp_path, business, status):
    rows = events()
    rows[-1]['type'] = 'response.' + status
    rows[-1]['response'].update(status=status, output=[], incomplete_details={'reason': 'max_output_tokens'})
    result, _, saved, body = run(business, tmp_path, rows)
    assert not result['ok'] and result['code'] == 'response_' + status
    assert result['usage']['total_tokens'] == 195 and saved == [result['usage']]
    assert result['public_tool_call'] is None and body.closed


@pytest.mark.parametrize('usage', [None, {}, {'input_tokens': 1},
    {**USAGE, 'input_tokens': True}, {**USAGE, 'output_tokens': -1},
    {**USAGE, 'total_tokens': 999},
    {**USAGE, 'input_tokens_details': {'cached_tokens': 126}},
    {**USAGE, 'output_tokens_details': {'reasoning_tokens': 71}}])
def test_bad_or_missing_usage_is_not_zero_or_success(tmp_path, business, usage):
    rows = events()
    rows[-1]['response']['usage'] = usage
    result, _, saved, _ = run(business, tmp_path, rows)
    assert not result['ok'] and result['usage'] is None and saved == []


def test_optional_usage_details_stay_unknown(tmp_path, business):
    rows = events()
    rows[-1]['response']['usage'] = dict(input_tokens=125, output_tokens=70, total_tokens=195)
    result, _, _, _ = run(business, tmp_path, rows)
    assert result['ok']
    assert result['usage']['reasoning_tokens'] is None and result['usage']['cached_input_tokens'] is None


def test_real_refusal_events_preserve_terminal_usage(tmp_path, business):
    rows = events()
    message = dict(id='msg_1', type='message', role='assistant', status='completed', content=[
        dict(type='refusal', refusal=PRIVATE)])
    rows = [rows[0], dict(type='response.output_item.added', output_index=0, item=message),
        dict(type='response.refusal.delta', output_index=0, item_id='msg_1', content_index=0, delta=PRIVATE),
        dict(type='response.refusal.done', output_index=0, item_id='msg_1', content_index=0, refusal=PRIVATE),
        dict(type='response.output_item.done', output_index=0, item=message), rows[-1]]
    rows[-1]['response']['output'] = [message]
    rows = [dict(row, sequence_number=i) for i, row in enumerate(rows)]
    result, _, saved, _ = run(business, tmp_path, rows)
    assert not result['ok'] and result['code'] == 'non_tool_output'
    assert saved == [result['usage']] and result['usage']['total_tokens'] == 195
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('raw', ['{"score":100,"score":100}', '{"score":NaN}', '{',
    '[]', json.dumps({**REVIEW, 'extra': 'unexpected'})])
def test_strict_json_and_unchanged_schema(tmp_path, business, raw):
    result, _, saved, _ = run(business, tmp_path, events(raw))
    assert not result['ok'] and result['code'] == 'tool_schema_invalid'
    assert saved and result['usage'] is not None


@pytest.mark.parametrize('mutation,code', [
    ('model', 'model_identity'), ('response_id', 'response_identity'),
    ('tool_name', 'tool_final_mismatch'), ('final_arguments', 'tool_final_mismatch'),
    ('done_arguments', 'tool_arguments_mismatch'), ('sequence', 'event_sequence'),
    ('terminal', 'terminal_missing'), ('duplicate_terminal', 'event_after_terminal'),
    ('extra_tool', 'multiple_tools'), ('refusal', 'non_tool_output'),
    ('text_json', 'non_tool_output'), ('over_budget', 'usage_over_budget'),
    ('hidden_text', 'non_tool_output'), ('hidden_refusal', 'non_tool_output'),
    ('reasoning', 'reasoning_identity'), ('output_limit', 'output_limit_identity'),
])
def test_real_sse_protocol_rejections(tmp_path, business, mutation, code):
    rows = events()
    if mutation == 'model':
        rows[-1]['response']['model'] = 'another-model'
    elif mutation == 'reasoning':
        rows[-1]['response']['reasoning'] = {'effort': 'low'}
    elif mutation == 'output_limit':
        rows[-1]['response']['max_output_tokens'] = 99999
    elif mutation == 'response_id':
        rows[-1]['response']['id'] = 'resp_changed'
    elif mutation in ('tool_name', 'final_arguments'):
        # Final inventory differs from all previously emitted deltas/done.
        rows[-1] = deepcopy(rows[-1])
        rows[-1]['response']['output'][1]['name' if mutation == 'tool_name' else 'arguments'] = 'changed'
    elif mutation == 'done_arguments':
        rows[8]['arguments'] = '{}'
    elif mutation == 'sequence':
        rows[7]['sequence_number'] += 1
    elif mutation == 'terminal':
        rows.pop()
    elif mutation == 'duplicate_terminal':
        rows.append({**rows[-1], 'sequence_number': len(rows)})
    elif mutation == 'extra_tool':
        extra = deepcopy(rows[5])
        extra.update(output_index=2, sequence_number=6)
        extra['item'].update(id='fc_2', call_id='call_2')
        rows.insert(6, extra)
    elif mutation in ('hidden_text', 'hidden_refusal'):
        rows.insert(6, dict(type='response.' + ('output_text' if mutation == 'hidden_text' else 'refusal')
            + '.delta', output_index=1, item_id='fc_1', content_index=0, delta='hidden'))
        rows = [dict(row, sequence_number=i) for i, row in enumerate(rows)]
    elif mutation in ('refusal', 'text_json'):
        message = dict(id='msg_1', type='message', role='assistant', status='completed', content=[
            dict(type='refusal', refusal='No') if mutation == 'refusal' else
            dict(type='output_text', text=json.dumps(REVIEW), annotations=[])])
        rows = [rows[0], dict(type='response.output_item.added', output_index=0, item=message),
            dict(type='response.output_item.done', output_index=0, item=message), rows[-1]]
        rows[-1]['response']['output'] = [message]
        rows = [dict(row, sequence_number=i) for i, row in enumerate(rows)]
    elif mutation == 'over_budget':
        rows[-1]['response']['usage'].update(input_tokens=64001, total_tokens=64071)
    result, _, _, body = run(business, tmp_path, rows)
    assert not result['ok'] and result['code'] == code
    assert body.closed


@pytest.mark.parametrize('failure', ['after_terminal', 'close'])
def test_failure_after_terminal_cannot_be_success(tmp_path, business, failure):
    result, _, saved, body = run(business, tmp_path, events(),
        after_error=failure == 'after_terminal', close_error=failure == 'close')
    assert not result['ok'] and saved == [result['usage']] and body.closed
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('tail', [b'data: [DONE]\n\n', b'event: error\r\ndata: {}\r\n\r\n',
                                  b'data: {}\r\r'])
def test_sdk_ignored_tail_after_done_is_rejected(tmp_path, business, tail):
    result, _, saved, body = run(business, tmp_path, events(), tail=tail)
    assert not result['ok'] and result['code'] == 'sse_after_done'
    assert saved == [result['usage']] and body.closed


def test_http_429_has_one_attempt_and_no_usage_or_error_body_log(tmp_path, business):
    attempts = []
    def handler(request):
        attempts.append(request)
        return httpx.Response(429, json={'error': {'message': PRIVATE}}, headers={'retry-after': '0'})
    result = transport.collect(business, profile=transport.Profile(group='GPT-pro'), api_key=KEY,
        observation_dir=tmp_path/'observation', transport=httpx.MockTransport(handler))
    assert len(attempts) == 1 and not result['ok'] and result['usage'] is None
    assert PRIVATE not in json.dumps(result)


def test_redirect_does_not_forward_credential(tmp_path, business):
    attempts = []
    def handler(request):
        attempts.append(request)
        return httpx.Response(307, headers={'location': 'https://unexpected.invalid/v1/responses'})
    result = transport.collect(business, profile=transport.Profile(group='GPT-pro'), api_key=KEY,
        observation_dir=tmp_path/'observation', transport=httpx.MockTransport(handler))
    assert len(attempts) == 1 and not result['ok']


def test_sdk_does_not_discover_other_account_credentials(tmp_path, business, monkeypatch):
    original = os.environ.get
    def guarded(key, default=None):
        if key in {'OPENAI_API_KEY', 'OPENAI_ADMIN_KEY', 'OPENAI_ORG_ID',
                   'OPENAI_PROJECT_ID', 'OPENAI_WEBHOOK_SECRET'}:
            raise AssertionError('implicit credential discovery')
        return original(key, default)
    monkeypatch.setattr(os.environ, 'get', guarded)
    result, _, _, _ = run(business, tmp_path, events())
    assert result['ok'], result['code']


def test_saved_screen_bound_to_existing_business_validator(business):
    validate = screen_validator(business)
    assert validate(json.dumps(REVIEW)).verdict == 'pass'
    with pytest.raises(ValueError, match='revision_without_issues'):
        validate(json.dumps({**REVIEW, 'verdict': 'needs_revision'}))
    changed = deepcopy(business)
    changed['messages'][0]['content'] += 'changed policy'
    with pytest.raises(ValueError, match='screen_request_binding'):
        screen_validator(changed)


def test_usage_storage_failure_keeps_in_memory_usage_but_rejects(tmp_path, business):
    def cannot_save(value):
        raise OSError(PRIVATE)
    body = Bytes(events())
    result = transport.collect(business, profile=transport.Profile(group='GPT-pro'), api_key=KEY,
        observation_dir=tmp_path/'observation', on_usage=cannot_save,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=body,
            headers={'content-type': 'text/event-stream'})))
    assert not result['ok'] and result['usage']['total_tokens'] == 195 and body.closed
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('verdict,accepted', [('pass', True), ('needs_revision', False)])
def test_real_worker_to_supervisor_preserves_business_gate(tmp_path, business, verdict, accepted):
    # Exercise the shipped worker and parent together, replacing only HTTP IO.
    code = '''
import json, runpy, socket
import httpx
from scripts import reviewer_responses_process as process
from scripts.reviewer_responses_transport import collect
fixture = runpy.run_path('tests/test_reviewer_responses_transport.py')
def forbidden(*args, **kwargs):
    raise AssertionError('offline child attempted network')
socket.socket = socket.create_connection = forbidden
review = {**fixture['REVIEW'], 'verdict': VERDICT}
def handler(request):
    return httpx.Response(200, stream=fixture['Bytes'](fixture['events'](json.dumps(review))),
        headers={'content-type': 'text/event-stream'})
def offline_collect(*args, **kwargs):
    return collect(*args, **kwargs, transport=httpx.MockTransport(handler))
process.collect = offline_collect
process.worker()
'''.replace('VERDICT', repr(verdict))
    receipt = run_once(business, profile=transport.Profile(group='GPT-pro'), api_key=KEY,
        directory=tmp_path/'call', command=[sys.executable, '-c', code], timeout_s=20)
    assert receipt['ok'] is accepted, receipt['code']
    assert receipt['reaped'] and receipt['http_requests'] == 1 and receipt['usage_state'] == 'known'
    result = json.loads((tmp_path/'call/worker-result.json').read_text())
    assert result['business_validated'] is accepted
    if not accepted:
        assert result['code'] == 'business_contract_invalid'
    public = ''.join(p.read_text(encoding='utf-8') for p in (tmp_path/'call').rglob('*.json'))
    assert KEY not in public and PRIVATE not in public
