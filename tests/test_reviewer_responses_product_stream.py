"""Real SDK SSE parsing with synthetic bytes; no upstream-quality claims."""
import json
from copy import deepcopy

import httpx
import pytest

from scripts import reviewer_responses_stream as stream
from scripts import reviewer_responses_nonstream as nonstream
from scripts.reviewer_responses_transport import Profile, digest
from tests.test_reviewer_responses_nonstream import business, offline, response, PRIVATE, KEY
from tests.product_stream_fixtures import Bytes, events_for_response


def decode(business, rows, callback=lambda value: None):
    decoder = stream.Decoder(business, callback)
    for row in rows:
        decoder.feed(row)
    return decoder.finish()


def test_wire_preserves_business_and_forced_tool(business):
    before = deepcopy(business)
    wire = stream.build_wire(business)
    assert wire == dict(nonstream.build_wire(business), stream=True)
    assert business == before
    assert wire['max_output_tokens'] == 16384
    assert wire['reasoning'] == {'effort': 'high'}


@pytest.mark.parametrize('preamble,omit_name', [(False, False), (False, True), (True, True)])
def test_actual_sdk_accepts_bounded_compatibility(tmp_path, business, preamble, omit_name):
    rows = events_for_response(response(), preamble=preamble, omit_done_name=omit_name)
    recorded, uses = [], []
    def handler(request):
        recorded.append(json.loads(request.content))
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=Bytes(rows))
    result = stream.collect(business, profile=Profile(group='GPT-企业专线', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation', transport=httpx.MockTransport(handler), on_usage=uses.append)
    assert result['ok'], result
    assert recorded == [stream.build_wire(business)]
    assert uses == [result['usage']]
    compatibility = result['stream_protocol']['compatibility']
    assert compatibility.get('empty_created_replacement', 0) == int(preamble)
    assert compatibility.get('done_name_from_bound_item', 0) == int(omit_name)
    assert result['public_tool_call']['arguments'] == response()['output'][0]['arguments']
    assert result['diagnostic_tool_call']['wire_sha256'] == digest(recorded[0])
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize('fault,expected', [
    ('identity', 'response_identity'), ('name', 'tool_arguments_mismatch'),
    ('arguments', 'tool_arguments_mismatch'), ('final', 'tool_final_mismatch'),
    ('sequence', 'event_sequence'), ('duplicate_terminal', 'event_after_terminal'),
    ('model', 'model_identity'), ('reasoning', 'reasoning_identity'),
    ('limit', 'output_limit_identity'), ('inventory', 'terminal_inventory'),
    ('status', 'terminal_status'), ('late_created', 'duplicate_response'),
])
def test_conflicts_reject_without_losing_terminal_usage(business, fault, expected):
    rows = events_for_response(response())
    done = next(r for r in rows if r['type'] == 'response.function_call_arguments.done')
    if fault == 'identity': rows[-1]['response']['id'] = 'another'
    elif fault == 'name': done['name'] = 'other_tool'
    elif fault == 'arguments': done['arguments'] += ' '
    elif fault == 'final': rows[-1]['response']['output'][0] = dict(rows[-1]['response']['output'][0], arguments='{}')
    elif fault == 'sequence': rows[3]['sequence_number'] = rows[2]['sequence_number']
    elif fault == 'duplicate_terminal': rows.append(deepcopy(rows[-1]))
    elif fault == 'model': rows[-1]['response']['model'] = 'other'
    elif fault == 'reasoning': rows[-1]['response']['reasoning'] = {'effort': 'low'}
    elif fault == 'limit': rows[-1]['response']['max_output_tokens'] = 32768
    elif fault == 'inventory': rows[-1]['response']['output'] = []
    elif fault == 'status': rows[-1]['type'] = 'response.failed'
    elif fault == 'late_created': rows.insert(-1, dict(rows[0], sequence_number=rows[-1]['sequence_number']))
    uses = []
    result = decode(business, rows, uses.append)
    assert not result['ok'] and result['public_tool_call'] is None
    assert expected in result['stream_protocol']['errors'], result
    assert result['usage']['total_tokens'] == 20 and len(uses) == 1


def test_private_body_not_persisted_and_mixed_output_policy(business, tmp_path):
    value = response()
    value['output'] = [dict(id='reasoning1', type='reasoning', summary=[{'text': PRIVATE}]),
        *value['output'], dict(id='message1', type='message', status='completed', content=[{'type': 'output_text', 'text': PRIVATE}])]
    result = stream.collect(business, profile=Profile(group='GPT-企业专线', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation',
        transport=httpx.MockTransport(lambda _: httpx.Response(200, headers={'content-type': 'text/event-stream'},
            stream=Bytes(events_for_response(value)))))
    assert result['ok'], result
    persisted = json.dumps(result) + ''.join(p.read_text() for p in tmp_path.rglob('*.json'))
    assert PRIVATE not in persisted and KEY not in persisted


@pytest.mark.parametrize('kind', ['missing', 'schema', 'multiple', 'usage_conflict', 'callback_failure'])
def test_terminal_and_usage_edge_cases(business, kind):
    value = response()
    if kind == 'schema': value['output'][0]['arguments'] = '{}'
    if kind == 'multiple': value['output'].append(dict(value['output'][0], id='fc2', call_id='call2'))
    rows = events_for_response(value)
    if kind == 'missing': rows.pop()
    if kind == 'usage_conflict':
        other = deepcopy(rows[-1]); other['response']['usage'] = dict(input_tokens=13, output_tokens=8, total_tokens=21)
        rows.append(other)
    def callback(value):
        if kind == 'callback_failure': raise OSError('private path')
    result = decode(business, rows, callback)
    assert not result['ok'] and result['public_tool_call'] is None
    assert result['usage'] is None if kind == 'missing' else result['usage']['total_tokens'] == 20
    assert result['usage_conflict'] == (kind == 'usage_conflict')


@pytest.mark.parametrize('fault', ['disconnect', 'close', '524'])
def test_http_failure_never_approved_and_usage_survives(tmp_path, business, fault):
    rows = events_for_response(response())
    body = Bytes(rows, **({'after_error': True} if fault == 'disconnect' else {'close_error': True} if fault == 'close' else {}))
    result = stream.collect(business, profile=Profile(group='GPT-企业专线', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation',
        transport=httpx.MockTransport(lambda _: httpx.Response(524, content=b'{}') if fault == '524' else
            httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=body)))
    assert not result['ok'] and result['public_tool_call'] is None
    assert result['usage'] is None if fault == '524' else result['usage']['total_tokens'] == 20
    obs = json.loads((tmp_path/'observation/observation.json').read_text())
    assert obs['http_requests'] == 1
