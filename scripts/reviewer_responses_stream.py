"""Product-shaped Responses SSE with explicit, bounded relay compatibility.

No credentials, raw reasoning or message text enter protocol diagnostics.
Legacy streams/nonstream receipts remain separate; no old receipt is reclassified.
"""
import hashlib
import math
from collections import Counter

import httpx
from openai import OpenAI

from scripts import reviewer_responses_transport as legacy
from scripts import reviewer_responses_nonstream as codec
from scripts.stream_observation import StreamObservation

MODE = 'natural-sol-product-stream-v1'

# Log only named protocol tokens, never an arbitrary server-supplied type/body.
# Unknown tokens retain a digest so repeated types can still be distinguished.
OBSERVED_TYPES = frozenset({
    'ping', 'heartbeat', 'keepalive', 'keep_alive', 'error',
    'response.created', 'response.queued', 'response.in_progress',
    'response.completed', 'response.incomplete', 'response.failed', 'response.done',
    'response.output_item.added', 'response.output_item.done',
    'response.function_call_arguments.delta', 'response.function_call_arguments.done',
    *('response.' + family + '.' + suffix for family in (
        'output_text', 'refusal', 'content_part', 'reasoning_text',
        'reasoning_summary_text', 'reasoning_summary_part')
      for suffix in ('added', 'delta', 'done')),
})
OBSERVED_FIELDS = ('type', 'sequence_number', 'response', 'item', 'item_id',
                   'output_index', 'content_index', 'summary_index', 'name',
                   'arguments', 'delta', 'error', 'code', 'message', 'timestamp')
KEEPALIVE_TYPES = frozenset(('ping', 'heartbeat', 'keepalive', 'keep_alive'))
MAX_EMPTY_PREAMBLE_EVENTS = 64


def shape(value):
    if value is None: return 'null'
    if type(value) is bool: return 'boolean'
    if type(value) is int: return 'integer'
    if type(value) is float: return 'number'
    if isinstance(value, str): return 'string'
    if isinstance(value, list): return 'array'
    if isinstance(value, dict): return 'object'
    return 'other'


def build_wire(business):
    return dict(codec.build_wire(business), stream=True)


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest() if isinstance(value, str) else None


def response_shape(value):
    """Only bounded structural facts; never echo nested text or reasoning."""
    if not isinstance(value, dict):
        return dict(shape=shape(value))
    identity = value.get('id')
    try:
        legacy.safe_id(identity)
        identity_shape = 'valid'
    except legacy.TransportError:
        identity_shape = 'empty' if identity == '' else 'invalid' if 'id' in value else 'missing'
    status = value.get('status')
    output = value.get('output')
    return dict(shape='object', identity=identity_shape,
        status=status if status in ('queued', 'in_progress', 'completed', 'incomplete', 'failed') else 'other',
        output_shape=shape(output), output_count=len(output) if isinstance(output, list) else None,
        fields={key:shape(value[key]) for key in ('usage', 'error', 'incomplete_details') if key in value},
        model_matches=value.get('model') == legacy.MODEL, model_present='model' in value,
        reasoning_echo=codec.reasoning_echo(value),
        output_limit_matches=value.get('max_output_tokens') == codec.MAX_OUTPUT)


def empty_envelope(response):
    return (response.get('output') == [] and response.get('usage') is None
            and response.get('error') is None and response.get('incomplete_details') is None
            and response.get('model') in (None, legacy.MODEL)
            and codec.reasoning_echo(response) not in ('conflict', 'malformed')
            and response.get('max_output_tokens') in (None, codec.MAX_OUTPUT))


