"""Explicit development-only full/facts identity; never a production review."""
from dataclasses import replace
import hashlib
import json

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as legacy
from scripts.prepare_review_duty_probe import REPLACEMENTS, VERSION as OFFLINE_VERSION

VERSION = 'document-review-duty-observed-v1'
TRANSPORT = 'golden-glm53-review-duty-observed-time600-high-32768-v1'
MARKER = 'document_review_duty_comparison'
BASELINE, CANDIDATE = 'full', 'facts'
VARIANTS = (BASELINE, CANDIDATE)


def prepare_request(request, variant):
    if variant not in VARIANTS or MARKER in request.metadata:
        raise ValueError('duty_variant')
    result = replace(request, metadata={**request.metadata,
        MARKER: dict(version=VERSION, variant=variant)})
    request_bytes(result)
    return result


def projection(request):
    marker = request.metadata.get(MARKER)
    if (not isinstance(marker, dict) or set(marker) != {'version', 'variant'}
            or marker['version'] != VERSION or marker['variant'] not in VARIANTS):
        raise ValueError('duty_marker')
    metadata = dict(request.metadata)
    del metadata[MARKER]
    policy = request.messages[0].content
    if marker['variant'] == CANDIDATE:
        if metadata.pop('offline_review_duty', None) != OFFLINE_VERSION:
            raise ValueError('duty_offline_marker')
        for before, after in REPLACEMENTS:
            if policy.count(after) != 1 or before in policy:
                raise ValueError('duty_policy')
            policy = policy.replace(after, before)
    elif 'offline_review_duty' in metadata:
        raise ValueError('duty_full_partial_scope')
    result = replace(request, metadata=metadata,
        messages=(replace(request.messages[0], content=policy), *request.messages[1:]))
    if timing.role_for_request(result) != 'review':
        raise ValueError('duty_review_only')
    return result


def request_bytes(request, *, transport_id=TRANSPORT):
    if transport_id != TRANSPORT:
        raise ValueError('duty_transport')
    legacy.validate_request(projection(request), transport_id=legacy.TIMED_REVIEW_TRANSPORT_ID)
    raw = json.dumps(request, default=legacy._mapping, ensure_ascii=False,
                     allow_nan=False).encode('utf-8')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if len(raw) > legacy.MAX_BYTES or estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('duty_request_size')
    return raw


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()
