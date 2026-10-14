"""Temperature-only review identity and isolated bounded GLM worker."""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as legacy_bridge

VERSION = 'document-review-sampling-temperature-02-v1'
MARKER = 'document_review_sampling'
TRANSPORT = 'golden-glm53-document-sampling-screening-time600-high-32768-v1'
BASELINE = 'baseline'
CANDIDATE = 'temperature-02'
VARIANTS = (BASELINE, CANDIDATE)


def prepare_request(request, variant):
    if variant not in VARIANTS or MARKER in request.metadata:
        raise ValueError('sampling_request_variant')
    if timing.role_for_request(request) != 'review':
        raise ValueError('sampling_request_role')
    if request.temperature != 1.0 or request.top_p != .95 or request.max_tokens != 32768:
        raise ValueError('sampling_request_controls')
    value = replace(request, temperature=1.0 if variant == BASELINE else .2,
        metadata={**request.metadata, MARKER: {'version': VERSION, 'variant': variant}})
    request_bytes(value)
    return value


def projection(request):
    marker = request.metadata.get(MARKER)
    if (not isinstance(marker, dict) or set(marker) != {'version', 'variant'}
            or marker.get('version') != VERSION or marker.get('variant') not in VARIANTS):
        raise ValueError('sampling_request_marker')
    expected = 1.0 if marker['variant'] == BASELINE else .2
    if request.temperature != expected:
        raise ValueError('sampling_temperature')
    metadata = dict(request.metadata)
    del metadata[MARKER]
    value = replace(request, temperature=1.0, metadata=metadata)
    if timing.role_for_request(value) != 'review':
        raise ValueError('sampling_request_role')
    return value


def request_bytes(request, *, transport_id=TRANSPORT):
    if transport_id != TRANSPORT:
        raise ValueError('sampling_transport_identity')
    legacy_bridge.validate_request(projection(request),
        transport_id=legacy_bridge.TIMED_REVIEW_TRANSPORT_ID)
    raw = json.dumps(request, default=legacy_bridge._mapping, ensure_ascii=False,
                     allow_nan=False).encode('utf-8')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if len(raw) > legacy_bridge.MAX_BYTES or estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('sampling_request_size')
    return raw


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


def isolated_bridge():
    name = 'scripts._sampling_process_bridge'
    spec = importlib.util.spec_from_file_location(name, legacy_bridge.__file__)
    bridge = importlib.util.module_from_spec(spec)
    sys.modules[name] = bridge
    spec.loader.exec_module(bridge)
    old = bridge.TIMED_REVIEW_TRANSPORT_ID
    for field in ('TRANSPORTS', 'REVIEW_TRANSPORTS', 'TIMED_TRANSPORTS'):
        setattr(bridge, field, tuple(TRANSPORT if x == old else x for x in getattr(bridge, field)))
    bridge.TIMED_REVIEW_TRANSPORT_ID = TRANSPORT
    bridge.validate_request = request_bytes
    child = bridge.run_child

    def run_child(command, raw, **kwargs):
        command = list(command)
        index = command.index('-m') + 1
        if command[index] != 'app.evaluation.golden_stream_bridge':
            raise ValueError('sampling_worker_entrypoint')
        command[index] = 'scripts.document_sampling_screening_request'
        return child(command, raw, **kwargs)

    bridge.run_child = run_child
    return bridge


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', required=True, type=Path)
    parser.add_argument('--started', required=True, type=float)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('--transport-id', required=True, choices=(TRANSPORT,))
    parser.add_argument('--buffered-tools', action='store_true')
    args = parser.parse_args()
    bridge = isolated_bridge()
    try:
        bridge.worker(args.worker, args.started, args.deadline, args.transport_id,
                      stream_tool_arguments=not args.buffered_tools)
    except BaseException as error:
        bridge.write_new_json(args.worker / 'failure.json', {
            'category': 'assembly_rejected' if isinstance(error, bridge.StreamAdapterError) else 'worker_failed',
            'assembly_code': error.code if isinstance(error, bridge.StreamAdapterError) else None,
            'provider_code': error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None})
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
