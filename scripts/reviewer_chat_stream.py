"""Explicit Chat candidate transport; no credential discovery or batch launcher.

The existing single-call supervisor owns deadlines, cancellation and durable
receipts. Only explicitly selected Chat modes use this transport; existing
tasks and the default product route are not migrated.
"""
import math

import httpx
from openai import OpenAI

from scripts.reviewer_chat_contract import Decoder, build_wire
from scripts import reviewer_responses_nonstream as codec
from scripts import reviewer_responses_transport as transport_contract
from scripts.stream_observation import StreamObservation

MODE = 'natural-sol-product-chat-candidate-v1'


def collect(business, *, profile, api_key, observation_dir, timeout_s=300,
            on_usage=lambda value: None, on_usage_conflict=lambda first, other: None, transport=None):
    wire = build_wire(business)
    if not isinstance(profile, transport_contract.Profile) or profile.route != 'proxy-12000':
        raise transport_contract.TransportError('chat_explicit_proxy_required')
    if not isinstance(api_key, str) or not api_key:
        raise transport_contract.TransportError('explicit_credential_required')
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 300:
        raise transport_contract.TransportError('timeout_invalid')
    decoder = Decoder(business, on_usage, on_usage_conflict)
    observer = StreamObservation(observation_dir)
    client = response = None
    error_code = failure_category = None

    def received(value):
        observer.on_response(value)
        if value.status_code == 200:
            value.stream = transport_contract.TailCheckedStream(value.stream)

    try:
        client = OpenAI(api_key=api_key, base_url=profile.base_url, max_retries=0,
            admin_api_key='', organization='', project='', webhook_secret='',
            http_client=httpx.Client(timeout=timeout_s, trust_env=False, follow_redirects=False,
                transport=transport if transport is not None else
                    httpx.HTTPTransport(proxy=transport_contract.PROXY_12000, retries=0),
                event_hooks=dict(request=[observer.on_request], response=[received])))
        response = client.chat.completions.create(**wire)
        for event in response:
            decoder.feed(event.model_dump(mode='json', exclude_unset=True))
            observer.update(chat_protocol=dict(version='relay-chat-candidate-v1',
                chunk_count=decoder.result['chunk_count'], errors=list(decoder.result['errors']),
                usage_conflict=decoder.result['usage_conflict']), response_contract=decoder.observation())
            if decoder.result['chunk_count'] > 131072:
                break
    except Exception as error:
        status = getattr(error, 'status_code', None)
        error_code = f'http_status_{status}' if type(status) is int and 100 <= status <= 599 else 'request_failed'
        if observer.values['phase'] == 'close_failed':
            error_code = 'close_failed'
        failure_category = transport_contract.classify_exception(error)
        observer.mark_failure(failure_category)
    finally:
        for resource in (response, client):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    error_code = error_code or 'close_failed'
    try:
        result = decoder.finish(eof=observer.values['eof'], closed=observer.values['closed'])
        observer.update(response_contract=result['response_observation'])
    finally:
        observer.close()
    result['failure_category'] = failure_category
    if error_code:
        result.update(ok=False, code=error_code)
    if result['ok'] and (observer.failure or observer.values['http_requests'] != 1
            or observer.values['response_status'] != 200 or observer.values['exception_type'] is not None):
        result.update(ok=False, code='observation_invalid')
    if result['public_tool_call'] is not None and codec.contains_credential(result['public_tool_call'], api_key):
        result.update(ok=False, code='credential_echo')
    if not result['ok']:
        result['public_tool_call'] = None
    return result
