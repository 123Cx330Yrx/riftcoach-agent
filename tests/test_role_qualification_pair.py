"""Real runner plumbing with synthetic transport; never live qualification."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.role_qualification import frozen_cases, read_role_calls, replay_case, validate_qualification
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_role_qualification_pair as runner
from scripts.prepare_role_qualification import PAIR_EVIDENCE


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def response(value):
    return ChatResponse(content=None, model='glm-5.3', provider='zhipu',
        finish_reason='tool_calls', usage=TokenUsage(20, 10),
        tool_calls=(ToolCall('offline-submit', 'submit_report_review', value),))


@pytest.fixture
def setup_pair(tmp_path, monkeypatch, prepared):
    prior = json.loads(PAIR_EVIDENCE.read_text(encoding='utf-8'))['original_json_contents']
    original = prior['attribution_original-baseline/response.json']['tool_calls'][0]['arguments']
    correct = prior['attribution_corrected-baseline/response.json']['tool_calls'][0]['arguments']
    sources = {f['key']: source for f, source in frozen_cases()[0]}
    edit = ChatResponse(content=sources['claim-scope:1'].report, provider='zhipu',
        model='glm-5.3-flash', finish_reason='stop', usage=TokenUsage(20, 10))
    queue = [response(original), edit, response(correct), response(correct)]
    calls = []

    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        calls.append(json.loads(raw))
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        assert answer.model == environ['LLM_MODEL']
        write_new_json(directory / 'result.json', dict(state='complete', transport_id=transport_id))
        return answer

    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return SimpleNamespace(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path / 'transport')
    return dict(directory=tmp_path, plan=prepared[0], factory=factory, queue=queue, calls=calls,
        original=original, correct=correct, source=sources)


def accept(path, remaining):
    assert remaining > 0
    return dict(accepted=True, response_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def observe(setup, **kwargs):
    return runner.observe(setup['factory'], setup['directory'], setup['plan'],
        adjudicate=kwargs.pop('adjudicate', accept), **kwargs)


def test_preview_is_stable_bounded_and_no_paid_settings(prepared, monkeypatch):
    monkeypatch.setattr(runner, 'load_role_settings', lambda *_: pytest.fail('preview loaded credentials'))
    result = runner.run(SimpleNamespace(execute=False))
    assert result['preparation_plan_sha256'] == digest(compact(prepared[0]))
    assert result['provider_requests'] == 0
    assert result['plan']['batch_budget']['max_calls'] == 7
    assert result['plan']['batch_budget']['max_seconds'] == 1500
    assert [c['expected_initial'] for c in result['plan']['cases']] == ['reject', 'accept']
    for raw in prepared[1].values():
        assert b'expected_initial' not in raw and b'expected_host_only' not in raw


def test_full_pair_records_actual_edit_host_stages_and_qualification_bindings(setup_pair):
    checked = []
    def adjudicate(path, remaining):
        checked.append((path.name, len(setup_pair['calls'])))
        return accept(path, remaining)
    result = observe(setup_pair, adjudicate=adjudicate)
    assert result['pair_accepted'] is True
    assert checked == [('initial.json', 1), ('revision.json', 2), ('final.json', 3), ('initial.json', 4)]
    assert [row['accounting']['reserved_calls'] for row in result['cases']] == [3, 1]
    assert not result['review_controls_qualified'] and not result['production_admitted']
    first = result['cases'][0]
    assert first['accounting']['revision_completed']
    assert first['final_report_sha256'] == digest(setup_pair['source']['claim-scope:1'].report)
    # A pair is a valid fragment, never a full fifteen-case qualification.
    with pytest.raises(ValueError, match='case_inventory_mismatch'):
        validate_qualification(dict(qualification_version=setup_pair['plan']['qualification_version'],
            identity=setup_pair['plan']['identity'], plan_sha256=setup_pair['plan']['qualification_plan_sha256'],
            cases=[row['qualification_row'] for row in result['cases']]), evidence_root=setup_pair['directory'])


@pytest.mark.parametrize('stage,expected_calls', [('initial', 1), ('revision', 2), ('final', 3)])
def test_semantic_rejection_stops_before_next_io(setup_pair, stage, expected_calls):
    def adjudicate(path, remaining):
        return dict(accept(path, remaining), accepted=path.stem != stage)
    result = observe(setup_pair, adjudicate=adjudicate)
    assert not result['pair_accepted'] and result['error_code'] == 'role_pair_host_rejected'
    assert len(setup_pair['calls']) == expected_calls
    assert len(result['cases']) == 1


def test_bad_host_hash_and_stale_first_request_stop_without_followup(setup_pair):
    result = observe(setup_pair, adjudicate=lambda *_: dict(accepted=True, response_sha256='0' * 64))
    assert result['error_code'] == 'role_pair_host_binding_invalid'
    assert len(setup_pair['calls']) == 1


def test_prepared_request_drift_stops_before_provider(setup_pair):
    setup_pair['plan'] = deepcopy(setup_pair['plan'])
    setup_pair['plan']['cases'][0]['request_sha256'] = '0' * 64
    result = observe(setup_pair)
    assert result['error_code'] == 'role_pair_first_request_changed'
    assert not setup_pair['calls']


def test_format_recovery_requires_host_check_of_original_bad_response(setup_pair):
    bad = deepcopy(setup_pair['original'])
    bad['unrequested_field'] = 'do not silently strip'
    setup_pair['queue'].insert(0, response(bad))
    checked = []
    def adjudicate(path, remaining):
        checked.append(path.stem)
        if path.stem.startswith('reassessment-before-'):
            saved = json.loads(path.read_text(encoding='utf-8'))
            assert saved['journal']['previous_response']['tool_calls'][0]['arguments'] == bad
            return dict(accept(path, remaining), accepted=False)
        return accept(path, remaining)
    result = observe(setup_pair, adjudicate=adjudicate)
    assert checked == ['reassessment-before-2']
    assert not result['pair_accepted'] and len(setup_pair['calls']) == 1


def test_host_time_consumes_same_deadline(setup_pair):
    now = [0.0]
    def adjudicate(path, remaining):
        now[0] += 901
        return accept(path, remaining)
    result = observe(setup_pair, adjudicate=adjudicate, clock=lambda: now[0])
    assert result['error_code'] == 'role_pair_execution_limit'
    assert len(setup_pair['calls']) == 1


def test_incomplete_transport_keeps_unknown_usage_and_closes_batch(setup_pair):
    setup_pair['queue'][0] = RuntimeError('offline interrupted transport')
    result = observe(setup_pair)
    assert not result['pair_accepted'] and len(setup_pair['calls']) == 1
    accounting = result['cases'][0]['accounting']
    assert accounting['reserved_calls'] == accounting['unknown_usage_calls'] == 1
    assert accounting['total_estimated_uncached_cny'] is None


def test_low_score_pass_does_not_qualify_runner_or_replay(setup_pair):
    setup_pair['queue'][2] = response(dict(setup_pair['correct'], score=84))
    result = observe(setup_pair)
    assert result['error_code'] == 'role_pair_final_review_failed'
    assert len(setup_pair['calls']) == 3
    frozen, source = {f['key']: (f, s) for f, s in frozen_cases()[0]}['attribution:1']
    calls = read_role_calls(setup_pair['directory'] / 'transport/attribution-1')
    with pytest.raises(ValueError, match='final_review_failed'):
        replay_case(frozen, source, calls)


def test_response_without_completion_receipt_cannot_form_accepted_fragment(setup_pair):
    def adjudicate(path, remaining):
        if path.stem == 'final':
            (setup_pair['directory'] / 'transport/attribution-1/call-result-003.json').unlink()
        return accept(path, remaining)
    result = observe(setup_pair, adjudicate=adjudicate)
    assert not result['pair_accepted']
    assert result['error_code'] == 'role_pair_incomplete_receipts'
    assert len(setup_pair['calls']) == 3
    assert result['cases'][0]['accounting']['observed_unaccepted_calls'] == 1
    assert not (setup_pair['directory'] / 'attribution-1/host-review.json').exists()


def test_closed_batch_cannot_restart_even_without_local_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path / 'never-created')
    for name in ('prepare', 'verify_public_ci', 'load_role_settings'):
        monkeypatch.setattr(runner, name, lambda *_: pytest.fail('closed batch performed execution IO'))
    with pytest.raises(ValueError, match='role_pair_batch_closed'):
        runner.run(SimpleNamespace(execute=True))
    assert not runner.RUN_DIRECTORY.exists()
