"""Real SDK, mock HTTP, owned worker: offline contract evidence, not model quality."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket
import sys

import httpx
import pytest

from scripts import reviewer_responses_nonstream as codec
from scripts import reviewer_responses_process as process
from scripts import reviewer_responses_transport as stream

PACKAGE = Path(__file__).resolve().parents[1] / 'data/evaluation/fixtures/reviewer_profile_screen_20261015'
PRIVATE = 'PRIVATE_BODY_AND_REASONING_SENTINEL'
KEY = 'OFFLINE_KEY_SENTINEL'
REVIEW = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[], repairs=[])
USAGE = dict(input_tokens=12, output_tokens=8, total_tokens=20)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline test attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def business():
    return json.loads((PACKAGE / 'requests/r02-facts.json').read_text(encoding='utf-8'))


def response(review=None, output=None):
    call = dict(type='function_call', id='fc_1', call_id='call_1', status='completed',
        name=stream.TOOL, arguments=json.dumps(REVIEW if review is None else review))
    return dict(id='resp_1', object='response', created_at=1, model=stream.MODEL,
        status='completed', error=None, incomplete_details=None, usage=deepcopy(USAGE),
        output=[call] if output is None else output)


@pytest.mark.parametrize('case', ['r01-facts', 'r01-completion', 'r02-facts', 'r02-completion'])
def test_full_request_preserved_and_tool_choice_explicit(case):
    business = json.loads((PACKAGE / f'requests/{case}.json').read_text(encoding='utf-8'))
    before = deepcopy(business)
    wire = codec.build_wire(business)
    assert business == before and wire['input'] == business['messages']
    assert wire['tools'][0]['parameters'] == business['tools'][0]['input_schema']
    assert wire['tool_choice'] == dict(type='function', name=stream.TOOL)
    assert wire['stream'] is False and wire['max_output_tokens'] == 16384
    assert wire['reasoning'] == {'effort': 'high'}
    # Old frozen protocol is not silently changed into the new diagnostic.
    assert stream.build_wire(business)['tool_choice'] == 'auto'


@pytest.mark.parametrize('kind,calls,code', [
    ('tool', 1, 'ok'), ('text', 0, 'non_tool_output'),
    ('mixed', 1, 'non_tool_output'), ('reasoning', 0, 'single_tool_required'),
    ('two_tools', 2, 'single_tool_required'), ('unknown', 0, 'non_tool_output'),
])
def test_counts_survive_rejection_without_response_body(business, kind, calls, code):
    value = response()
    message = dict(type='message', status='completed', content=[dict(text=PRIVATE)])
    reasoning = dict(type='reasoning', summary=[dict(text=PRIVATE)])
    value['output'] = {
        'tool': [reasoning, *value['output']], 'text': [message],
        'mixed': [*value['output'], message], 'reasoning': [reasoning],
        'two_tools': value['output'] * 2, 'unknown': [dict(type=PRIVATE)],
    }[kind]
    result = codec.inspect_response(value, business)
    assert result['code'] == code
    assert result['response_observation']['function_calls'] == calls
    assert result['response_observation']['reported_completed'] is True
    assert result['usage']['total_tokens'] == 20
    assert PRIVATE not in json.dumps(result)
    if code != 'ok':
        assert result['public_tool_call'] is None


@pytest.mark.parametrize('fault,code', [
    ('model', 'model_identity'), ('incomplete', 'response_not_completed'),
    ('terminal_error', 'terminal_error'), ('output', 'output_shape'),
    ('name', 'tool_contract'), ('arguments', 'tool_schema_invalid'),
    ('duplicate', 'tool_schema_invalid'), ('budget', 'usage_over_budget'),
    ('reasoning', 'reasoning_identity'), ('output_limit', 'output_limit_identity'),
])
def test_failure_keeps_reported_usage_and_terminal_separate(business, fault, code):
    value = response()
    if fault == 'model': value['model'] = PRIVATE
    elif fault == 'incomplete': value['status'] = 'incomplete'
    elif fault == 'terminal_error': value['error'] = dict(message=PRIVATE)
    elif fault == 'output': value['output'] = None
    elif fault == 'name': value['output'][0]['name'] = PRIVATE
    elif fault == 'arguments': value['output'][0]['arguments'] = PRIVATE
    elif fault == 'duplicate': value['output'][0]['arguments'] = '{"score":95,"score":90}'
    elif fault == 'budget': value['usage'] = dict(input_tokens=64001, output_tokens=1, total_tokens=64002)
    elif fault == 'reasoning': value['reasoning'] = dict(effort='low')
    elif fault == 'output_limit': value['max_output_tokens'] = 32768
    result = codec.inspect_response(value, business)
    assert result['code'] == code and not result['ok']
    assert result['usage_state'] == 'known'
    assert result['response_observation']['reported_completed'] is (fault != 'incomplete')
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('usage', [None, {}, {**USAGE, 'input_tokens': True},
    {**USAGE, 'total_tokens': 999}, {**USAGE, 'input_tokens_details': 'bad'}])
def test_invalid_usage_is_unknown_but_output_counts_remain(business, usage):
    value = response(); value['usage'] = usage
    result = codec.inspect_response(value, business)
    assert not result['ok'] and result['usage'] is None and result['usage_state'] == 'unknown'
    assert result['response_observation']['function_calls'] == 1


@pytest.mark.parametrize('variant', ['ok', 'mixed', '524', 'usage_write'])
def test_sdk_request_and_failure_observation(tmp_path, business, variant):
    requests = []
    value = response()
    if variant == 'mixed':
        value['output'].append(dict(type='message', status='completed', role='assistant',
            content=[dict(type='output_text', text=PRIVATE, annotations=[])]))
    def handler(request):
        requests.append(request)
        return httpx.Response(524 if variant == '524' else 200,
            stream=httpx.ByteStream(PRIVATE.encode() if variant == '524' else json.dumps(value).encode()),
            headers={'content-type': 'application/json'})
    def save_usage(usage):
        if variant == 'usage_write': raise OSError(PRIVATE)
    result = codec.collect(business, profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path / 'observation', on_usage=save_usage,
        transport=httpx.MockTransport(handler))
    assert len(requests) == 1
    assert json.loads(requests[0].content) == codec.build_wire(business)
    assert result['ok'] is (variant == 'ok')
    assert result['code'] == {'ok':'ok', 'mixed':'non_tool_output',
        '524':'http_status_524', 'usage_write':'usage_write_failed'}[variant]
    observed = json.loads((tmp_path / 'observation/observation.json').read_text())
    assert observed['closed'] and observed['eof'] and observed['http_requests'] == 1
    if variant != '524':
        assert observed['response_contract']['function_calls'] == 1
        assert observed['response_contract']['reported_completed']
        assert result['usage']['total_tokens'] == 20
    public = json.dumps(result) + json.dumps(observed)
    assert KEY not in public and PRIVATE not in public


@pytest.mark.parametrize('sdk', [False, True], ids=['mapping', 'real-sdk-mock-http'])
@pytest.mark.filterwarnings('error:Pydantic serializer warnings')
@pytest.mark.parametrize('field,echo,accepted', [
    ('omit', 'absent', True), (None, 'null', True),
    ({}, 'effort_missing', True), ({'effort': None}, 'effort_null', True),
    ({'effort': 'high'}, 'high', True),
    *[({'effort': effort}, 'conflict', False)
      for effort in ('none', 'minimal', 'low', 'medium', 'xhigh', 'max', 'ultra',
                     '', '  ', 'HIGH', ' high ', PRIVATE)],
    ({'effort': []}, 'malformed', False),
    ({'effort': True}, 'malformed', False),
    (PRIVATE, 'malformed', False), ([], 'malformed', False),
])
def test_optional_reasoning_echo_is_observed_without_claiming_identity(
        tmp_path, business, sdk, field, echo, accepted):
    value = response()
    value['output'].insert(0, dict(type='reasoning', id='rs_1',
        summary=[dict(type='summary_text', text=PRIVATE)]))
    if field != 'omit':
        value['reasoning'] = field
    if sdk:
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, stream=httpx.ByteStream(json.dumps(value).encode()),
                headers={'content-type': 'application/json'})
        result = codec.collect(business,
            profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
            api_key=KEY, observation_dir=tmp_path / 'observation',
            transport=httpx.MockTransport(handler))
        assert len(requests) == 1 and requests[0]['reasoning'] == {'effort': 'high'}
        observed = json.loads((tmp_path / 'observation/observation.json').read_text(encoding='utf-8'))
        assert observed['response_contract']['reasoning_echo'] == echo
        assert observed['eof'] and observed['closed']
        assert KEY not in json.dumps(observed) and PRIVATE not in json.dumps(observed)
    else:
        result = codec.inspect_response(value, business)
    assert result['ok'] is accepted
    assert result['code'] == ('ok' if accepted else 'reasoning_identity')
    assert result['response_observation']['reasoning_echo'] == echo
    detail = result['response_observation']['reasoning_effort_detail']
    if isinstance(field, dict) and isinstance(field.get('effort'), str):
        effort = field['effort']
        normalized = effort.strip().casefold()
        if effort in ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'):
            assert detail == dict(category='known', value=effort)
        elif normalized == 'high':
            assert detail == dict(category='noncanonical_known', value='high')
        else:
            assert detail == dict(category='blank' if not normalized else 'unrecognized', value=None)
    else:
        assert detail is None
    if sdk:
        assert observed['response_contract']['reasoning_effort_detail'] == detail
        decode = observed['response_contract']['decode']
        assert decode['identity_fields_equal'] and decode['raw_object'] and decode['sdk_object']
        assert decode['raw_reasoning_echo'] == echo and decode['raw_reasoning_effort_detail'] == detail
        assert observed['response_decode'] == decode
        assert observed['response_body_sha256'] == hashlib.sha256(json.dumps(value).encode()).hexdigest()
    assert {key: result['usage'][key] for key in USAGE} == USAGE
    assert result['usage_state'] == 'known'
    assert result['business_validated'] is False
    assert result['semantic_approval'] is False and result['upstream_identity_verified'] is False
    assert result['qualified'] is False and result['publication_allowed'] is False
    assert (result['public_tool_call'] is not None) is accepted
    assert PRIVATE not in json.dumps(result) and KEY not in json.dumps(result)


@pytest.mark.parametrize('variant,accepted', [
    ('ok', True), ('mixed', False), ('missing_repairs', False),
    ('effort_null', True), ('effort_conflict', False),
    ('effort_noncanonical', False), ('effort_unknown', False),
])
def test_owned_worker_to_receipt_uses_business_gate(tmp_path, business, variant, accepted):
    # Execute the actual child, replacing HTTP IO only. No key prompt or network.
    child = '''
import json, socket, runpy
import httpx
from scripts import reviewer_responses_nonstream as codec
from scripts import reviewer_responses_process as process
fixture = runpy.run_path('tests/test_reviewer_responses_nonstream.py')
value = fixture['response']()
if VARIANT == 'effort_null':
    value['reasoning'] = dict(effort=None)
elif VARIANT == 'effort_conflict':
    value['reasoning'] = dict(effort='low')
elif VARIANT == 'effort_noncanonical':
    value['reasoning'] = dict(effort=' HIGH ')
elif VARIANT == 'effort_unknown':
    value['reasoning'] = dict(effort=fixture['PRIVATE'])
elif VARIANT == 'mixed':
    value['output'].append(dict(type='message', role='assistant', status='completed', content=[]))
elif VARIANT == 'missing_repairs':
    raw = json.load(open('data/evaluation/fixtures/reviewer_route_recovery_20261018/r02-review.json', encoding='utf-8'))
    raw['repairs'] = []
    value = fixture['response'](raw)
def forbidden(*args, **kwargs): raise AssertionError('offline child attempted network')
socket.socket = socket.create_connection = forbidden
original = codec.collect
def offline_collect(*args, **kwargs):
    return original(*args, **kwargs, transport=httpx.MockTransport(lambda request: httpx.Response(200,
        stream=httpx.ByteStream(json.dumps(value).encode()), headers={'content-type':'application/json'})))
codec.collect = offline_collect
process.worker()
'''.replace('VARIANT', repr(variant))
    directory = tmp_path / 'call'
    receipt = process.run_once(business, profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
        api_key=KEY, directory=directory, response_mode=codec.MODE,
        command=[sys.executable, '-c', child], timeout_s=30)
    assert receipt['ok'] is accepted
    assert receipt['usage_state'] == 'known' and receipt['http_requests'] == 1 and receipt['reaped']
    assert receipt['wire_sha256'] == stream.digest(codec.build_wire(business))
    worker = json.loads((directory / 'worker-result.json').read_text())
    assert worker['business_validated'] is accepted
    if variant == 'missing_repairs': assert worker['code'] == 'business_contract_invalid'
    if variant.startswith('effort_'):
        assert worker['response_observation']['reasoning_echo'] == (
            'effort_null' if accepted else 'conflict')
        assert worker['upstream_identity_verified'] is False
        expected_detail = {
            'effort_null': None,
            'effort_conflict': dict(category='known', value='low'),
            'effort_noncanonical': dict(category='noncanonical_known', value='high'),
            'effort_unknown': dict(category='unrecognized', value=None),
        }[variant]
        assert worker['response_observation']['reasoning_effort_detail'] == expected_detail
        observed = json.loads((directory / 'observation/observation.json').read_text(encoding='utf-8'))
        assert observed['response_contract']['reasoning_effort_detail'] == expected_detail
        assert observed['response_decode']['identity_fields_equal'] is True
        if not accepted:
            assert worker['code'] == 'reasoning_identity'
    assert KEY not in ''.join(p.read_text() for p in directory.rglob('*.json'))
    assert PRIVATE not in json.dumps(worker)
    with pytest.raises(FileExistsError):
        process.run_once(business, profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
            api_key=KEY, directory=directory, response_mode=codec.MODE, cancel=lambda: True)


def test_mode_and_route_rejected_before_claim(tmp_path, business):
    for mode, route in [('bad', 'proxy-12000'), (codec.MODE, 'direct-no-proxy')]:
        with pytest.raises(ValueError):
            process.run_once(business, profile=stream.Profile(group='GPT-pro', route=route),
                api_key=KEY, directory=tmp_path / 'claim', response_mode=mode)
        assert not (tmp_path / 'claim').exists()


@pytest.mark.parametrize('mode', ['reasoning_conflict', 'sdk_decode_conflict'])
def test_reasoning_conflict_reaches_application_without_retry_or_lost_usage(tmp_path, mode):
    from tests.test_sol_natural_candidate import application
    from tests.test_natural_duty_candidate import run
    from app.runtime.store import RuntimeTraceStore

    app, factory, flows, attempts = application(tmp_path, mode=mode)
    result = run(app)
    assert attempts == [200] and len(factory.providers['candidate'].generator.requests) == 2
    assert flows[0].outcome == 'candidate_execution_failed'
    budget = flows[0].send.provider
    assert budget.calls == 3 and budget.reserved_tokens == 0
    directory = next((tmp_path / 'transport/candidate/review').glob('call-*'))
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    worker = json.loads((directory / 'worker-result.json').read_bytes())
    observed = json.loads((directory / 'observation/observation.json').read_bytes())
    assert receipt['worker_code'] == ('reasoning_identity' if mode == 'reasoning_conflict' else 'response_decode_mismatch')
    assert receipt['usage_state'] == 'known'
    assert receipt['reaped'] and receipt['http_requests'] == 1
    assert worker['response_observation'] == observed['response_contract']
    assert worker['response_observation']['reasoning_effort_detail'] == dict(category='known', value='low')
    assert worker['response_observation']['decode']['raw_reasoning_effort_detail'] == dict(
        category='known', value='low' if mode == 'reasoning_conflict' else 'high')
    assert worker['response_observation']['decode']['identity_fields_equal'] is (mode == 'reasoning_conflict')
    assert worker['public_tool_call'] is None and worker['business_validated'] is False
    diagnostic = worker['diagnostic_tool_call']
    assert diagnostic['purpose'] == 'diagnostic_only'
    assert diagnostic['arguments_sha256'] == hashlib.sha256(diagnostic['arguments'].encode('utf-8')).hexdigest()
    assert diagnostic['wire_sha256'] == receipt['wire_sha256']
    assert diagnostic['business_validated'] is False and diagnostic['publication_allowed'] is False
    # Retention must never manufacture a completed exchange or a replayable
    # successful review from the rejected worker's otherwise valid arguments.
    reviewer = factory.providers['candidate'].reviewer
    assert reviewer.last_exchange is None
    with pytest.raises(ValueError, match='sol_saved_complete_receipt_required'):
        reviewer.read_completed_at_ordinal(reviewer.last_failure['request'], ordinal=3, role='review')
    trace = RuntimeTraceStore(tmp_path / 'reports', 'candidate').read_trace(result.trace_reference)
    assert trace.usage.provider_calls_attempted == 3
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens
    failed = [e.signal for e in trace.events if e.signal.kind == 'provider_call_failed_usage']
    assert len(failed) == 1 and failed[0].input_tokens == 12 and failed[0].output_tokens == 8
    assert result.publication_status.value == 'rejected'


@pytest.mark.parametrize('fault', ['reasoning', 'model', 'usage', 'mixed', 'invalid', 'two_tools', 'name'])
def test_rejected_public_tool_retention_preserves_exact_bytes_only(business, fault):
    value = response()
    raw = json.dumps(REVIEW, ensure_ascii=False, indent=2) + '\n'
    value['output'][0]['arguments'] = raw
    value['output'].append(dict(type='reasoning', summary=[dict(text=PRIVATE)]))
    if fault == 'reasoning': value['reasoning'] = dict(effort='low')
    elif fault == 'model': value['model'] = PRIVATE
    elif fault == 'usage': value['usage'] = None
    elif fault == 'mixed': value['output'].append(dict(type='message', content=[dict(text=PRIVATE)]))
    elif fault == 'invalid': value['output'][0]['arguments'] = PRIVATE
    elif fault == 'two_tools': value['output'].insert(0, deepcopy(value['output'][0]))
    elif fault == 'name': value['output'][0]['name'] = PRIVATE
    result = codec.inspect_response(value, business)
    assert not result['ok'] and result['public_tool_call'] is None
    diagnostic = result['diagnostic_tool_call']
    if fault in ('invalid', 'two_tools', 'name'):
        assert diagnostic is None
    else:
        assert diagnostic['arguments'] == raw
        assert diagnostic['arguments_sha256'] == hashlib.sha256(raw.encode('utf-8')).hexdigest()
        assert diagnostic['wire_sha256'] == stream.digest(codec.build_wire(business))
        assert diagnostic['business_validated'] is False and diagnostic['semantic_approval'] is False
        assert diagnostic['publication_allowed'] is False
    assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize('fault', ['changed_effort', 'parser_error'])
def test_raw_metadata_survives_sdk_drift_or_parse_error(tmp_path, business, monkeypatch, fault):
    from openai._legacy_response import LegacyAPIResponse
    original = LegacyAPIResponse.parse
    def parse(self, *, to=None):
        if to is not None:
            return original(self, to=to)
        if fault == 'parser_error':
            raise ValueError(PRIVATE)
        value = original(self)
        value.reasoning.effort = 'low'
        return value
    monkeypatch.setattr(LegacyAPIResponse, 'parse', parse)
    value = response()
    value['reasoning'] = dict(effort='high')
    value['output'].append(dict(type='reasoning', summary=[dict(text=PRIVATE)]))
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=value)
    result = codec.collect(business, profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation', transport=httpx.MockTransport(handler))
    assert len(requests) == 1 and not result['ok'] and result['public_tool_call'] is None
    observed = json.loads((tmp_path/'observation/observation.json').read_bytes())
    decode = observed['response_decode']
    assert decode['raw_reasoning_effort_detail'] == dict(category='known', value='high')
    assert decode['identity_fields_equal'] is False
    if fault == 'changed_effort':
        assert result['code'] == 'response_decode_mismatch' and result['usage_state'] == 'known'
        assert result['diagnostic_tool_call'] is not None and decode['sdk_object'] is True
        assert result['response_observation']['reasoning_effort_detail'] == dict(category='known', value='low')
    else:
        assert result['code'] == 'request_failed' and decode['sdk_object'] is False
    assert KEY not in json.dumps(result)+json.dumps(observed)
    assert PRIVATE not in json.dumps(result)+json.dumps(observed)


@pytest.mark.parametrize('escaped', [False, True])
def test_credential_echo_in_public_tool_is_not_retained(tmp_path, business, escaped):
    # Obtain a schema-valid free-text location from the actual business tool.
    schema = codec.build_wire(business)['tools'][0]['parameters']
    from jsonschema import Draft202012Validator
    # A repair reason is public model output, never a credential source.
    review = json.loads((Path('data/evaluation/fixtures/reviewer_route_recovery_20261018/r02-review.json')).read_text(encoding='utf-8'))
    next(iter(review['repairs'][0]['edits'].values()))[0]['reason'] = KEY
    value = response(review)
    assert not list(Draft202012Validator(schema).iter_errors(json.loads(value['output'][0]['arguments'])))
    if escaped:
        value['output'][0]['arguments'] = value['output'][0]['arguments'].replace('OFFLINE', '\\u004fFFLINE')
    result = codec.collect(business, profile=stream.Profile(group='GPT-pro', route='proxy-12000'),
        api_key=KEY, observation_dir=tmp_path/'observation', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=value)))
    assert result['code'] == 'credential_echo' and not result['ok']
    assert result['public_tool_call'] is None and result['diagnostic_tool_call'] is None
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize('mode', ['stream', codec.MODE])
def test_cancel_before_send_preserves_exact_profile_contract(tmp_path, business, mode):
    profile = stream.Profile(group='GPT-pro', route='proxy-12000')
    directory = tmp_path / 'call'
    receipt = process.run_once(business, profile=profile, api_key=KEY, directory=directory,
        response_mode=mode, cancel=lambda: True)
    expected = dict(**asdict(profile), reasoning_effort='high', api='responses',
        max_output_tokens=32768 if mode == 'stream' else 16384, max_retries=0, timeout_s=300,
        group_verified=False, upstream_identity_verified=False)
    if mode != 'stream': expected['response_mode'] = mode
    assert json.loads((directory / 'profile.json').read_text()) == expected
    assert receipt['http_requests'] == 0 and receipt['usage_state'] == 'not_sent'
