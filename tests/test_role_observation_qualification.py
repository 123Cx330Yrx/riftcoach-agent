"""Sealed offline fixtures exercise acceptance bindings, never model quality."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation import role_qualification as q
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.role_task_outcome import stage_identity
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import qualify_role_observations as audit
from scripts.run_role_qualification_pair import observe
from scripts.run_role_task_observation import Observer, Workflow
from tests.test_role_review_notes import tool_response


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def change(path, mutate):
    value = read(path)
    mutate(value)
    path.write_text(json.dumps(value, ensure_ascii=True), encoding='utf-8')


def seal(run, root, export):
    value = dict(kind=audit.EXPORT_KIND, run_directory=run.relative_to(root).as_posix(),
        original_file_sha256={p.relative_to(run).as_posix(): audit._sha(p)
            for p in run.rglob('*') if p.is_file()})
    export.write_text(json.dumps(value), encoding='utf-8')
    return export, audit._sha(export)


@pytest.fixture
def make_run(tmp_path, monkeypatch):
    """Real executor/receipt writer; stub only network with source-bound replies."""
    plan, requests = q.prepare_qualification()
    sources = {f['key']: source for f, source in q.frozen_cases()[0]}
    counter = [0]

    def build(keys=('claim-scope:1', 'claim-scope:4'), *, write_fault=None, before_case=None, clock=lambda:0, profile='role', inspect_fault=None):
        from app.runtime.coach_contract import ROLE_COACH_CONTRACT
        backend, workflow, observer, contract = q, Workflow, Observer, ROLE_COACH_CONTRACT
        if profile == 'coarse':
            from app.evaluation import coarse_role_qualification as backend
            from scripts.run_coarse_role_qualification import Workflow as workflow, CoarseObserver as observer, CONTRACT as contract
        plan, requests = backend.prepare_qualification()
        counter[0] += 1
        run = tmp_path / ('run-' + str(counter[0]))
        run.mkdir()
        rows = [deepcopy(next(r for r in plan['cases'] if r['key'] == key)) for key in keys]
        budgets = [dict(max_calls=1 if r['expected_initial'] == 'accept' else 3,
            max_tokens=96768 if r['expected_initial'] == 'accept' else 290304,
            max_seconds=300 if r['expected_initial'] == 'accept' else 900) for r in rows]
        observation = dict(experiment=run.name, observation_version=audit.VERSION, identity=plan['identity'],
            original15_plan_sha256=digest(compact(plan)), original15_keys=[r['key'] for r in plan['cases']],
            cases=rows, case_budgets=budgets, allow_reassessment=False,
            batch_budget={k: sum(b[k] for b in budgets) for k in budgets[0]})
        write_new_json(run / 'plan.json', dict(preparation_plan=observation,
            plan_sha256=audit._canonical_sha(observation), head_sha='a' * 40, ci_run='123'))
        for row in rows:
            (run / (row['key'].replace(':', '-') + '-prepared-request.json')).write_bytes(requests[row['key']])
        good = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        bad = dict(score=80, verdict='needs_revision', issues=[dict(block=4, severity='medium',
            category='fact_error', source_ids=[27 if profile == 'coarse' else 1], explanation='Offline structural fixture.',
            suggested_correction='Repair the identified error.')], issue_resolutions=[], advisories=[])
        replies = []
        for row in rows:
            error = deepcopy(bad)
            if profile == 'coarse':
                from app.evaluation.golden_coarse_source_projection import source_catalog
                error['issues'][0]['source_ids'] = [source_catalog(workflow.build_inputs(sources[row['key']]))['roots'][0]['source_id']]
            replies.append(tool_response(good if row['expected_initial'] == 'accept' else error))
            if row['expected_initial'] == 'reject':
                replies += [ChatResponse(content=sources[row['key']].report + '\n\nOffline structural edit fixture.', model='glm-5.3-flash',
                    provider='zhipu', finish_reason='stop', usage=TokenUsage(10, 10)), tool_response(good)]

        def child(command, raw, *, directory, timeout_s, environ, transport_id):
            write_new_json(directory / 'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id))
            return replies.pop(0)
        monkeypatch.setattr(bridge, 'run_child', child)
        def settings(model):
            return NS(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
        factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
            reviewer_settings=settings('glm-5.3'), transport_root=run / 'transport',
            source_projection=contract.descriptor()['source_projection'])

        def adjudicate(path, remaining):
            stage = read(path)
            name, key = stage['stage'], stage['key']
            row = next(r for r in rows if r['key'] == key)
            report_sha, raw_sha = digest(stage['report']), audit._sha(path)
            final_report = None if name == 'initial' and row['expected_initial'] == 'reject' else dict(
                report_sha256=report_sha, reviewer='offline independent source fixture',
                source_review='Synthetic source inspection; no model quality claim.', **{k: True for k in audit.CHECKS})
            independent = dict(accepted=True, defects=[], key=key, input_sha256=row['input_sha256'],
                stage=name, stage_sha256=stage_identity(stage), response_sha256=raw_sha,
                report_sha256=report_sha, source_file_sha256=audit._sha(path.parent / 'source.json'),
                reviewer='offline independent source fixture', source_review='Synthetic source inspection.',
                target_and_correction_valid=True, final_report=final_report)
            independent_path = path.parent / ('independent-' + name + '-review.json')
            write_new_json(independent_path, independent)
            primary = dict(accepted=True, defects=[], stage_sha256=raw_sha, report_sha256=report_sha,
                independent_file=independent_path.name, independent_sha256=audit._sha(independent_path),
                reason='Synthetic primary source inspection.', target_and_correction_valid=True,
                final_report_checks={k: True for k in audit.CHECKS} if final_report else None,
                report_reason=final_report['source_review'] if final_report else 'Intentionally incorrect source.')
            write_new_json(path.parent / ('primary-' + name + '-review.json'), primary)
            decision = dict(response_sha256=raw_sha, accepted=True, candidate_sha256=digest(compact(plan['identity'])),
                input_sha256=row['input_sha256'], key=key, target_and_correction_valid=True,
                assessment=dict(stage=name, stage_sha256=stage_identity(stage), reviewer='offline primary fixture',
                    source_review=primary['reason'], accepted=True, defects=[]), final_report=final_report)
            write_new_json(path.parent / ('decision-' + name + '.json'), decision)
            if profile == 'coarse':
                from scripts.run_coarse_role_qualification import validate_handoff
                if inspect_fault:
                    inspect_fault(path)
                return validate_handoff(path, decision, observation, directory=run)
            return decision

        from scripts import run_role_qualification_pair as pair
        def write(path, value):
            if write_fault:
                write_fault(path, value)
            return write_new_json(path, value)
        with monkeypatch.context() as patch:
            patch.setattr(pair, 'write_new_json', write)
            result = observe(factory, run, observation, adjudicate=adjudicate, clock=clock,
                workflow_type=workflow, replay=lambda *a: backend.replay_case(*a, include_stage_evidence=False),
                success_field='tasks_observed', task_observer=observer,
                before_case=before_case, coach_contract=contract)
        if write_fault or before_case or inspect_fault:
            return run, result
        assert result['tasks_observed'], result
        export = tmp_path / (run.name + '-closed.json')
        sealed = seal(run, tmp_path, export)
        return run, sealed
    return build


def test_completed_case_survives_next_case_and_batch_summary_write_failure(make_run, tmp_path):
    def interrupt(path, value):
        if path == tmp_path/'run-1/result.json' or path == tmp_path/'run-1/claim-scope-4/source.json':
            raise OSError('simulated interrupted storage')
    with pytest.raises(OSError, match='interrupted storage'):
        make_run(write_fault=interrupt)
    run = tmp_path/'run-1'
    completion = read(run/'claim-scope-1/case-completed.json')
    assert completion['plan_sha256'] == audit._canonical_sha(read(run/'plan.json')['preparation_plan'])
    assert completion['task_observation_sha256'] == audit._sha(run/'claim-scope-1/task-observation.json')
    outcome = completion['outcome']
    assert outcome['status'] == 'task_observed' and outcome['elapsed_seconds'] == 0
    assert outcome['accounting']['reserved_calls'] == 1
    assert not (run/'result.json').exists()
    assert not (run/'transport/claim-scope-4').exists()


def test_failed_completion_receipt_stops_before_next_provider(make_run):
    def fail(path, value):
        if path.name == 'case-completed.json':
            raise OSError('completion disk failure')
    run, result = make_run(write_fault=fail)
    assert not result['tasks_observed'] and result['error_type'] == 'OSError'
    assert result['cases'][0]['status'] == 'failed'
    assert len(result['cases']) == 1
    assert not (run/'claim-scope-4').exists()
    assert not (run/'claim-scope-1/case-completed.json').exists()


def test_original_durable_receipt_can_be_qualified_after_lost_batch_summary(make_run, tmp_path):
    run, sealed = make_run()
    (run/'result.json').unlink()
    sealed = seal(run,tmp_path,sealed[0])
    before = {p:audit._sha(p) for p in run.rglob('*') if p.is_file()}
    result = accept(run,sealed,tmp_path)
    assert result['validated_inputs']==2
    assert not result['review_controls_qualified']
    host=read(tmp_path/'audit/claim-scope-1-host-review.json')
    assert host['completion_source']=='durable_case_receipts_without_batch_result'
    assert before=={p:audit._sha(p) for p in run.rglob('*') if p.is_file()}


def interrupted_run(make_run, tmp_path):
    def fail(path, value):
        if path.parent.name=='claim-scope-4' and path.name=='initial.json':
            raise ValueError('task_observation_host_deadline')
    run,result=make_run(write_fault=fail)
    assert result['error_code']=='task_observation_host_deadline'
    return run,seal(run,tmp_path,tmp_path/'interrupted.json')


def test_failed_batch_accepts_completed_prefix_and_retains_all_charges(make_run,tmp_path):
    run,sealed=interrupted_run(make_run,tmp_path)
    before={p:audit._sha(p) for p in run.rglob('*') if p.is_file()}
    result=accept(run,sealed,tmp_path)
    assert result['validated_keys']==['claim-scope:1']
    assert 'claim-scope:4' in result['remaining_keys']
    assert not result['review_controls_qualified']
    boundary=read(tmp_path/'audit/source-seals.json')['closed_runs'][0]['interruption_boundary']
    assert boundary['original_error_code']=='task_observation_host_deadline'
    assert boundary['full_batch_reserved_calls']==2
    assert boundary['unqualified_started_cases'][0]['key']=='claim-scope:4'
    assert boundary['unqualified_started_cases'][0]['qualified'] is False
    assert boundary['full_batch_charged_tokens']==sum(
        row['accounting']['input_tokens']+row['accounting']['output_tokens'] for row in read(run/'result.json')['cases'])
    assert before=={p:audit._sha(p) for p in run.rglob('*') if p.is_file()}


@pytest.mark.parametrize('defect',['prefix','tail_status','tail_key','tail_accounting','missing_tail','unrecorded_transport'])
def test_failed_summary_cannot_override_completions_or_hide_tail(make_run,tmp_path,defect):
    run,sealed=interrupted_run(make_run,tmp_path)
    if defect=='prefix':
        change(run/'result.json',lambda d:d['cases'][0].update(initial_score=99))
    elif defect=='tail_status':
        change(run/'result.json',lambda d:d['cases'][1].update(status='task_observed'))
    elif defect=='tail_key':
        change(run/'result.json',lambda d:d['cases'][1].update(key='observed:2'))
    elif defect=='tail_accounting':
        change(run/'result.json',lambda d:d['cases'][1]['accounting'].update(reserved_calls=0))
    elif defect=='missing_tail':
        change(run/'result.json',lambda d:d['cases'].pop())
    else:
        (run/'transport/not-in-plan').mkdir()
    sealed=seal(run,tmp_path,sealed[0])
    with pytest.raises(ValueError):
        accept(run,sealed,tmp_path)
    assert not (tmp_path/'audit').exists()


def test_failed_tail_calls_count_against_batch_cap(make_run,tmp_path):
    run,sealed=interrupted_run(make_run,tmp_path)
    saved=read(run/'plan.json')
    saved['preparation_plan']['batch_budget']['max_calls']=1
    saved['plan_sha256']=audit._canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved),encoding='utf-8')
    change(run/'claim-scope-1/case-completed.json',lambda d:d.update(plan_sha256=saved['plan_sha256']))
    sealed=seal(run,tmp_path,sealed[0])
    with pytest.raises(ValueError,match='batch_budget_exceeded'):
        accept(run,sealed,tmp_path)


@pytest.mark.parametrize('tiny_cap',[False,True])
def test_unknown_tail_uses_issued_request_reservation_not_declared_allowance(make_run,tmp_path,tiny_cap):
    run,sealed=interrupted_run(make_run,tmp_path)
    transport=run/'transport/claim-scope-4'
    call=q.read_role_calls(transport)[0]
    upper=q.size(call['request'])+call['request'].max_tokens
    (transport/'review/response-001.json').unlink()
    (transport/'call-result-001.json').unlink()
    summary=q.summarize_role_calls(transport)
    assert summary['unknown_usage_calls']==1
    change(run/'result.json',lambda d:d['cases'][1].update(accounting=summary))
    if tiny_cap:
        saved=read(run/'plan.json')
        saved['preparation_plan']['case_budgets'][1]['max_tokens']=1
        saved['preparation_plan']['batch_budget']['max_tokens']=21
        saved['plan_sha256']=audit._canonical_sha(saved['preparation_plan'])
        (run/'plan.json').write_text(json.dumps(saved),encoding='utf-8')
        change(run/'claim-scope-1/case-completed.json',lambda d:d.update(plan_sha256=saved['plan_sha256']))
    sealed=seal(run,tmp_path,sealed[0])
    if tiny_cap:
        with pytest.raises(ValueError,match='case_budget_exceeded'):
            accept(run,sealed,tmp_path)
    else:
        assert accept(run,sealed,tmp_path)['validated_inputs']==1
        boundary=read(tmp_path/'audit/source-seals.json')['closed_runs'][0]['interruption_boundary']
        assert boundary['unknown_usage_calls']==1
        assert boundary['full_batch_charged_tokens']==20+upper


@pytest.mark.parametrize('with_result',[False,True])
def test_no_case_can_be_skipped_after_first_incomplete(make_run,tmp_path,with_result):
    run,sealed=make_run(('claim-scope:1','claim-scope:4','claim-scope:2'))
    for key in ('claim-scope-4','claim-scope-2'):
        (run/key/'case-completed.json').unlink()
    if with_result:
        change(run/'result.json',lambda d:(d.update(error_type='ValueError'),
            d['cases'][1].update(status='failed'),d['cases'].pop()))
    else:
        (run/'result.json').unlink()
    sealed=seal(run,tmp_path,sealed[0])
    with pytest.raises(ValueError,match='execution_after_incomplete_case'):
        accept(run,sealed,tmp_path)


def test_not_ready_next_case_never_creates_provider_or_loses_previous_completion(make_run,tmp_path):
    def ready(directory,row,plan,remaining):
        assert remaining==plan['batch_budget']['max_seconds']
        assert not (directory/'transport'/row['key'].replace(':','-')).exists()
        if row['key']=='claim-scope:4':
            assert (directory/'claim-scope-1/case-completed.json').exists()
            raise ValueError('task_observation_ready_deadline')
    run,result=make_run(before_case=ready)
    assert result['error_code']=='task_observation_ready_deadline'
    assert len(result['cases'])==1
    assert not (run/'claim-scope-4').exists()
    sealed=seal(run,tmp_path,tmp_path/'ready-closed.json')
    assert accept(run,sealed,tmp_path)['validated_keys']==['claim-scope:1']


def test_later_readiness_batch_timeout_retains_on_time_completed_case(make_run,tmp_path):
    now=[0.0]
    def ready(directory,row,plan,remaining):
        if row['key']=='claim-scope:4':
            now[0]=plan['batch_budget']['max_seconds']+.2
    run,result=make_run(before_case=ready,clock=lambda:now[0])
    assert result['error_code']=='role_pair_execution_limit'
    assert result['elapsed_seconds']==1200.2
    assert not (run/'claim-scope-4').exists()
    sealed=seal(run,tmp_path,tmp_path/'batch-timeout.json')
    assert accept(run,sealed,tmp_path)['validated_keys']==['claim-scope:1']
    boundary=read(tmp_path/'audit/source-seals.json')['closed_runs'][0]['interruption_boundary']
    assert boundary['original_elapsed_seconds']==1200.2
    assert boundary['original_error_code']=='role_pair_execution_limit'


@pytest.mark.parametrize('defect',['missing_all','gap','plan','observation','elapsed','batch_elapsed','inconsistent_clock'])
def test_partial_completion_cannot_fabricate_a_timed_execution(make_run,tmp_path,defect):
    run,sealed=make_run()
    (run/'result.json').unlink()
    first=run/'claim-scope-1/case-completed.json'
    last=run/'claim-scope-4/case-completed.json'
    if defect=='missing_all':
        first.unlink();last.unlink()
    elif defect=='gap':
        first.unlink()
    elif defect=='plan':
        change(first,lambda d:d.update(plan_sha256='0'*64))
    elif defect=='observation':
        change(first,lambda d:d.update(task_observation_sha256='0'*64))
    elif defect=='elapsed':
        change(first,lambda d:d['outcome'].update(elapsed_seconds=301))
    elif defect=='inconsistent_clock':
        change(first,lambda d:(d['outcome'].update(elapsed_seconds=200),d.update(batch_elapsed_seconds=1)))
        change(last,lambda d:(d['outcome'].update(elapsed_seconds=100),d.update(batch_elapsed_seconds=500)))
    else:
        change(last,lambda d:d.update(batch_elapsed_seconds=1201))
    sealed=seal(run,tmp_path,sealed[0])
    with pytest.raises(ValueError):
        accept(run,sealed,tmp_path)
    assert not (tmp_path/'audit').exists()


def accept(run, sealed, root, output='audit'):
    return audit.qualify([run], evidence_root=root, output_directory=root / output, closed_exports=[sealed])


def test_partial_replays_real_receipts_without_using_observation_success_flags(make_run, tmp_path, monkeypatch):
    run, sealed = make_run()
    change(run / 'result.json', lambda d: d.update(tasks_observed=False))
    for key in ('claim-scope-1', 'claim-scope-4'):
        change(run / key / 'task-observation.json', lambda d: d.update(task_outcome=False, reviewer_quality=False))
    sealed = seal(run, tmp_path, sealed[0])
    monkeypatch.setattr(q, 'validate_qualification', lambda *a, **k: pytest.fail('partial granted gate'))
    before = {p: audit._sha(p) for p in run.rglob('*') if p.is_file()}
    result = accept(run, sealed, tmp_path)
    assert result['status'] == 'validated_partial' and result['validated_inputs'] == 2
    assert set(result['validated_keys']) == {'claim-scope:1', 'claim-scope:4'}
    assert len(result['remaining_keys']) == 13
    assert not any(result[k] for k in ('review_controls_qualified', 'actual_product_task_qualified', 'production_admitted'))
    assert before == {p: audit._sha(p) for p in run.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='input_or_output'):
        accept(run, sealed, tmp_path)


@pytest.mark.parametrize('defect', ['middle_rejected', 'missing_stage', 'host_hash', 'source',
    'incomplete', 'over_time', 'over_tokens', 'independent', 'false_report', 'changed_identity', 'injected_call'])
def test_invalid_evidence_rejected_even_with_a_new_seal(make_run, tmp_path, defect):
    run, sealed = make_run(('claim-scope:4',))
    arm = run / 'claim-scope-4'
    if defect == 'middle_rejected':
        change(arm / 'revision-host.json', lambda d: d.update(accepted=False))
    elif defect == 'missing_stage':
        (arm / 'revision.json').unlink()
    elif defect == 'host_hash':
        change(arm / 'final-host.json', lambda d: d.update(response_sha256='0' * 64))
    elif defect == 'source':
        change(arm / 'source.json', lambda d: d.update(report='changed'))
    elif defect == 'incomplete':
        (run / 'transport/claim-scope-4/call-result-003.json').unlink()
    elif defect == 'over_time':
        change(run / 'result.json', lambda d: d['cases'][0].update(elapsed_seconds=901))
    elif defect == 'over_tokens':
        change(run / 'plan.json', lambda d: (d['preparation_plan']['case_budgets'][0].update(max_tokens=1),
            d.update(plan_sha256=audit._canonical_sha(d['preparation_plan']))))
    elif defect == 'independent':
        change(arm / 'independent-final-review.json', lambda d: d.update(accepted=False, defects=[{'kind':'wrong_final_report','detail':'wrong'}]))
    elif defect == 'false_report':
        change(arm / 'final-host.json', lambda d: d['final_report'].update(true_errors_fixed=False))
    elif defect == 'changed_identity':
        change(run / 'plan.json', lambda d: d['preparation_plan']['identity'].update(policy_sha256='0'*64))
    else:
        change(run / 'result.json', lambda d: d['cases'][0].update(fresh_receipts_verified=False))
    sealed = seal(run, tmp_path, sealed[0])
    with pytest.raises((ValueError, FileNotFoundError)):
        accept(run, sealed, tmp_path)
    assert not (tmp_path / 'audit').exists()


def test_tampered_original_or_export_is_not_resealed_implicitly(make_run, tmp_path):
    run, sealed = make_run(('claim-scope:1',))
    change(run / 'claim-scope-1/primary-initial-review.json', lambda d: d.update(reason='changed'))
    with pytest.raises(ValueError, match='sealed_file_hash'):
        accept(run, sealed, tmp_path)
    with pytest.raises(ValueError, match='closed_export_hash'):
        accept(run, (sealed[0], '0'*64), tmp_path)


def test_duplicate_key_across_complete_runs_is_rejected(make_run, tmp_path):
    run1, seal1 = make_run(('claim-scope:1',))
    run2, seal2 = make_run(('claim-scope:1',))
    with pytest.raises(ValueError, match='duplicate_or_unknown_case'):
        audit.qualify([run1, run2], evidence_root=tmp_path, output_directory=tmp_path/'audit', closed_exports=[seal1, seal2])


def test_later_batch_without_optional_plan_hash_keeps_current_identity_checks(make_run, tmp_path):
    run, sealed = make_run(('claim-scope:1',))
    def remove_optional(saved):
        saved['preparation_plan'].pop('original15_plan_sha256')
        saved['plan_sha256'] = audit._canonical_sha(saved['preparation_plan'])
    change(run / 'plan.json', remove_optional)
    sealed = seal(run, tmp_path, sealed[0])
    assert accept(run, sealed, tmp_path)['validated_keys'] == ['claim-scope:1']


def test_only_full_fifteen_call_unchanged_original_validator(make_run, tmp_path, monkeypatch):
    plan, _ = q.prepare_qualification()
    keys = tuple(r['key'] for r in plan['cases'])
    run, sealed = make_run(keys)
    called = []
    original = q.validate_qualification
    def validate(result, **kwargs):
        called.append(result)
        return original(result, **kwargs)
    monkeypatch.setattr(q, 'validate_qualification', validate)
    result = accept(run, sealed, tmp_path)
    assert len(called) == 1 and result['review_controls_qualified'] is True
    assert result['status'] == 'qualified_original_review_controls' and not result['remaining_keys']
    assert result['accepted_inputs'] == 15
    assert not result['actual_product_task_qualified'] and not result['production_admitted']
