"""Scripted protocol/stop boundaries; these tests do not prove model quality."""
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.runtime.reviewer_roles import RoleRoutedProvider
from scripts import run_mixed_review_tail_diagnostic as runner
from scripts.native_contract_options import body
from tests.test_coarse_edit_diagnostic import Host
from tests.test_native_editor_product_budget import offline
from tests.test_reviewer_role_proposal import providers

BEFORE = '将所选全部 5 局（包括辅助局）合并计算后，胜局与败局的平均补刀/分钟也基本持平。'
AFTER = '合并所选全部5局后，胜局与败局平均补刀/分钟约为8.8与6.45，混合补刀差距受辅助局影响。'


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


def factory(fault):
    generator, reviewer = providers()
    requests = []

    def chat(provider, request, role):
        requests.append(request)
        if fault == 'transport':
            raise RuntimeError('Synthetic incomplete transport')
        if role == 'revision':
            op = dict(block=6, before=BEFORE, after=AFTER, reason='Synthetic necessary correction.')
            if fault == 'anchor':
                op['before'] = 'ABSENT'
            edits = [op]
            if fault == 'propagated_false_issue':
                edits.append(dict(block=4, before='早期死亡在胜败样本间几乎相同',
                    after='中单早期死亡在胜败样本间存在差异', reason='Synthetic unnecessary change.'))
            if fault == 'missed_true_error':
                edits = []
            arguments, tool = dict(edits=edits), runner.editor.TOOL
        else:
            arguments = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
            if fault == 'fresh_failed':
                arguments.update(score=40, verdict='fail')
            tool = 'submit_report_review'
        response = ChatResponse(provider='zhipu', model=provider.model_name, content=None,
            finish_reason='tool_calls', tool_calls=(ToolCall('synthetic', tool, arguments),),
            usage=TokenUsage(input_tokens=20, output_tokens=10))
        provider.last_exchange = Exchange(request, response, hashlib.sha256(runner.base.validate_request(
            request, transport_id=runner.base.CAPACITY_TRANSPORT_ID if role == 'revision'
            else runner.base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
        return response

    generator.chat = lambda r: chat(generator, r, 'revision')
    reviewer.chat = lambda r: chat(reviewer, r, 'review')
    router = RoleRoutedProvider(generator, reviewer,
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return lambda _: router, requests


def test_exact_rejected_initial_is_only_historical_input():
    plan = prepared()
    source, inputs, historical, initial, initial_sha, edit = runner.prepared_source()
    raw_initial = historical.response.tool_calls[0].arguments
    seal = json.loads((runner.base.ROOT/runner.source_seal.SEAL).read_bytes())
    archived = seal['public_json_contents']
    prefix = 'transport/claim-scope-3/review/'
    assert historical.receipt_request_sha256 == archived[prefix+'stream-001/reservation.json']['request_sha256']
    assert historical.receipt_request_sha256 == seal['original_file_sha256'][prefix+'request-001.json']
    assert historical.receipt_request_sha256 != initial_sha
    assert json.loads(runner.base.validate_request(historical.issued_request,
        transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)) == archived[prefix+'request-001.json']
    assert plan['historical_issued_request_sha256'] == historical.receipt_request_sha256
    assert [i['block'] for i in raw_initial['issues']] == [4, 6]
    # Existing editor policy omits nonblocking advisories. Neither actionable
    # issue is filtered, repaired or labelled as false in the model request.
    assert body(edit)['accepted_review'] == {k: v for k, v in raw_initial.items() if k != 'advisories'}
    assert edit.messages[1:] == runner.editor.Current.make_request(inputs,
        accepted=runner.editor.Current.validate_review(json.dumps(dict(raw_initial)), inputs)[1]).messages[1:]
    assert not plan['initial_review_accepted'] and plan['historical_initial_inputs'] == 1
    assert plan['role_calls'] == {'glm-5.3-flash': 1, 'glm-5.3': 1}
    assert plan['budget']['max_calls'] == 2 and plan['required_exception'] == runner.EXCEPTION


@pytest.mark.parametrize('fault,calls', [(None, 2), ('anchor', 1), ('propagated_false_issue', 1),
    ('missed_true_error', 1), ('host_reject', 1), ('host_unavailable', 1), ('missing_report', 1),
    ('fresh_failed', 2), ('transport', 1), ('budget', 0)])
def test_actual_workflow_injection_edit_fresh_and_stop(tmp_path, fault, calls):
    plan = deepcopy(prepared())
    if fault == 'budget':
        plan['budget']['max_tokens'] = 1
    host = Host(plan, fault)
    provider_factory, requests = factory(fault)
    source = runner.prepared_source()[0]

    def judge(path, remaining):
        stage = json.loads(path.with_name('stage.json').read_bytes())
        # Scripted source oracle for stop-path testing, never a live host review.
        if stage['report'] != source.report.replace(BEFORE, AFTER):
            host.fault = 'host_reject'
        return host.adjudicate(path, remaining)

    result = runner.observe(provider_factory, tmp_path, plan, event_source=host, adjudicate=judge)
    assert result['calls'] == len(requests) == calls, result
    assert result['diagnostic_accepted'] is (fault is None), result
    assert result['offline_initial_injections'] == 1 and not result['initial_review_accepted']
    assert not result['product_admitted'] and not result['original15_qualified']
    assert json.loads((tmp_path/'result.json').read_bytes()) == result
    assert (result['unknown_reserved_tokens'] > 0) is (fault == 'transport')
    assert result['known_tokens'] == (0 if fault == 'transport' else calls*30)
    assert [r['role'] for r in result['attempts']] == ['revision', 'review'][:calls]
    historical = json.loads((tmp_path/'injected-initial-journal.json').read_bytes())
    assert historical['fixture_only'] and not historical['new_provider_call']
    assert not historical['initial_review_accepted']
    if calls < 2:
        assert not (tmp_path/'conditional-fresh').exists()
    if fault is None:
        edited = json.loads((tmp_path/'necessary-edit/stage.json').read_bytes())
        assert edited['report'] == source.report.replace(BEFORE, AFTER)
        expected = runner.editor.Current.make_request(runner.editor.Current.build_inputs(
            replace(source, report=edited['report'])))
        assert requests[-1].messages == expected.messages
        assert not {'previous_review', 'accepted_review', 'previous_issues'} & body(requests[-1]).keys()
        assert result['timing']['completed_host_waits'] == 2
    if fault == 'fresh_failed':
        assert (tmp_path/'conditional-fresh/response.json').exists()
        assert (tmp_path/'final-journal.json').exists()


def test_exception_is_required_before_any_setup(monkeypatch):
    def forbidden(**kwargs):
        pytest.fail('exception gate reached preparation or IO')
    monkeypatch.setattr(runner, 'prepare', forbidden)
    with pytest.raises(ValueError, match='explicit_exception_approval_required'):
        runner.run(SimpleNamespace(execute=True))


def test_closed_run_and_ci_failure_stop_before_credentials(tmp_path, monkeypatch):
    plan = prepared()
    monkeypatch.setattr(runner, 'prepare', lambda **_: plan)
    monkeypatch.setattr(runner.base, 'ROOT', tmp_path)
    monkeypatch.setattr(runner.base, 'load_role_settings', lambda *_: pytest.fail('credentials read'))
    prep = tmp_path/'plan.json'
    prep.write_text(json.dumps(plan), encoding='utf-8')
    args = SimpleNamespace(execute=True, allow_mixed_initial_diagnostic=True,
        root_thread_id='synthetic-root', independent_thread_id='synthetic-independent',
        preparation=prep, env_file=tmp_path/'secret', codex_executable=tmp_path/'codex',
        plan_sha=runner.base.canonical_sha(plan), ci_run='synthetic')
    def bad_ci(_):
        raise ValueError('synthetic_ci_not_passed')
    monkeypatch.setattr(runner.base, 'verify_public_ci', bad_ci)
    with pytest.raises(ValueError, match='ci_not_passed'):
        runner.run(args)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(args)


@pytest.mark.parametrize('tamper', [None, 'stage', 'source', 'response', 'request', 'injected', 'binding'])
def test_real_receipted_factory_handoff_rebuild_and_native_import(tmp_path, monkeypatch, tamper):
    from app.evaluation import golden_stream_bridge as bridge
    from scripts import mixed_review_tail_handoff as handoff
    plan = prepared()
    host = Host(plan, None)
    fake, _ = factory(None)
    replies = fake('fixture')

    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw, strict=True)
        provider = replies.generator if request.metadata['review_phase'] == 'native_business_revision' else replies.reviewer
        response = provider.chat(request)
        runner.base.write_new_json(directory/'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id))
        return response

    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return SimpleNamespace(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
    actual = runner.base.RunScopedRoleReceiptedProviderFactory(
        generator_settings=settings('glm-5.3-flash'), reviewer_settings=settings('glm-5.3'),
        transport_root=tmp_path/'transport', source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    runner.base.write_new_json(tmp_path/'plan.json', dict(preparation_plan=plan, plan_sha256=runner.base.canonical_sha(plan)))

    def inspect(path, remaining):
        if tamper:
            target = {'stage': path.with_name('stage.json'), 'source': tmp_path/'source.json',
                'response': path.with_name('response.json'), 'request': path.with_name('request.json'),
                'injected': tmp_path/'injected-initial-journal.json', 'binding': path}[tamper]
            value = json.loads(target.read_bytes())
            value['tampered'] = True
            target.write_text(json.dumps(value), encoding='utf-8')
            with pytest.raises(ValueError, match='mixed_tail_'):
                handoff.material(tmp_path, path.parent.name)
            raise ValueError('synthetic_tamper_detected')
        restored_plan, stage, bound = handoff.material(tmp_path, path.parent.name)
        assert restored_plan == plan
        assert handoff.task(tmp_path, path.parent.name)
        submission = host.adjudicate(path, remaining)
        primary = submission['primary']
        notes = dict(stage_assessment=primary['stage_assessment'], report_assessment=primary['report_assessment'])
        event_id = submission['independent']['independent_source_event']['event_id']
        handoff.submit(tmp_path, path.parent.name, notes, event_id, host)
        with pytest.raises(FileExistsError):
            handoff.submit(tmp_path, path.parent.name, notes, event_id, host)
        return json.loads(path.with_name('review-submission.json').read_bytes())

    result = runner.observe(actual, tmp_path, plan, event_source=host, adjudicate=inspect)
    assert result['diagnostic_accepted'] is (tamper is None), result
    assert result['calls'] == (2 if tamper is None else 1), result
    with pytest.raises(ValueError, match='batch_closed'):
        handoff.material(tmp_path, 'necessary-edit')
