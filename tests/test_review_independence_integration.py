"""Actual v2 submission/replay path, explicitly fake host and Provider.

These fixtures do not claim real model quality or independent review.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import qualify_role_observations as audit
from scripts import review_independence_contract as contract
from scripts import role_stage_review_drafts as drafts
from tests.test_role_observation_qualification import make_run, read


class OfflineHostEvents:
    """Test double, never a production host evidence adapter."""

    def __init__(self):
        self.events = {}
        self.fetches = []

    def attach(self, review, bound):
        event_id = 'offline-event-' + str(len(self.events) + 1)
        event = dict(schema_version=contract.VERSION, event_kind=contract.EVENT_KIND,
            state='completed', event_id=event_id, dispatch_id='offline-dispatch',
            author_principal_id='offline-independent', root_thread_id='offline-root-thread',
            binding=contract.required_binding(bound), review_sha256=contract.review_digest(review),
            raw_event_sha256=hashlib.sha256(b'synthetic-host-event').hexdigest(),
            review=deepcopy(review))
        self.events[event_id] = deepcopy(event)
        return dict(review, independent_source_event=event)

    def fetch(self, *, event_id, binding):
        self.fetches.append((event_id, deepcopy(binding)))
        event = self.events[event_id]
        assert event['binding'] == binding
        return deepcopy(event)


def test_v2_continuous_three_stage_handoff_and_sealed_replay(make_run, tmp_path):
    source = OfflineHostEvents()
    run, sealed = make_run(('claim-scope:4',), profile='boundary-examples',
        host_drafts=True, host_event_source=source)
    assert read(run/'result.json')['tasks_observed']
    plan = read(run/'plan.json')['preparation_plan']
    prepared_sha = plan['cases'][0]['request_sha256']
    before = {p: audit._sha(p) for p in run.rglob('*') if p.is_file()}
    for stage in drafts.STAGES:
        path = run/'claim-scope-4'/(stage+'.json')
        bound = drafts.binding(run, 'claim-scope:4', stage, profile='boundary-examples')
        primary = read(path.with_name('primary-'+stage+'-review.json'))
        contract.validate_primary_attestation(primary, plan=plan, bound=bound)
        if stage != 'initial':
            assert bound['request_sha256'] != prepared_sha
        drafts.validate_submission(path, event_source=source)
    result = audit.inspect_runs([run], evidence_root=tmp_path,
        closed_exports=[sealed], profile='boundary-examples', event_source=source)
    assert result[4] == {'claim-scope:4'}
    assert len(source.events) == 3
    with pytest.raises(ValueError, match='trusted_event_fetch_required'):
        audit.inspect_runs([run], evidence_root=tmp_path, closed_exports=[sealed],
            profile='boundary-examples')
    source.events['offline-event-3']['author_principal_id'] = 'offline-primary'
    with pytest.raises(ValueError, match='event_envelope_mismatch'):
        audit.inspect_runs([run], evidence_root=tmp_path, closed_exports=[sealed],
            profile='boundary-examples', event_source=source)
    assert before == {p: audit._sha(p) for p in run.rglob('*') if p.is_file()}


def test_v2_full15_qualification_reenters_frozen_consumer_with_same_source(make_run, tmp_path):
    from app.evaluation import boundary_examples_qualification as backend
    plan, _ = backend.prepare_qualification()
    source = OfflineHostEvents()
    run, sealed = make_run(tuple(row['key'] for row in plan['cases']),
        profile='boundary-examples', host_drafts=True, host_event_source=source)
    result = audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'qualification',
        closed_exports=[sealed], profile='boundary-examples', event_source=source)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert not result['production_admitted'] and not result['actual_product_task_qualified']
    assert len(source.events) == 35
    assert contract.current_host_event_source() is None
    with contract.using_host_event_source(source):
        assert backend.validate_qualification(result, evidence_root=tmp_path)['accepted_inputs'] == 15
    with pytest.raises(ValueError, match='trusted_event_fetch_required'):
        backend.validate_qualification(result, evidence_root=tmp_path)


def test_native_schema_adapter_completes_actual_three_stage_consumer_path(make_run, tmp_path):
    from scripts.codex_review_event_source import CodexHostReviewEventSource, review_task

    class NativeSchemaEvents:
        primary_id = 'offline-root-thread'

        def __init__(self):
            self.turns = []
            plan = contract.freeze_v2_identity(dict(host_review_submission_mode=contract.MODE_V2),
                root_thread_id=self.primary_id, primary_id=self.primary_id, independent_id='offline-independent')
            def request(method, params):
                assert params['threadId'] == 'offline-independent'
                if method == 'thread/read':
                    return dict(thread=dict(id='offline-independent', parentThreadId=self.primary_id,
                        source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id=self.primary_id, depth=1)))))
                assert method == 'thread/turns/list'
                return dict(data=deepcopy(self.turns), nextCursor=None)
            self.source = CodexHostReviewEventSource(SimpleNamespace(request=request), plan)

        def attach(self, review, bound):
            number = len(self.turns) + 1
            turn_id, message_id = 'turn-' + str(number), 'message-' + str(number)
            self.turns.append(dict(id=turn_id, status='completed', itemsView='full', items=[
                dict(id='dispatch-' + str(number), type='userMessage', content=[dict(type='text',
                    text=review_task(bound, 'Offline independent source fixture, no real quality claim.'))]),
                dict(id=message_id, type='agentMessage', phase='final_answer',
                    text=json.dumps(dict(binding=contract.required_binding(bound), review=review))),
            ]))
            event = self.fetch(event_id='offline-independent/' + turn_id + '/' + message_id,
                binding=contract.required_binding(bound))
            return dict(review, independent_source_event=event)

        def fetch(self, **kwargs):
            return self.source.fetch(**kwargs)

    source = NativeSchemaEvents()
    run, sealed = make_run(('claim-scope:4',), profile='boundary-examples',
        host_drafts=True, host_event_source=source)
    result = audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'native-audit',
        closed_exports=[sealed], profile='boundary-examples', event_source=source)
    assert result['validated_inputs'] == 1
    assert not result['review_controls_qualified']
    assert len(source.turns) == 3
