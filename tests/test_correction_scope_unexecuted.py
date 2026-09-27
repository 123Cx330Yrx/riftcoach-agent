"""Closed batches cannot refund charges or rerun any started controls."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from scripts import run_correction_scope_unexecuted as runner
from scripts import run_correction_scope_qualification as prior
from scripts.diagnose_role_context import canonical_sha
from app.evaluation.golden_review_experiment import compact, digest
from tests.test_role_observation_qualification import make_run, change


def save_closed(module, evidence, *, update_plan=True):
    saved = evidence['public_json_contents']['plan.json']
    if update_plan:
        saved['plan_sha256'] = evidence['plan_sha256'] = canonical_sha(saved['preparation_plan'])
        module.PREPARATION.write_text(json.dumps(saved['preparation_plan']), encoding='utf-8')
    module.CLOSED_RESULT.write_text(json.dumps(evidence), encoding='utf-8')
    module.CLOSED_SHA = hashlib.sha256(module.CLOSED_RESULT.read_bytes()).hexdigest()


@pytest.fixture
def same_checkout_parents(tmp_path, monkeypatch):
    """Synthetic same-OS seals test preparation, never real qualification.

    Windows manifest bytes differ on Linux. Preserve real requests but bind
    synthetic exports to the test checkout. Raw execution gates are separate.
    """
    first = json.loads(prior.CLOSED_RESULT.read_bytes())
    second = json.loads(runner.CLOSED_RESULT.read_bytes())
    current, requests = runner.qualification.prepare_qualification()
    for module, label in ((prior, 'original'), (runner, 'continuation')):
        monkeypatch.setattr(module, 'CLOSED_RESULT', tmp_path/(label+'-closed.json'))
        monkeypatch.setattr(module, 'PREPARATION', tmp_path/(label+'-preparation.json'))
        monkeypatch.setattr(module, 'CLOSED_SHA', module.CLOSED_SHA)
        monkeypatch.setattr(module, 'RUN_DIRECTORY', tmp_path/label)
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_RUN_DIRECTORY', tmp_path/'post-host-audit')
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_RESULT', tmp_path/'post-host-audit-closed.json')
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_PREPARATION', tmp_path/'post-host-audit-preparation.json')
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA', None)
    original = first['public_json_contents']['plan.json']['preparation_plan']
    original.update(identity=current['identity'], cases=current['cases'],
        original15_plan_sha256=digest(compact(current)))
    save_closed(prior, first)
    previous = second['public_json_contents']['plan.json']['preparation_plan']
    previous.update(identity=current['identity'], cases=current['cases'][2:],
        original15_plan_sha256=digest(compact(current)),
        parent_seal_sha256=prior.CLOSED_SHA, parent_plan_sha256=first['plan_sha256'])
    save_closed(runner, second)
    return first, second, current, requests


def test_only_twelve_untouched_requests_fit_original_remaining_budget(same_checkout_parents):
    first, second, original, all_requests = same_checkout_parents
    plan, requests = runner.prepare(after_host_audit=True)
    assert plan['experiment'] == 'correction-scope-post-host-audit-v1'
    assert plan['identity'] == original['identity']
    assert plan['cases'] == original['cases'][3:]
    assert requests == {r['key']: all_requests[r['key']] for r in plan['cases']}
    assert len(requests) == 12
    assert plan['charged_prior_budget'] == dict(max_calls=5, max_tokens=74142, max_seconds=1380.516)
    assert {k: plan['batch_budget'][k] for k in runner.BUDGET_FIELDS} == dict(
        max_calls=28, max_tokens=2709504, max_seconds=8400)
    assert plan['excluded_started_keys'] == ['claim-scope:1', 'claim-scope:4', 'claim-scope:3']
    assert plan['parent_seal_sha256'] == prior.CLOSED_SHA
    assert plan['parent_plan_sha256'] == first['plan_sha256']
    assert plan['prior_continuation_seal_sha256'] == runner.CLOSED_SHA
    assert plan['prior_continuation_plan_sha256'] == second['plan_sha256']
    for name in runner.BUDGET_FIELDS:
        assert plan['charged_prior_budget'][name] + plan['batch_budget'][name] <= plan['original_batch_budget'][name]
    assert not any(plan[k] for k in ('review_controls_qualified', 'allow_reassessment',
        'actual_product_task_qualified', 'production_admitted', 'inherited_completed_cases',
        'inherited_provider_calls', 'offline_initial_injections'))


@pytest.mark.parametrize('parent', ['original', 'continuation'])
@pytest.mark.parametrize('defect', ['seal', 'unknown_usage', 'boundary', 'identity', 'charges', 'request', 'cases'])
def test_parent_changes_do_not_unlock_calls(monkeypatch, parent, defect, same_checkout_parents):
    first, second, _, _ = same_checkout_parents
    evidence, module = (first, prior) if parent == 'original' else (second, runner)
    plan = evidence['public_json_contents']['plan.json']['preparation_plan']
    if defect == 'unknown_usage':
        evidence['unknown_usage_calls'] = 1
        evidence['public_json_contents']['result.json']['cases'][0]['accounting']['unknown_usage_calls'] = 1
    elif defect == 'boundary':
        evidence['unexecuted_keys'].pop()
    elif defect == 'identity':
        plan['identity']['manifest_sha256'] = '0'*64
    elif defect == 'charges':
        evidence['provider_requests'] += 1
    elif defect == 'request':
        plan['cases'][-1]['request_sha256'] = '0'*64
    elif defect == 'cases':
        plan['cases'][-2:] = reversed(plan['cases'][-2:])
    if defect == 'seal':
        module.CLOSED_RESULT.write_bytes(module.CLOSED_RESULT.read_bytes() + b' ')
    else:
        save_closed(module, evidence)
        # Maintain linkage to isolate semantic validation from fixed seal identity.
        if module is prior:
            previous = second['public_json_contents']['plan.json']['preparation_plan']
            previous.update(parent_seal_sha256=prior.CLOSED_SHA, parent_plan_sha256=first['plan_sha256'])
            save_closed(runner, second)
    with pytest.raises(ValueError, match='correction_scope_'):
        runner.prepare(after_host_audit=True)


@pytest.mark.parametrize('value', [-1, True, 0.5, float('nan'), float('inf')])
def test_invalid_accounting_cannot_be_used_as_a_refund(value, same_checkout_parents):
    _, second, _, _ = same_checkout_parents
    second['input_tokens'] = value
    second['public_json_contents']['result.json']['cases'][0]['accounting']['input_tokens'] = value
    save_closed(runner, second)
    with pytest.raises(ValueError, match='accounting_changed'):
        runner.prepare(after_host_audit=True)


@pytest.mark.parametrize('field,value', [('provider_requests', 8), ('input_tokens', 3386880),
                                        ('actual_batch_elapsed_seconds', 10500)])
def test_prior_charges_still_count_against_original_cap(field, value, same_checkout_parents):
    first, second, _, _ = same_checkout_parents
    first[field] = value
    result = first['public_json_contents']['result.json']
    if field == 'actual_batch_elapsed_seconds':
        result['elapsed_seconds'] = value
    else:
        accounting = 'reserved_calls' if field == 'provider_requests' else field
        result['cases'][0]['accounting'][accounting] = value - result['cases'][1]['accounting'][accounting]
    save_closed(prior, first)
    previous = second['public_json_contents']['plan.json']['preparation_plan']
    previous.update(parent_seal_sha256=prior.CLOSED_SHA, parent_plan_sha256=first['plan_sha256'],
        charged_prior_budget=runner._charges(first))
    save_closed(runner, second)
    with pytest.raises(ValueError, match='original_budget_exceeded'):
        runner.prepare(after_host_audit=True)


@pytest.mark.parametrize('after', [False, True])
def test_closed_preview_keeps_frozen_identity_and_source_hashes(monkeypatch, after, same_checkout_parents):
    _, second, current, requests = same_checkout_parents
    expected, _ = runner.prepare(after_host_audit=after)
    if after:
        sealed = deepcopy(second)
        saved = sealed['public_json_contents']['plan.json']
        saved.update(preparation_plan=expected, plan_sha256=canonical_sha(expected))
        sealed['plan_sha256'] = saved['plan_sha256']
        runner.POST_HOST_AUDIT_PREPARATION.write_text(json.dumps(expected), encoding='utf-8')
        runner.POST_HOST_AUDIT_CLOSED_RESULT.write_text(json.dumps(sealed), encoding='utf-8')
        monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA',
            hashlib.sha256(runner.POST_HOST_AUDIT_CLOSED_RESULT.read_bytes()).hexdigest())
    current['identity']['manifest_sha256'] = '0'*64
    monkeypatch.setattr(runner.qualification, 'prepare_qualification', lambda: (current, requests))
    monkeypatch.setattr(runner, 'digest', lambda *_: pytest.fail('historical identity rebuilt'))
    monkeypatch.setattr(runner, '_parents', lambda *_: pytest.fail('historical parents rebuilt'))
    plan, selected = runner.prepare(after_host_audit=after)
    assert plan == expected
    assert len(selected) == (12 if after else 13)


def test_real_closed_thirteen_preview_retains_original_canonical_hash():
    plan, requests = runner.prepare()
    assert canonical_sha(plan) == '358f178c829d788be7cd328620fecc63573fec5b5cfb7eb0952c8be519128cea'
    assert len(requests) == 13


def test_real_closed_twelve_preview_retains_original_canonical_hash():
    plan, requests = runner.prepare(after_host_audit=True)
    assert canonical_sha(plan) == '22a857bdda8e8c0a9e4b5312b8b72041f56bfbd9ba069f0908145a81d49f4fec'
    assert len(requests) == 12


@pytest.mark.parametrize('defect', ['preparation', 'request'])
def test_closed_preview_still_checks_plan_and_complete_requests(monkeypatch, defect, same_checkout_parents):
    _, _, current, requests = same_checkout_parents
    if defect == 'preparation':
        runner.PREPARATION.write_text('{}', encoding='utf-8')
    else:
        requests['observed:5'] += b' '
        monkeypatch.setattr(runner.qualification, 'prepare_qualification', lambda: (current, requests))
    with pytest.raises(ValueError, match='closed_request_changed'):
        runner.prepare()


def test_unregistered_new_closed_seal_is_rejected(same_checkout_parents):
    runner.POST_HOST_AUDIT_CLOSED_RESULT.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='seal_changed'):
        runner.prepare(after_host_audit=True)


def test_registered_closed_batch_cannot_rebuild_or_restart_without_files(monkeypatch, same_checkout_parents):
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA', 'a'*64)
    monkeypatch.setattr(runner, '_parents', lambda *_: pytest.fail('closed plan rebuilt'))
    assert not runner.POST_HOST_AUDIT_RUN_DIRECTORY.exists()
    assert not runner.POST_HOST_AUDIT_CLOSED_RESULT.exists()
    with pytest.raises(FileNotFoundError):
        runner.prepare(after_host_audit=True)
    monkeypatch.setattr(runner, 'prepare', lambda **_: pytest.fail('prepare accessed'))
    with pytest.raises(ValueError, match='post_host_audit_closed_or_exists'):
        runner.run(NS(execute=True, after_host_audit=True))


@pytest.mark.parametrize('artifact', ['absent', 'run', 'closed'])
def test_old_continuation_can_never_restart(monkeypatch, artifact, same_checkout_parents):
    runner.CLOSED_RESULT.unlink()
    if artifact == 'run':
        runner.RUN_DIRECTORY.mkdir()
    elif artifact == 'closed':
        runner.CLOSED_RESULT.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(runner, 'prepare', lambda **_: pytest.fail('prepare accessed'))
    with pytest.raises(ValueError, match='unexecuted_closed_or_exists'):
        runner.run(NS(execute=True))


@pytest.mark.parametrize('artifact', ['run', 'closed'])
def test_new_closed_run_rejected_before_parent_or_ci(monkeypatch, artifact, same_checkout_parents):
    if artifact == 'run':
        runner.POST_HOST_AUDIT_RUN_DIRECTORY.mkdir()
    else:
        runner.POST_HOST_AUDIT_CLOSED_RESULT.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(runner, 'prepare', lambda **_: pytest.fail('prepare accessed'))
    with pytest.raises(ValueError, match='post_host_audit_closed_or_exists'):
        runner.run(NS(execute=True, after_host_audit=True))


def test_raw_parent_is_audited_before_ci_or_execution(monkeypatch, same_checkout_parents):
    monkeypatch.setattr(runner, 'prepare', lambda **_: ({}, {}))
    def reject():
        raise ValueError('sealed_file_hash')
    monkeypatch.setattr(runner, 'verify_after_host_audit_parents', reject)
    monkeypatch.setattr(prior, 'execute_prepared', lambda *a, **k: pytest.fail('CI or execution reached'))
    with pytest.raises(ValueError, match='sealed_file_hash'):
        runner.run(NS(execute=True, after_host_audit=True))


def test_new_branch_reuses_existing_executor_after_raw_gate(monkeypatch, same_checkout_parents):
    order = []
    plan, requests = runner.prepare(after_host_audit=True)
    monkeypatch.setattr(runner, 'prepare', lambda **_: (plan, requests))
    monkeypatch.setattr(runner, 'verify_after_host_audit_parents', lambda: order.append('raw'))
    def execute(args, actual_plan, actual_requests, *, directory, preparation):
        assert order == ['raw']
        assert (actual_plan, actual_requests) == (plan, requests)
        assert directory == runner.POST_HOST_AUDIT_RUN_DIRECTORY
        assert preparation == runner.POST_HOST_AUDIT_PREPARATION
        return {'shared_executor': True}
    monkeypatch.setattr(prior, 'execute_prepared', execute)
    assert runner.run(NS(execute=True, after_host_audit=True)) == {'shared_executor': True}


@pytest.mark.parametrize('keys,count', [(set(), 0), ({'claim-scope:4'}, 1),
                                       ({'claim-scope:1', 'claim-scope:4'}, 2)])
def test_original_parent_must_have_exactly_one_strict_case(monkeypatch, keys, count, same_checkout_parents):
    _, _, current, _ = same_checkout_parents
    def inspect(directories, **options):
        assert directories == [prior.RUN_DIRECTORY]
        assert options['closed_exports'] == [(prior.CLOSED_RESULT, prior.CLOSED_SHA)]
        assert options['profile'] == 'correction-scope'
        return None, current, None, [None]*count, keys, None
    monkeypatch.setattr(runner, 'inspect_runs', inspect)
    with pytest.raises(ValueError, match='prefix_invalid'):
        runner.verify_parent()


@pytest.fixture
def raw_continuation(make_run, same_checkout_parents, monkeypatch):
    """Real offline receipt writer; original strict replay is isolated here."""
    first, second, _, requests = same_checkout_parents
    def reject(path):
        change(path.with_name('independent-'+path.stem+'-review.json'),
            lambda d: d.update(accepted=False, defects=[{'kind': 'wrong_correction', 'detail': 'Offline rejection.'}]))
    run, result = make_run(('claim-scope:3',), profile='correction-scope', inspect_fault=reject)
    assert not result['tasks_observed'] and result['cases'][0]['accounting']['reserved_calls'] == 1
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', run)
    result.update(experiment=runner.EXPERIMENT, error_code='role_pair_host_rejected')
    second['public_json_contents']['result.json'] = result
    second['actual_batch_elapsed_seconds'] = result['elapsed_seconds']
    for name in ('input_tokens', 'output_tokens'):
        second[name] = result['cases'][0]['accounting'][name]
    second['run_directory'] = str(run.resolve())
    for directory, evidence in ((prior.RUN_DIRECTORY, first), (run, second)):
        directory.mkdir(exist_ok=True)
        plan = evidence['public_json_contents']['plan.json']['preparation_plan']
        for name in ('plan.json', 'result.json'):
            (directory/name).write_text(json.dumps(evidence['public_json_contents'][name]), encoding='utf-8')
        for row in plan['cases']:
            (directory/(row['key'].replace(':', '-')+'-prepared-request.json')).write_bytes(requests[row['key']])
    audited = []
    monkeypatch.setattr(runner, 'verify_parent', lambda: audited.append('strict original prefix'))
    def reseal():
        second['original_file_sha256'] = {p.relative_to(run).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in run.rglob('*') if p.is_file()}
        save_closed(runner, second)
    reseal()
    return run, second, audited, reseal


def test_after_gate_reads_real_raw_receipts_without_accepting_rejected_case(raw_continuation):
    _, _, audited, _ = raw_continuation
    runner.verify_after_host_audit_parents()
    assert audited == ['strict original prefix']


@pytest.mark.parametrize('defect', ['raw_source', 'missing', 'started', 'empty_started',
    'prepared_request', 'projection', 'accounting'])
def test_actual_originals_and_unstarted_boundary_are_required(raw_continuation, defect):
    run, second, _, reseal = raw_continuation
    if defect == 'raw_source':
        (run/'claim-scope-3/source.json').write_text('{}', encoding='utf-8')
    elif defect == 'missing':
        (run/'claim-scope-3/source.json').unlink()
    elif defect == 'started':
        (run/'transport/attribution-1').mkdir()
        (run/'transport/attribution-1/call-001.json').write_text('{}', encoding='utf-8')
        reseal()
    elif defect == 'empty_started':
        (run/'attribution-1').mkdir()
    elif defect == 'prepared_request':
        (run/'observed-5-prepared-request.json').write_bytes(b'{}')
        reseal()
    elif defect == 'projection':
        change(run/'plan.json', lambda p: p.update(ci_run='different'))
        reseal()
    else:
        result = second['public_json_contents']['result.json']
        result['cases'][0]['accounting']['input_tokens'] += 1
        second['input_tokens'] += 1
        (run/'result.json').write_text(json.dumps(result), encoding='utf-8')
        reseal()
    with pytest.raises(ValueError, match='(role_observation_|correction_scope_)'):
        runner.verify_after_host_audit_parents()


def test_issued_request_is_compared_in_full_after_budget_annotation(monkeypatch, raw_continuation):
    run, _, _, _ = raw_continuation
    calls = runner.qualification.read_calls(run/'transport/claim-scope-3')
    calls[0]['request'] = replace(calls[0]['request'], max_tokens=100)
    monkeypatch.setattr(runner.qualification, 'read_calls', lambda _: calls)
    with pytest.raises(ValueError, match='actual_request_changed'):
        runner.verify_after_host_audit_parents()
