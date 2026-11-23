"""Offline Chat candidate; real SDK with blocked sockets and synthetic SSE."""
from copy import deepcopy
import json

import httpx
from openai import OpenAI
import pytest

from scripts import reviewer_chat_contract as chat
from scripts import reviewer_responses_nonstream as responses
from tests.test_reviewer_responses_nonstream import business, offline, PACKAGE, PRIVATE, KEY, REVIEW


def chunk(delta=None, finish=None, usage=None):
    return dict(id='chatcmpl-local', object='chat.completion.chunk', created=1,
        model='gpt-6.1-sol', choices=[] if delta is None else [
            dict(index=0, delta=delta, finish_reason=finish)], usage=usage)


def rows(raw=None, split=17):
    raw = json.dumps(REVIEW, ensure_ascii=False) if raw is None else raw
    result = [chunk(dict(role='assistant', content=None)),
              chunk(dict(reasoning_content=PRIVATE)), chunk(dict(content=PRIVATE))]
    for offset in range(0, len(raw), split):
        function = dict(arguments=raw[offset:offset+split])
        call = dict(index=0, function=function)
        if offset == 0:
            call.update(id='call-local', type='function')
            function['name'] = chat.responses.TOOL
        result.append(chunk(dict(tool_calls=[call])))
    result.extend([chunk({}, finish='tool_calls'), chunk(usage=dict(
        prompt_tokens=12, completion_tokens=8, total_tokens=20))])
    return result


def inspect(business, events=None, **kwargs):
    return chat.inspect_chunks(rows() if events is None else events, business,
        eof=kwargs.get('eof', True), closed=kwargs.get('closed', True))


@pytest.mark.parametrize('case', ['r01-facts', 'r01-completion', 'r02-facts', 'r02-completion'])
def test_complete_request_mapping_preserves_messages_and_schema(case):
    business = json.loads((PACKAGE/f'requests/{case}.json').read_text(encoding='utf-8'))
    before = deepcopy(business)
    wire = chat.build_wire(business)
    assert wire['messages'] == business['messages'] and business == before
    expected = responses.build_wire(business)['tools'][0]
    assert wire['tools'][0]['function'] == {k:v for k,v in expected.items() if k != 'type'}
    assert wire['tools'][0]['function']['strict'] is False
    assert wire['tool_choice'] == {'type':'function','function':{'name':chat.responses.TOOL}}
    assert wire['max_completion_tokens'] == 16384 and wire['reasoning_effort'] == 'high'
    assert wire['stream_options'] == {'include_usage':True}
    assert not ({'input','reasoning','max_tokens','thinking','tool_stream'} & wire.keys())


@pytest.mark.parametrize('split', [1, 17, 10000])
def test_tool_arguments_preserved_and_private_channels_not_returned(business, split):
    raw = json.dumps(REVIEW, ensure_ascii=False)
    result = inspect(business, rows(raw, split))
    assert result['ok'], result
    assert result['public_tool_call']['arguments'] == raw
    assert result['usage']['total_tokens'] == 20
    assert result['usage']['cached_input_tokens'] is None
    assert result['usage']['reasoning_tokens'] is None
    assert not result['business_validated'] and not result['publication_allowed']
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('fault', [
    'model', 'identity', 'choice_index', 'choices', 'tool_name', 'tool_id',
    'second_tool', 'bad_arguments', 'schema', 'duplicate_json', 'length', 'stop',
    'missing_terminal', 'duplicate_terminal', 'late_payload', 'error', 'refusal',
    'unknown_delta', 'effort', 'usage_before_terminal', 'usage_conflict', 'budget',
])
def test_structural_failures_never_lose_final_usage_or_become_reviews(business, fault):
    events = rows()
    if fault == 'model': events[1]['model'] = 'other-model'
    elif fault == 'identity': events[1]['id'] = 'other-id'
    elif fault == 'choice_index': events[0]['choices'][0]['index'] = 1
    elif fault == 'choices': events[0]['choices'] *= 2
    elif fault == 'tool_name': events[3]['choices'][0]['delta']['tool_calls'][0]['function']['name'] = 'other_tool'
    elif fault == 'tool_id': events[4]['choices'][0]['delta']['tool_calls'][0]['id'] = 'other-tool-id'
    elif fault == 'second_tool': events[3]['choices'][0]['delta']['tool_calls'][0]['index'] = 1
    elif fault == 'bad_arguments': events = rows('{')
    elif fault == 'schema': events = rows('{}')
    elif fault == 'duplicate_json': events = rows('{"score":95,"score":95}')
    elif fault == 'length': events[-2]['choices'][0]['finish_reason'] = 'length'
    elif fault == 'stop': events[-2]['choices'][0]['finish_reason'] = 'stop'
    elif fault == 'missing_terminal': events.pop(-2)
    elif fault == 'duplicate_terminal': events.insert(-1, deepcopy(events[-2]))
    elif fault == 'late_payload': events.insert(-1, chunk(dict(content=PRIVATE)))
    elif fault == 'error': events[0]['error'] = {'message':PRIVATE}
    elif fault == 'refusal': events[0]['choices'][0]['delta']['refusal'] = PRIVATE
    elif fault == 'unknown_delta': events[0]['choices'][0]['delta']['other'] = PRIVATE
    elif fault == 'effort': events[0]['reasoning_effort'] = 'low'
    elif fault == 'usage_before_terminal': events.insert(0, deepcopy(events[-1]))
    elif fault == 'usage_conflict':
        events.append(chunk(usage=dict(prompt_tokens=13,completion_tokens=8,total_tokens=21)))
    elif fault == 'budget': events[-1]['usage'] = dict(prompt_tokens=12,completion_tokens=16385,total_tokens=16397)
    result = inspect(business, events)
    assert not result['ok'] and result['public_tool_call'] is None
    assert result['usage']['total_tokens'] == (16397 if fault == 'budget' else 20)
    assert result['usage_conflict'] is (fault == 'usage_conflict')
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('fault', ['missing', 'invalid_total', 'negative', 'bool', 'bad_details', 'bad_cache'])
def test_unknown_usage_is_never_fabricated_as_zero(business, fault):
    events = rows()
    if fault == 'missing': events.pop()
    elif fault == 'invalid_total': events[-1]['usage']['total_tokens'] = 21
    elif fault == 'negative': events[-1]['usage']['prompt_tokens'] = -1
    elif fault == 'bool': events[-1]['usage']['prompt_tokens'] = True
    elif fault == 'bad_details': events[-1]['usage']['completion_tokens_details'] = 'invalid'
    elif fault == 'bad_cache': events[-1]['usage']['prompt_tokens_details'] = {'cached_tokens':13}
    result = inspect(business, events)
    assert not result['ok'] and result['usage'] is None and result['usage_state'] == 'unknown'