class Decoder(legacy.Decoder):
    def __init__(self, business, on_usage):
        super().__init__(business, on_usage)
        self.business = business
        self.raw_sequence = -1
        self.created = 0
        self.errors = []
        self.counts = Counter()
        self.metadata = []
        self.metadata_truncated = False
        self.result = codec.inspect_response(None, business, output_policy=codec.TOOL_WITH_MESSAGE)
        self.compatibility = Counter()
        self.event_ordinal = 0
        self.context_events = []
        self.context_truncated = False
        self.first_rejection = None
        self.current_context = None
        self.anonymous_preamble = 0
        self.anonymous_bound = False

    def reject(self, code):
        if self.first_rejection is None:
            self.first_rejection = dict(code=code, event=self.current_context)
        if code not in self.errors:
            self.errors.append(code)

    def protocol(self):
        return dict(version='product-stream-protocol-v2', errors=list(self.errors),
                    compatibility=dict(self.compatibility), counts=dict(self.counts),
                    events=list(self.metadata), metadata_truncated=self.metadata_truncated,
                    event_context_version='body-free-event-context-v2',
                    event_context=list(self.context_events), context_truncated=self.context_truncated,
                    first_rejection=self.first_rejection)

    def feed(self, event):
        if not isinstance(event, dict):
            self.current_context = dict(ordinal=self.event_ordinal+1, shape=shape(event))
            self.reject('event_shape')
            return
        kind = event.get('type', '')
        self.event_ordinal += 1
        self.current_context = dict(
            ordinal=self.event_ordinal,
            type=kind if isinstance(kind, str) and kind in OBSERVED_TYPES else 'unrecognized',
            type_sha256=fingerprint(kind),
            sequence=event.get('sequence_number') if type(event.get('sequence_number')) is int else None,
            previous_sequence=self.raw_sequence,
            created_count=self.created, output_items=len(self.items),
            terminal_seen=self.terminal is not None,
            fields={key:shape(event[key]) for key in OBSERVED_FIELDS if key in event},
            extra_field_count=sum(key not in OBSERVED_FIELDS for key in event),
            response_shape=response_shape(event.get('response')) if 'response' in event else None)
        # Keep every early event plus lifecycle/non-delta events. The first
        # rejection has its own slot so a long valid delta stream cannot hide it.
        if self.event_ordinal <= 8 or not isinstance(kind, str) or not kind.endswith('.delta'):
            if len(self.context_events) < 64:
                self.context_events.append(self.current_context)
            else:
                self.context_truncated = True
        lifecycle = kind in ('response.created', 'response.queued', 'response.in_progress',
                            'response.completed', 'response.incomplete', 'response.failed')
        terminal = kind in ('response.completed', 'response.incomplete', 'response.failed')
        label = kind if lifecycle or kind in (
            'response.output_item.added', 'response.output_item.done',
            'response.function_call_arguments.delta', 'response.function_call_arguments.done',
            'error') else 'other_body_event'
        self.counts[label] += 1
        if sum(self.counts.values()) > 100000:
            self.reject('event_limit')
        # Transport keepalives have no model identity or model sequence. Only
        # a known name with bounded metadata qualifies; payloads/unknown types
        # still follow the rejecting path, even after a completed response.
        if self._metadata_keepalive(event):
            self.compatibility['metadata_keepalive'] += 1
            return
        response = event.get('response') if isinstance(event.get('response'), dict) else {}
        seq = event.get('sequence_number')
        if lifecycle or kind in ('response.function_call_arguments.done', 'response.output_item.done'):
            item = event.get('item') if isinstance(event.get('item'), dict) else {}
            args = event.get('arguments') if kind == 'response.function_call_arguments.done' else (
                item.get('arguments') if item.get('type') == 'function_call' else None)
            if len(self.metadata) < 64:
                self.metadata.append(dict(type=label, sequence=seq if type(seq) is int else None,
                    response_id_sha256=fingerprint(response.get('id')),
                    item_id_sha256=fingerprint(event.get('item_id') or item.get('id')),
                    arguments_sha256=fingerprint(args), name_present='name' in event,
                    name_matches=event.get('name') == legacy.TOOL if 'name' in event else None))
            else:
                self.metadata_truncated = True
        # Capture terminal usage and bounded output before protocol checks reject it.
        if terminal:
            current = codec.inspect_response(response, self.business, output_policy=codec.TOOL_WITH_MESSAGE)
            if current['diagnostic_tool_call'] is not None:
                current['diagnostic_tool_call']['wire_sha256'] = legacy.digest(build_wire(self.business))
            usage = current['usage']
            if usage is not None:
                if self.usage is None:
                    self.usage = usage
                    try:
                        self.on_usage(usage)
                    except Exception:
                        self.reject('usage_write_failed')
                elif usage != self.usage:
                    self.usage_conflict = True
                    self.reject('usage_conflict')
            self.result = current
        if self.terminal is not None:
            self.reject('event_after_terminal')
            return
        # Empty relay queue envelopes do not establish a model response. Their
        # count/order is not a business invariant; the real created event must
        # bind a nonempty identity before any output and the terminal must agree.
        if self._anonymous_prefix(kind, response, seq):
            return
        # A second empty created envelope before *any* output can replace a relay
        # preamble. A changed identity after output starts never enters this branch.
        restart = (not self.anonymous_bound and kind == 'response.created' and self.created == 1 and not self.items
                   and response.get('output') == [] and response.get('usage') is None
                   and response.get('error') is None and response.get('incomplete_details') is None)
        if type(seq) is not int or seq < 0 or (seq <= self.raw_sequence and not restart):
            self.reject('event_sequence')
        elif self.raw_sequence >= 0 and seq > self.raw_sequence+1:
            self.compatibility['sequence_gap'] += 1
        if type(seq) is int:
            self.raw_sequence = seq
        try:
            if lifecycle:
                self._lifecycle(kind, response, restart)
                return
            # Reuse the item/call state machine, with a private contiguous counter.
            # Raw sequence values and all compatibility decisions remain separate.
            adapted = dict(event, sequence_number=self.sequence+1)
            if kind == 'response.function_call_arguments.done' and 'name' not in event:
                row = self._item(event, event.get('item_id'))
                if row['type'] != 'function_call' or row.get('name') != legacy.TOOL:
                    raise legacy.TransportError('tool_name_binding')
                adapted['name'] = row['name']
                self.compatibility['done_name_from_bound_item'] += 1
            super().feed(adapted)
        except (KeyError, TypeError, AttributeError):
            self.reject('event_shape')
        except legacy.TransportError as error:
            self.reject(str(error))

    def _anonymous_prefix(self, kind, response, seq):
        if kind in ('response.created', 'response.queued', 'response.in_progress') and response.get('id') in (None, ''):
            if (self.response_id is not None or self.created or self.items or self.anonymous_bound
                    or response.get('status') not in ('queued', 'in_progress') or not empty_envelope(response)
                    or seq is not None and (type(seq) is not int or seq < 0)
                    or self.anonymous_preamble >= MAX_EMPTY_PREAMBLE_EVENTS):
                self.reject('anonymous_preamble_binding')
            else:
                self.anonymous_preamble += 1
            return True
        if self.anonymous_preamble and not self.anonymous_bound and kind == 'response.created':
            try:
                legacy.safe_id(response.get('id'))
            except legacy.TransportError:
                self.reject('anonymous_preamble_binding')
                return False
            if (not self.created and not self.items and empty_envelope(response)
                    and response.get('status') in ('queued', 'in_progress') and not self.errors):
                self.anonymous_bound = True
                self.compatibility['anonymous_preamble_bound'] += 1
        return False

    @staticmethod
    def _metadata_keepalive(event):
        kind = event.get('type')
        if not isinstance(kind, str) or kind not in KEEPALIVE_TYPES or set(event) - {'type', 'sequence_number', 'timestamp'}:
            return False
        sequence, stamp = event.get('sequence_number'), event.get('timestamp')
        return ((sequence is None or type(sequence) is int and sequence >= 0)
                and (stamp is None or type(stamp) is int or type(stamp) is float and math.isfinite(stamp)
                     or isinstance(stamp, str) and len(stamp) <= 64))

    def _lifecycle(self, kind, response, restart):
        terminal = kind in ('response.completed', 'response.incomplete', 'response.failed')
        if response.get('model') not in (None, legacy.MODEL):
            self.reject('model_identity')
        if codec.reasoning_echo(response) in ('conflict', 'malformed'):
            self.reject('reasoning_identity')
        if response.get('max_output_tokens') not in (None, codec.MAX_OUTPUT):
            self.reject('output_limit_identity')
        identity = legacy.safe_id(response.get('id'))
        if kind == 'response.created':
            self.created += 1
            if response.get('output') != [] or response.get('usage') is not None:
                self.reject('created_not_empty')
            if self.created > 1 and not restart:
                self.reject('duplicate_response')
            elif restart:
                self.compatibility['empty_created_replacement'] += 1
            self.response_id = identity if self.created == 1 or restart else self.response_id
        elif identity != self.response_id:
            self.reject('response_identity')
        if not terminal:
            if response.get('output') or response.get('usage') is not None or response.get('error') is not None:
                self.reject('lifecycle_not_empty')
            if response.get('status') not in ('queued', 'in_progress') or response.get('incomplete_details') is not None:
                self.reject('lifecycle_status')
            return
        self.terminal = kind
        if response.get('status') != kind.removeprefix('response.'):
            self.reject('terminal_status')
        if self.result['ok'] is not True:
            self.reject(self.result['code'])
        output = response.get('output')
        if not isinstance(output, list) or len(output) != len(self.items):
            self.reject('terminal_inventory')
            return
        for index, item in enumerate(output):
            row = self._item(dict(output_index=index), item.get('id'))
            if not row['done'] or row['type'] != item.get('type'):
                self.reject('terminal_inventory')
            if row['type'] == 'function_call':
                self._match_call(row, item)

    def finish(self):
        if self.anonymous_preamble and not self.anonymous_bound:
            self.reject('anonymous_preamble_unbound')
        if self.terminal is None:
            self.reject('terminal_missing')
        result = dict(self.result, usage=self.usage, usage_conflict=self.usage_conflict,
                      stream_protocol=self.protocol())
        if self.errors:
            result.update(ok=False, code=self.errors[0], public_tool_call=None)
        return result


