"""Offline receipt fixtures prove continuation boundaries, not model quality."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace as NS

import pytest

from app.evaluation import correction_scope_qualification as backend
from app.evaluation.golden_review_experiment import compact, digest
from scripts import role_continuation as continuation
from scripts import run_correction_scope_qualification as original_runner
from scripts import run_correction_scope_unexecuted as runner
from scripts.diagnose_role_context import canonical_sha
from tests.test_role_observation_qualification import make_run, change
from tests import test_role_observation_qualification as fixture_tools

_LEDGER_CACHE = None


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def ledger(tmp_path, monkeypatch, make_run):
    """Three same-checkout real offline transports, including a failed final."""
    global _LEDGER_CACHE
    if _LEDGER_CACHE is not None:
        shutil.copytree(_LEDGER_CACHE.root, tmp_path, dirs_exist_ok=True)
        value = NS(root=tmp_path, path=tmp_path / _LEDGER_CACHE.path,
            campaign=read(tmp_path / _LEDGER_CACHE.path), current=_LEDGER_CACHE.current,
            requests=_LEDGER_CACHE.requests, runs=[tmp_path / p for p in _LEDGER_CACHE.runs],
            exports=[tmp_path / p for p in _LEDGER_CACHE.exports], charges=_LEDGER_CACHE.charges,
            anchors=_LEDGER_CACHE.anchors)
        monkeypatch.setattr(original_runner, 'CLOSED_SHA', value.anchors[0])
        monkeypatch.setattr(runner, 'CLOSED_SHA', value.anchors[1])
        monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA', value.anchors[2])
        return value
    current, requests = backend.prepare_qualification()
    prototype = read(original_runner.PREPARATION)
    prototype.update(identity=current['identity'], cases=current['cases'],
        original15_plan_sha256=digest(compact(current)))
    campaign = read(runner.CAMPAIGN)
    campaign.update(identity=current['identity'], original15_plan_sha256=digest(compact(current)))
    campaign['parents'] = []
    started = set()
    charge = dict(max_calls=0, max_tokens=0, max_seconds=0)
    descriptors, exports, runs = [], [], []
    sequences = [('claim-scope:1', 'claim-scope:4'), ('claim-scope:3',),
                 ('attribution:1', 'scope:4', 'scope:3')]
    for index, keys in enumerate(sequences):
        def reject(path):
            stage = read(path)
            # The first failed suffix has actual revision and final calls;
            # its missing human acceptance must not skip their binding audit.
            reject_stage = 'final' if index == 0 else 'initial'
            if stage['key'] == keys[-1] and stage['stage'] == reject_stage:
                change(path.with_name('independent-' + path.stem + '-review.json'),
                    lambda d: d.update(accepted=False, defects=[dict(kind='wrong_correction', detail='Offline rejection.')]))
        run, result = make_run(keys, profile='correction-scope', inspect_fault=reject)
        result['elapsed_seconds'] = (index + 1) * 100.125
        write(run / 'result.json', result)
        rows = [r for r in current['cases'] if r['key'] not in started]
        budget_by_key = dict(zip([r['key'] for r in current['cases']], prototype['case_budgets'], strict=True))
        budgets = [budget_by_key[r['key']] for r in rows]
        plan = dict(prototype, experiment=run.name, cases=rows, case_budgets=budgets,
            batch_budget={k: sum(b[k] for b in budgets) for k in continuation.BUDGET_FIELDS})
        if index:
            plan.update(parent_seals=deepcopy(descriptors), charged_prior_budget=dict(charge),
                original_batch_budget=read(runs[0] / 'plan.json')['preparation_plan']['batch_budget'],
                excluded_started_keys=[r['key'] for r in current['cases'] if r['key'] in started])
        saved = dict(preparation_plan=plan, plan_sha256=canonical_sha(plan), head_sha='a' * 40, ci_run='123')
        write(run / 'plan.json', saved)
        for p in run.glob('*/case-completed.json'):
            change(p, lambda d: d.update(plan_sha256=saved['plan_sha256']))
        for row in rows:
            (run / (row['key'].replace(':', '-') + '-prepared-request.json')).write_bytes(requests[row['key']])
        preparation = tmp_path / ('preparations/parent-' + str(index) + '.json')
        write(preparation, plan)
        export = tmp_path / ('exports/parent-' + str(index) + '.json')
        completed = [r['key'] for r in result['cases'] if r['status'] == 'task_observed']
        incomplete = [r['key'] for r in result['cases'] if r['status'] != 'task_observed']
        evidence = dict(kind='role_task_observation_public_result_v1', run_directory=run.relative_to(tmp_path).as_posix(),
            original_file_sha256={p.relative_to(run).as_posix(): sha(p) for p in run.rglob('*') if p.is_file()},
            public_json_contents={'plan.json': saved, 'result.json': result}, plan_sha256=saved['plan_sha256'],
            completed_keys=completed, incomplete_keys=incomplete,
            unexecuted_keys=[r['key'] for r in rows if r['key'] not in completed + incomplete],
            original_error_code=result['error_code'], actual_batch_elapsed_seconds=result['elapsed_seconds'],
            provider_requests=sum(r['accounting']['reserved_calls'] for r in result['cases']),
            input_tokens=sum(r['accounting']['input_tokens'] for r in result['cases']),
            output_tokens=sum(r['accounting']['output_tokens'] for r in result['cases']), unknown_usage_calls=0)
        write(export, evidence)
        item = dict(run_directory=run.relative_to(tmp_path).as_posix(), closed_export=export.relative_to(tmp_path).as_posix(),
            closed_export_sha256=sha(export), preparation=preparation.relative_to(tmp_path).as_posix())
        campaign['parents'].append(item)
        descriptors.append({k: item[k] for k in ('run_directory', 'closed_export', 'closed_export_sha256')})
        descriptors[-1]['plan_sha256'] = saved['plan_sha256']
        started.update(completed + incomplete)
        charge['max_calls'] += evidence['provider_requests']
        charge['max_tokens'] += evidence['input_tokens'] + evidence['output_tokens']
        charge['max_seconds'] = float(Decimal(str(charge['max_seconds'])) + Decimal(str(result['elapsed_seconds'])))
        runs.append(run)
        exports.append(export)
    campaign['last_closed_export_sha256'] = campaign['parents'][-1]['closed_export_sha256']
    path = tmp_path / 'data/evaluation/manifests/correction_scope_continuation_campaign_v1.json'
    write(path, campaign)
    sources = set(prototype['source_sha256']) | set(campaign['source_files'])
    for name in sources:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((backend.old.ROOT / name).read_bytes())
    anchors = [p['closed_export_sha256'] for p in campaign['parents']]
    monkeypatch.setattr(original_runner, 'CLOSED_SHA', anchors[0])
    monkeypatch.setattr(runner, 'CLOSED_SHA', anchors[1])
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA', anchors[2])
    cache = tmp_path.parent / 'continuation-offline-fixture-base'
    shutil.copytree(tmp_path, cache)
    _LEDGER_CACHE = NS(root=cache, path=path.relative_to(tmp_path), current=current, requests=requests,
        runs=[p.relative_to(tmp_path) for p in runs], exports=[p.relative_to(tmp_path) for p in exports],
        charges=charge, anchors=anchors)
    return NS(root=tmp_path, path=path, campaign=campaign, current=current, requests=requests,
        runs=runs, exports=exports, charges=charge, anchors=anchors)


def prepare(ledger):
    return continuation.prepare_campaign(ledger.path, root=ledger.root)


def reseal_last(ledger, monkeypatch, mutate=None):
    path, run = ledger.exports[-1], ledger.runs[-1]
    evidence = read(path)
    evidence['original_file_sha256'] = {p.relative_to(run).as_posix(): sha(p)
        for p in run.rglob('*') if p.is_file()}
    if mutate:
        mutate(evidence)
    write(path, evidence)
    ledger.campaign['parents'][-1]['closed_export_sha256'] = sha(path)
    ledger.campaign['last_closed_export_sha256'] = sha(path)
    write(ledger.path, ledger.campaign)
    monkeypatch.setattr(runner, 'POST_HOST_AUDIT_CLOSED_SHA', sha(path))


def test_full_ledger_derives_nine_and_retains_failed_charges(ledger):
    before = [{p.relative_to(run).as_posix(): sha(p) for p in run.rglob('*') if p.is_file()}
              for run in ledger.runs]
    plan, requests = prepare(ledger)
    assert list(requests) == ['claim-scope:2', 'claim-scope:5', 'claim-scope:6', 'claim-scope:7',
        'observed:1', 'observed:2', 'observed:3', 'observed:4', 'observed:5']
    assert plan['charged_prior_budget'] == ledger.charges
    assert ledger.charges['max_calls'] == 12
    assert {k: plan['batch_budget'][k] for k in continuation.BUDGET_FIELDS} == {
        'max_calls': 19, 'max_tokens': 1838592, 'max_seconds': 5700}
    assert plan['previously_qualified_keys'] == ['claim-scope:1', 'attribution:1', 'scope:4']
    assert len(plan['excluded_started_inputs']) == 6
    assert plan['host_review_submission_mode'] == 'independent-drafts-v1'
    assert set(continuation.REQUIRED_SOURCES).issubset(plan['source_sha256'])
    assert not any(plan[k] for k in ('review_controls_qualified', 'actual_product_task_qualified',
        'production_admitted', 'allow_reassessment', 'sdk_retries', 'inherited_completed_cases', 'inherited_provider_calls'))
    assert before == [{p.relative_to(run).as_posix(): sha(p) for p in run.rglob('*') if p.is_file()}
                      for run in ledger.runs]


@pytest.mark.parametrize('defect', ['omit_first', 'omit_middle', 'omit_last_and_frontier', 'duplicate', 'reorder'])
def test_complete_parent_registry_cannot_be_shortened_or_reordered(ledger, defect):
    value = ledger.campaign
    if defect == 'omit_first':
        value['parents'].pop(0)
    elif defect == 'omit_middle':
        value['parents'].pop(1)
    elif defect == 'omit_last_and_frontier':
        value['parents'].pop()
        value['last_closed_export_sha256'] = value['parents'][-1]['closed_export_sha256']
    elif defect == 'duplicate':
        value['parents'].append(deepcopy(value['parents'][-1]))
    else:
        value['parents'][:2] = reversed(value['parents'][:2])
    write(ledger.path, value)
    with pytest.raises(ValueError, match='role_continuation_(registered_parent_missing|duplicate_parent)'):
        prepare(ledger)


@pytest.mark.parametrize('defect', ['file_changed', 'file_added', 'empty_case', 'ready_only', 'unknown_transport'])
def test_parent_raw_and_started_boundary_cannot_hide_attempts(ledger, monkeypatch, defect):
    run = ledger.runs[-1]
    if defect == 'file_changed':
        (run / 'scope-3/source.json').write_text('{}')
    elif defect == 'file_added':
        (run / 'extra.json').write_text('{}')
    elif defect == 'empty_case':
        (run / 'claim-scope-2').mkdir()
    elif defect == 'unknown_transport':
        (run / 'transport/unknown').mkdir()
    else:
        write(run / 'handoff/claim-scope-2-ready-required.json', {})
        reseal_last(ledger, monkeypatch)
    with pytest.raises(ValueError, match='(role_observation_sealed_file|role_continuation_.*(boundary|inventory))'):
        prepare(ledger)


@pytest.mark.parametrize('value', [-1, True])
def test_noninteger_or_invalid_call_accounting_cannot_refund(ledger, monkeypatch, value):
    reseal_last(ledger, monkeypatch, lambda e: e.update(provider_requests=value))
    with pytest.raises(ValueError, match='accounting_(invalid|changed)'):
        prepare(ledger)


@pytest.mark.parametrize('field,value', [('unknown_usage_calls', 1),
    ('actual_batch_elapsed_seconds', float('nan')), ('input_tokens', 0)])
def test_unknown_or_invalid_usage_and_clock_fail_closed(ledger, monkeypatch, field, value):
    reseal_last(ledger, monkeypatch, lambda e: e.update({field: value}))
    with pytest.raises(ValueError, match='(accounting_(invalid|changed)|compact_nonfinite_number)'):
        prepare(ledger)


@pytest.mark.parametrize('value', [-1, True, 0.5, float('nan'), float('inf')])
def test_numeric_accounting_rejects_noninteger_and_nonfinite_values(value):
    with pytest.raises(ValueError, match='accounting_invalid'):
        continuation._number(value)


def test_real_failed_batch_time_is_not_refunded_from_original_cap(ledger, monkeypatch):
    run = ledger.runs[-1]
    result = read(run / 'result.json')
    result['elapsed_seconds'] = 6000
    write(run / 'result.json', result)
    def update(e):
        e['public_json_contents']['result.json'] = result
        e['actual_batch_elapsed_seconds'] = 6000
    reseal_last(ledger, monkeypatch, update)
    with pytest.raises(ValueError, match='original_budget_exceeded'):
        prepare(ledger)


@pytest.mark.parametrize('ordinal', [1, 2, 3])
def test_unqualified_complete_suffix_still_reconstructs_every_request(ledger, monkeypatch, ordinal):
    read_calls = backend.read_calls
    failed_transport = ledger.runs[0] / 'transport/claim-scope-4'
    def changed(path):
        calls = read_calls(path)
        if Path(path) == failed_transport:
            issued = calls[ordinal - 1]['request']
            messages = (replace(issued.messages[0], content=issued.messages[0].content + '\nChanged.'), *issued.messages[1:])
            calls[ordinal - 1]['request'] = replace(issued, messages=messages)
        return calls
    monkeypatch.setattr(backend, 'read_calls', changed)
    with pytest.raises(ValueError, match='parent_actual_request_changed'):
        prepare(ledger)


def test_unqualified_revision_response_cannot_substitute_a_different_report(ledger, monkeypatch):
    read_calls = backend.read_calls
    failed_transport = ledger.runs[0] / 'transport/claim-scope-4'
    def changed(path):
        calls = read_calls(path)
        if Path(path) == failed_transport:
            response = calls[1]['response']
            calls[1]['response'] = replace(response, content=response.content + '\n\nDifferent actual paragraph.')
        return calls
    monkeypatch.setattr(backend, 'read_calls', changed)
    with pytest.raises(ValueError, match='(parent_actual_request_changed|parent_stage_changed)'):
        prepare(ledger)


@pytest.mark.parametrize('stage', ['initial', 'final'])
@pytest.mark.parametrize('matching_journal', [True, False])
def test_executor_semantic_stop_requires_exact_unexposed_journal(
        make_run, monkeypatch, stage, matching_journal):
    response = fixture_tools.tool_response
    seen = []
    def wrong(payload):
        seen.append(deepcopy(payload))
        if stage == 'initial' and len(seen) == 1:
            payload = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        elif stage == 'final' and len(seen) == 2:
            payload = seen[0]
        return response(payload)
    monkeypatch.setattr(fixture_tools, 'tool_response', wrong)
    run, result = make_run(('claim-scope:4',), profile='correction-scope', inspect_fault=lambda _path: None)
    arm = run / 'claim-scope-4'
    assert result['error_code'] == ('role_pair_initial_semantics_failed' if stage == 'initial'
                                     else 'role_pair_final_review_failed')
    assert not (arm / (stage + '.json')).exists()
    assert (arm / (stage + '-journal.json')).exists()
    row = next(r for r in backend.prepare_qualification()[0]['cases'] if r['key'] == 'claim-scope:4')
    source = next(s for f, s in backend.frozen_cases()[0] if f['key'] == row['key'])
    calls = backend.read_calls(run / 'transport/claim-scope-4')
    assert len(calls) == (1 if stage == 'initial' else 3)
    if not matching_journal:
        change(arm / (stage + '-journal.json'), lambda d: d.update(input_sha256='0' * 64))
        with pytest.raises(ValueError, match='parent_journal_changed'):
            continuation._replay_prefix(run, row, source, calls, backend,
                outcome=result['cases'][0], error_code=result['error_code'])
    else:
        continuation._replay_prefix(run, row, source, calls, backend,
            outcome=result['cases'][0], error_code=result['error_code'])
        with pytest.raises(ValueError, match='parent_unexplained_missing_stage'):
            continuation._replay_prefix(run, row, source, calls, backend,
                outcome=result['cases'][0], error_code='a_different_failure')
        assert not (arm / 'case-completed.json').exists()
        (arm / (stage + '-journal.json')).unlink()
        with pytest.raises(FileNotFoundError):
            continuation._replay_prefix(run, row, source, calls, backend,
                outcome=result['cases'][0], error_code=result['error_code'])


def test_candidate_identity_change_fails_before_parent_replay(ledger, monkeypatch):
    ledger.campaign['identity']['manifest_sha256'] = '0' * 64
    write(ledger.path, ledger.campaign)
    monkeypatch.setattr(continuation, '_seal', lambda *_: pytest.fail('parent read before identity gate'))
    with pytest.raises(ValueError, match='candidate_changed'):
        prepare(ledger)


def test_stale_campaign_sha_fails_before_parent_replay(ledger, monkeypatch):
    old = sha(ledger.path)
    ledger.path.write_bytes(ledger.path.read_bytes() + b'\n')
    monkeypatch.setattr(continuation, '_seal', lambda *_: pytest.fail('parent read after stale campaign'))
    with pytest.raises(ValueError, match='campaign_changed'):
        continuation.prepare_campaign(ledger.path, expected_sha=old, root=ledger.root)


@pytest.mark.parametrize('kind', ['registered_closed', 'run_exists', 'export_exists', 'old_target'])
def test_fixed_target_cannot_reopen_or_change_to_closed_parent(ledger, kind):
    target = ledger.campaign['target']
    if kind == 'registered_closed':
        target.update(state='closed', closed_export_sha256='a' * 64)
    elif kind == 'run_exists':
        (ledger.root / target['run_directory']).mkdir(parents=True)
    elif kind == 'export_exists':
        write(ledger.root / target['closed_export'], {})
    else:
        target['preparation'] = ledger.campaign['parents'][0]['preparation']
    write(ledger.path, ledger.campaign)
    with pytest.raises(ValueError, match='target_closed_or_exists'):
        prepare(ledger)


def test_same_parent_frontier_cannot_be_renamed_to_a_second_target(ledger):
    ledger.campaign['target'] = {k: v.replace('campaign-v1', 'campaign-v2').replace('campaign_preparation_v1',
        'campaign_preparation_v2').replace('campaign_result_v1', 'campaign_result_v2') if isinstance(v, str) else v
        for k, v in ledger.campaign['target'].items()}
    write(ledger.path, ledger.campaign)
    with pytest.raises(ValueError, match='target_identity_changed'):
        prepare(ledger)


def test_campaign_execution_requires_current_hash_without_touching_keys(monkeypatch):
    monkeypatch.setattr(continuation, 'load_campaign', lambda *_args, **_kw: pytest.fail('ledger read'))
    monkeypatch.setattr(original_runner, 'execute_prepared', lambda *_args, **_kw: pytest.fail('executor reached'))
    with pytest.raises(ValueError, match='campaign_hash_required'):
        runner.run(NS(campaign=True, execute=True, campaign_sha=None))


def test_campaign_reuses_existing_executor_only_after_full_parent_audit(ledger, monkeypatch):
    monkeypatch.setattr(runner, 'CAMPAIGN', ledger.path)
    monkeypatch.setattr(runner, 'ROOT', ledger.root)
    def execute(args, plan, requests, *, directory, preparation):
        assert plan['charged_prior_budget'] == ledger.charges
        assert len(requests) == 9 and plan['previously_qualified_keys'] == ['claim-scope:1', 'attribution:1', 'scope:4']
        assert directory == ledger.root / ledger.campaign['target']['run_directory']
        assert preparation == ledger.root / ledger.campaign['target']['preparation']
        return {'shared_executor': True}
    monkeypatch.setattr(original_runner, 'execute_prepared', execute)
    assert runner.run(NS(campaign=True, execute=True, campaign_sha=sha(ledger.path))) == {'shared_executor': True}


def test_bad_parent_stops_before_shared_executor(ledger, monkeypatch):
    monkeypatch.setattr(runner, 'CAMPAIGN', ledger.path)
    monkeypatch.setattr(runner, 'ROOT', ledger.root)
    (ledger.runs[-1] / 'scope-3/source.json').write_text('{}')
    monkeypatch.setattr(original_runner, 'execute_prepared', lambda *_args, **_kw: pytest.fail('executor reached'))
    with pytest.raises(ValueError, match='sealed_file_hash_mismatch'):
        runner.run(NS(campaign=True, execute=True, campaign_sha=sha(ledger.path)))


def test_new_closed_parent_appends_without_a_new_execution_branch(ledger):
    plan, requests = prepare(ledger)
    old_target = dict(ledger.campaign['target'])
    run = ledger.root / old_target['run_directory']
    run.mkdir(parents=True)
    saved = dict(preparation_plan=plan, plan_sha256=canonical_sha(plan), head_sha='b' * 40, ci_run='456')
    # A closed process that failed before touching the first case still has a
    # permanent target identity. It grants no qualification and refunds nothing.
    result = dict(experiment=plan['experiment'], cases=[], elapsed_seconds=0,
        tasks_observed=False, error_code='offline_before_first_case')
    write(run / 'plan.json', saved)
    write(run / 'result.json', result)
    for key, raw in requests.items():
        (run / (key.replace(':', '-') + '-prepared-request.json')).write_bytes(raw)
    write(ledger.root / old_target['preparation'], plan)
    export = ledger.root / old_target['closed_export']
    write(export, dict(kind='role_task_observation_public_result_v1', run_directory=old_target['run_directory'],
        original_file_sha256={p.relative_to(run).as_posix(): sha(p) for p in run.rglob('*') if p.is_file()},
        public_json_contents={'plan.json': saved, 'result.json': result}, plan_sha256=saved['plan_sha256'],
        completed_keys=[], incomplete_keys=[], unexecuted_keys=list(requests),
        original_error_code=result['error_code'], actual_batch_elapsed_seconds=0,
        provider_requests=0, input_tokens=0, output_tokens=0, unknown_usage_calls=0))
    ledger.campaign['parents'].append(dict(run_directory=old_target['run_directory'],
        preparation=old_target['preparation'], closed_export=old_target['closed_export'], closed_export_sha256=sha(export)))
    ledger.campaign['last_closed_export_sha256'] = sha(export)
    ledger.campaign['target'] = {k: v.replace('campaign-v1', 'campaign-v2').replace('campaign_preparation_v1',
        'campaign_preparation_v2').replace('campaign_result_v1', 'campaign_result_v2') if isinstance(v, str) else v
        for k, v in old_target.items()}
    write(ledger.path, ledger.campaign)
    next_plan, next_requests = prepare(ledger)
    assert next_requests == requests
    assert next_plan['charged_prior_budget'] == plan['charged_prior_budget']
    assert len(next_plan['parent_seals']) == 4
    assert next_plan['previously_qualified_keys'] == ['claim-scope:1', 'attribution:1', 'scope:4']
    # Changing the target back to the now-closed parent is denied by the ledger,
    # independently of whether the target's raw directory remains available.
    ledger.campaign['target'] = old_target
    write(ledger.path, ledger.campaign)
    with pytest.raises(ValueError, match='target_closed_or_exists'):
        prepare(ledger)


def test_committed_campaign_manifest_has_lf_byte_rule():
    raw = runner.CAMPAIGN.read_bytes()
    assert b'\r' not in raw
    assert '/data/evaluation/manifests/correction_scope_continuation_campaign_v1.json text eol=lf' in (
        runner.ROOT / '.gitattributes').read_text(encoding='utf-8')


def test_real_sealed_campaign_read_only_preview_when_raw_evidence_is_available():
    campaign = read(runner.CAMPAIGN)
    target = campaign['target']
    if (target['state'] != 'unstarted'
            or (runner.ROOT / target['run_directory']).exists()
            or (runner.ROOT / target['closed_export']).exists()):
        pytest.skip('The unique real target was started or closed; preview must never reopen it.')
    if any(not (runner.ROOT / p['run_directory']).exists() for p in campaign['parents']):
        pytest.skip('Ignored real raw evidence is only available in its original checkout.')
    if campaign['identity'] != backend.candidate_identity():
        pytest.skip('Historical raw identity differs from this checkout; never rebind it.')
    plan, requests = continuation.prepare_campaign(runner.CAMPAIGN)
    assert len(requests) == 9
    assert plan['charged_prior_budget'] == dict(max_calls=12, max_tokens=169342, max_seconds=2799.094)
    assert plan['batch_budget']['max_calls'] == 19
