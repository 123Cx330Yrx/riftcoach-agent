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
    MODE_V2,
    VERSION,
    canonical_json,
    freeze_v2_identity,
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


def test_event_source_fetches_by_event_id_and_exact_binding():
    bound, plan = _binding(), _plan()
    review, event = _independent(bound, plan)

    class Source:
        def fetch(self, *, event_id, binding):
            assert event_id == 'event-1'
            assert binding == bound
            return event

    validate_independent_event(review, plan=plan, bound=bound, event_source=Source())


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


@pytest.mark.parametrize('mode', [None, 'independent-drafts-v1'])
def test_freeze_v2_identity_requires_explicit_v2_mode(mode):
    plan = {} if mode is None else {'host_review_submission_mode': mode}
    with pytest.raises(ValueError, match='mode_not_v2'):
        freeze_v2_identity(plan, root_thread_id='root-thread-1',
                           primary_id='root-principal', independent_id='child-principal')


def test_freeze_v2_identity_rejects_same_principal():
    with pytest.raises(ValueError, match='principal_roles_not_independent'):
        freeze_v2_identity({'host_review_submission_mode': MODE_V2},
                           root_thread_id='root-thread-1',
                           primary_id='same-principal', independent_id='same-principal')


def test_freeze_v2_identity_returns_a_frozen_registry_copy():
    original = {
        'host_review_submission_mode': MODE_V2,
        'identity': {'workflow_id': 'correction-scope'},
        'review_principals': {'legacy': {'principal_id': 'do-not-preserve'}},
    }
    frozen = freeze_v2_identity(original, root_thread_id='root-thread-1',
                                primary_id='root-principal', independent_id='child-principal')

    assert frozen is not original
    assert frozen['host_review_submission_mode'] == MODE_V2
    assert frozen['root_thread_id'] == 'root-thread-1'
    assert frozen['review_event_provider'] == 'codex-collaboration-host-v1'
    assert frozen['review_principals'] == {
        'primary': {'principal_id': 'root-principal'},
        'independent': {'principal_id': 'child-principal'},
    }
    frozen['identity']['workflow_id'] = 'mutated-copy-only'
    assert original['identity']['workflow_id'] == 'correction-scope'
    assert 'root_thread_id' not in original
    assert 'review_event_provider' not in original


def test_host_dependency_scope_resets_after_nested_failure_and_does_not_leak():
    from contextvars import Context
    from scripts.review_independence_contract import current_host_event_source, using_host_event_source
    first, second = object(), object()
    assert current_host_event_source() is None
    with using_host_event_source(first):
        assert current_host_event_source() is first
        assert Context().run(current_host_event_source) is None
        with pytest.raises(RuntimeError):
            with using_host_event_source(second):
                assert current_host_event_source() is second
                raise RuntimeError('offline failure')
        assert current_host_event_source() is first
    assert current_host_event_source() is None