def collect(business, *, profile, api_key, observation_dir, timeout_s=300,
            on_usage=lambda value: None, transport=None):
    wire = build_wire(business)
    if not isinstance(profile, legacy.Profile) or profile.route != 'proxy-12000':
        raise legacy.TransportError('stream_explicit_proxy_required')
    if not isinstance(api_key, str) or not api_key:
        raise legacy.TransportError('explicit_credential_required')
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 300:
        raise legacy.TransportError('timeout_invalid')
    observer = StreamObservation(observation_dir)
    decoder = Decoder(business, on_usage)
    client = response = None
    error_code = failure_category = None
    def received(value):
        observer.on_response(value)
        if value.status_code == 200:
            value.stream = legacy.TailCheckedStream(value.stream)
    try:
        client = OpenAI(api_key=api_key, base_url=profile.base_url, max_retries=0,
            admin_api_key='', organization='', project='', webhook_secret='',
            http_client=httpx.Client(timeout=timeout_s, trust_env=False, follow_redirects=False,
                transport=transport if transport is not None else httpx.HTTPTransport(proxy=legacy.PROXY_12000, retries=0),
                event_hooks=dict(request=[observer.on_request], response=[received])))
        response = client.responses.create(**wire)
        for event in response:
            decoder.feed(event.model_dump(mode='json', exclude_unset=True))
            observer.update(stream_protocol=decoder.protocol())
            if decoder.result['response_observation']['response_received']:
                observer.update(response_contract=decoder.result['response_observation'])
    except Exception as error:
        status = getattr(error, 'status_code', None)
        error_code = f'http_status_{status}' if type(status) is int and 100 <= status <= 599 else 'request_failed'
        failure_category = legacy.classify_exception(error)
        observer.mark_failure(failure_category)
    finally:
        for resource in (response, client):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    error_code = error_code or 'close_failed'
        observer.close()
    result = decoder.finish()
    result['failure_category'] = failure_category
    if error_code:
        result.update(ok=False, code=error_code)
    if result['ok'] and (observer.failure or observer.values['http_requests'] != 1
            or observer.values['response_status'] != 200 or not observer.values['eof']
            or not observer.values['closed'] or observer.values['exception_type'] is not None):
        result.update(ok=False, code='observation_invalid')
    for key in ('public_tool_call', 'diagnostic_tool_call'):
        value = result.get(key)
        if value is not None and codec.contains_credential(value, api_key):
            result.update(ok=False, code='credential_echo', public_tool_call=None, diagnostic_tool_call=None)
    if not result['ok']:
        result['public_tool_call'] = None
    return result
