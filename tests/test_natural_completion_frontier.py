"""Synthetic HTTP/native only; exercise a facts timeout before semantic reject."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_review_contract as candidate
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, canonical, digest, tree
from app.evaluation.sol_session_review import SessionReviewGate
from scripts import prepare_natural_completion_frontier as preparation
from scripts import natural_completion_continuation as continuation
from scripts.prepare_completion_continuation import preview_prefix
from scripts.host_review_workspace import HostReviewWorkspace
from tests.test_sol_session_review import controls, author
from tests.test_sol_natural_session import app_for, NoSearch
from tests.test_natural_duty_candidate import run


@pytest.fixture
def parent(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('unexpected network')
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket.socket, 'connect', deny)
    opened, turns, _ = controls(tmp_path/'native')
    _, template = opened()
    root = tmp_path/'parent'
    workspace = HostReviewWorkspace(cwd=Path.cwd(), python=sys.executable,
        answers=tmp_path/'parent-authors', evidence_roots=[root])
    def session(previous=None, **kwargs):
        value = CandidateSession(root/'execution/session',
            binding=dict(fixture_only=True, candidate_contract=candidate.VERSION,
                review_plan_sha256=digest(canonical(template.plan))),
            transport_root=root/'execution/transport/candidate', journal_root=root/'execution/journal',
            guard_sha=previous.guard_sha if previous else None,
            checkpoint_sha=previous.checkpoint_sha if previous else None,
            before_new_model=lambda: None, contract_module=candidate, **kwargs)
        gate = SessionReviewGate(value, plan=template.plan, workspace=workspace,
                                 event_source=template.native.event_source)
        return value, gate
    previous = None
    for segment in range(3):
        current, gate = session(previous, manual_retry=segment == 1)
        with pytest.raises(SessionPaused), current:
            app, _, _ = app_for(root/'execution', current, segment,
                statuses=(524,) if segment == 0 else (), candidate=candidate,
                knowledge=None if segment == 0 else NoSearch())
            run(app)
        previous = current
        if segment == 0:
            continue
        current, gate = session(previous)
        with current:
            handle = list(gate.handles())[-1]
            primary, event = author(handle, turns, workspace, accepted=segment == 1)
            assert gate.submit(handle['binding']['key'], primary, event) is (segment == 1)
        previous = current
    (root/'plan.json').write_bytes(canonical(dict(run_id='candidate', review_plan=template.plan,
        python=str(Path(sys.executable).resolve()), cwd=str(Path.cwd()))))
    return root, workspace, template.native.event_source, turns


def test_timeout_prefix_replays_with_original_retry_and_all_semantic_failure_cost(parent):
    root, workspace, events, _ = parent
    spec = preparation.prefix_state(root)
    # The synthetic request selects five tools; the real parent selected three.
    assert spec['prefix_operations'] == 13
    assert spec['historical_budget']['calls'] == spec['derived_budget']['calls'] == 5
    assert spec['historical_budget']['reserved_tokens'] > 0
    assert spec['historical_budget']['retries'] == 1
    assert spec['derived_budget']['logical'] == {'generation':2, 'review':1}
    assert spec['derived_budget']['attempts'] == spec['historical_budget']['attempts']
    before = tree(root), tree(workspace.answers)
    def builder(scratch, session):
        app, factory, calls = app_for(scratch, session, 99, candidate=candidate, knowledge=NoSearch())
        try:
            run(app)
        finally:
            router = factory.providers['candidate']
            assert calls == router.generator.requests == []
            assert router.candidate_budget.snapshot() == spec['derived_budget']
    proof = preview_prefix(root, spec, candidate, workspace, events, builder=builder)
    assert proof['frontier'] == spec['frontier']
    assert proof['original_native_review_replayed']
    assert proof['provider_requests'] == proof['key_reads'] == 0
    assert before == (tree(root), tree(workspace.answers))


@pytest.mark.parametrize('fault', ['accepted_facts', 'failure_cost', 'terminal', 'changed_request'])
def test_rejection_cannot_erase_decision_cost_or_request(parent, fault):
    root, workspace, events, _ = parent
    state = preparation.prefix_state(root)
    operations = root/'execution/session/operations'
    if fault == 'changed_request':
        state = deepcopy(state)
        state['frontier_sha256'] = '0'*64
        # Application may turn the inner ValueError into a rejected runtime
        # result; the outer audit must still refuse to claim the frontier.
        with pytest.raises(ValueError, match='completion_frontier_'):
            preview_prefix(root, state, candidate, workspace, events,
                builder=lambda scratch, session: run(app_for(scratch, session, 99,
                    candidate=candidate, knowledge=NoSearch())[0]))
        return
    if fault == 'terminal':
        path = root/'execution/session/terminal.json'
        row = json.loads(path.read_bytes())
        row['key'] = 'facts-initial'
    else:
        ordinal = state['prefix_operations'] if fault == 'accepted_facts' else state['prefix_operations']+1
        path = operations/f'{ordinal:04d}-result.json'
        row = json.loads(path.read_bytes())
        if fault == 'accepted_facts':
            row['value']['accepted'] = False
        else:
            row['value']['budget']['reserved_tokens'] = 0
    path.write_bytes(canonical(row))
    with pytest.raises(ValueError, match='frontier_'):
        preparation.prefix_state(root)


@pytest.mark.parametrize('scenario', ['success', 'timeout', 'reject'])
def test_existing_runtime_consumes_only_new_tail_and_preserves_parent(parent, tmp_path, scenario):
    from scripts.reviewer_profile_batch import inventory
    root, workspace, events, turns = parent
    review_plan = json.loads((root/'plan.json').read_bytes())['review_plan']
    state = preparation.prefix_state(root)
    last = sorted((root/'execution/session/checkpoints').glob('*.json'))[-1]
    original_replay = dict(strict_replay=True,reason='semantic_rejected',
        accounting={k:state['historical_budget'][k] for k in ('calls','tokens','reserved_tokens','retries')})
    seal = dict(inventory=inventory(root), original_roots=dict(checkpoint=digest(last.read_bytes())),
                result=original_replay)
    (root/'seal.json').write_bytes(canonical(seal))
    proof = dict(version=preparation.VERSION, original_native_review_replayed=True,
        original_rejected_completion_retained=True, provider_requests=0,key_reads=0,
        parent_operator=str(root),parent_inventory=inventory(root),
        parent_author_inventory=inventory(workspace.answers),parent_seal_sha256=digest(canonical(seal)),
        original_strict_replay=original_replay,state=state,imported_operations=state['prefix_operations'],
        inherited_active_seconds=json.loads(last.read_bytes())['active_seconds'],
        **{k:state[k] for k in ('historical_budget','derived_budget','accepted_handle','frontier')})
    proof_file = tmp_path/'synthetic-proof.json'
    proof_file.write_bytes(canonical(proof))
    spec = continuation.bind(proof_file,digest(proof_file.read_bytes()))
    child, previous = tmp_path/'child', None
    answers = tmp_path/'child-authors'
    child_workspace = HostReviewWorkspace(cwd=Path.cwd(),python=sys.executable,
        answers=answers,evidence_roots=[child])
    count, stages, generator = 0, [], 0
    before = tree(root),tree(workspace.answers)
    retried = False
    for segment in range(10):
        current = CandidateSession(child/'session',
            binding=dict(fixture_only=True,candidate_contract=candidate.VERSION,
                review_plan_sha256=digest(canonical(review_plan)),continuation_sha256=digest(canonical(spec))),
            transport_root=child/'transport/candidate',journal_root=child/'journal',
            guard_sha=previous.guard_sha if previous else None,
            checkpoint_sha=previous.checkpoint_sha if previous else None,
            before_new_model=lambda:None,contract_module=candidate,continuation=spec,
            max_new_models=1,manual_retry=scenario=='timeout' and segment==1)
        gate = SessionReviewGate(current,plan=review_plan,workspace=child_workspace,event_source=events)
        continuation.attach_native(gate,spec,events)
        with current:
            try:
                app,factory,calls=app_for(child,current,segment,candidate=candidate,
                    statuses=(524,) if scenario=='timeout' and segment==0 else (),knowledge=NoSearch())
                run(app)
            except SessionPaused as error:
                if 'timeout_awaiting_manual_retry' in str(error):
                    assert not retried and not (child/'journal/application.json').exists()
                    retried=True
                    previous=current
                    count+=len(calls)
                    generator+=len(factory.providers['candidate'].generator.requests)
                    continue
                assert str(error)=='session_awaiting_native_review'
            else:
                assert scenario!='reject'
                current.close(dict(synthetic=True))
                count+=len(calls)
                generator+=len(factory.providers['candidate'].generator.requests)
                break
            count+=len(calls)
            generator+=len(factory.providers['candidate'].generator.requests)
            handle=list(gate.handles())[-1]
            key=handle['binding']['key']
            stages.append(key)
            primary,event=author(handle,turns,child_workspace,
                accepted=not(scenario=='reject' and key=='completion-initial'))
            # Real turns have unique IDs even when a new trial reuses a stage
            # key. Retain the old rejected completion's separate synthetic turn.
            turns[0]['id']=f'child-{segment}-{key}'
            event='synthetic-child/'+turns[0]['id']+'/final'
            accepted=gate.submit(key,primary,event)
            if not accepted:
                assert not (child/'journal/application.json').exists()
                break
        previous=current
    else:
        pytest.fail('new tail never completed')
    assert generator==0
    assert count==(1 if scenario=='reject' else 3+int(retried))
    assert stages==(['completion-initial'] if scenario=='reject' else
        ['completion-initial','compatibility','edit','facts-fresh','completion-fresh'])
    assert before==(tree(root),tree(workspace.answers))
    if scenario!='reject':
        assert len(list((child/'journal').glob('application.json')))==1
        applied=json.loads((child/'journal/application.json').read_bytes())
        for duty in ('facts','completion'):
            material=json.loads((child/'journal/host'/(duty+'-fresh')/'material.json').read_bytes())
            assert digest(material['report'].encode())==applied['report_sha256']
        budget=factory.providers['candidate'].candidate_budget.snapshot()
        assert budget['calls']==5+count
        assert budget['reserved_tokens']>=state['historical_budget']['reserved_tokens']
        assert budget['retries']==1+int(retried)
    # A proof file cannot replace the carried cost independently of the
    # immutable operation prefix, even if a caller pins the altered file.
    altered=deepcopy(proof)
    altered['derived_budget']['tokens']=0
    changed=tmp_path/'altered-proof.json'
    changed.write_bytes(canonical(altered))
    with pytest.raises(SessionBlocked, match='launch_completion_parent_changed'):
        continuation.bind(changed,digest(changed.read_bytes()))


def test_new_semantic_diagnostic_needs_its_own_explicit_grant(tmp_path, monkeypatch):
    from scripts import sol_natural_launch as launch
    from tests.test_sol_natural_launch import plan,grant
    p,pin=plan(tmp_path,monkeypatch,candidate=candidate)
    p['continuation']=dict(version=continuation.VERSION,seal_sha256='2'*64,
        remaining_attempts=5,max_new_tokens=401920)
    g=grant(p,pin)
    g['continuation']=dict(parent_seal_sha256='2'*64,max_new_attempts=5,
        max_new_tokens=401920,generation_requests=0)
    with pytest.raises(ValueError,match='diagnostic_specific_authorization_required'):
        launch.validate_grant(g,p,pin)
    g.update(new_logical_reviews=3,semantic_retry_not_quality_repair=True)
    launch.validate_grant(g,p,pin)
