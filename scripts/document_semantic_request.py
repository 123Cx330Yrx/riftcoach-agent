"""Prospective semantic comparison identity; no product/default admission.

The old timed identity is used only to validate the exact restored baseline.
Transport, receipts and hashes always retain the new policy and marker.
"""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as legacy_bridge
from app.evaluation.golden_role_boundary_examples import EXAMPLES
from scripts.prepare_document_semantic_options import SEQUENCE
from scripts.report_contrast_review import CONTRASTS

VERSION = 'document-semantic-comparison-request-v1'
MARKER = 'document_semantic_comparison'
TRANSPORT = 'golden-glm53-semantic-comparison-time600-high-32768-v1'
SUFFIXES = {'expanded_examples': CONTRASTS, 'short_examples': EXAMPLES,
            'decision_sequence': SEQUENCE}


def baseline(request):
    marker = request.metadata.get(MARKER)
    if (not isinstance(marker, dict) or set(marker) != {'version', 'variant'}
            or marker['version'] != VERSION or marker['variant'] not in SUFFIXES):
        raise ValueError('semantic_request_marker')
    suffix = SUFFIXES[marker['variant']]
    policy = request.messages[0].content
    if not isinstance(policy, str) or not policy.endswith(suffix) or policy.count(suffix) != 1:
        raise ValueError('semantic_request_policy')
    metadata = dict(request.metadata)
    del metadata[MARKER]
    restored = replace(request, metadata=metadata, messages=(replace(request.messages[0],
        content=policy[:-len(suffix)] + CONTRASTS), *request.messages[1:]))
    if timing.role_for_request(restored) != 'review':
        raise ValueError('semantic_request_role')
    return restored


def prepare_request(request, variant):
    if variant not in SUFFIXES or MARKER in request.metadata:
        raise ValueError('semantic_request_variant')
    if timing.role_for_request(request) != 'review':
        raise ValueError('semantic_request_role')
    policy = request.messages[0].content
    if not policy.endswith(CONTRASTS) or policy.count(CONTRASTS) != 1:
        raise ValueError('semantic_baseline_policy')
    value = replace(request, metadata={**request.metadata,
        MARKER: {'version': VERSION, 'variant': variant}}, messages=(
        replace(request.messages[0], content=policy[:-len(CONTRASTS)] + SUFFIXES[variant]),
        *request.messages[1:]))
    if baseline(value) != request:
        raise ValueError('semantic_baseline_roundtrip')
    return value


def request_bytes(request, *, transport_id=TRANSPORT):
    if transport_id != TRANSPORT:
        raise ValueError('semantic_transport_identity')
    restored = baseline(request)
    # Existing complete protocol, input/output and 600-second limits are checked
    # on the validated projection. Its bytes never become an issued receipt.
    legacy_bridge.validate_request(restored, transport_id=legacy_bridge.TIMED_REVIEW_TRANSPORT_ID)
    raw = json.dumps(request, default=legacy_bridge._mapping, ensure_ascii=False,
                     allow_nan=False).encode('utf-8')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if len(raw) > legacy_bridge.MAX_BYTES or estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('semantic_request_size')
    return raw


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


def isolated_bridge():
    """Reuse the complete process/SDK/assembly lifecycle without global patches.

    A private module owns the explicit new transport identity and validator.
    The actual subprocess loads this module too; no baseline request is sent.
    """
    name = 'scripts._semantic_process_bridge'
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
            raise ValueError('semantic_worker_entrypoint')
        command[index] = 'scripts.document_semantic_request'
        return child(command, raw, **kwargs)

    bridge.run_child = run_child
    return bridge


def main():
    # This entrypoint is IPC only. Preparation never invokes it or reads keys.
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
        bridge.worker(args.worker, args.started, args.deadline, TRANSPORT,
                      stream_tool_arguments=not args.buffered_tools)
    except BaseException as error:
        # Same bounded failure record as the existing process bridge.
        bridge.write_new_json(args.worker / 'failure.json', {
            'category': 'assembly_rejected' if isinstance(error, bridge.StreamAdapterError) else 'worker_failed',
            'assembly_code': error.code if isinstance(error, bridge.StreamAdapterError) else None,
            'provider_code': error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None})
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
