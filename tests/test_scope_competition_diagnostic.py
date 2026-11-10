"""Real receipt/handoff plumbing with scripted transport; no model quality claims."""
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts import run_scope_competition_diagnostic as runner
from scripts import scope_competition_handoff as handoff
from tests.test_scope_resolution_diagnostic import Host
from tests.test_scope_competition_prototype import answer, check, issue


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


def factory(tmp_path, monkeypatch, fault=None):
    seen = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw, strict=True)
        assert transport_id == bridge.REVIEW_MODEL_TRANSPORT_ID
        assert 'previous_review' not in runner.prototype._data(request)
        seen.append(request)
        if fault == 'transport':
            raise RuntimeError('Synthetic interruption')
        explicit = len(seen) == 2
        issues = [issue(6, 'Synthetic true pooled CS error')]
        if explicit: issues.insert(0, issue(4, 'Synthetic explicit MIDDLE error'))
        value = answer(checks=[] if explicit else [check()], issues=issues)
        if fault == 'schema': value.pop('scope_checks')
        if fault == 'missing_audit': value['scope_checks'] = []
        if fault == 'wrong_audit': value['scope_checks'] = [check(cohort='MIDDLE')]
        if fault == 'missed_error': value.update(issues=[], score=96, verdict='pass')
        if fault == 'false_positive': value['issues'].insert(0, issue(4, 'Synthetic false issue'))
        runner.base.write_new_json(directory / 'result.json', dict(state='complete', elapsed_ms=0,
            transport_id=transport_id))
        return ChatResponse(provider='zhipu', model='glm-5.3', content=None,
            finish_reason='tool_calls', usage=TokenUsage(input_tokens=20, output_tokens=10),
            tool_calls=(ToolCall(id='synthetic-review', name='submit_report_review', arguments=value),))
    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return SimpleNamespace(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
    actual = runner.base.RunScopedRoleReceiptedProviderFactory(
        generator_settings=settings('glm-5.3-flash'), reviewer_settings=settings('glm-5.3'),
        transport_root=tmp_path / 'transport',
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return actual, seen


@pytest.mark.parametrize('fault,calls', [(None, 2), ('schema', 1), ('missing_audit', 1),
    ('wrong_audit', 1), ('missed_error', 1), ('false_positive', 1), ('reject', 1),
    ('identity', 1), ('unavailable', 1), ('transport', 1), ('budget', 0)])
def test_first_failure_stops_and_unknown_usage_is_not_released(tmp_path, monkeypatch, fault, calls):
    plan = deepcopy(prepared())
    if fault == 'budget': plan['budget']['max_tokens'] = 1
    host = Host(plan, fault)
    actual, seen = factory(tmp_path, monkeypatch, fault)
    result = runner.observe(actual, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert result['calls'] == len(seen) == calls, result
    assert result['diagnostic_accepted'] == (fault is None), result
    assert not result['product_admitted'] and not result['original15_qualified']
    assert (result['unknown_reserved_tokens'] > 0) == (fault == 'transport')
    assert all(a['role'] == 'review' for a in result['attempts'])
    if fault is None:
        assert result['known_tokens'] == 60
        assert len(runner.read_completed_calls(tmp_path/'transport/diagnostic')) == 2
    if calls < 2:
        assert not (tmp_path / runner.KEYS[1]).exists()


def test_actual_receipt_handoff_import_is_bound_and_create_only(tmp_path, monkeypatch):
    plan = prepared()
    runner.base.write_new_json(tmp_path/'plan.json', dict(preparation_plan=plan,
        plan_sha256=runner.base.canonical_sha(plan)))
    host = Host(plan)
    actual, seen = factory(tmp_path, monkeypatch)
    def inspect(path, remaining):
        key = path.parent.name
        task = json.loads(handoff.task(tmp_path, key))
        submission = host.adjudicate(path, remaining)
        assert task['binding'] == submission['primary']['binding']
        assert 'host_only_expected' not in task['instructions']
        notes = {k: submission['primary']['stage_assessment'][k]
                 for k in ('accepted', 'defects', 'source_review')}
        event_id = submission['independent']['independent_source_event']['event_id']
        handoff.submit(tmp_path, key, notes, event_id, host)
        with pytest.raises(FileExistsError): handoff.submit(tmp_path, key, notes, event_id, host)
        return json.loads((path.parent/'review-submission.json').read_bytes())
    result = runner.observe(actual, tmp_path, plan, event_source=host, adjudicate=inspect)
    assert result['diagnostic_accepted'], result
    assert len(seen) == 2
    with pytest.raises(ValueError, match='batch_closed'): handoff.material(tmp_path, runner.KEYS[0])


@pytest.mark.parametrize('fault', ['request', 'model', 'ordinal', 'reservation', 'usage', 'terminal', 'orphan'])
def test_replayed_receipt_tampering_is_rejected(tmp_path, monkeypatch, fault):
    plan = prepared()
    host = Host(plan)
    actual, _ = factory(tmp_path, monkeypatch)
    assert runner.observe(actual, tmp_path, plan, event_source=host,
        adjudicate=host.adjudicate)['diagnostic_accepted']
    root = tmp_path/'transport/diagnostic'
    path = root/'call-001.json'
    if fault == 'request': path = root/'review/request-001.json'
    if fault == 'reservation': path = root/'review/stream-001/reservation.json'
    if fault == 'terminal': path = root/'review/stream-001/result.json'
    if fault == 'usage': path = root/'call-result-001.json'
    value = json.loads(path.read_bytes())
    if fault == 'request': value['temperature'] = .1
    if fault == 'model': value['model'] = 'glm-5.3-flash'
    if fault == 'ordinal': value['ordinal'] = True
    if fault == 'reservation': value['request_sha256'] = '0'*64
    if fault == 'terminal': value['state'] = 'reading'
    if fault == 'usage': value['input_tokens'] = True
    if fault == 'orphan': path = root/'call-result-003.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError): runner.read_completed_calls(root)


def test_changed_request_and_reused_sender_cannot_send_or_retry(tmp_path, monkeypatch):
    actual, seen = factory(tmp_path, monkeypatch)
    clock = runner.base.DevelopmentHostClock(tmp_path, max_host_seconds=10)
    send = runner.DiagnosticSender(actual('diagnostic').reviewer, prepared(), clock)
    request = runner.controls()[0][2]
    with pytest.raises(ValueError): send(replace(request, temperature=.1))
    with pytest.raises(ValueError, match='sender_stopped'): send(request)
    assert not seen and send.calls == 0


def test_plan_budget_labels_and_old_product_rejection_are_preserved():
    plan = prepared()
    assert plan['budget']['max_calls'] == 2 and plan['budget']['estimated_uncached_cny'] == '2.859008'
    assert not plan['execution_authorized'] and plan['historical_initial_inputs'] == 0
    from app.runtime.reviewer_roles import role_for_request
    for cell, _, request in runner.controls():
        with pytest.raises(ValueError): role_for_request(request,
            source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
        assert 'host_only_' not in str(request.messages)
        assert cell['request_sha256'] == runner.base.digest(runner.base.validate_request(
            request, transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID).decode('utf-8'))


def test_ci_and_frozen_plan_checked_before_credentials(tmp_path, monkeypatch):
    plan = prepared()
    monkeypatch.setattr(runner, 'prepare', lambda **_: plan)
    monkeypatch.setattr(runner.base, 'ROOT', tmp_path)
    frozen = tmp_path/'plan.json'
    frozen.write_text(json.dumps(plan), encoding='utf-8')
    args = SimpleNamespace(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent',
        execute=True, preparation=frozen, env_file=tmp_path/'absent.env', codex_executable=tmp_path/'absent.exe',
        plan_sha=runner.base.canonical_sha(plan), ci_run='synthetic')
    def forbidden(*_): pytest.fail('credentials read before CI')
    monkeypatch.setattr(runner.base, 'load_role_settings', forbidden)
    def reject(*_): raise ValueError('synthetic_ci_failure')
    monkeypatch.setattr(runner.base, 'verify_public_ci', reject)
    with pytest.raises(ValueError, match='synthetic_ci_failure'): runner.run(args)
    frozen.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='preparation_required'): runner.run(args)


def test_valid_subspan_audit_is_not_forced_to_copy_host_label():
    cell, inputs, _ = runner.controls()[0]
    scope = check()
    scope['claim']['exact_text'] = '早期死亡在胜败样本间'
    _, wire, _ = runner.prototype.validate(runner.base.compact(answer(checks=[scope],
        issues=[issue(6, 'Synthetic true error')])), inputs)
    runner.expected_findings(wire, cell, inputs)


def test_complete_observed_usage_settles_even_if_receipt_write_fails(tmp_path, monkeypatch):
    from app.evaluation import golden_journal
    actual, seen = factory(tmp_path, monkeypatch)
    original = golden_journal.write_new_json
    def fail_result(path, value):
        if path.name == 'call-result-001.json':
            raise OSError('Synthetic receipt write failure')
        return original(path, value)
    monkeypatch.setattr(golden_journal, 'write_new_json', fail_result)
    plan = prepared()
    host = Host(plan)
    result = runner.observe(actual, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert not result['diagnostic_accepted'] and result['calls'] == len(seen) == 1
    assert result['known_tokens'] == 30 and result['unknown_reserved_tokens'] == 0
    assert not (tmp_path/runner.KEYS[1]).exists()


def test_close_during_event_fetch_cannot_publish_late_handoff(tmp_path, monkeypatch):
    plan = prepared()
    key = runner.KEYS[0]
    arm = tmp_path/key
    arm.mkdir()
    bound = dict(plan_sha256=runner.base.canonical_sha(plan), key=key, stage='initial',
        request_sha256='a'*64, response_sha256='b'*64, report_sha256='c'*64)
    stage = dict(stage='initial', report='Synthetic report', journal={})
    path = arm/'review-required.json'
    runner.base.write_new_json(path, dict(binding=bound, stage_sha256=runner.base.stage_identity(stage)))
    host = Host(plan)
    submission = host.adjudicate(path, 10)
    monkeypatch.setattr(handoff, 'material', lambda *_: (plan, stage, bound))
    fetch = host.fetch
    def close(**kwargs):
        if not (tmp_path/'result.json').exists():
            runner.previous.close_result(tmp_path, dict(diagnostic_accepted=False))
        return fetch(**kwargs)
    host.fetch = close
    event_id = submission['independent']['independent_source_event']['event_id']
    with pytest.raises(ValueError, match='batch_closed'):
        handoff.submit(tmp_path, key, dict(accepted=True, defects=[], source_review='Synthetic'), event_id, host)
    assert not (arm/'review-submission.json').exists()
