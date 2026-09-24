"""Bounded diagnostic control-flow tests, never real-model qualification."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from scripts import diagnose_role_context as runner
from tests.test_review_model_comparison import fake_provider


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def response(*, valid=True):
    value = dict(score=96, verdict='pass', issues=[], advisories=[], issue_resolutions=[])
    if not valid:
        value = dict(score=84, verdict='needs_revision', advisories=[], issue_resolutions=[], issues=[
            dict(block=4, category='fact_error', source_ids=[1], explanation='Synthetic false positive.',
                suggested_correction='Synthetic correction, missing required severity.')])
    return ChatResponse(content=None, provider='zhipu', model='glm-5.3', finish_reason='tool_calls',
        usage=TokenUsage(20, 10), tool_calls=(ToolCall('test', 'submit_report_review', value),))


def round_review(flags):
    def review(path, remaining):
        assert remaining > 0
        rows = json.loads(path.read_text(encoding='utf-8'))
        return dict(round_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), observations=[
            dict(condition=row['condition'], response_sha256=row['response_sha256'],
                target_overgeneralization=flag, review_acceptable=False, reason='Synthetic diagnostic classification.')
            for row, flag in zip(rows, flags, strict=True)])
    return review


def test_factorial_preserves_target_sources_and_never_sends_labels(prepared):
    plan, variants = prepared
    assert len(variants) == 4 and len(plan['order']) == 8
    assert plan['budget']['max_calls'] == 8 and not plan['qualification_evidence']
    rows = {r['id']: r for r in plan['cells']}
    assert {rows[k]['block_count'] for k in ('original', 'expanded')} == {25}
    assert {rows[k]['block_count'] for k in ('no_intro', 'expanded_no_intro')} == {24}
    for name, (inputs, request) in variants.items():
        row = rows[name]
        assert runner.digest(inputs.source.blocks[row['target_block_host_only']-1][1]) == plan['original_target_sha256']
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        assert hashlib.sha256(raw).hexdigest() == row['request_sha256']
        for forbidden in ('target_block_host_only', 'target_overgeneralization', 'historical_success', 'expected_initial'):
            assert forbidden not in raw.decode()
    original = variants['original'][0].source.report
    expanded = variants['expanded'][0].source.report
    assert '以上统计不能证明个人能力或胜负原因。' in original
    assert '以上统计不能证明个人能力或胜负原因。' not in expanded


@pytest.mark.parametrize('flags,expected', [([True]*4, 4), ([False]*4, 4), ([True,False,True,False], 8)])
def test_predetermined_semantic_contrast_controls_second_round(prepared, tmp_path, flags, expected):
    plan, variants = prepared
    provider = fake_provider([response() for _ in range(8)])
    calls = []
    original = provider.chat
    def chat(request):
        calls.append(validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID))
        return original(request)
    provider.chat = chat
    result = runner.observe(provider, tmp_path, plan, variants, review_round=round_review(flags))
    assert result['completed'] and result['provider_requests'] == expected
    assert result['unknown_usage_calls'] == 0 and not result['semantic_fix_verified']
    if expected == 8:
        assert calls[:4] == list(reversed(calls[4:]))


def test_missing_severity_is_observed_never_repaired_or_accepted(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([response(valid=False) for _ in range(8)])
    result = runner.observe(provider, tmp_path, plan, variants, review_round=round_review([True]*4))
    assert result['provider_requests'] == 4 and result['completed']
    assert all(not r['protocol_valid'] for r in result['cases'])
    saved = json.loads((tmp_path/'01-original/response.json').read_text(encoding='utf-8'))
    assert 'severity' not in saved['tool_calls'][0]['arguments']['issues'][0]
    assert 'severity' in (tmp_path/'01-original/journal.json').read_text(encoding='utf-8')


@pytest.mark.parametrize('fault', ['model', 'receipt', 'channel', 'security', 'transport'])
def test_unusable_execution_stops_without_followup(prepared, tmp_path, fault):
    plan, variants = prepared
    provider = fake_provider([response() for _ in range(8)])
    chat = provider.chat
    def broken(request):
        answer = chat(request)
        if fault == 'transport':
            raise RuntimeError('context_test_interrupted')
        if fault == 'receipt':
            provider.last_exchange = None
        elif fault == 'model':
            answer = replace(answer, model='glm-5.3-flash')
        elif fault == 'channel':
            answer = replace(answer, content='unaccepted prose')
        elif fault == 'security':
            value = dict(answer.tool_calls[0].arguments, issues=[dict(category='prompt_injection',severity='high')])
            answer = replace(answer, tool_calls=(replace(answer.tool_calls[0], arguments=value),))
        if provider.last_exchange is not None:
            provider.last_exchange = replace(provider.last_exchange, response=answer)
        return answer
    provider.chat = broken
    result = runner.observe(provider, tmp_path, plan, variants, review_round=lambda *_: pytest.fail('unsafe followup'))
    assert not result['completed'] and result['provider_requests'] == 1
    assert result['unknown_usage_calls'] == int(fault == 'transport')


def test_budget_does_not_shorten_repeat_request_or_retry(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([response() for _ in range(8)])
    now = [0]
    chat = provider.chat
    def slow(request):
        answer = chat(request)
        now[0] = 2200
        return answer
    provider.chat = slow
    result = runner.observe(provider, tmp_path, plan, variants, clock=lambda: now[0])
    assert result['provider_requests'] == 1 and result['error_code'] == 'context_batch_budget'


@pytest.mark.parametrize('severity', ['low', 'medium'])
def test_valid_non_high_injection_still_stops_before_next_call(prepared, tmp_path, severity):
    plan, variants = prepared
    answer = response(valid=False)
    value = dict(answer.tool_calls[0].arguments)
    value['issues'] = [dict(value['issues'][0], category='prompt_injection', severity=severity)]
    answer = replace(answer, tool_calls=(replace(answer.tool_calls[0],arguments=value),))
    provider = fake_provider([answer]*8)
    result = runner.observe(provider,tmp_path,plan,variants)
    assert not result['completed'] and result['provider_requests'] == 1
    assert result['error_code'] == 'native_security_terminal'


def test_preflight_time_counts_before_any_provider_io(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([response()]*8)
    now = [0]
    def preflight():
        now[0] = 2200
    result = runner.observe(provider,tmp_path,plan,variants,before_send=preflight,clock=lambda: now[0])
    assert result['provider_requests'] == 0 and result['error_code'] == 'context_batch_budget'


def test_unknown_partial_usage_survives_stop(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([response()])
    def interrupted(request):
        provider._calls += 1
        stream = tmp_path/'transport/stream-001'
        stream.mkdir(parents=True)
        from app.evaluation.golden_stream_bridge import CapacityBridgeObservation
        (stream/'progress.json').write_text(CapacityBridgeObservation(state='failed', input_tokens=12,
            output_tokens=8).model_dump_json(),encoding='utf-8')
        raise RuntimeError('context_test_interrupted')
    provider.chat = interrupted
    result = runner.observe(provider,tmp_path,plan,variants)
    assert result['unknown_usage_calls'] == 0
    assert (result['input_tokens'],result['output_tokens']) == (12,8)


def test_host_binding_error_stops_after_four(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([response() for _ in range(8)])
    result = runner.observe(provider, tmp_path, plan, variants, review_round=lambda *_: {'round_sha256':'bad'})
    assert not result['completed'] and result['provider_requests'] == 4


def test_real_receipted_transport_preserves_all_repeated_request_bytes(prepared, tmp_path, monkeypatch):
    from app.evaluation import golden_stream_bridge as bridge
    from app.evaluation.golden_journal import write_new_json
    captured = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        assert environ['LLM_MODEL'] == 'glm-5.3' and transport_id == REVIEW_MODEL_TRANSPORT_ID
        assert timeout_s == 300
        captured.append(raw)
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        return response()
    monkeypatch.setattr(bridge, 'run_child', child)
    settings = NS(model='glm-5.3', api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    provider = runner.ReceiptedStreamProvider(settings=settings, directory=tmp_path/'transport',
        transport_id=REVIEW_MODEL_TRANSPORT_ID)
    result = runner.observe(provider,tmp_path,*prepared,review_round=round_review([True,False,True,False]))
    assert result['completed'] and result['provider_requests'] == 8
    assert captured[:4] == list(reversed(captured[4:]))
    for n, raw in enumerate(captured, 1):
        reservation = json.loads((tmp_path/f'transport/stream-{n:03d}/reservation.json').read_text())
        assert reservation['request_sha256'] == hashlib.sha256(raw).hexdigest()


def test_execution_requires_frozen_plan_ci_and_closes_permanently(prepared, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'prepare', lambda: prepared)
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed.json')
    plan_path = tmp_path/'plan.json'
    plan_path.write_text(json.dumps(prepared[0]),encoding='utf-8')
    monkeypatch.setattr(runner, 'PREPARATION', plan_path)
    monkeypatch.setattr(runner, 'verify_public_ci', lambda *_: pytest.fail('bad plan reached CI'))
    with pytest.raises(ValueError, match='context_preparation_required'):
        runner.run(NS(execute=True, plan_sha='wrong',env_file=None,ci_run=''))
    runner.CLOSED_RESULT.write_text('{}')
    monkeypatch.setattr(runner, 'prepare', lambda: pytest.fail('closed batch prepared inputs'))
    with pytest.raises(ValueError, match='context_batch_closed'):
        runner.run(NS(execute=True))
