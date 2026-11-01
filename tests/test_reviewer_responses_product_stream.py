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


@pytest.mark.parametrize('preamble,omit_name', [(False, False), (False, True), (True, True), ('anonymous', True)])
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
    assert compatibility.get('empty_created_replacement', 0) == int(preamble is True)
    assert compatibility.get('anonymous_preamble_bound', 0) == int(preamble == 'anonymous')
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


def test_extra_events_are_located_without_relaxing_rejection(business, tmp_path):
    rows = events_for_response(response())
    rows.insert(0, {'type': 'ping', 'message': PRIVATE, 'secret_field': KEY})
    rows.insert(-1, {'type': 'keepalive', 'delta': PRIVATE})
    result = stream.collect(business, profile=Profile(group='GPT-企业专线', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation',
        transport=httpx.MockTransport(lambda _: httpx.Response(200,
            headers={'content-type': 'text/event-stream'}, stream=Bytes(rows))))
    assert result['ok'] is False and result['public_tool_call'] is None
    assert result['usage']['total_tokens'] == 20
    protocol = result['stream_protocol']
    assert protocol['errors'] == ['event_sequence', 'response_not_created', 'unexpected_event']
    first = protocol['first_rejection']
    assert first['code'] == 'event_sequence'
    assert first['event']['ordinal'] == 1 and first['event']['type'] == 'ping'
    assert first['event']['sequence'] is None and first['event']['created_count'] == 0
    extra = next(e for e in protocol['event_context'] if e['type'] == 'keepalive')
    assert extra['created_count'] == 1 and extra['output_items'] == 1
    persisted = json.dumps(result) + ''.join(p.read_text() for p in tmp_path.rglob('*.json'))
    assert PRIVATE not in persisted and KEY not in persisted and 'secret_field' not in persisted


def test_late_rejection_keeps_bounded_metadata_without_unknown_body(business):
    decoder = stream.Decoder(business, lambda _: None)
    rows = events_for_response(response())
    for event in rows[:-1]: decoder.feed(event)
    for i in range(100):
        decoder.feed({'type': 'response.reasoning_text.delta', 'sequence_number': decoder.raw_sequence+1,
                      'delta': PRIVATE, 'output_index': 0, 'item_id': 'arbitrary'})
    decoder.feed({'type': PRIVATE, 'sequence_number': None, KEY: PRIVATE})
    protocol = decoder.protocol()
    assert len(protocol['event_context']) <= 64
    assert protocol['first_rejection']['event']['type'] == 'unrecognized'
    assert protocol['first_rejection']['event']['ordinal'] > 100
    assert PRIVATE not in json.dumps(protocol) and KEY not in json.dumps(protocol)


@pytest.mark.parametrize('fault', [
    'missing_id', 'null_id', 'content', 'usage', 'error', 'incomplete', 'model', 'reasoning', 'limit',
    'status', 'sequence', 'extra', 'order', 'short', 'unbound', 'late', 'second_identity', 'terminal_identity',
])
def test_anonymous_preamble_requires_empty_pair_and_immediate_identity(business, fault):
    rows = events_for_response(response(), preamble='anonymous')
    # Independent objects make mutations to either envelope meaningful.
    rows[0]['response'] = deepcopy(rows[0]['response'])
    first = rows[0]['response']
    if fault == 'missing_id': first.pop('id')
    elif fault == 'null_id': first['id'] = None
    elif fault == 'content': first['output'] = [{'type': 'message', 'text': PRIVATE}]
    elif fault == 'usage': first['usage'] = dict(input_tokens=1, output_tokens=1, total_tokens=2)
    elif fault == 'error': rows[1]['response']['error'] = {'message': PRIVATE}
    elif fault == 'incomplete': first['incomplete_details'] = {'reason': PRIVATE}
    elif fault == 'model': first['model'] = PRIVATE
    elif fault == 'reasoning': first['reasoning'] = {'effort': PRIVATE}
    elif fault == 'limit': first['max_output_tokens'] = 32768
    elif fault == 'status': first['status'] = 'completed'
    elif fault == 'sequence': rows[1]['sequence_number'] = 2
    elif fault == 'extra': rows.insert(2, deepcopy(rows[1]))
    elif fault == 'order': rows[0], rows[1] = rows[1], rows[0]
    elif fault == 'short': rows.pop(1)
    elif fault == 'unbound': rows = rows[:2]
    elif fault == 'late': rows = rows[2:4]+rows[:2]+rows[4:]
    elif fault == 'second_identity': rows.insert(3, deepcopy(rows[2]))
    elif fault == 'terminal_identity': rows[-1]['response']['id'] = 'different'
    result = decode(business, rows)
    assert result['ok'] is False and result['public_tool_call'] is None
    assert result['usage'] is None if fault == 'unbound' else result['usage']['total_tokens'] == 20
    assert PRIVATE not in json.dumps(result['stream_protocol'])


def test_anonymous_context_records_nested_shapes_not_nested_text(business):
    rows = events_for_response(response(), preamble='anonymous')
    rows[0]['response']['unrecognized'] = {'text': PRIVATE, 'key': KEY}
    result = decode(business, rows)
    assert result['ok']
    contexts = result['stream_protocol']['event_context']
    assert [c['response_shape']['identity'] for c in contexts[:3]] == ['empty', 'empty', 'valid']
    assert contexts[0]['response_shape']['output_count'] == 0
    assert contexts[0]['response_shape']['status'] == 'queued'
    assert PRIVATE not in json.dumps(contexts) and KEY not in json.dumps(contexts)
