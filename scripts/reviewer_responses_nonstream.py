"""Prospective research contract; no live CLI, batch, prompt patch or admission.

The owned process in reviewer_responses_process supplies deadline, cancellation
and create-only execution. Old streaming requests and saved receipts are untouched.
Observe the returned structure before accepting it; never persist message text,
reasoning, arbitrary item types, IDs, exception messages or credentials.
"""
from collections.abc import Mapping
import hashlib
import math

import httpx
from jsonschema import Draft202012Validator
from openai import OpenAI

from app.evaluation.golden_native_issues_review import strict_json
from scripts import reviewer_responses_transport as stream
from scripts.stream_observation import StreamObservation

MODE = 'nonstream-tool-v1'
MAX_INPUT = 64000
MAX_OUTPUT = 16384
KNOWN_EFFORTS = frozenset(('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'))


def build_wire(business):
    """Explicitly change tool selection, preserving all messages and the schema."""
    wire = stream.build_wire(business)
    wire.update(stream=False, max_output_tokens=MAX_OUTPUT,
                tool_choice=dict(type='function', name=stream.TOOL))
    return wire


def mapping(value):
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json', exclude_unset=True, warnings=False)
    return value if isinstance(value, Mapping) else None


def reasoning_echo(value):
    """Classify optional provider metadata without retaining arbitrary text.

    Missing metadata does not verify the requested effort or upstream identity.
    An explicit conflict or malformed shape still rejects the response.
    """
    if 'reasoning' not in value:
        return 'absent'
    if value['reasoning'] is None:
        return 'null'
    reasoning = mapping(value['reasoning'])
    if reasoning is None:
        return 'malformed'
    if 'effort' not in reasoning:
        return 'effort_missing'
    effort = reasoning['effort']
    if effort is None:
        return 'effort_null'
    if not isinstance(effort, str):
        return 'malformed'
    return 'high' if effort == 'high' else 'conflict'


def reasoning_effort_detail(value):
    """Bounded diagnostic only; normalization never changes acceptance.

    Persist only fixed categories and allowlisted effort names, never an
    arbitrary provider string. Existing echoes cover absent/null/bad shapes.
    """
    reasoning = mapping(value.get('reasoning'))
    effort = reasoning.get('effort') if reasoning is not None else None
    if not isinstance(effort, str):
        return None
    normalized = effort.strip().casefold()
    if effort in KNOWN_EFFORTS:
        return dict(category='known', value=effort)
    if normalized in KNOWN_EFFORTS:
        return dict(category='noncanonical_known', value=normalized)
    return dict(category='blank' if not normalized else 'unrecognized', value=None)


def diagnostic_tool_call(calls, wire):
    """Retain only one schema-valid, expected public tool, before admission.

    Exact argument UTF-8 bytes are preserved; never copy messages, reasoning,
    arbitrary tools or unparseable text. This record is not an accepted call.
    The worker artifact is covered by the existing receipt/session inventory.
    """
    if len(calls) != 1:
        return None
    call = calls[0]
    if (call.get('name') != stream.TOOL or call.get('status') != 'completed'
            or not isinstance(call.get('arguments'), str)):
        return None
    raw = call['arguments']
    try:
        Draft202012Validator(wire['tools'][0]['parameters']).validate(strict_json(raw))
    except Exception:
        return None
    return dict(purpose='diagnostic_only', name=stream.TOOL, arguments=raw,
        arguments_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        wire_sha256=stream.digest(wire), business_validated=False,
        semantic_approval=False, publication_allowed=False)


def contains_credential(value, credential):
    if isinstance(value, str):
        return credential in value
    if isinstance(value, dict):
        return any(contains_credential(k, credential) or contains_credential(v, credential)
                   for k, v in value.items())
    if isinstance(value, list):
        return any(contains_credential(item, credential) for item in value)
    return False


