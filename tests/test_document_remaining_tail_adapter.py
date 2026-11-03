"""Public fixtures and synthetic IO verify selection, not model quality."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import document_remaining_tail_adapter as adapter
from scripts import run_document_accepted_tails as old_legacy
from scripts import run_document_checkpoint_tails as old_runner
from scripts import document_checkpoint_tail_handoff as old_handoff
from scripts import seal_document_checkpoint_tails as old_seal
from tests.test_document_accepted_tails import public_controls, unique_host
from tests.test_document_checkpoint_tails import actual_factory, public_checkout_only


@pytest.fixture(scope='module')
def frozen():
    variants = public_controls()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(adapter.original, 'controls', lambda: variants)
        plan = adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
        original = old_runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
    return plan, variants, original


@pytest.fixture
def setup(tmp_path, monkeypatch, frozen):
    plan, all_variants, _ = frozen
    plan = deepcopy(plan)
    monkeypatch.setattr(adapter.original, 'controls', lambda: all_variants)
    monkeypatch.setattr(adapter.runner, 'prepare', lambda **_: plan)
    variants = adapter.controls()
    policy_root = tmp_path / 'public-policy-inputs'
    for row, _, _, _, historical, _ in variants:
        path = policy_root / row['key'].replace(':', '-') / 'issued-request.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(adapter.base.validate_request(historical.issued_request,
            transport_id=adapter.base.REVIEW_MODEL_TRANSPORT_ID))
    monkeypatch.setattr(adapter.runner, 'HISTORICAL_RUN', policy_root)
    adapter.base.write_new_json(tmp_path / 'plan.json', dict(preparation_plan=plan,
        plan_sha256=adapter.base.canonical_sha(plan)))
    return plan, variants


def test_selection_keeps_requests_and_old_modules_unchanged(frozen):
    plan, variants, original = frozen
    assert plan['sequence'] == list(adapter.KEYS)
    assert plan['cells'] == original['cells'][1:]
    assert plan['identity'] == original['identity']
    assert plan['historical_initial_inputs'] == 5
    assert plan['role_calls'] == {'glm-5.3-flash': 5, 'glm-5.3': 5}
    assert plan['budget']['max_calls'] == 10
    assert plan['budget']['max_tokens'] == 967680
    assert plan['budget']['max_active_seconds'] == 3000
    assert plan['budget']['estimated_uncached_cny'] == '7.862272'
    assert not plan['execution_authorized'] and plan['excluded_case']['credit'] == 0
    assert plan['run_id'] != old_runner.RUN_ID
    assert old_legacy.KEYS == old_runner.KEYS == tuple(row['key'] for row, *_ in variants)
    assert old_handoff.runner is old_runner and old_seal.runner is old_runner
    assert adapter.handoff.runner is adapter.runner and adapter.seal.handoff is adapter.handoff
    assert all(plan['source_sha256'][k] == v for k, v in original['source_sha256'].items())
    assert set(plan['source_sha256']) - set(original['source_sha256']) == {adapter.ADAPTER_SOURCE}


@pytest.mark.parametrize('mode', ['success', 'semantic_reject', 'abort', 'missing_checkpoint',
    'native_unavailable', 'source_abort'])
def test_selected_receipted_pipeline(tmp_path, monkeypatch, setup, mode):
    plan, variants = setup
    factory, requests = actual_factory(tmp_path, monkeypatch, variants)
    host = unique_host(plan)

    def judge(path, remaining):
        bound = json.loads(path.read_bytes())['binding']
        key, stage = bound['key'], bound['stage']
        assert key in adapter.KEYS and key != 'scope:4'
        if mode in ('abort', 'source_abort'):
            if mode == 'source_abort':
                (path.parent.parent / 'source.json').write_text('{"changed":true}', encoding='utf-8')
            adapter.handoff.abort(tmp_path, key, stage, 'reviewer_unavailable')
            return adapter.runner.wait_reviews(path, remaining)
        if mode == 'missing_checkpoint':
            return host.adjudicate(path, remaining)
        packet = adapter.handoff.publish_checkpoint(tmp_path, key, stage, tmp_path / 'operator')
        host.fault = ('host_reject' if mode == 'semantic_reject' and key == adapter.KEYS[0]
            else 'host_unavailable' if mode == 'native_unavailable' else None)
        submission = host.adjudicate(path, remaining)
        notes = {k: submission['primary'][k] for k in ('stage_assessment', 'report_assessment')}
        event = submission['independent']['independent_source_event']['event_id']
        adapter.handoff.submit(tmp_path, key, stage, notes, event, host,
            packet['checkpoint'], packet['checkpoint_sha256'])
        with pytest.raises(ValueError, match='closed'):
            adapter.handoff.submit(tmp_path, key, stage, notes, event, host,
                packet['checkpoint'], packet['checkpoint_sha256'])
        return json.loads(path.with_name('review-submission.json').read_bytes())

    result = adapter.observe(factory, tmp_path, plan, event_source=host, adjudicate=judge)
    completed = mode in ('success', 'semantic_reject')
    expected_calls = 10 if mode == 'success' else 9 if mode == 'semantic_reject' else 1
    assert result['calls'] == len(requests) == expected_calls, result
    assert all(key in adapter.KEYS and role in ('revision', 'review') for key, role, _ in requests)
    assert not (tmp_path / 'scope-4').exists()
    assert result['scan_completed'] is completed, result
    assert result['diagnostic_accepted'] is (mode == 'success'), result
    assert not result['original15_qualified'] and not result['review_controls_qualified']
    if mode == 'source_abort':
        with pytest.raises(ValueError, match='source_changed'):
            adapter.seal.replay(tmp_path, event_source=host)
    else:
        rebuilt = adapter.seal.replay(tmp_path, event_source=host)
        assert rebuilt['run_id'] == adapter.RUN_ID
        assert rebuilt['accounting']['calls'] == expected_calls
        assert rebuilt['execution_result']['unexecuted_keys'] == ([] if completed else list(adapter.KEYS[1:]))
    with pytest.raises(ValueError, match='closed'):
        adapter.handoff.publish_checkpoint(tmp_path, adapter.KEYS[0], 'revision', tmp_path / 'late')


def test_existing_run_stops_before_ci_credentials_or_model(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.base, 'ROOT', tmp_path)
    (tmp_path / 'data/runs/model_comparison' / adapter.RUN_ID).mkdir(parents=True)
    with pytest.raises(ValueError, match='closed_or_exists'):
        adapter.runner.execute(SimpleNamespace(), {})


def test_prior_seal_change_stops_preparation_before_history(monkeypatch):
    monkeypatch.setattr(adapter, 'PREVIOUS_SHA', '0' * 64)
    monkeypatch.setattr(adapter.original, 'controls', lambda: pytest.fail('History must not be consumed'))
    with pytest.raises(ValueError, match='prior_seal_changed'):
        adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
