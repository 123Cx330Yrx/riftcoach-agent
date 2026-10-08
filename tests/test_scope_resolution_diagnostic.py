"""Synthetic control-flow evidence; no live quality claims or Provider IO."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.runtime.reviewer_roles import RoleRoutedProvider
from scripts import run_scope_resolution_diagnostic as runner
from scripts import review_independence_contract as identity
from tests.test_reviewer_role_proposal import providers


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


def reply(request, explicit):
    text = request.messages[1].content
    data = json.loads(text.split('\n', 1)[1].rsplit('\n', 1)[0])
    answer = deepcopy(data['previous_review'])
    if not explicit:
        answer['issues'] = [answer['issues'][1]]
    answer['issue_resolutions'] = [
        dict(previous_id=1, disposition='replaced' if explicit else 'withdrawn',
             final_issue=1 if explicit else None, source_ids=[31, 32], explanation='Synthetic source judgment.'),
        dict(previous_id=2, disposition='replaced', final_issue=2 if explicit else 1,
             source_ids=[31, 32], explanation='Synthetic true-error preservation.')]
    return answer


class Host:
    def __init__(self, plan, fault=None):
        self.plan, self.fault, self.events = plan, fault, {}

    def fetch(self, *, event_id, binding):
        if self.fault == 'unavailable':
            raise ValueError('synthetic_unavailable')
        return self.events[event_id]

    def adjudicate(self, path, remaining):
        required = json.loads(path.read_bytes())
        bound = required['binding']
        result = {}
        for role in ('primary', 'independent'):
            accepted = not (self.fault == 'reject' and role == 'independent')
            review = dict(binding=bound, report_assessment=None,
                stage_assessment=dict(stage='initial', stage_sha256=required['stage_sha256'],
                    reviewer=self.plan['review_principals'][role]['principal_id'],
                    source_review='Synthetic check of assessment, not a corrected report.',
                    accepted=accepted, defects=[] if accepted else [dict(kind='false_positive', detail='Synthetic extra issue.')]))
            if self.fault == 'report_certification':
                review['report_assessment'] = {'true_errors_fixed': True}
            if self.fault == 'missing_report_field':
                review.pop('report_assessment')
            if role == 'primary':
                review['primary_attestation'] = identity.make_primary_attestation(review, plan=self.plan, bound=bound)
            else:
                event_id = 'synthetic-independent/turn/' + path.parent.name
                event = dict(schema_version=identity.VERSION, event_kind=identity.EVENT_KIND,
                    state='completed', host_review_evidence_policy=identity.FINAL_POLICY,
                    author_principal_id=self.plan['review_principals'][role]['principal_id'],
                    root_thread_id='synthetic-root', binding=bound,
                    review_sha256=identity.review_digest(review), event_id=event_id,
                    dispatch_id='synthetic-dispatch', raw_event_sha256='a' * 64, review=deepcopy(review))
                if self.fault == 'identity':
                    event['author_principal_id'] = 'synthetic-wrong-author'
                self.events[event_id] = event
                review['independent_source_event'] = event
            result[role] = review
        return result


def factory(monkeypatch, fault):
    generator, reviewer = providers()
    seen = []
    def forbidden(*_):
        pytest.fail('reassessment routed to Flash')
    def chat(request):
        assert request.metadata['review_phase'] == 'native_business_reassessment'
        if fault == 'transport':
            raise RuntimeError('Synthetic interruption')
        answer = reply(request, explicit=bool(seen))
        seen.append(request)
        if fault == 'missing_mapping':
            answer['issue_resolutions'].pop()
        if fault == 'missed_error':
            answer.update(score=96, verdict='pass', issues=[])
            for r in answer['issue_resolutions']:
                r.update(disposition='withdrawn', final_issue=None)
        if fault == 'wrong_mapping' and len(seen) == 2:
            answer['issue_resolutions'][0]['final_issue'] = 2
            answer['issue_resolutions'][1]['final_issue'] = 1
        response = ChatResponse(provider='zhipu', model='glm-5.3', content=None,
            finish_reason='tool_calls', usage=TokenUsage(input_tokens=20, output_tokens=10),
            tool_calls=(ToolCall(id='synthetic-review', name='submit_report_review', arguments=answer),))
        reviewer.last_exchange = Exchange(request, response, hashlib.sha256(runner.base.validate_request(
            request, transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
        return response
    monkeypatch.setattr(generator, 'chat', forbidden)
    monkeypatch.setattr(reviewer, 'chat', chat)
    router = RoleRoutedProvider(generator, reviewer,
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return lambda _: router


@pytest.mark.parametrize('fault,calls', [(None, 2), ('missing_mapping', 1), ('missed_error', 1),
    ('wrong_mapping', 2), ('reject', 1), ('unavailable', 1), ('identity', 1),
    ('report_certification', 1), ('missing_report_field', 1), ('transport', 1), ('budget', 0)])
def test_bounded_reassessment_no_editor_and_first_failure_stops(tmp_path, monkeypatch, fault, calls):
    plan = deepcopy(prepared())
    if fault == 'budget':
        plan['budget']['max_tokens'] = 1
    host = Host(plan, fault)
    result = runner.observe(factory(monkeypatch, fault), tmp_path, plan,
        event_source=host, adjudicate=host.adjudicate)
    assert result['calls'] == calls, result
    assert result['diagnostic_accepted'] == (fault is None), result
    assert not result['product_admitted'] and not result['original15_qualified']
    assert json.loads((tmp_path / 'result.json').read_bytes()) == json.loads(json.dumps(result))
    assert (result['unknown_reserved_tokens'] > 0) == (fault == 'transport')
    if calls < 2:
        assert not (tmp_path / 'explicit-middle-counterfactual').exists()
    if fault is None:
        assert len(result['stages']) == 2
        assert result['known_tokens'] == 60
        assert all(a['role'] == 'review' and a['model'] == 'glm-5.3' for a in result['attempts'])
        for key in runner.KEYS:
            arm = tmp_path / key
            source = json.loads((arm / 'source.json').read_bytes())
            stage = json.loads((arm / 'stage.json').read_bytes())
            assert stage['report'] == source['report']
            assert stage['journal']['previous_raw'] == source['previous_raw']


def test_frozen_plan_and_ci_failure_before_credentials(tmp_path, monkeypatch):
    plan = prepared()
    monkeypatch.setattr(runner, 'prepare', lambda **_: plan)
    monkeypatch.setattr(runner.base, 'ROOT', tmp_path)
    frozen = tmp_path / 'plan.json'
    frozen.write_text(json.dumps(plan), encoding='utf-8')
    args = SimpleNamespace(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent',
        execute=True, preparation=frozen, env_file=tmp_path/'absent.env', codex_executable=tmp_path/'absent.exe',
        plan_sha=runner.base.canonical_sha(plan), ci_run='synthetic')
    def forbidden(*_):
        pytest.fail('credentials before prerequisites')
    monkeypatch.setattr(runner.base, 'load_role_settings', forbidden)
    def ci_failure(*_):
        raise ValueError('synthetic_ci_failure')
    monkeypatch.setattr(runner.base, 'verify_public_ci', ci_failure)
    with pytest.raises(ValueError, match='synthetic_ci_failure'):
        runner.run(args)
    frozen.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='preparation_required'):
        runner.run(args)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(args)


def test_plan_keeps_two_call_limit_and_host_labels_outside_request():
    plan = prepared()
    assert plan['budget']['max_calls'] == 2
    assert plan['budget']['estimated_uncached_cny'] == '2.859008'
    assert plan['role_calls'] == {'glm-5.3': 2, 'glm-5.3-flash': 0}
    assert not plan['execution_authorized']
    for cell, inputs, request, previous in runner.controls():
        assert request.max_tokens == 32768 and request.timeout_s == 300
        assert 'host_only_expected' not in str(request.messages)
        assert cell['previous_raw_sha256'] == runner.base.digest(previous)


def test_actual_receipt_writer_and_operator_import_rebuild_exact_stage(tmp_path, monkeypatch):
    from app.evaluation import golden_stream_bridge as bridge
    from scripts import scope_resolution_handoff as handoff
    plan = prepared()
    runner.base.write_new_json(tmp_path / 'plan.json', dict(preparation_plan=plan,
        plan_sha256=runner.base.canonical_sha(plan)))
    count = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = runner.REQUEST.validate_json(raw, strict=True)
        answer = reply(request, bool(count))
        count.append(request)
        runner.base.write_new_json(directory / 'result.json', dict(state='complete', elapsed_ms=0,
            transport_id=transport_id))
        return ChatResponse(provider='zhipu', model='glm-5.3', content=None,
            finish_reason='tool_calls', usage=TokenUsage(input_tokens=20, output_tokens=10),
            tool_calls=(ToolCall(id='synthetic', name='submit_report_review', arguments=answer),))
    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return SimpleNamespace(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
    actual = runner.base.RunScopedRoleReceiptedProviderFactory(
        generator_settings=settings('glm-5.3-flash'), reviewer_settings=settings('glm-5.3'),
        transport_root=tmp_path / 'transport',
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    host = Host(plan)
    def review(path, remaining):
        key = path.parent.name
        task = json.loads(handoff.task(tmp_path, key))
        submission = host.adjudicate(path, remaining)
        assert task['binding'] == submission['primary']['binding']
        assert 'host_only_expected' not in task['instructions']
        judgment = submission['primary']['stage_assessment']
        notes = {k: judgment[k] for k in ('accepted', 'defects', 'source_review')}
        event_id = submission['independent']['independent_source_event']['event_id']
        handoff.submit(tmp_path, key, notes, event_id, host)
        with pytest.raises(FileExistsError):
            handoff.submit(tmp_path, key, notes, event_id, host)
        assert not list(path.parent.glob('.submission-*.tmp'))
        return json.loads((path.parent/'review-submission.json').read_bytes())
    result = runner.observe(actual, tmp_path, plan, event_source=host, adjudicate=review)
    assert result['diagnostic_accepted'], result
    assert len(count) == 2
    with pytest.raises(ValueError, match='batch_closed'):
        handoff.material(tmp_path, runner.KEYS[0])


def test_batch_closing_during_native_fetch_cannot_receive_late_submission(tmp_path, monkeypatch):
    from scripts import scope_resolution_handoff as handoff
    plan = prepared()
    key = runner.KEYS[0]
    arm = tmp_path / key
    arm.mkdir()
    bound = dict(plan_sha256=runner.base.canonical_sha(plan), key=key, stage='initial',
        request_sha256='a'*64, response_sha256='b'*64, report_sha256='c'*64)
    stage = dict(stage='initial', report='Synthetic unrepaired report', journal={})
    path = arm / 'review-required.json'
    runner.base.write_new_json(path, dict(binding=bound, stage_sha256=runner.base.stage_identity(stage)))
    host = Host(plan)
    opinion = host.adjudicate(path, 10)
    monkeypatch.setattr(handoff, 'material', lambda *_: (plan, stage, bound))
    original_fetch = host.fetch
    def late_fetch(**kwargs):
        if not (tmp_path / 'result.json').exists():
            runner.close_result(tmp_path, {'diagnostic_accepted': False, 'error_code': 'host_timeout'})
        return original_fetch(**kwargs)
    host.fetch = late_fetch
    event_id = opinion['independent']['independent_source_event']['event_id']
    notes = dict(accepted=True, defects=[], source_review='Synthetic primary')
    with pytest.raises(ValueError, match='batch_closed'):
        handoff.submit(tmp_path, key, notes, event_id, host)
    assert not (arm / 'review-submission.json').exists()
    assert not list(arm.glob('.submission-*.tmp'))
