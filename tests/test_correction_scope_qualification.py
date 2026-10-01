from tests.test_role_observation_qualification import legacy_qualification_fixture
"""Versioned original-15 wiring uses the real executor with network substitutes."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import correction_scope_qualification as q
from app.evaluation import coarse_role_qualification as old
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import qualify_role_observations as audit
from scripts import run_correction_scope_qualification as runner
from tests.test_role_observation_qualification import make_run, change, seal, read


def accept(run, sealed, root):
    return legacy_qualification_fixture([run], evidence_root=root, output_directory=root/'audit',
        closed_exports=[sealed], profile=q.PROFILE)


def test_new_preparation_is_fresh_original_fifteen_with_only_policy_changed():
    # The pure constructor does not inspect, reopen or rewrite the closed batch.
    plan, requests = runner.prepare_fresh()
    qualification, expected = q.prepare_qualification()
    previous, old_requests = old.prepare_qualification()
    assert plan['identity'] == qualification['identity'] != previous['identity']
    assert plan['cases'] == qualification['cases'] and requests == expected
    assert len(plan['cases']) == len(requests) == 15
    assert plan['identity']['contract']['version'] == '1.5.4'
    assert plan['allow_reassessment'] is False
    assert plan['inherited_completed_cases'] == plan['inherited_provider_calls'] == plan['offline_initial_injections'] == 0
    assert plan['batch_budget']['max_calls'] == sum(1 if r['expected_initial'] == 'accept' else 3 for r in plan['cases'])
    assert not plan['production_admitted'] and not plan['actual_product_task_qualified']
    for row in plan['cases']:
        current = REQUEST.validate_json(requests[row['key']], strict=True)
        before = REQUEST.validate_json(old_requests[row['key']], strict=True)
        assert current.messages[0].content.startswith(before.messages[0].content + '\n')
        # This intervention preserves full sources, schema, role routing and
        # decoding. Policy identity is carried by the versioned candidate.
        assert replace(current, messages=before.messages) == before
        assert current.messages[1:] == before.messages[1:]
        assert row['request_sha256'] == hashlib.sha256(requests[row['key']]).hexdigest()


def test_fresh_preview_does_not_reopen_the_registered_run(tmp_path, monkeypatch):
    closed = tmp_path / 'closed-result.json'
    closed.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', closed)
    plan, requests = runner.prepare_fresh(experiment='explicit-next-proposal')
    assert plan['experiment'] == 'explicit-next-proposal' and len(requests) == 15
    with pytest.raises(ValueError, match='qualification_closed_or_exists'):
        runner.run(NS(execute=True))
    assert closed.read_text(encoding='utf-8') == '{}'


def test_full_fifteen_use_real_continuous_executor_and_sealed_gate(make_run, tmp_path):
    plan, _ = q.prepare_qualification()
    run, sealed = make_run(tuple(r['key'] for r in plan['cases']), profile=q.PROFILE)
    result = accept(run, sealed, tmp_path)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert result['qualification_version'] == q.VERSION and result['remaining_keys'] == []
    assert not result['actual_product_task_qualified'] and not result['production_admitted']
    change(run/'claim-scope-4/independent-final-review.json', lambda d: d.update(accepted=False))
    with pytest.raises(ValueError, match='sealed_file_hash'):
        q.validate_qualification(result, evidence_root=tmp_path)


def test_saved_plan_host_handoff_works_in_separate_process(make_run, tmp_path):
    run, sealed = make_run(('claim-scope:4',), profile=q.PROFILE, host_process=True)
    result = accept(run, sealed, tmp_path)
    assert result['validated_inputs'] == 1 and not result['review_controls_qualified']
    calls = q.read_calls(run/'transport/claim-scope-4')
    assert [c['binding']['role'] for c in calls] == ['review', 'revision', 'review']
    first = calls[0]['request']
    final = calls[2]['request']
    assert first.messages[0].content == final.messages[0].content
    data = json.loads(final.messages[1].content.split('\n', 1)[1].rsplit('\n', 1)[0])
    assert not {'previous_review', 'previous_issues', 'accepted_review'} & data.keys()


@pytest.mark.parametrize('profile', ['role', 'coarse'])
def test_old_qualifications_cannot_enter_new_gate(make_run, tmp_path, profile):
    run, sealed = make_run(profile=profile)
    with pytest.raises(ValueError, match='plan_identity_mismatch'):
        accept(run, sealed, tmp_path)
    assert not (tmp_path/'audit').exists()


@pytest.mark.parametrize('profile', ['role', 'coarse'])
def test_new_receipts_cannot_enter_old_gate(make_run, tmp_path, profile):
    run, sealed = make_run(profile=q.PROFILE)
    with pytest.raises(ValueError, match='plan_identity_mismatch'):
        audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'audit',
            closed_exports=[sealed], profile=profile)


@pytest.mark.parametrize('defect', ['source', 'request', 'injected_initial', 'old_identity',
    'reassessment', 'missing_revision', 'rejected_final', 'unknown_call'])
def test_resealed_invalid_evidence_never_qualifies(make_run, tmp_path, defect):
    run, sealed = make_run(('claim-scope:4',), profile=q.PROFILE)
    arm = run/'claim-scope-4'
    if defect == 'source':
        change(arm/'source.json', lambda d: d.update(input_json='{}'))
    elif defect == 'request':
        change(run/'transport/claim-scope-4/review/request-001.json', lambda d: d.update(max_tokens=100))
    elif defect == 'injected_initial':
        change(run/'result.json', lambda d: d['cases'][0].update(fresh_receipts_verified=False))
    elif defect in ('old_identity', 'reassessment'):
        def change_plan(saved):
            saved['preparation_plan'].update(
                {'identity': old.candidate_identity()} if defect == 'old_identity' else {'allow_reassessment': True})
            saved['plan_sha256'] = audit._canonical_sha(saved['preparation_plan'])
        change(run/'plan.json', change_plan)
    elif defect == 'missing_revision':
        (arm/'revision.json').unlink()
    elif defect == 'rejected_final':
        change(arm/'independent-final-review.json', lambda d: d.update(accepted=False))
    else:
        (run/'transport/unrecorded-case').mkdir()
    sealed = seal(run, tmp_path, sealed[0])
    with pytest.raises((ValueError, FileNotFoundError)):
        accept(run, sealed, tmp_path)
    assert not (tmp_path/'audit').exists()


@pytest.mark.parametrize('defect', ['rejected', 'missing', 'wrong_source', 'wrong_response'])
def test_bad_independent_review_stops_before_edit(make_run, defect):
    def sabotage(path):
        independent = path.with_name('independent-'+path.stem+'-review.json')
        if defect == 'missing':
            independent.unlink()
        elif defect == 'rejected':
            change(independent, lambda d: d.update(accepted=False, defects=[{'kind': 'wrong_correction', 'detail': 'Fixture rejection.'}]))
        else:
            field = 'source_file_sha256' if defect == 'wrong_source' else 'response_sha256'
            change(independent, lambda d: d.update({field: '0'*64}))
    run, result = make_run(('claim-scope:4',), profile=q.PROFILE, inspect_fault=sabotage)
    assert not result['tasks_observed']
    assert result['cases'][0]['accounting']['reserved_calls'] == 1
    assert not (run/'claim-scope-4/revision.json').exists()


def test_closed_or_unfrozen_run_stops_before_ci_or_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path/'run')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed.json')
    monkeypatch.setattr(runner, 'verify_public_ci', lambda *_: pytest.fail('CI accessed'))
    monkeypatch.setattr(runner, 'load_role_settings', lambda *_: pytest.fail('credentials accessed'))
    with pytest.raises(ValueError, match='preparation_required'):
        runner.run(NS(execute=True, env_file=None, ci_run=None, plan_sha=None))
    (tmp_path/'run').mkdir()
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))
