"""One receipted semantic comparison call; reuse the owned process bridge.

No role router, editor, retry or default admission is added. A complete
transport response is retained even when the downstream review rejects it.
"""
from pathlib import Path

from scripts import document_semantic_request as identity
from scripts.prepare_document_semantic_comparison import sha
from app.evaluation.golden_stream_bridge import RESPONSE, TimedReviewBridgeObservation
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_inference_scope_v5 import strict_json


def read(path):
    return strict_json(Path(path).read_text(encoding='utf-8'))


def validate_complete(directory, request, response):
    directory = Path(directory)
    raw = identity.request_bytes(request)
    if (directory.joinpath('issued-request.json').read_bytes() != raw
            or directory.joinpath('raw-response.json').read_bytes() != RESPONSE.dump_json(response)):
        raise ValueError('semantic_transport_exchange_changed')
    _, terminal, progress = validate_partial(directory, request)
    if (terminal is None or progress is None
            or terminal['state'] != 'complete' or type(terminal['elapsed_ms']) is not int
            or not 0 <= terminal['elapsed_ms'] <= 600000
            or progress['state'] != 'complete' or progress['close_state'] != 'closed'
            or progress['http_requests'] != 1 or progress['error'] is not None
            or progress['input_tokens'] != response.usage.input_tokens
            or progress['output_tokens'] != response.usage.output_tokens
            or response.provider != 'zhipu' or response.model != 'glm-5.3'
            or response.usage.input_tokens > 64000 or response.usage.output_tokens > 32768):
        raise ValueError('semantic_transport_receipt_invalid')
    return dict(transport_id=identity.TRANSPORT, state='complete',
        request_sha256=sha(raw), response_sha256=sha(RESPONSE.dump_json(response)),
        reservation_sha256=sha((directory/'stream-001/reservation.json').read_bytes()),
        terminal_sha256=sha((directory/'stream-001/result.json').read_bytes()),
        progress_sha256=sha((directory/'stream-001/progress.json').read_bytes()),
        input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)


def validate_partial(directory, request):
    """Validate incomplete evidence too, without treating it as an Exchange."""
    directory = Path(directory)
    raw = identity.request_bytes(request)
    if (directory/'issued-request.json').read_bytes() != raw:
        raise ValueError('semantic_partial_request_changed')
    stream = directory/'stream-001'
    bridge = identity.isolated_bridge()
    expected = dict(transport_id=identity.TRANSPORT, ordinal=1,
        request_sha256=sha(raw), stream_tool_arguments=True, state='reserved_before_io',
        request_metrics=bridge.request_metrics(request,raw), model='glm-5.3',
        thinking_profile_id=bridge.transport_profile(identity.TRANSPORT).profile_id)
    reservation = read(stream/'reservation.json') if (stream/'reservation.json').exists() else None
    terminal = read(stream/'result.json') if (stream/'result.json').exists() else None
    progress = read(stream/'progress.json') if (stream/'progress.json').exists() else None
    if reservation is not None and reservation != expected:
        raise ValueError('semantic_partial_reservation_invalid')
    if terminal is not None:
        if (reservation is None or set(terminal) != {'transport_id','state','elapsed_ms','body_free'}
                or terminal['transport_id'] != identity.TRANSPORT or terminal['body_free'] is not True
                or terminal['state'] not in ('complete','failed','deadline','interrupted','unreaped','cleanup_failed')
                or type(terminal['elapsed_ms']) is not int or terminal['elapsed_ms'] < 0):
            raise ValueError('semantic_partial_terminal_invalid')
    if progress is not None:
        if reservation is None:
            raise ValueError('semantic_partial_progress_without_reservation')
        TimedReviewBridgeObservation.model_validate(progress,strict=True)
        if set(progress) != set(TimedReviewBridgeObservation.model_fields):
            raise ValueError('semantic_partial_progress_fields')
    if terminal and terminal['state'] == 'complete' and (progress is None
            or progress['state'] != 'complete' or progress['close_state'] != 'closed'
            or progress['http_requests'] != 1 or progress['error'] is not None):
        raise ValueError('semantic_partial_complete_state')
    if (stream/'failure.json').exists():
        failure=read(stream/'failure.json')
        from app.providers.stream_adapter_contract import StreamAdapterError
        if (terminal and terminal['state'] == 'complete'
                or (directory/'raw-response.json').exists()
                or set(failure) != {'category','assembly_code','provider_code'}
                or failure['category'] not in ('assembly_rejected','worker_failed')
                or (failure['category'] == 'assembly_rejected') != (failure['assembly_code'] is not None)
                or (failure['assembly_code'] is not None and failure['provider_code'] is not None)
                or failure['provider_code'] not in (None,*bridge.SAFE_PROVIDER_FAILURE_CODES)):
            raise ValueError('semantic_worker_failure_fields')
        if failure['assembly_code'] is not None:
            StreamAdapterError(failure['assembly_code'])
    if (directory/'raw-response.json').exists():
        response=RESPONSE.validate_json((directory/'raw-response.json').read_bytes())
        if (reservation is None or terminal is None or terminal['state'] != 'complete'
                or progress is None or progress['state'] != 'complete'
                or progress['close_state'] != 'closed' or progress['http_requests'] != 1
                or response.provider != 'zhipu' or response.model != 'glm-5.3'
                or response.usage.input_tokens > 64000 or response.usage.output_tokens > 32768
                or progress['input_tokens'] != response.usage.input_tokens
                or progress['output_tokens'] != response.usage.output_tokens):
            raise ValueError('semantic_partial_response_invalid')
    return reservation,terminal,progress


