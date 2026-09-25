"""Actual executor and sealed receipt audit with network-only substitutes."""
import pytest

from app.evaluation import coarse_role_qualification as q
from scripts import qualify_role_observations as audit
from scripts import run_coarse_role_qualification as runner
from tests.test_role_observation_qualification import make_run, change, seal, read


def accept(run, sealed, root):
    return audit.qualify([run], evidence_root=root, output_directory=root/'audit',
        closed_exports=[sealed], profile='coarse')


def test_full_fifteen_use_actual_coarse_executor_and_gate(make_run, tmp_path):
    plan, _ = q.prepare_qualification()
    run, sealed = make_run(tuple(r['key'] for r in plan['cases']), profile='coarse')
    result = accept(run, sealed, tmp_path)
    assert result['accepted_inputs'] == 15 and result['review_controls_qualified']
    assert result['qualification_version'] == q.VERSION and not result['remaining_keys']
    assert not result['actual_product_task_qualified'] and not result['production_admitted']
    # The callable gate must recheck original inspections, not trust a summary
    # that still hashes correctly after the original evidence is damaged.
    original = run/'claim-scope-4/independent-final-review.json'
    change(original, lambda d: d.update(accepted=False))
    with pytest.raises(ValueError, match='sealed_file_hash'):
        q.validate_qualification(result, evidence_root=tmp_path)
    row = result['cases'][0]
    host_path = tmp_path/row['host_review_file']
    change(host_path, lambda d: d.pop('closed_export'))
    row['host_review_sha256'] = audit._sha(host_path)
    with pytest.raises(ValueError, match='sealed_observation_required'):
        q.validate_qualification(result, evidence_root=tmp_path)


def test_partial_never_calls_full_gate(make_run, tmp_path, monkeypatch):
    run, sealed = make_run(profile='coarse')
    monkeypatch.setattr(q, 'validate_qualification', lambda *a, **k: pytest.fail('partial granted gate'))
    result = accept(run, sealed, tmp_path)
    assert result['validated_inputs'] == 2 and len(result['remaining_keys']) == 13
    assert not result['review_controls_qualified']


@pytest.mark.parametrize('defect', ['source', 'schema', 'catalog', 'missing_revision', 'rejected_review',
    'missing_clock', 'over_time', 'injected_initial', 'old_identity', 'missing_receipt', 'extra_transport'])
def test_resealed_invalid_evidence_cannot_qualify(make_run, tmp_path, defect):
    run, sealed = make_run(('claim-scope:4',), profile='coarse')
    arm = run/'claim-scope-4'
    if defect == 'source':
        change(arm/'source.json', lambda d: d.update(input_json='{}'))
    elif defect in ('schema', 'catalog'):
        key = 'schema_sha256' if defect == 'schema' else 'source_catalog_sha256'
        def alter(saved):
            saved['preparation_plan']['cases'][0][key] = '0'*64
            saved['plan_sha256'] = audit._canonical_sha(saved['preparation_plan'])
        change(run/'plan.json', alter)
    elif defect == 'missing_revision':
        (arm/'revision.json').unlink()
    elif defect == 'rejected_review':
        change(arm/'independent-final-review.json', lambda d: d.update(accepted=False))
    elif defect == 'missing_clock':
        change(run/'result.json', lambda d: d['cases'][0].pop('elapsed_seconds'))
    elif defect == 'over_time':
        change(run/'result.json', lambda d: d['cases'][0].update(elapsed_seconds=901))
    elif defect == 'injected_initial':
        change(run/'result.json', lambda d: d['cases'][0].update(fresh_receipts_verified=False))
    elif defect == 'old_identity':
        from app.evaluation.role_qualification import candidate_identity
        change(run/'plan.json', lambda d: d['preparation_plan'].update(identity=candidate_identity()))
    elif defect == 'missing_receipt':
        (run/'transport/claim-scope-4/call-result-001.json').unlink()
    else:
        (run/'transport/unrecorded-case').mkdir()
    sealed = seal(run, tmp_path, sealed[0])
    with pytest.raises((ValueError, FileNotFoundError)):
        accept(run, sealed, tmp_path)
    assert not (tmp_path/'audit').exists()


def test_old_complete_run_cannot_transfer(make_run, tmp_path):
    run, sealed = make_run()
    with pytest.raises(ValueError, match='plan_identity_mismatch'):
        accept(run, sealed, tmp_path)


def test_new_projection_cannot_enter_old_default_gate(make_run, tmp_path):
    run, sealed = make_run(profile='coarse')
    with pytest.raises(ValueError, match='plan_identity_mismatch'):
        audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'audit', closed_exports=[sealed])


def test_new_completed_prefix_survives_interruption(make_run, tmp_path):
    run, sealed = make_run(profile='coarse')
    (run/'result.json').unlink()
    sealed = seal(run, tmp_path, sealed[0])
    result = accept(run, sealed, tmp_path)
    assert result['validated_inputs'] == 2 and not result['review_controls_qualified']
    assert all(r['status'] == 'host_accepted' for r in result['cases'])


def test_runner_is_full_original_set_and_does_not_inject_tail():
    plan, requests = runner.prepare()
    original, expected = q.prepare_qualification()
    assert plan['cases'] == original['cases'] and requests == expected
    assert len(plan['cases']) == 15 and plan['allow_reassessment'] is False
    assert plan['batch_budget']['max_calls'] == sum(1 if r['expected_initial']=='accept' else 3 for r in plan['cases'])
    assert not plan['production_admitted'] and not plan['actual_product_task_qualified']


@pytest.mark.parametrize('defect', ['rejected', 'missing', 'wrong_response'])
def test_independent_defect_stops_before_editor_request(make_run, defect):
    def sabotage(path):
        other = path.parent/('independent-'+path.stem+'-review.json')
        if defect == 'missing':
            other.unlink()
        elif defect == 'rejected':
            change(other, lambda d: d.update(accepted=False, defects=[{'kind':'wrong_correction','detail':'Unsafe edit.'}]))
        else:
            change(other, lambda d: d.update(response_sha256='0'*64))
    run, result = make_run(('claim-scope:4',), profile='coarse', inspect_fault=sabotage)
    assert not result['tasks_observed']
    assert result['cases'][0]['accounting']['reserved_calls'] == 1
    assert not (run/'claim-scope-4/revision.json').exists()
