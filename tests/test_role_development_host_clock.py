"""Test the actual observer with offline transport; no live qualification."""
import json

import pytest

from app.evaluation.golden_journal import write_new_json
from scripts.role_development_host_clock import (
    DevelopmentHostClock, TIMING_MODE, validate_adopted_timing,
)
from scripts import qualify_role_observations as audit
from scripts.run_role_task_observation import adjudicate_file, await_case_ready
from tests import test_role_observation_qualification as fixtures
from tests.test_role_observation_qualification import make_run, change


def test_real_file_gate_wait_survives_conversation_gap_without_resetting_active_clock(tmp_path):
    now = [0.0]
    clock = DevelopmentHostClock(tmp_path, max_host_seconds=4000, wall_clock=lambda: now[0])
    stage = tmp_path/'initial.json'
    write_new_json(stage, dict(stage='initial', report='offline', journal=None))
    from scripts.run_role_task_observation import StageDecision
    decision = dict(response_sha256=audit._sha(stage), accepted=False,
        candidate_sha256='a'*64, input_sha256='b'*64, key='claim-scope:4',
        target_and_correction_valid=False, final_report=None, assessment=dict(
            stage='initial',stage_sha256='c'*64,accepted=False,
            reviewer='offline',source_review='Offline intentional rejection.',
            defects=[dict(kind='wrong_correction',detail='Offline counterexample.')]))
    decision = StageDecision.model_validate(decision).model_dump()
    def publish(_):
        now[0] += 3600
        assert clock() == 0
        with pytest.raises(ValueError, match='provider_during_host_wait'):
            clock.before_send()
        write_new_json(tmp_path/'decision-initial.json', decision)
    def review(path, remaining):
        return adjudicate_file(path,remaining,clock=lambda:now[0],sleep=publish)
    assert clock.adjudicate(stage,900,review) == decision
    assert clock.summary()['host_elapsed_seconds'] == 3600
    now[0] += 37
    assert clock() == 37
    assert clock.summary()['wall_elapsed_seconds'] == 3637
    with pytest.raises(FileExistsError):
        DevelopmentHostClock(tmp_path,max_host_seconds=4000,wall_clock=lambda:now[0])


@pytest.mark.parametrize('failure', [
    None, 'host_deadline', 'product_deadline', 'initial_rejected', 'revision_rejected',
])
def test_existing_executor_keeps_stage_gates_and_distinct_budgets(
        make_run, tmp_path, monkeypatch, failure):
    now = [0.0]
    original = fixtures.observe
    evidence = {}

    def adapted(factory, run, plan, **kwargs):
        clock = DevelopmentHostClock(run, max_host_seconds=3600, wall_clock=lambda: now[0])
        plan['host_review_timing'] = dict(mode=TIMING_MODE, adopted=False)
        change(run/'plan.json', lambda saved: saved.update(
            preparation_plan=plan, plan_sha256=audit._canonical_sha(plan)))
        review = kwargs['adjudicate']
        send_checks = [0]

        def before_send():
            clock.before_send()
            now[0] += 901 if failure == 'product_deadline' and send_checks[0] == 1 else 5
            send_checks[0] += 1

        def host(path, remaining):
            def wait_for_host(path, available):
                calls = list((run/'transport').rglob('call-*.json'))
                now[0] += 3601 if failure == 'host_deadline' else 600
                assert list((run/'transport').rglob('call-*.json')) == calls
                if failure == 'host_deadline':
                    return {}  # A late callback cannot approve another request.
                return review(path, available)
            return clock.adjudicate(path, remaining, wait_for_host)

        kwargs.update(adjudicate=host, clock=clock, before_send=before_send)
        result = original(factory, run, plan, **kwargs)
        evidence.update(clock.summary())
        return result

    monkeypatch.setattr(fixtures, 'observe', adapted)

    def reject(path):
        target = ('initial' if failure == 'initial_rejected'
                  else 'revision' if failure == 'revision_rejected' else None)
        if path.stem == target:
            change(path.with_name('independent-'+target+'-review.json'), lambda d: d.update(
                accepted=False, defects=[dict(kind='wrong_correction',
                    detail='Offline source rejection.')]))

    # With inspect_fault present, the fixture returns the execution result,
    # not (export_path, sha). Seal only after checking successful execution.
    run, result = make_run(('claim-scope:4',), profile='boundary-examples',
        clock=lambda: now[0], inspect_fault=reject)
    if failure is None:
        assert result['tasks_observed']
        assert result['cases'][0]['accounting']['reserved_calls'] == 3
        assert result['cases'][0]['elapsed_seconds'] == 20
        assert evidence['host_elapsed_seconds'] == 1800
        assert evidence['wall_elapsed_seconds'] == 1820
        sealed = fixtures.seal(run, tmp_path, tmp_path/'prototype-closed.json')
        with pytest.raises(ValueError, match='unadopted_host_timing'):
            audit.qualify([run], evidence_root=tmp_path, output_directory=tmp_path/'audit',
                closed_exports=[sealed], profile='boundary-examples')
        assert not (tmp_path/'audit').exists()
    else:
        assert not result['tasks_observed']
        expected_calls = 2 if failure == 'revision_rejected' else 1
        assert result['cases'][0]['accounting']['reserved_calls'] == expected_calls
        assert not (run/'claim-scope-4/case-completed.json').exists()
        if failure == 'host_deadline':
            assert result['error_code'] == 'development_host_deadline'
        if failure == 'product_deadline':
            assert result['error_code'] == 'role_pair_execution_limit'


