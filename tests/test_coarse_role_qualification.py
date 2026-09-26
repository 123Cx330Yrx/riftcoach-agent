"""Actual executor and sealed receipt audit with network-only substitutes."""
import pytest
import json
from types import SimpleNamespace as NS

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


def test_separate_host_process_and_saved_plan_pass_existing_gate(make_run, tmp_path):
    from app.evaluation.golden_review_experiment import compact, digest
    run, sealed = make_run(('claim-scope:1',), profile='coarse', host_process=True)
    plan = read(run/'plan.json')['preparation_plan']
    stage = run/'claim-scope-1/initial.json'
    decision = read(stage.with_name('decision-initial.json'))
    assert runner.CoarseObserver.validate_stage(plan, plan['cases'][0], stage, decision)
    assert accept(run, sealed, tmp_path)['validated_inputs'] == 1
    # Do not accept the actual historical bug as a compatibility digest.
    wrong = dict(decision, candidate_sha256=digest(compact(plan['identity'])))
    with pytest.raises(ValueError, match='host_binding'):
        runner.CoarseObserver.validate_stage(plan, plan['cases'][0], stage, wrong)


def test_closed_failed_batch_is_immutable_and_cannot_execute():
    plan, _ = runner.prepare()
    assert runner.canonical_sha(plan) == 'eb59acdd374cf7586ddea4ba090a793ba149e201a09c5f838472a444e33091c7'
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))


def test_repair_plan_keeps_model_identity_and_exact_requests():
    old, old_requests = runner.prepare()
    new, new_requests = runner.prepare(file_handoff_repair=True)
    assert old['identity'] == new['identity'] and old['cases'] == new['cases']
    assert old_requests == new_requests and old['batch_budget'] == new['batch_budget']
    assert new['prior_failure']['inherited_completed_cases'] == 0
    assert new['experiment'] != old['experiment']
    assert json.loads(runner.REPAIR_PREPARATION.read_bytes()) == new


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


@pytest.mark.parametrize('defect', ['rejected', 'missing', 'wrong_response', 'wrong_source', 'wrong_stage'])
def test_independent_defect_stops_before_editor_request(make_run, defect):
    def sabotage(path):
        other = path.parent/('independent-'+path.stem+'-review.json')
        if defect == 'missing':
            other.unlink()
        elif defect == 'rejected':
            change(other, lambda d: d.update(accepted=False, defects=[{'kind':'wrong_correction','detail':'Unsafe edit.'}]))
        elif defect == 'wrong_source':
            change(other, lambda d: d.update(source_file_sha256='0'*64))
        elif defect == 'wrong_stage':
            change(other, lambda d: d.update(stage_sha256='0'*64))
        else:
            change(other, lambda d: d.update(response_sha256='0'*64))
    run, result = make_run(('claim-scope:4',), profile='coarse', inspect_fault=sabotage)
    assert not result['tasks_observed']
    assert result['cases'][0]['accounting']['reserved_calls'] == 1
    assert not (run/'claim-scope-4/revision.json').exists()
    if defect in ('wrong_source', 'wrong_stage'):
        assert (run/'claim-scope-4/decision-initial.json').exists()
        assert result['error_code'] == 'role_observation_independent_binding_mismatch'
