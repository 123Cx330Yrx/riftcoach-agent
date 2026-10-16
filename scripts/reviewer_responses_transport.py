"""Single-request research codec. No product registration, credentials or batch.

`ok` means transport/schema acceptance only. Channel-reported identity/usage
cannot authenticate the upstream model, reasoning setting or account group.
Private reasoning is consumed by the SDK but never retained in evidence.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re

import httpx
from jsonschema import Draft202012Validator
from openai import OpenAI

from app.evaluation.golden_native_issues_review import strict_json
from scripts.stream_observation import StreamObservation

MODEL = 'gpt-6.1-sol'
BASE_URL = 'https://yujianwudi.top/v1'
TOOL = 'submit_report_review'
MAX_OUTPUT = 32768


class TransportError(ValueError):
    """Fixed codes only; never serialize exception text from a provider."""


@dataclass(frozen=True)
class Profile:
    group: str
    base_url: str = BASE_URL
    model: str = MODEL

    def __post_init__(self):
        if (self.base_url != BASE_URL or self.model != MODEL or
                self.group not in ('GPT-plus', 'GPT-pro', 'GPT-企业专线')):
            raise TransportError('profile_not_supported')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def build_wire(business):
    """Preserve all visible input and optional schema fields, without labels."""
    if (set(business) != {'messages', 'tools', 'tool_choice', 'response_contract'} or
            business['tool_choice'] != 'auto' or business['response_contract'] is not None):
        raise TransportError('business_contract')
    messages, tools = business['messages'], business['tools']
    if (not isinstance(messages, list) or len(messages) != 4 or
            any(set(m) != {'role', 'content'} or m['role'] not in ('system', 'user', 'assistant')
                or not isinstance(m['content'], str) or not m['content'] for m in messages)):
        raise TransportError('business_messages')
    if (len(tools) != 1 or set(tools[0]) != {'name', 'description', 'input_schema'} or
            tools[0]['name'] != TOOL):
        raise TransportError('business_tool')
    tool = tools[0]
    Draft202012Validator.check_schema(tool['input_schema'])
    return dict(model=MODEL, input=deepcopy(messages),
        tools=[dict(type='function', name=TOOL, description=tool['description'],
            parameters=deepcopy(tool['input_schema']), strict=False)],
        tool_choice='auto', parallel_tool_calls=False, reasoning=dict(effort='high'),
        max_output_tokens=MAX_OUTPUT, stream=True, store=False)


def usage_value(value):
    """Missing/invalid fields are unknown, never implicit zero or estimated."""
    if not isinstance(value, dict):
        raise TransportError('usage_missing')
    result = {}
    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
        number = value.get(key)
        if type(number) is not int or number < 0:
            raise TransportError('usage_invalid')
        result[key] = number
    for details, key, target, maximum in (
        ('input_tokens_details', 'cached_tokens', 'cached_input_tokens', result['input_tokens']),
        ('output_tokens_details', 'reasoning_tokens', 'reasoning_tokens', result['output_tokens']),
    ):
        # Optional breakdowns stay unknown, while the real totals can be known.
        number = (value.get(details) or {}).get(key)
        if number is not None and (type(number) is not int or not 0 <= number <= maximum):
            raise TransportError('usage_invalid')
        result[target] = number
    if result['total_tokens'] != result['input_tokens'] + result['output_tokens']:
        raise TransportError('usage_invalid')
    return result


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', value):
        raise TransportError('response_identity')
    return value


class Decoder:
    def __init__(self, business, on_usage):
        self.validator = Draft202012Validator(build_wire(business)['tools'][0]['parameters'])
        self.on_usage = on_usage
        self.sequence = -1
        self.response_id = None
        self.items = {}
        self.terminal = None
        self.usage = None
        self.usage_conflict = False
        self.public_tool_call = None
        self.non_tool_seen = False

    def feed(self, event):
        kind = event.get('type', '')
        terminal = kind in ('response.completed', 'response.incomplete', 'response.failed')
        if terminal:
            # Persist real totals before identity/schema/terminal checks can fail.
            reported = usage_value((event.get('response') or {}).get('usage'))
            if self.usage is None:
                self.usage = reported
                self.on_usage(reported)
            elif reported != self.usage:
                self.usage_conflict = True
                raise TransportError('usage_conflict')
        seq = event.get('sequence_number')
        if type(seq) is not int or seq != self.sequence + 1:
            raise TransportError('event_sequence')
        self.sequence = seq
        if self.terminal is not None:
            raise TransportError('event_after_terminal')
        if kind in ('response.created', 'response.in_progress') or terminal:
            response = event.get('response') or {}
            identity = safe_id(response.get('id'))
            if response.get('model') != MODEL:
                raise TransportError('model_identity')
            if (response.get('reasoning') is not None and
                    response['reasoning'].get('effort') != 'high'):
                raise TransportError('reasoning_identity')
            if response.get('max_output_tokens') not in (None, MAX_OUTPUT):
                raise TransportError('output_limit_identity')
            if kind == 'response.created':
                if self.response_id is not None or seq != 0:
                    raise TransportError('duplicate_response')
                self.response_id = identity
            elif self.response_id != identity:
                raise TransportError('response_identity')
            if terminal:
                self.terminal = kind
                self._finish(response, kind)
            return
        if self.response_id is None:
            raise TransportError('response_not_created')
        if kind == 'response.output_item.added':
            index, item = event['output_index'], event['item']
            if type(index) is not int or index != len(self.items):
                raise TransportError('output_index')
            item_type = item.get('type')
            if item_type not in ('function_call', 'reasoning', 'message'):
                raise TransportError('output_type')
            identity = safe_id(item.get('id'))
            if any(row['id'] == identity for row in self.items.values()):
                raise TransportError('output_identity')
            row = dict(id=identity, type=item_type, done=False)
            if item_type == 'function_call':
                if any(r['type'] == 'function_call' for r in self.items.values()):
                    raise TransportError('multiple_tools')
                if item.get('name') != TOOL or item.get('arguments') != '':
                    raise TransportError('tool_added_contract')
                row.update(call_id=safe_id(item.get('call_id')), name=TOOL,
                    arguments='', arguments_done=False)
            self.items[index] = row
        elif kind.startswith('response.function_call_arguments.'):
            row = self._item(event, event.get('item_id'))
            if row['type'] != 'function_call' or row['done'] or row['arguments_done']:
                raise TransportError('tool_event_order')
            if kind.endswith('.delta'):
                delta = event.get('delta')
                if not isinstance(delta, str) or len(row['arguments']) + len(delta) > 2_000_000:
                    raise TransportError('tool_arguments_limit')
                row['arguments'] += delta
            elif kind.endswith('.done'):
                if event.get('arguments') != row['arguments'] or event.get('name') != TOOL:
                    raise TransportError('tool_arguments_mismatch')
                row['arguments_done'] = True
            else:
                raise TransportError('tool_event_type')
        elif kind == 'response.output_item.done':
            item = event['item']
            row = self._item(event, item.get('id'))
            if row['done'] or item.get('type') != row['type']:
                raise TransportError('output_done')
            if row['type'] == 'function_call':
                self._match_call(row, item)
            row['done'] = True
        elif kind == 'error':
            raise TransportError('provider_error_event')
        elif kind.startswith(('response.output_text.', 'response.refusal.', 'response.content_part.')):
            # Refusal/text are valid API outcomes, though invalid for this
            # review. Retain no body and read their terminal usage before reject.
            self._item(event, event.get('item_id'))
            self.non_tool_seen = True
        elif not kind.startswith('response.reasoning_'):
            raise TransportError('unexpected_event')
        # Reasoning/text/refusal bodies are deliberately not retained. The full
        # terminal inventory below rejects messages and requires a real tool.

    def _item(self, event, identity):
        index = event.get('output_index')
        if type(index) is not int or index not in self.items or self.items[index]['id'] != identity:
            raise TransportError('output_identity')
        return self.items[index]

    @staticmethod
    def _match_call(row, item):
        if (not row['arguments_done'] or item.get('status') != 'completed' or
                any(item.get(key) != row[key] for key in ('id', 'name', 'call_id', 'arguments'))):
            raise TransportError('tool_final_mismatch')

    def _finish(self, response, kind):
        if response.get('status') != kind.removeprefix('response.'):
            raise TransportError('terminal_status')
        if kind != 'response.completed':
            raise TransportError(kind.replace('.', '_'))
        if response.get('error') or response.get('incomplete_details'):
            raise TransportError('terminal_error')
        if self.non_tool_seen:
            raise TransportError('non_tool_output')
        output = response.get('output')
        if not isinstance(output, list) or len(output) != len(self.items):
            raise TransportError('terminal_inventory')
        calls = []
        for index, item in enumerate(output):
            row = self._item(dict(output_index=index), item.get('id'))
            if not row['done'] or item.get('type') != row['type']:
                raise TransportError('terminal_inventory')
            if row['type'] == 'function_call':
                self._match_call(row, item)
                calls.append({key: row[key] for key in ('id', 'call_id', 'name', 'arguments')})
            elif row['type'] != 'reasoning':
                raise TransportError('non_tool_output')
        if len(calls) != 1:
            raise TransportError('single_tool_required')
        self.public_tool_call = calls[0]
        try:
            value = strict_json(calls[0]['arguments'])
            self.validator.validate(value)
        except Exception:
            raise TransportError('tool_schema_invalid') from None
        if self.usage['input_tokens'] > 64000 or self.usage['output_tokens'] > MAX_OUTPUT:
            raise TransportError('usage_over_budget')


class TailCheckedStream(httpx.SyncByteStream):
    """The SDK stops at [DONE]; drain and validate the tail before yielding it.

    Inspect framing only. No body enters logs. The observer wraps the underlying
    stream, so every drained byte and real EOF is measured, including comments
    after [DONE] that the SDK itself will not consume.
    """
    def __init__(self, stream):
        self.stream, self.pending, self.ended = stream, b'', False

    def __iter__(self):
        iterator = iter(self.stream)
        for chunk in iterator:
            self._consume(chunk)
            if self.ended:
                for tail in iterator:
                    self._consume(tail)
                if self.pending:
                    self._line(self.pending.rstrip(b'\r'))
                yield chunk
                return
            yield chunk
        if self.pending:
            self._line(self.pending.rstrip(b'\r'))

    def _consume(self, chunk):
        self.pending += chunk
        if len(self.pending) > 8_000_000:
            raise TransportError('sse_line_limit')
        while match := re.search(b'\r\n|\r|\n', self.pending):
            if match.group() == b'\r' and match.end() == len(self.pending):
                break  # May be half of CRLF at the next byte boundary.
            self._line(self.pending[:match.start()])
            self.pending = self.pending[match.end():]

    def _line(self, line):
        if self.ended and line.strip() and not line.startswith(b':'):
            raise TransportError('sse_after_done')
        if line.startswith(b'data:') and line[5:].strip() == b'[DONE]':
            self.ended = True

    def close(self):
        self.pending = b''
        self.stream.close()


def collect(business, *, profile, api_key, observation_dir, timeout_s=300,
            on_usage=lambda value: None, transport=None):
    """SDK worker body; run via process.run_once for hard deadline/cancellation.

    `transport` is an httpx offline-test seam. No environment credentials/proxy,
    redirect or automatic SDK retry. Not a public live/batch CLI.
    """
    wire = build_wire(business)
    if not isinstance(api_key, str) or not api_key:
        raise TransportError('explicit_credential_required')
    decoder = Decoder(business, on_usage)
    observer = StreamObservation(observation_dir)
    stream = client = None
    code = 'ok'
    def on_response(response):
        observer.on_response(response)
        if response.status_code == 200:
            response.stream = TailCheckedStream(response.stream)
    try:
        client = OpenAI(api_key=api_key, base_url=profile.base_url, max_retries=0,
            admin_api_key='', organization='', project='', webhook_secret='',
            http_client=httpx.Client(timeout=timeout_s, trust_env=False, follow_redirects=False,
                transport=transport, event_hooks=dict(request=[observer.on_request],
                                                     response=[on_response])))
        stream = client.responses.create(**wire)
        for event in stream:
            decoder.feed(event.model_dump(mode='json', exclude_unset=True))
        if decoder.terminal is None:
            raise TransportError('terminal_missing')
    except TransportError as error:
        code = str(error)
    except Exception:
        code = 'sdk_or_stream_failed'
    finally:
        for resource in (stream, client):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    if code == 'ok':
                        code = 'close_failed'
        observer.close()
    if code == 'ok' and (observer.failure or observer.values['http_requests'] != 1 or
                         observer.values['response_status'] != 200 or not observer.values['closed'] or
                         not observer.values['eof']):
        code = 'observation_invalid'
    return dict(ok=code == 'ok', code=code, usage=decoder.usage,
        usage_conflict=decoder.usage_conflict, public_tool_call=decoder.public_tool_call,
        response_id=decoder.response_id, terminal=decoder.terminal,
        business_validated=False, semantic_approval=False, upstream_identity_verified=False)
