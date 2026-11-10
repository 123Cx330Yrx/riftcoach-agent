"""Teaching-only comparison identity over the existing 600-second GLM worker."""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as legacy_bridge
from scripts.report_relation_contrast import OLD, NEW

VERSION = 'document-relation-teaching-comparison-v1'
MARKER = 'document_relation_comparison'
TRANSPORT = 'golden-glm53-document-relation-time600-high-32768-v1'
BASELINE, CANDIDATE = 'baseline', 'relation-contrast'
VARIANTS = (BASELINE, CANDIDATE)


def prepare_request(request, variant):
    if variant not in VARIANTS or MARKER in request.metadata:
        raise ValueError('relation_variant')
    if timing.role_for_request(request) != 'review':
        raise ValueError('relation_review_only')
    policy = request.messages[0].content
    if policy.count(OLD) != 1:
        raise ValueError('relation_parent_policy')
    value = replace(request, metadata={**request.metadata, MARKER: {'version': VERSION, 'variant': variant}},
        messages=(replace(request.messages[0], content=policy.replace(OLD, NEW)
            if variant == CANDIDATE else policy), *request.messages[1:]))
    request_bytes(value)
    return value


def projection(request):
    marker = request.metadata.get(MARKER)
    if (not isinstance(marker, dict) or set(marker) != {'version', 'variant'}
            or marker.get('version') != VERSION or marker.get('variant') not in VARIANTS):
        raise ValueError('relation_marker')
    policy = request.messages[0].content
    if marker['variant'] == CANDIDATE:
        if policy.count(NEW) != 1:
            raise ValueError('relation_policy')
        policy = policy.replace(NEW, OLD)
    metadata = dict(request.metadata)
    del metadata[MARKER]
    result = replace(request, metadata=metadata,
        messages=(replace(request.messages[0], content=policy), *request.messages[1:]))
    if timing.role_for_request(result) != 'review':
        raise ValueError('relation_review_only')
    return result


def request_bytes(request, *, transport_id=TRANSPORT):
    if transport_id != TRANSPORT:
        raise ValueError('relation_transport')
    legacy_bridge.validate_request(projection(request), transport_id=legacy_bridge.TIMED_REVIEW_TRANSPORT_ID)
    raw = json.dumps(request, default=legacy_bridge._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
    if len(raw) > legacy_bridge.MAX_BYTES or size(request) > 64000:
        raise ValueError('relation_request_size')
    return raw


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


def isolated_bridge():
    name = 'scripts._relation_process_bridge'
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
            raise ValueError('relation_worker_entrypoint')
        command[index] = 'scripts.document_relation_request'
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
        bridge.write_new_json(args.worker / 'failure.json', dict(
            category='assembly_rejected' if isinstance(error, bridge.StreamAdapterError) else 'worker_failed',
            assembly_code=error.code if isinstance(error, bridge.StreamAdapterError) else None,
            provider_code=error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
