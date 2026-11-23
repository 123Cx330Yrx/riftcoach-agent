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
from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Mapping, Protocol

VERSION = 'independent-source-v2'
EVENT_KIND = 'codex-collaboration-review-event-v1'
MODE_V2 = 'independent-drafts-v2'
EVIDENCE_POLICY_FIELD = 'host_review_evidence_policy'
DISPATCH_POLICY = 'dispatch-and-final-v1'
FINAL_POLICY = 'native-final-attestation-v1'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


class HostReviewEventSource(Protocol):
    """Trusted host boundary; implementations must fetch platform events."""

    def fetch(self, *, event_id: str, binding: Mapping[str, object]) -> Mapping[str, object]:
        """Return the immutable completed event for this exact binding."""
        ...


_qualification_event_source: ContextVar[HostReviewEventSource | None] = ContextVar(
    'qualification_event_source', default=None)


@contextmanager
def using_host_event_source(event_source: HostReviewEventSource | None):
    """Scope a host dependency across the frozen legacy qualification API.

    That API re-enters inspect_runs without dependency arguments. A task-local
    scope preserves its versioned code/identity and mandatory full replay; it
    never grants acceptance or substitutes an event. The default stays closed.
    """
    token = _qualification_event_source.set(event_source)
    try:
        yield
    finally:
        _qualification_event_source.reset(token)


def current_host_event_source() -> HostReviewEventSource | None:
    return _qualification_event_source.get()


def _fail(code: str) -> None:
    raise ValueError('review_independence_' + code)


def evidence_policy(plan: Mapping[str, object]) -> str:
    """An explicit plan choice, never a fallback after an old proof fails."""
    policy = plan.get(EVIDENCE_POLICY_FIELD, DISPATCH_POLICY)
    if policy not in (DISPATCH_POLICY, FINAL_POLICY):
        _fail('evidence_policy_unadopted')
    return policy


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
    evidence_policy(plan)
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


def freeze_v2_identity(plan: Mapping[str, object], *, root_thread_id: str,
                       primary_id: str, independent_id: str) -> dict[str, object]:
    """Return a new plan with the complete v2 identity contract frozen.

    This is preparation only: it performs no host lookup and no Provider call.
    The caller must recompute the enclosing plan SHA after this function.
    """
    if plan.get('host_review_submission_mode') != MODE_V2:
        _fail('mode_not_v2')
    values = deepcopy(dict(plan))
    values.update(
        root_thread_id=root_thread_id,
        review_event_provider='codex-collaboration-host-v1',
        review_principals={
            'primary': {'principal_id': primary_id},
            'independent': {'principal_id': independent_id},
        },
    )
    _registry(values)
    return values


def require_execution_event_source(plan: Mapping[str, object],
                                   event_source: HostReviewEventSource | None) -> None:
    """Reject an unusable new execution before credentials or Provider IO.

    This checks wiring, not host authenticity or future availability. The
    application supplies the trusted adapter; each completed event is still
    fetched and verified at submission and read-only qualification. Historical
    v1 receipts remain readable, but cannot start another paid execution.
    """
    if plan.get('host_review_submission_mode') != MODE_V2:
        _fail('mode_not_v2')
    _registry(plan)
    if event_source is None or not callable(getattr(event_source, 'fetch', None)):
        _fail('trusted_event_fetch_required')


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


def make_primary_attestation(review: Mapping[str, object], *, plan: Mapping[str, object],
                             bound: Mapping[str, object]) -> dict[str, object]:
    """Create the root-side binding record; no independent identity is implied."""
    primary_id, _, _ = _registry(plan)
    expected = required_binding(bound)
    return {
        'version': VERSION,
        'role': 'primary',
        'principal_id': primary_id,
        'binding': expected,
        'review_sha256': review_digest(review),
        'source_kind': 'local-primary-decision-v1',
    }


def validate_independent_event(review: Mapping[str, object], *, plan: Mapping[str, object],
                               bound: Mapping[str, object], event: Mapping[str, object] | None = None,
                               event_source: HostReviewEventSource | None = None) -> None:
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
    if event is None and event_source is not None:
        event_id = envelope.get('event_id')
        if not isinstance(event_id, str) or not event_id.strip():
            _fail('independent_event_identity')
        try:
            event = event_source.fetch(event_id=event_id, binding=required_binding(bound))
        except Exception as exc:
            raise ValueError('review_independence_trusted_event_fetch_failed') from exc
    if event is None:
        _fail('trusted_event_fetch_required')
    if not isinstance(event, Mapping) or dict(event) != envelope:
        _fail('event_envelope_mismatch')
    expected = required_binding(bound)
    if event.get(EVIDENCE_POLICY_FIELD, DISPATCH_POLICY) != evidence_policy(plan):
        _fail('event_evidence_policy_mismatch')
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