@pytest.mark.parametrize('eof,closed', [(False,True),(True,False),(False,False)])
def test_complete_looking_tool_requires_eof_and_close(business, eof, closed):
    result = inspect(business, eof=eof, closed=closed)
    assert not result['ok'] and result['public_tool_call'] is None
    assert result['usage']['total_tokens'] == 20


def test_read_failure_after_usage_retains_usage_without_acceptance(business):
    def broken():
        yield from rows()
        raise RuntimeError(PRIVATE)
    result = inspect(business, broken())
    assert not result['ok'] and 'stream_interrupted' in result['errors']
    assert result['usage']['total_tokens'] == 20 and PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('duty', ['facts', 'completion'])
@pytest.mark.parametrize('stage', ['initial', 'fresh'])
def test_current_product_business_binding_and_validation_are_reusable(duty, stage):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.product import sol_contract as product
    from app.product.review_purpose import bind_inputs
    from scripts.prepare_reviewer_profile_screen import visible, json_value
    from tests.test_natural_duty_candidate import Responses
    inputs = bind_inputs(build_inputs(Responses().req), 'observed')
    request = product.make_request(inputs, duty, stage)
    business = visible(json_value(request))
    validate = product.validate_business(business, request.metadata[product.CONTEXT])
    wire = chat.build_wire(business)
    assert wire['messages'] == business['messages']
    assert 'trusted_product_task_purpose=observed' in wire['messages'][0]['content']
    payload = deepcopy(REVIEW)
    if stage == 'fresh': payload.pop('repairs')
    result = inspect(business, rows(json.dumps(payload)))
    assert result['ok'], result['errors']
    assert validate(result['public_tool_call']['arguments']).verdict == 'pass'
    # Transport/schema success cannot substitute for even structural business
    # validation, much less an independent semantic judgment.
    payload['verdict'] = 'needs_revision'
    invalid = inspect(business, rows(json.dumps(payload)))
    assert invalid['ok'] and not invalid['business_validated']
    with pytest.raises(ValueError, match='revision_without_issues'):
        validate(invalid['public_tool_call']['arguments'])
    altered = deepcopy(business)
    altered['messages'][0]['content'] += ' changed purpose'
    with pytest.raises(ValueError, match='product_review_business_binding'):
        product.validate_business(altered, request.metadata[product.CONTEXT])


@pytest.mark.parametrize('tail', ['', ': harmless comment\n\n', 'data: {"unexpected":true}\n\n'])
def test_real_sdk_request_and_sse_decode_with_mock_transport(business, tail):
    class Bytes(httpx.SyncByteStream):
        ended = closed = False
        def __iter__(self):
            payload = ''.join('data: '+json.dumps(r)+'\n\n' for r in rows())+'data: [DONE]\n\n'+tail
            encoded = payload.encode()
            for i in range(0,len(encoded),7):
                yield encoded[i:i+7]
            self.ended = True
        def close(self): self.closed = True
    body, requests = Bytes(), []
    def handler(request):
        requests.append(dict(path=request.url.path,body=json.loads(request.content)))
        return httpx.Response(200,headers={'content-type':'text/event-stream'},
            stream=chat.responses.TailCheckedStream(body))
    with OpenAI(api_key=KEY,base_url='https://offline.invalid/v1',max_retries=0,
        admin_api_key='',organization='',project='',webhook_secret='',
        http_client=httpx.Client(transport=httpx.MockTransport(handler),trust_env=False)) as client:
        chunks, error = [], None
        try:
            with client.chat.completions.create(**chat.build_wire(business)) as stream:
                for value in stream: chunks.append(value)
        except chat.responses.TransportError as exc:
            error = str(exc)
        result = inspect(business,chunks,eof=body.ended and error is None,closed=body.closed)
    assert requests == [dict(path='/v1/chat/completions',body=chat.build_wire(business))]
    if tail.startswith('data:'):
        assert error == 'sse_after_done' and not result['ok']
    else:
        assert result['ok'], {k:result[k] for k in ('errors','eof','closed','chunk_count')}
    assert result['usage']['total_tokens'] == 20
    assert PRIVATE not in json.dumps(result) and KEY not in json.dumps(result)
