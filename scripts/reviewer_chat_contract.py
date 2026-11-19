"""Offline relay Chat candidate: pure request/chunk mapping, no client or CLI.

This is not registered as a product provider. Callers
must supply transport EOF/close evidence; SDK iteration alone is insufficient.
Only the expected public tool may leave this module, never prose or reasoning.
"""
from copy import deepcopy
import hashlib

from jsonschema import Draft202012Validator

from app.providers.models import TokenUsage
from app.providers.stream_adapter_contract import (
    ProviderStreamAssembler, ProviderStreamEvent, StreamAdapterError, StreamToolCallDelta,
)
from scripts import reviewer_responses_nonstream as codec
from scripts import reviewer_responses_transport as responses


def build_wire(business):
    """Preserve all messages/schema; change only the endpoint representation."""
    original = codec.build_wire(business)
    tool = original['tools'][0]
    return dict(model=original['model'], messages=deepcopy(original['input']),
        tools=[dict(type='function', function={k:deepcopy(v) for k,v in tool.items() if k != 'type'})],
        tool_choice=dict(type='function', function=dict(name=responses.TOOL)),
        parallel_tool_calls=False, reasoning_effort='high',
        max_completion_tokens=codec.MAX_OUTPUT, stream=True,
        stream_options=dict(include_usage=True), store=False)


def _usage(value):
    """Keep missing breakdowns unknown; use the existing strict total check."""
    if not isinstance(value, dict):
        raise responses.TransportError('usage_invalid')
    return responses.usage_value(dict(input_tokens=value.get('prompt_tokens'),
        output_tokens=value.get('completion_tokens'), total_tokens=value.get('total_tokens'),
        input_tokens_details=value.get('prompt_tokens_details'),
        output_tokens_details=value.get('completion_tokens_details')))


def _event(chunk, ordinal, usage):
    if chunk.get('object') != 'chat.completion.chunk':
        raise StreamAdapterError('chat_chunk_shape')
    if chunk.get('error') is not None:
        raise StreamAdapterError('chat_error')
    if chunk.get('reasoning_effort') not in (None, 'high'):
        raise StreamAdapterError('reasoning_identity')
    model, identity = chunk.get('model'), chunk.get('id')
    if model is not None and model != responses.MODEL:
        raise StreamAdapterError('model_identity')
    if identity is not None:
        responses.safe_id(identity)
    choices = chunk.get('choices')
    if not isinstance(choices, list) or len(choices) > 1:
        raise StreamAdapterError('chat_choices')
    fragments, raw_parts = [], []
    finish, content_seen, reasoning_seen = None, False, False
    if choices:
        choice = choices[0]
        if not isinstance(choice, dict) or type(choice.get('index')) is not int or choice['index'] != 0:
            raise StreamAdapterError('chat_choice_index')
        delta = choice.get('delta')
        if not isinstance(delta, dict):
            raise StreamAdapterError('chat_delta_shape')
        if set(delta) - {'role', 'content', 'reasoning_content', 'tool_calls', 'refusal'}:
            raise StreamAdapterError('chat_delta_fields')
        if delta.get('role') not in (None, 'assistant'):
            raise StreamAdapterError('chat_role')
        if delta.get('refusal') is not None:
            raise StreamAdapterError('chat_refusal')
        for field in ('content', 'reasoning_content'):
            value = delta.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > 4_000_000):
                raise StreamAdapterError('chat_text_shape')
        content_seen, reasoning_seen = 'content' in delta, 'reasoning_content' in delta
        calls = delta.get('tool_calls')
        if calls is not None:
            if not isinstance(calls, list) or len(calls) > 1:
                raise StreamAdapterError('single_tool_required')
            for call in calls:
                if (not isinstance(call, dict) or type(call.get('index')) is not int
                        or call['index'] != 0 or call.get('type') not in (None, 'function')):
                    raise StreamAdapterError('chat_tool_shape')
                function = call.get('function')
                if not isinstance(function, dict):
                    raise StreamAdapterError('chat_tool_shape')
                name, arguments = function.get('name'), function.get('arguments')
                if name is not None and name != responses.TOOL:
                    raise StreamAdapterError('tool_name_binding')
                fragments.append(StreamToolCallDelta(index=0, call_id=call.get('id'),
                    name=name, arguments_delta=arguments))
                if arguments is not None:
                    raw_parts.append(arguments)
        finish = choice.get('finish_reason')
    elif usage is None:
        raise StreamAdapterError('chat_empty_chunk')
    normalized_usage = None if usage is None else TokenUsage(
        input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'],
        cached_input_tokens=usage['cached_input_tokens'] or 0)
    return ProviderStreamEvent(tool_call_deltas=tuple(fragments), finish_reason=finish,
        usage=normalized_usage, model=model, sequence=ordinal,
        request_id_sha256=hashlib.sha256(identity.encode()).hexdigest() if identity else None,
        content_observed=content_seen, reasoning_observed=reasoning_seen), raw_parts