def decode_observation(raw, parsed):
    """Compare identity metadata before/after SDK construction, without bodies.

    A returned field describes channel metadata, not authenticated upstream
    settings. Equality is checked on actual values; only fixed classifications
    and allowlisted effort values are persisted.
    """
    parsed = mapping(parsed)
    raw = mapping(raw)
    if raw is None or parsed is None:
        return dict(raw_object=raw is not None, sdk_object=parsed is not None,
                    identity_fields_equal=False,
                    raw_reasoning_echo=reasoning_echo(raw) if raw is not None else None,
                    raw_reasoning_effort_detail=reasoning_effort_detail(raw) if raw is not None else None)
    fields = ('model', 'reasoning', 'status', 'max_output_tokens')
    return dict(raw_object=True, sdk_object=True,
        identity_fields_equal=all((key in raw) == (key in parsed) and raw.get(key) == parsed.get(key)
                                  for key in fields),
        raw_reasoning_echo=reasoning_echo(raw),
        raw_reasoning_effort_detail=reasoning_effort_detail(raw))


def inspect_response(response, business):
    """Separate body-free observations, diagnostic public tool and admission.

    `reported_completed` is a provider terminal claim, not business acceptance.
    `function_calls` counts candidates, not validated calls. Known usage survives
    model, terminal, output, schema and business failures; it is not a bill.
    """
    wire = build_wire(business)
    value = mapping(response)
    observation = dict(response_received=value is not None, terminal_status=None,
        reported_completed=False, output_items=None, function_calls=None,
        output_type_counts=None, model_matches=False, reasoning_echo=None,
        reasoning_effort_detail=None)
    result = dict(ok=False, code='response_shape', usage=None, usage_state='unknown',
        public_tool_call=None, diagnostic_tool_call=None,
        business_validated=False, semantic_approval=False,
        upstream_identity_verified=False, qualified=False, publication_allowed=False,
        response_observation=observation)
    if value is None:
        return result
    observation['reasoning_echo'] = reasoning_echo(value)
    observation['reasoning_effort_detail'] = reasoning_effort_detail(value)
    status = value.get('status')
    observation.update(terminal_status=status if status in (
        'completed', 'incomplete', 'failed', 'cancelled', 'queued', 'in_progress') else 'other',
        reported_completed=status == 'completed', model_matches=value.get('model') == stream.MODEL)
    output = value.get('output')
    calls = []
    if isinstance(output, list):
        counts = dict(function_call=0, reasoning=0, message=0, other=0)
        for item in output:
            item = mapping(item)
            kind = item.get('type') if item else None
            key = kind if isinstance(kind, str) and kind in counts else 'other'
            counts[key] += 1
            if key == 'function_call':
                calls.append(item)
        observation.update(output_items=len(output), function_calls=len(calls),
                           output_type_counts=counts)
        result['diagnostic_tool_call'] = diagnostic_tool_call(calls, wire)
    try:
        result['usage'] = stream.usage_value(value.get('usage'))
        result['usage_state'] = 'known'
    except (ValueError, TypeError, AttributeError):
        result['code'] = 'usage_invalid'
        return result

    def reject(code):
        result['code'] = code
        return result

    if not observation['model_matches']:
        return reject('model_identity')
    if observation['reasoning_echo'] in ('conflict', 'malformed'):
        return reject('reasoning_identity')
    if value.get('max_output_tokens') not in (None, MAX_OUTPUT):
        return reject('output_limit_identity')
    if status != 'completed':
        return reject('response_not_completed')
    if value.get('error') is not None or value.get('incomplete_details') is not None:
        return reject('terminal_error')
    if result['usage']['input_tokens'] > MAX_INPUT or result['usage']['output_tokens'] > MAX_OUTPUT:
        return reject('usage_over_budget')
    if not isinstance(output, list):
        return reject('output_shape')
    if counts['message'] or counts['other']:
        return reject('non_tool_output')
    if len(calls) != 1:
        return reject('single_tool_required')
    call = calls[0]
    if (call.get('name') != stream.TOOL or call.get('status') != 'completed'
            or not isinstance(call.get('arguments'), str)):
        return reject('tool_contract')
    try:
        arguments = strict_json(call['arguments'])
        Draft202012Validator(wire['tools'][0]['parameters']).validate(arguments)
    except Exception:
        return reject('tool_schema_invalid')
    result.update(ok=True, code='ok', public_tool_call=dict(
        name=stream.TOOL, arguments=call['arguments']))
    return result