def test_unadopted_host_timing_cannot_enter_qualification(make_run, tmp_path):
    run, _ = make_run(('claim-scope:4',), profile='boundary-examples')
    plan_path = run / 'plan.json'
    saved = json.loads(plan_path.read_bytes())
    saved['preparation_plan']['host_review_timing'] = dict(
        mode=TIMING_MODE, adopted=False)
    saved['plan_sha256'] = audit._canonical_sha(saved['preparation_plan'])
    plan_path.write_text(json.dumps(saved, ensure_ascii=True), encoding='utf-8')
    export = tmp_path / 'closed.json'
    sealed = fixtures.seal(run, tmp_path, export)
    with pytest.raises(ValueError, match='unadopted_host_timing'):
        audit.qualify([run], evidence_root=tmp_path,
            output_directory=tmp_path/'audit', closed_exports=[sealed],
            profile='boundary-examples')
    assert not (tmp_path/'audit').exists()


def test_unmarked_host_clock_receipts_are_rejected_at_seal(make_run, tmp_path):
    run, _ = make_run(('claim-scope:4',), profile='boundary-examples')
    clock = DevelopmentHostClock(run, max_host_seconds=4000)
    row = dict(key='claim-scope:4', request_sha256='a' * 64)
    clock.await_case(run, row, dict(example='offline'), 900,
        lambda directory, current_row, plan, available: None)
    export = tmp_path / 'closed-with-clock.json'
    sealed = fixtures.seal(run, tmp_path, export)
    with pytest.raises(ValueError, match='unadopted_host_timing'):
        audit.qualify([run], evidence_root=tmp_path,
            output_directory=tmp_path/'audit-with-clock', closed_exports=[sealed],
            profile='boundary-examples')


def test_adopted_host_clock_requires_bound_receipts_and_checks_clock_equation(tmp_path):
    run = tmp_path/'run'
    arm = run/'claim-scope-4'
    arm.mkdir(parents=True)
    stage = arm/'initial.json'
    write_new_json(stage, dict(stage='initial', report='offline', journal=None))
    plan_sha = 'a' * 64
    plan = dict(host_review_timing=dict(mode=TIMING_MODE, adopted=True,
        max_host_seconds=4000))
    clock = DevelopmentHostClock(run, max_host_seconds=4000,
        qualification_adopted=True, plan_sha256=plan_sha)
    clock.adjudicate(stage, 900, lambda _path, _available: dict(accepted=True))
    checked = validate_adopted_timing(run, plan, saved_plan_sha256=plan_sha)
    assert checked['waits'] == 1 and checked['host_elapsed_seconds'] == 0
    finished = run/'development-host-clock/0001-finished.json'
    value = json.loads(finished.read_bytes())
    value['wall_elapsed_seconds'] = 1
    finished.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='clock_inconsistent'):
        validate_adopted_timing(run, plan, saved_plan_sha256=plan_sha)


def test_case_readiness_wait_uses_host_budget_and_same_bound_handoff(tmp_path):
    now=[0.0]
    clock=DevelopmentHostClock(tmp_path,max_host_seconds=4000,wall_clock=lambda:now[0])
    row=dict(key='claim-scope:4',request_sha256='a'*64)
    plan=dict(example='offline')
    def ready(directory,row,plan,available):
        def signal(_):
            now[0]+=3600
            required=directory/'handoff/claim-scope-4-ready-required.json'
            value=json.loads(required.read_bytes())
            write_new_json(directory/'handoff/claim-scope-4-ready.json',dict(
                schema_version='role-case-ready-v1',ready=True,key=row['key'],
                plan_sha256=value['plan_sha256'],required_sha256=audit._sha(required)))
        return await_case_ready(directory,row,plan,available,clock=lambda:now[0],sleep=signal)
    clock.await_case(tmp_path,row,plan,900,ready)
    assert clock()==0 and clock.summary()['host_elapsed_seconds']==3600


@pytest.mark.parametrize('value',[0,-1,True,float('inf'),float('nan')])
def test_invalid_host_budget_cannot_create_clock(tmp_path,value):
    with pytest.raises(ValueError,match='budget_invalid'):
        DevelopmentHostClock(tmp_path,max_host_seconds=value)
    assert not (tmp_path/'development-host-clock').exists()