class Decoder:
    """Incremental assembly so reported usage can survive process termination."""
    def __init__(self, business, on_usage=lambda value: None, on_usage_conflict=lambda first, other: None):
        self.wire = build_wire(business)
        self.assembler = ProviderStreamAssembler(provider_id='relay-chat-candidate',
            requested_model=responses.MODEL, max_output_tokens=codec.MAX_OUTPUT,
            require_request_identity=True, max_tool_calls=1)
        self.result = dict(ok=False, code=None, errors=[], usage=None, usage_state='unknown',
            usage_conflict=False, public_tool_call=None, business_validated=False,
            semantic_approval=False, publication_allowed=False, qualified=False,
            upstream_identity_verified=False, eof=False, closed=False,
            wire_sha256=responses.digest(self.wire), chunk_count=0)
        self.raw_parts, self.on_usage = [], on_usage
        self.on_usage_conflict = on_usage_conflict
        self.identity = None
        self.observed = dict(api='chat.completions', response_received=False,
            model_matches=None, identity_bound=False, identity_consistent=True,
            finish_reason=None, function_calls=0)

    def observation(self):
        return dict(self.observed, protocol_errors=list(self.result['errors']))

    def observe_identity(self, chunk):
        self.observed['response_received'] = True
        if chunk.get('model') is not None:
            matches = chunk['model'] == responses.MODEL
            self.observed['model_matches'] = matches and self.observed['model_matches'] is not False
        if chunk.get('id') is not None:
            try:
                responses.safe_id(chunk['id'])
                if self.identity is None:
                    self.identity = chunk['id']
                    self.observed['identity_bound'] = True
                elif chunk['id'] != self.identity:
                    self.observed['identity_consistent'] = False
            except responses.TransportError:
                self.observed['identity_consistent'] = False

    def reject(self, code):
        if code not in self.result['errors']:
            self.result['errors'].append(code)

    def feed(self, value):
        result = self.result
        result['chunk_count'] += 1
        ordinal = result['chunk_count']
        if ordinal > 131072:
            self.reject('stream_event_limit')
            return
        try:
            chunk = codec.mapping(value)
            if chunk is None:
                raise StreamAdapterError('chat_chunk_shape')
            self.observe_identity(chunk)
            reported = None
            if chunk.get('usage') is not None:
                reported = _usage(chunk['usage'])
                if result['usage'] is None:
                    result.update(usage=reported, usage_state='known')
                    try:
                        self.on_usage(reported)
                    except Exception:
                        self.reject('usage_write_failed')
                elif reported != result['usage']:
                    first_conflict = not result['usage_conflict']
                    result['usage_conflict'] = True
                    self.reject('usage_conflict')
                    if first_conflict:
                        try:
                            self.on_usage_conflict(result['usage'], reported)
                        except Exception:
                            self.reject('usage_write_failed')
            # A poisoned stream still contributes usage, never accepted content.
            if result['errors']:
                return
            event, parts = _event(chunk, ordinal, reported)
            self.assembler.accept(event)
            if event.tool_call_deltas:
                self.observed['function_calls'] = 1
            if event.finish_reason is not None:
                self.observed['finish_reason'] = event.finish_reason
            self.raw_parts.extend(parts)
        except StreamAdapterError as error:
            self.reject(error.code)
        except responses.TransportError as error:
            self.reject(str(error))  # fixed local codes, never vendor messages
        except (TypeError, ValueError, KeyError, AttributeError):
            self.reject('chat_chunk_shape')

    def finish(self, *, eof=False, closed=False):
        result = self.result
        result.update(eof=eof is True, closed=closed is True)
        if eof is not True:
            self.reject('stream_not_exhausted')
        if closed is not True:
            self.reject('stream_not_closed')
        if not result['errors']:
            try:
                self.assembler.mark_exhausted()
                response = self.assembler.finalize().response
                if response.finish_reason != 'tool_calls' or len(response.tool_calls) != 1:
                    raise StreamAdapterError('single_tool_required')
                if result['usage']['input_tokens'] > codec.MAX_INPUT:
                    raise StreamAdapterError('usage_over_budget')
                raw = ''.join(self.raw_parts)
                Draft202012Validator(self.wire['tools'][0]['function']['parameters']).validate(codec.strict_json(raw))
                result['public_tool_call'] = dict(name=responses.TOOL, arguments=raw)
            except StreamAdapterError as error:
                self.reject(error.code)
            except Exception:
                self.reject('tool_schema_invalid')
        result.update(ok=not result['errors'], code=result['errors'][0] if result['errors'] else 'ok')
        if result['usage_conflict']:
            result['usage_state'] = 'unknown'
        result['response_observation'] = self.observation()
        return result


def inspect_chunks(chunks, business, *, eof=False, closed=False):
    """Offline shape/schema inspection; callers still supply EOF/close evidence."""
    decoder = Decoder(business)
    try:
        for value in chunks:
            decoder.feed(value)
            if decoder.result['chunk_count'] > 131072:
                break
    except Exception:
        decoder.reject('stream_interrupted')
    return decoder.finish(eof=eof, closed=closed)