def collect(business, *, profile, api_key, observation_dir, timeout_s=300,
            on_usage=lambda value: None, transport=None):
    """Internal worker body. Only the owned supervisor supplies a hard deadline."""
    wire = build_wire(business)
    if not isinstance(profile, stream.Profile) or profile.route != 'proxy-12000':
        raise stream.TransportError('nonstream_explicit_proxy_required')
    if not isinstance(api_key, str) or not api_key:
        raise stream.TransportError('explicit_credential_required')
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 300:
        raise stream.TransportError('timeout_invalid')
    observer = StreamObservation(observation_dir)
    result = inspect_response(None, business)
    result.update(code='request_failed', failure_category=None, usage_conflict=False)
    client = None
    try:
        client = OpenAI(api_key=api_key, base_url=profile.base_url, max_retries=0,
            admin_api_key='', organization='', project='', webhook_secret='',
            http_client=httpx.Client(timeout=timeout_s, trust_env=False, follow_redirects=False,
                transport=transport if transport is not None else
                    httpx.HTTPTransport(proxy=stream.PROXY_12000, retries=0),
                event_hooks=dict(request=[observer.on_request], response=[observer.on_response])))
        raw_response = client.responses.with_raw_response.create(**wire)
        # Same HTTP response, no retrieval request or raw-body file. The SDK's
        # public raw-response interface lets us separate channel JSON from
        # Pydantic construction instead of inferring one from the other.
        raw_http = raw_response.parse(to=httpx.Response)
        raw_value = raw_http.json()
        body_sha = hashlib.sha256(raw_http.content).hexdigest()
        observer.update(response_decode=decode_observation(raw_value, None), response_body_sha256=body_sha)
        response = raw_response.parse()
        result.update(inspect_response(response, business))
        result['response_observation']['decode'] = decode_observation(raw_value, response)
        result['response_observation']['response_body_sha256'] = body_sha
        observer.update(response_decode=result['response_observation']['decode'])
        if not result['response_observation']['decode']['identity_fields_equal']:
            result.update(ok=False, code='response_decode_mismatch')
        # Credentials are never business input, but exclude an echoed exact
        # credential even if a malformed channel puts it in a valid tool field.
        diagnostic = result['diagnostic_tool_call']
        if diagnostic is not None and contains_credential(strict_json(diagnostic['arguments']), api_key):
            result.update(ok=False, code='credential_echo', diagnostic_tool_call=None)
        observer.update(response_contract=result['response_observation'])
        if result['usage'] is not None:
            try:
                on_usage(result['usage'])
            except Exception:
                result.update(ok=False, code='usage_write_failed')
    except Exception as error:
        status = getattr(error, 'status_code', None)
        category = stream.classify_exception(error)
        code = f'http_status_{status}' if type(status) is int and 100 <= status <= 599 else 'request_failed'
        result.update(ok=False, code=code, failure_category=category)
        observer.mark_failure(category)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                if result['ok']:
                    result.update(ok=False, code='close_failed')
        observer.close()
    if result['ok'] and (observer.failure or observer.values['http_requests'] != 1
            or observer.values['response_status'] != 200 or not observer.values['eof']
            or not observer.values['closed'] or observer.values['exception_type'] is not None):
        result.update(ok=False, code='observation_invalid')
    if not result['ok']:
        result['public_tool_call'] = None
    return result
