"""Offline qualification boundary checks; no live qualification is produced."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from scripts import qualify_full_chain_controls as q


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    preparation = q.prepare()
    root = tmp_path_factory.mktemp('qualification-plan')
    session = q.FullChainEvidence(directory=root/'run', answers=root/'authors', observations=root/'obs')
    plan = session.prepare(root_thread_id=q.PRINCIPALS['primary'], independent_thread_id=q.PRINCIPALS['independent'])
    return preparation, dict(preparation_plan=plan, plan_sha256=session.runner.canonical_sha(plan),
        execution_head='a'*40, ci_run=123)


def synthetic_seal(preparation):
    cases, flat = [], []
    for target in preparation['combination']['cases']:
        names = ['initial'] if target['original_label'] == 'accept' else ['initial', 'revision', 'final']
        stages = [dict(stage=n, host_accepted=True, binding={'synthetic_test_only': True}) for n in names]
        row = dict(key=target['key'], semantic_accepted=True, stages=stages,
            initial_verdict='pass' if len(names) == 1 else 'needs_revision', initial_score=96 if len(names) == 1 else 70)
        if len(names) == 3: row.update(final_verdict='pass', final_score=95)
        cases.append(row)
        flat.extend(dict(key=target['key'], **s) for s in stages)
    return dict(kind=q.EVIDENCE+'-result', stages=flat, execution_result=dict(cases=cases,
        scan_completed=True, diagnostic_accepted=True, unexecuted_keys=[], unfinished_keys=[],
        provider_calls=len(flat), unknown_reserved_tokens=0), accounting=dict(calls=len(flat),
        unknown_usage_calls=0, local_attempts_without_transport_receipt=0))


def test_prepared_combo_does_not_authorize_or_admit(prepared):
    preparation, saved = prepared
    assert q.require_plan(saved, preparation) == saved['preparation_plan']
    assert not any(preparation[k] for k in ('execution_authorized', 'execution_ready',
        'review_controls_qualified', 'actual_product_task_qualified', 'production_admitted'))
    assert len(q.require_coverage(synthetic_seal(preparation), preparation)) == 35


@pytest.mark.parametrize('fault', ['policy', 'editor', 'timing', 'source', 'input', 'label',
    'request', 'principal', 'subset', 'historical_credit', 'head_missing', 'rehearsal'])
def test_mixed_or_changed_plan_rejected(prepared, fault):
    preparation, saved = deepcopy(prepared)
    plan = saved['preparation_plan']
    if fault == 'policy': plan['candidate_policy'] = 'another-policy'
    if fault == 'editor': plan['candidate_editor'] = 'old-editor'
    if fault == 'timing': plan['request_timing_identity'] = 'old-timeout'
    if fault == 'source': plan['source_sha256'].pop(next(iter(plan['source_sha256'])))
    if fault == 'input': plan['cells'][0]['input_sha256'] = '0'*64
    if fault == 'label': plan['cells'][0]['expected_initial'] = 'reject'
    if fault == 'request': plan['cells'][0]['candidate_request_sha256'] = '0'*64
    if fault == 'principal': plan['review_principals']['independent']['principal_id'] = 'another-agent'
    if fault == 'subset': plan['sequence'].pop()
    if fault == 'historical_credit': plan['historical_reviews_reused'] = True
    if fault == 'head_missing': del saved['execution_head']
    if fault == 'rehearsal': plan['kind'] = 'offline-complete-response-binding-v1'
    with pytest.raises(ValueError, match='full_chain_qualification_'):
        q.require_plan(saved, preparation)


@pytest.mark.parametrize('fault', ['missing_case', 'duplicate_case', 'reorder', 'missing_revision',
    'missing_final', 'rejected', 'initial_wrong', 'final_low', 'unfinished', 'unknown_usage',
    'receiptless', 'extra_call', 'extra_stage', 'legacy_seal'])
def test_claimed_success_cannot_override_missing_evidence(prepared, fault):
    preparation = prepared[0]
    seal = synthetic_seal(preparation)
    result = seal['execution_result']
    reject = next(c for c in result['cases'] if len(c['stages']) == 3)
    if fault == 'missing_case': result['cases'].pop()
    if fault == 'duplicate_case': result['cases'][-1] = deepcopy(result['cases'][0])
    if fault == 'reorder': result['cases'].reverse()
    if fault == 'missing_revision': reject['stages'].pop(1)
    if fault == 'missing_final': reject['stages'].pop()
    if fault == 'rejected': reject['stages'][0]['host_accepted'] = False
    if fault == 'initial_wrong': result['cases'][0]['initial_verdict'] = 'needs_revision'
    if fault == 'final_low': reject['final_score'] = 84
    if fault == 'unfinished': result['unfinished_keys'] = [reject['key']]
    if fault == 'unknown_usage': seal['accounting']['unknown_usage_calls'] = 1
    if fault == 'receiptless': seal['accounting']['local_attempts_without_transport_receipt'] = 1
    if fault == 'extra_call': result['provider_calls'] += 1
    if fault == 'extra_stage': seal['stages'].append(deepcopy(seal['stages'][0]))
    if fault == 'legacy_seal': seal['kind'] = 'full15-resumption-candidate-result-v1'
    with pytest.raises(ValueError, match='full_chain_qualification_'):
        q.require_coverage(seal, preparation)


def observation_files(tmp_path):
    worker = str((tmp_path/'run/stream-001').resolve())
    side = tmp_path/'obs'/hashlib.sha256(worker.encode()).hexdigest()
    (side/'sampling').mkdir(parents=True)
    parent = dict(transport_complete=True, elapsed_ms=1, observation_present=True,
        observation_age_ms=1, observation_valid=True, observation_failure=False, files={})
    sample = dict(schema_version='stream-observation-v1', body_free=True, http_requests=1,
        response_status=200, closed=True, exception_type=None, raw_bytes=100)
    row = dict(state='valid', worker_directory=worker, files={k:'0'*64 for k in
        ('binding.json', 'parent-audit.json', 'sampling/anchor.json', 'sampling/observation.json')})
    return side, parent, sample, row


@pytest.mark.parametrize('fault', [None, 'fixture', 'missing_sample', 'missing_author', 'retry', 'http_error', 'partial'])
def test_http_receipt_shape_cannot_be_replaced_by_fixture(tmp_path, fault):
    side, parent, sample, row = observation_files(tmp_path)
    seal = dict(body_free_observations=[row], author_evidence={'test':{}})
    if fault == 'fixture': parent['fixture'] = 'OFFLINE'
    if fault == 'missing_sample': del row['files']['sampling/observation.json']
    if fault == 'missing_author': seal['author_evidence'] = {}
    if fault == 'retry': sample['http_requests'] = 2
    if fault == 'http_error': sample['response_status'] = 500
    if fault == 'partial': sample['closed'] = False
    (side/'parent-audit.json').write_text(json.dumps(parent), encoding='utf-8')
    (side/'sampling/observation.json').write_text(json.dumps(sample), encoding='utf-8')
    session = NS(observations=tmp_path/'obs')
    if fault is None:
        q.require_http_observations(session, seal, [1])  # shape only; hashes are checked by strict replay
    else:
        with pytest.raises(ValueError, match='full_chain_qualification_'):
            q.require_http_observations(session, seal, [1])


@pytest.mark.parametrize('fault', [None, 'native_missing', 'seal_changed', 'mutation', 'ci_wrong_head'])
@pytest.mark.parametrize('execution_profile', [False, True])
def test_validation_orchestration_reads_native_and_never_writes_run(tmp_path, monkeypatch, prepared, fault, execution_profile):
    # Boundary orchestration uses a synthetic replay backend. Existing real
    # FullChainEvidence integration tests cover native/author/receipt replay.
    preparation, saved = deepcopy(prepared)
    if execution_profile:
        from scripts import full_chain_execution as execution
        preparation = q.prepare(execution_profile=execution.VERSION)
        plan = saved['preparation_plan']
        plan.update(execution_profile=execution.VERSION, run_id=execution.RUN_ID,
                    budget=execution.budget_for(plan))
        plan['source_sha256'].update(preparation['execution_source_sha256'])
    run = tmp_path/'run'; run.mkdir()
    saved['preparation_plan']['evidence_paths'].update(directory=str(run), answers=str(tmp_path/'answers'),
        observations=str(tmp_path/'obs'))
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    (run/'submission-close.lock').write_bytes(b'')
    seal = synthetic_seal(preparation)
    seal['original_file_sha256'] = {p.name:q.sha(p) for p in run.iterdir()}
    prep_path, seal_path = tmp_path/'preparation.json', tmp_path/'seal.json'
    prep_path.write_text(json.dumps(preparation), encoding='utf-8')
    seal_path.write_text(json.dumps(seal), encoding='utf-8')
    seen = []
    def snapshot(): return {p.name:q.sha(p) for p in run.iterdir()}
    def replay(directory, *, event_source):
        seen.append('native-replay')
        if fault == 'native_missing': raise ValueError('native_final_unavailable')
        if fault == 'mutation': (run/'pollution').write_bytes(b'x')
        result = deepcopy(seal)
        if fault == 'seal_changed': result['accounting']['known_tokens'] = 1
        return result
    session = NS(snapshot=snapshot, check=lambda:seen.append('inventory'),
        evidence=NS(load_plan=lambda p:saved['preparation_plan'], replay=replay))
    class Native:
        def __init__(self, executable): seen.append('native-open')
        def __enter__(self): return self
        def __exit__(self, *args): seen.append('native-close')
    monkeypatch.setattr(q, 'prepare', lambda **kwargs:deepcopy(preparation))
    monkeypatch.setattr(q, 'FullChainEvidence', lambda **kwargs:session)
    if execution_profile:
        monkeypatch.setattr(execution, 'ControlledFullChain', lambda **kwargs:session)
    monkeypatch.setattr(q, 'require_http_observations', lambda *args:seen.append('observations'))
    monkeypatch.setattr(q, 'verify_public_ci', lambda run_id:'b'*40 if fault == 'ci_wrong_head' else 'a'*40)
    monkeypatch.setattr(q, 'CodexReadOnlyClient', Native)
    monkeypatch.setattr(q, 'CodexHostReviewEventSource', lambda *args:object())
    call = lambda:q.validate(preparation_path=prep_path, preparation_sha=q.sha(prep_path), directory=run,
        seal_path=seal_path, seal_sha=q.sha(seal_path), codex_executable='test-native')
    before = snapshot()
    if fault is None:
        result = call()
        assert result['accepted_inputs'] == 15 and result['certified_stages'] == 35
        assert result['review_controls_qualified'] and not result['production_admitted']
        assert not result['actual_product_task_qualified'] and not result['execution_authorized']
        assert seen == ['inventory', 'observations', 'native-open', 'native-replay', 'native-close']
    else:
        with pytest.raises(ValueError): call()
    if fault != 'mutation': assert before == snapshot()


def test_historical_batches_and_rehearsals_are_not_eligible(prepared):
    candidates = [q.ROOT/'data/evaluation/results'/f'golden_document_{name}_time600_result_{day}.json'
        for name, day in [('full15','20261010'),('remaining8','20261011'),('remaining4','20261011')]]
    candidates += [q.ROOT/'data/evaluation/results/full_chain_host_rehearsal_20261013'/name/'seal.json'
        for name in ('initial-disagreement','explicit-count')]
    for path in candidates:
        before = q.sha(path)
        with pytest.raises(ValueError, match='full_chain_qualification_'):
            q.require_coverage(q.read(path), prepared[0])
        assert q.sha(path) == before


def test_cli_rejects_old_batch_without_native_or_output(tmp_path, monkeypatch, prepared):
    old = q.ROOT/'data/evaluation/results/golden_document_full15_time600_result_20261010.json'
    run = tmp_path/'legacy-run'; run.mkdir()
    (run/'plan.json').write_text(json.dumps(q.read(old)['public_json_contents']['plan.json']), encoding='utf-8')
    prep = tmp_path/'preparation.json'
    prep.write_text(json.dumps(prepared[0]), encoding='utf-8')
    output = tmp_path/'not-created.json'
    monkeypatch.setattr('sys.argv', ['qualify', 'validate', '--output', str(output),
        '--preparation', str(prep), '--preparation-sha', q.sha(prep), '--directory', str(run),
        '--seal', str(old), '--seal-sha', q.sha(old), '--codex-executable', 'must-not-start'])
    monkeypatch.setattr(q, 'CodexReadOnlyClient', lambda *args:pytest.fail('native must not start'))
    before = {p.name:q.sha(p) for p in run.iterdir()}
    with pytest.raises(ValueError, match='legacy_evidence_paths'):
        q.main()
    assert not output.exists() and before == {p.name:q.sha(p) for p in run.iterdir()}
