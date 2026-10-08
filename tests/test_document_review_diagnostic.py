"""Scripted engineering checks only; no live semantic-quality evidence."""
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
from scripts import run_document_review_diagnostic as runner
from scripts import document_review_handoff as handoff
from tests.test_scope_resolution_diagnostic import Host
from tests.test_reviewer_role_proposal import providers


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


@lru_cache
def controls():
    return runner.controls()


@pytest.fixture(autouse=True)
def fixed_controls(monkeypatch):
    # Construct once using real source/hash validation; reuse immutable values
    # to keep repeated budget/Host failure checks focused and offline.
    value = controls()
    monkeypatch.setattr(runner, 'controls', lambda: value)


def reply(key):
    seal = json.loads((runner.probe.ROOT/runner.probe.SEAL).read_bytes())['public_json_contents']
    original = 'claim-scope-1' if key == 'correct-context' else 'claim-scope-3'
    answer = json.loads(seal[original+'/initial-journal.json']['raw'])
    if key == 'actual-mixed':
        answer['issues'] = answer['issues'][1:]
    return answer


def factory(monkeypatch, fault=None):
    generator, reviewer = providers()
    seen = []
    def forbidden(*_):
        pytest.fail('initial-only diagnostic routed to Flash')
    def chat(request):
        assert len(request.messages) == 4
        assert request.metadata['review_phase'] == 'native_business_review'
        assert 'host_only_expected' not in str(request.messages)
        if fault == 'transport':
            raise RuntimeError('Scripted interrupted request')
        answer = reply(runner.KEYS[len(seen)])
        seen.append(request)
        if fault == 'schema':
            answer['unexpected_field'] = True
        response = ChatResponse(provider='zhipu', model='glm-5.3' if fault != 'wrong_model' else 'glm-5.3-flash',
            content=None, finish_reason='tool_calls', usage=TokenUsage(input_tokens=20, output_tokens=10),
            tool_calls=(ToolCall(id='scripted-review', name='submit_report_review', arguments=answer),))
        reviewer.last_exchange = Exchange(request, response, hashlib.sha256(runner.base.validate_request(
            request, transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
        if fault == 'receipt':
            reviewer.last_exchange = replace(reviewer.last_exchange, receipt_request_sha256='0'*64)
        return response
    monkeypatch.setattr(generator, 'chat', forbidden)
    monkeypatch.setattr(reviewer, 'chat', chat)
    router = RoleRoutedProvider(generator, reviewer,
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return lambda _: router


@pytest.mark.parametrize('fault,calls', [(None, 3), ('transport', 1), ('wrong_model', 1), ('receipt', 1),
    ('schema', 1), ('reject', 1), ('identity', 1), ('unavailable', 1),
    ('report_certification', 1), ('missing_report_field', 1), ('budget', 0)])
def test_real_budget_gate_and_first_failure_stop(tmp_path, monkeypatch, fault, calls):
    plan = deepcopy(prepared())
    if fault == 'budget':
        plan['budget']['max_tokens'] = 1
    host = Host(plan, fault)
    result = runner.observe(factory(monkeypatch, fault), tmp_path, plan,
        event_source=host, adjudicate=host.adjudicate)
    assert result['calls'] == calls, result
    assert result['diagnostic_accepted'] == (fault is None), result
    assert not result['original15_qualified'] and not result['product_admitted']
    assert json.loads((tmp_path/'result.json').read_bytes()) == json.loads(json.dumps(result))
    assert (result['unknown_reserved_tokens'] > 0) == (fault in ('transport', 'wrong_model'))
    if calls < 3:
        assert not (tmp_path/'correct-context').exists()
    if fault is None:
        assert result['known_tokens'] == 90
        for key in runner.KEYS:
            stage = json.loads((tmp_path/key/'stage.json').read_bytes())
            assert stage['journal']['report_presentation'] == runner.probe.view.VERSION
            assert stage['journal']['previous_raw'] is None


def test_exact_document_route_rejects_other_request_and_default_product_still_rejects():
    variants = controls()[1]
    route = runner.DocumentDiagnosticRoute(variants)
    _, _, request = variants[0]
    assert route.request_identity(request) == ('zhipu', 'glm-5.3')
    assert route.request_identity(replace(request, timeout_s=200,
        metadata={**request.metadata, 'coach_budget_contract':'coach-bounded-review-v2'})) == ('zhipu','glm-5.3')
    with pytest.raises(ValueError):
        runner.base.CONTRACT.request_identity(request)
    for bad in (replace(request, timeout_s=301), replace(request, tools=()),
        replace(request, messages=(replace(request.messages[0], content='altered-policy'), *request.messages[1:])),
        replace(request, metadata={**request.metadata, 'extra':'unfrozen'})):
        with pytest.raises(ValueError, match='not_frozen'):
            route.request_identity(bad)


def test_receipt_transport_roundtrip_native_import_and_late_close(tmp_path, monkeypatch):
    from app.evaluation import golden_stream_bridge as bridge
    from app.evaluation.role_qualification import read_role_calls
    plan = prepared()
    runner.base.write_new_json(tmp_path/'plan.json', dict(preparation_plan=plan,
        plan_sha256=runner.base.canonical_sha(plan)))
    count = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = runner.shared.REQUEST.validate_json(raw, strict=True)
        assert len(request.messages) == 4
        count.append(request)
        runner.base.write_new_json(directory/'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id))
        return ChatResponse(provider='zhipu', model='glm-5.3', content=None, finish_reason='tool_calls',
            usage=TokenUsage(input_tokens=20, output_tokens=10),
            tool_calls=(ToolCall(id='scripted',name='submit_report_review',arguments=reply(runner.KEYS[len(count)-1])),))
    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return SimpleNamespace(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    actual = runner.base.RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport',
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    host = Host(plan)
    def review(path, remaining):
        key = path.parent.name
        task = json.loads(handoff.task(tmp_path,key))
        submission = host.adjudicate(path,remaining)
        assert task['binding'] == submission['primary']['binding']
        assert 'host_only_expected' not in task['instructions']
        # Default original15 readback cannot admit the new route.
        with pytest.raises(ValueError):
            read_role_calls(tmp_path/'transport/diagnostic',
                source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
        judgment = submission['primary']['stage_assessment']
        notes = {k:judgment[k] for k in ('accepted','defects','source_review')}
        event_id = submission['independent']['independent_source_event']['event_id']
        handoff.submit(tmp_path,key,notes,event_id,host)
        with pytest.raises(FileExistsError):
            handoff.submit(tmp_path,key,notes,event_id,host)
        assert not list(path.parent.glob('.submission-*.tmp'))
        return json.loads((path.parent/'review-submission.json').read_bytes())
    result = runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=review)
    assert result['diagnostic_accepted'],result
    assert len(count)==3 and len(runner.read_calls(tmp_path/'transport/diagnostic'))==3
    assert not (tmp_path/'transport/diagnostic/generation').exists()
    with pytest.raises(ValueError,match='batch_closed'):
        handoff.material(tmp_path,runner.KEYS[0])
    # Raw request edits cannot be hidden by the diagnostic identity resolver.
    request_file=tmp_path/'transport/diagnostic/review/request-001.json'
    request_file.write_bytes(request_file.read_bytes()+b' ')
    with pytest.raises(ValueError,match='receipt_request_mismatch'):
        runner.read_calls(tmp_path/'transport/diagnostic')


def test_ci_or_plan_mismatch_precedes_credentials_and_closed_batch_never_restarts(tmp_path,monkeypatch):
    plan=prepared()
    monkeypatch.setattr(runner,'prepare',lambda **_:plan)
    monkeypatch.setattr(runner.base,'ROOT',tmp_path)
    frozen=tmp_path/'plan.json'
    frozen.write_text(json.dumps(plan),encoding='utf-8')
    args=SimpleNamespace(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent',
        execute=True,preparation=frozen,env_file=tmp_path/'absent.env',codex_executable=tmp_path/'absent.exe',
        plan_sha=runner.base.canonical_sha(plan),ci_run='scripted')
    def forbidden(*_):
        pytest.fail('credentials used before frozen plan and CI')
    monkeypatch.setattr(runner.base,'load_role_settings',forbidden)
    def failed_ci(*_):
        raise ValueError('scripted_ci_failure')
    monkeypatch.setattr(runner.base,'verify_public_ci',failed_ci)
    with pytest.raises(ValueError,match='scripted_ci_failure'):
        runner.run(args)
    frozen.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(args)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError,match='closed_or_exists'):
        runner.run(args)


def test_batch_closing_during_native_fetch_cannot_receive_late_submission(tmp_path, monkeypatch):
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
            runner.shared.close_result(tmp_path, {'diagnostic_accepted': False, 'error_code': 'host_timeout'})
        return original_fetch(**kwargs)
    host.fetch = late_fetch
    event_id = opinion['independent']['independent_source_event']['event_id']
    notes = dict(accepted=True, defects=[], source_review='Synthetic primary')
    with pytest.raises(ValueError, match='batch_closed'):
        handoff.submit(tmp_path, key, notes, event_id, host)
    assert not (arm / 'review-submission.json').exists()
    assert not list(arm.glob('.submission-*.tmp'))