class SemanticProvider:
    def __init__(self, settings, *, bridge=None):
        self.settings = settings
        self.bridge = bridge or identity.isolated_bridge()

    def chat(self, request, directory):
        raw = identity.request_bytes(request)
        directory = Path(directory)
        # A cell can never be bought twice, even after a recording failure.
        directory.mkdir(parents=True, exist_ok=False)
        with (directory/'issued-request.json').open('xb') as stream:
            stream.write(raw)
        provider = self.bridge.GoldenProcessStreamProvider(settings=self.settings,
            directory=directory, transport_id=identity.TRANSPORT)
        response = provider.chat(request)
        with (directory/'raw-response.json').open('xb') as stream:
            stream.write(RESPONSE.dump_json(response))
        receipt = validate_complete(directory, request, response)
        write_new_json(directory/'receipt.json', receipt)
        return response


def usage(directory):
    """Derive attempted, actually observed HTTP sends and partial known usage.

    A missing usage tail stays unknown; a reservation is not a paid-send claim.
    A complete response without the wrapper receipt is retained as receiptless.
    """
    directory = Path(directory)
    paths = list(directory.glob('*/transport/issued-request.json'))
    known, unknown, receiptless, sends, send_unknown = 0, 0, 0, 0, 0
    for path in paths:
        folder = path.parent
        from scripts.prepare_document_semantic_comparison import read_request
        request=read_request(path.read_bytes())
        reservation,terminal,progress=validate_partial(folder,request)
        complete = folder/'raw-response.json'
        if progress is None and reservation is not None:
            send_unknown += 1
        elif progress is not None:
            sends += progress['http_requests']
        if complete.exists():
            response = RESPONSE.validate_json(complete.read_bytes())
            known += response.usage.input_tokens + response.usage.output_tokens
        elif progress and all(type(progress.get(k)) is int for k in ('input_tokens', 'output_tokens')):
            known += progress['input_tokens'] + progress['output_tokens']
        else:
            unknown += 1
        if not (folder/'receipt.json').exists():
            receiptless += 1
    return dict(attempted_calls=len(paths), observed_http_requests=sends,
        http_send_unknown_calls=send_unknown, known_tokens=known,
        unknown_usage_calls=unknown, receiptless_calls=receiptless)
