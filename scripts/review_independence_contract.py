"""Fail-closed contract for importing an actually independent review.

The old v1 handoff only compared JSON and hashes.  This module deliberately
does not invent a cryptographic identity: a root process can generate two
keys or two JSON files itself, which would reproduce the original defect.  A
v2 review must therefore carry a platform-produced collaboration event, and
the caller must obtain that event through a trusted host adapter.  The local
validator checks the event's complete binding and exact review digest; it does
not claim that an arbitrary file is a trusted platform event.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping

VERSION = 'independent-source-v2'
EVENT_KIND = 'codex-collaboration-review-event-v1'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


def _fail(code: str) -> None:
    raise ValueError('review_independence_' + code)


def _hash(value: str, *, code: str = 'hash_invalid') -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        _fail(code)
    return value


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       allow_nan=False, separators=(',', ':'))).encode('utf-8')


def review_digest(review: Mapping[str, object]) -> str:
    """Hash review content, excluding only the external source envelope."""
    body = {k: v for k, v in review.items()
            if k not in ('independent_source_event', 'primary_attestation')}
    return hashlib.sha256(canonical_json(body)).hexdigest()


def required_binding(bound: Mapping[str, object]) -> dict[str, object]:
    fields = ('plan_sha256', 'key', 'stage', 'response_sha256', 'report_sha256',
              'request_sha256')
    try:
        result = {field: bound[field] for field in fields}
    except KeyError as exc:
        _fail('binding_incomplete')
        raise AssertionError from exc
    for field in ('plan_sha256', 'response_sha256', 'report_sha256', 'request_sha256'):
        _hash(result[field], code='binding_hash_invalid')
    if not isinstance(result['key'], str) or not result['key']:
        _fail('binding_key_invalid')
    if result['stage'] not in ('initial', 'revision', 'final'):
        _fail('binding_stage_invalid')
    return result


def _registry(plan: Mapping[str, object]) -> tuple[str, str, str]:
    values = plan.get('review_principals')
    if not isinstance(values, dict):
        _fail('principal_registry_missing')
    primary = values.get('primary')
    independent = values.get('independent')
    if not isinstance(primary, dict) or not isinstance(independent, dict):
        _fail('principal_registry_incomplete')
    primary_id, independent_id = primary.get('principal_id'), independent.get('principal_id')
    root_thread = plan.get('root_thread_id')
    if not all(isinstance(value, str) and value.strip()
               for value in (primary_id, independent_id, root_thread)):
        _fail('principal_registry_incomplete')
    if primary_id == independent_id:
        _fail('principal_roles_not_independent')
    if plan.get('review_event_provider') != 'codex-collaboration-host-v1':
        _fail('event_provider_unadopted')
    return primary_id, independent_id, root_thread


def validate_primary_attestation(review: Mapping[str, object], *, plan: Mapping[str, object],
                                 bound: Mapping[str, object]) -> None:
    """Validate the root decision's declared identity and signed body boundary.

    The primary is the root execution principal, so its provenance is the
    frozen plan identity.  It is still bound to the exact body to prevent a
    later writer from changing the decision after the identity check.
    """
    primary_id, _, _ = _registry(plan)
    attestation = review.get('primary_attestation')
    if not isinstance(attestation, dict):
        _fail('primary_attestation_missing')
    if (attestation.get('version') != VERSION or attestation.get('role') != 'primary'
            or attestation.get('principal_id') != primary_id):
        _fail('primary_identity_mismatch')
    expected = required_binding(bound)
    if attestation.get('binding') != expected:
        _fail('primary_binding_mismatch')
    if attestation.get('review_sha256') != review_digest(review):
        _fail('primary_review_mismatch')
    if attestation.get('source_kind') != 'local-primary-decision-v1':
        _fail('primary_source_kind')


def validate_independent_event(review: Mapping[str, object], *, plan: Mapping[str, object],
                               bound: Mapping[str, object], event: Mapping[str, object] | None = None) -> None:
    """Validate a host-fetched independent event and exact review content.

    ``event`` must come from the host collaboration adapter.  Passing a JSON
    object read from the run directory is intentionally unsupported by the
    production handoff; tests may inject a host-fetched object to exercise the
    deterministic binding checks.
    """
    _, independent_id, root_thread = _registry(plan)
    envelope = review.get('independent_source_event')
    if not isinstance(envelope, dict):
        _fail('independent_event_missing')
    if event is None:
        _fail('trusted_event_fetch_required')
    if not isinstance(event, Mapping) or dict(event) != envelope:
        _fail('event_envelope_mismatch')
    expected = required_binding(bound)
    if (event.get('schema_version') != VERSION or event.get('event_kind') != EVENT_KIND
            or event.get('state') != 'completed'
            or event.get('author_principal_id') != independent_id
            or event.get('root_thread_id') != root_thread
            or event.get('binding') != expected
            or event.get('review_sha256') != review_digest(review)):
        _fail('independent_event_binding')
    for field in ('event_id', 'dispatch_id', 'author_principal_id', 'root_thread_id'):
        if not isinstance(event.get(field), str) or not event[field].strip():
            _fail('independent_event_identity')
    _hash(event.get('raw_event_sha256'), code='independent_event_raw_hash')
    if event.get('review') != {k: v for k, v in review.items() if k != 'independent_source_event'}:
        _fail('independent_review_content_mismatch')


def load_host_event(path: str | Path) -> dict[str, object]:
    """Load only through a future host adapter boundary, never as a run file."""
    _fail('trusted_event_adapter_unavailable')
    raise AssertionError(path)
