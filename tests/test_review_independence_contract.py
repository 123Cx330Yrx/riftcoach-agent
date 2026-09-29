"""Deterministic checks for the v2 host-event boundary.

These tests validate bindings and fail-closed behavior only. They do not claim
that an in-process fixture is an independent reviewer; the production adapter
must supply the event from the collaboration host.
"""

from copy import deepcopy
import hashlib

import pytest

from scripts.review_independence_contract import (
    EVENT_KIND,
    VERSION,
    canonical_json,
    review_digest,
    validate_independent_event,
    validate_primary_attestation,
)


def _binding():
    return {
        'plan_sha256': 'a' * 64,
        'key': 'claim-scope:4',
        'stage': 'final',
        'response_sha256': 'b' * 64,
        'report_sha256': 'c' * 64,
        'request_sha256': 'd' * 64,
    }


def _plan():
    return {
        'root_thread_id': 'root-thread-1',
        'review_event_provider': 'codex-collaboration-host-v1',
        'review_principals': {
            'primary': {'principal_id': 'root-principal'},
            'independent': {'principal_id': 'child-principal'},
        },
    }


def _primary(bound, plan):
    review = {'accepted': True, 'defects': [], 'source_review': 'primary'}
    review['primary_attestation'] = {
        'version': VERSION, 'role': 'primary', 'principal_id': 'root-principal',
        'binding': deepcopy(bound), 'review_sha256': review_digest(review),
        'source_kind': 'local-primary-decision-v1',
    }
    return review


def _independent(bound, plan):
    review = {'accepted': True, 'defects': [], 'source_review': 'independent'}
    event = {
        'schema_version': VERSION, 'event_kind': EVENT_KIND, 'state': 'completed',
        'event_id': 'event-1', 'dispatch_id': 'dispatch-1',
        'author_principal_id': 'child-principal', 'root_thread_id': 'root-thread-1',
        'binding': deepcopy(bound), 'review_sha256': review_digest(review),
        'raw_event_sha256': hashlib.sha256(b'host-event-bytes').hexdigest(),
        'review': deepcopy(review),
    }
    review['independent_source_event'] = event
    return review, event


def test_primary_is_bound_to_frozen_root_and_exact_body():
    bound, plan = _binding(), _plan()
    validate_primary_attestation(_primary(bound, plan), plan=plan, bound=bound)


def test_independent_requires_host_fetched_event_and_exact_content():
    bound, plan = _binding(), _plan()
    review, event = _independent(bound, plan)
    validate_independent_event(review, plan=plan, bound=bound, event=event)
    with pytest.raises(ValueError, match='trusted_event_fetch_required'):
        validate_independent_event(review, plan=plan, bound=bound)


@pytest.mark.parametrize('mutation, error', [
    (lambda e: e.update(author_principal_id='root-principal'), 'independent_event_binding'),
    (lambda e: e['binding'].update(stage='initial'), 'independent_event_binding'),
    (lambda e: e['review'].update(accepted=False), 'independent_review_content_mismatch'),
    (lambda e: e.update(state='pending'), 'independent_event_binding'),
])
def test_independent_event_rejects_identity_binding_and_content_tampering(mutation, error):
    bound, plan = _binding(), _plan()
    review, event = _independent(bound, plan)
    mutation(event)
    with pytest.raises(ValueError, match=error):
        validate_independent_event(review, plan=plan, bound=bound, event=event)


def test_same_principal_registry_is_rejected():
    bound = _binding()
    plan = _plan()
    plan['review_principals']['independent']['principal_id'] = 'root-principal'
    with pytest.raises(ValueError, match='principal_roles_not_independent'):
        validate_primary_attestation(_primary(bound, plan), plan=plan, bound=bound)
