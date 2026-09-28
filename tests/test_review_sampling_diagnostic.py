"""Offline proof of the diagnostic's actual wire and failure boundaries."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.providers.zhipu import ZhipuProvider
from scripts import run_review_sampling_diagnostic as runner
from scripts.prepare_review_model_comparison import mock_wire
from tests.test_review_model_comparison import fake_provider, decision
from tests.test_role_review_notes import tool_response
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage, tool_fragment


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def replies():
    return [dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[]),
        dict(score=75, verdict='needs_revision', issues=[dict(block=4, severity='high',
            category='unsupported_comparison', source_ids=[22], explanation='Synthetic error.',
            suggested_correction='Synthetic correction.')], issue_resolutions=[], advisories=[])]


def test_committed_preparation_rebuilds_without_local_run_artifacts(prepared):
    assert prepared[0] == runner.read(runner.PREPARATION)


def test_full_reports_initial_fresh_reassessment_and_editor_keep_other_fields(prepared):
    plan, variants = prepared
    assert len(plan['all15_input_audit']) == 15
    assert [c['key'] for c in plan['cells']] == ['claim-scope:1', 'scope:3']
    assert [c['expected_initial'] for c in plan['cells']] == ['accept', 'reject']
    prior = compact(replies()[0])
    for _, source in runner.frozen_cases()[0]:
        inputs = runner.Workflow.build_inputs(source)
        for kwargs in ({}, {'previous_raw': prior, 'diagnostics': {'reason': 'synthetic'}}):
            original = runner.Workflow.make_request(inputs, **kwargs)
            actual = runner.request_for(inputs, **kwargs)
            assert actual.temperature == .2 and replace(actual, temperature=original.temperature) == original
        _, accepted, _ = runner.Workflow.validate_review(prior, inputs)
        assert runner.request_for(inputs, accepted=accepted) == runner.Workflow.make_request(inputs, accepted=accepted)
    assert all(c['changed_sdk_fields'] == ['temperature'] for c in plan['cells'])


def test_actual_observer_adapter_sdk_preserves_sampling_and_high(prepared, tmp_path):
    plan, variants = prepared
    provider = fake_provider([])
    captured = []
    def chat(request):
        ordinal = provider._calls
        raw = ClosableStream([chunk(model='glm-5.3', tool_calls=[tool_fragment(index=0,
            call_id='call', name=request.tools[0].name, arguments=compact(replies()[ordinal]))],
            finish_reason='tool_calls'), chunk(model='glm-5.3', raw_usage=usage())])
        client = FakeClient(raw)
        actual = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3', profile=runner.PROFILE)
        (tmp_path/f'adapter-{ordinal}').mkdir()
        response = bridge.collect(request, lambda r, hook: actual.stream_adapter(tool_stream=True,
            evaluation_request_policy=bridge.transport_request_policy(bridge.REVIEW_MODEL_TRANSPORT_ID)
            ).stream_session(r, include_usage_tail=True), directory=tmp_path/f'adapter-{ordinal}',
            started=0, deadline=300, clock=lambda: 1, allow_tool_content=True,
            transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)
        captured.append(mock_wire(client.completions.calls[0]))
        provider._calls += 1
        provider.last_exchange = Exchange(request, response, hashlib.sha256(bridge.validate_request(
            request, transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
        assert raw.closed
        return response
    provider.chat = chat
    result = runner.observe(provider, tmp_path, variants, plan, inspect_response=runner.inspect_response,
        adjudicate=decision(True), clock=lambda: 0)
    assert result['pair_accepted'], result
    assert captured == [runner.sdk_wire(v[2]) for v in variants]
    assert all(w['temperature'] == .2 and w['top_p'] == .95 and w['reasoning_effort'] == 'high' for w in captured)


@pytest.mark.parametrize('failure', ['host', 'schema', 'source', 'request', 'head'])
def test_failed_first_control_never_sends_second(prepared, tmp_path, failure):
    plan, variants = prepared
    values = replies()
    if failure in ('schema', 'source'):
        values[0] = values[1]
        if failure == 'schema':
            values[0]['issues'][0].pop('suggested_correction')
        else:
            values[0]['issues'][0]['source_ids'] = [99999]
    provider = fake_provider([tool_response(v) for v in values])
    def inspect(request, exchange, inputs):
        return runner.inspect_response(replace(request, temperature=1) if failure == 'request' else request, exchange, inputs)
    def send():
        if failure == 'head':
            raise ValueError('changed_checkout')
    result = runner.observe(provider, tmp_path, variants, plan, inspect_response=inspect,
        adjudicate=decision(False), before_send=send, clock=lambda: 0)
    assert not result['pair_accepted']
    assert provider._calls == (0 if failure == 'head' else 1)


def test_preview_and_frozen_ci_closed_gates_precede_secrets(prepared, tmp_path, monkeypatch):
    plan, _ = prepared
    monkeypatch.setattr(runner, 'prepare', lambda: prepared)
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path/'run')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed')
    monkeypatch.setattr(runner, 'PREPARATION', tmp_path/'plan.json')
    monkeypatch.setattr(runner, 'load_role_settings', lambda *_: pytest.fail('credentials read'))
    assert runner.run(NS(execute=False, output=None))['provider_requests'] == 0
    args = NS(execute=True, env_file=tmp_path/'secret', ci_run='1', plan_sha='bad')
    with pytest.raises(ValueError, match='preparation_required'):
        runner.run(args)
    write_new_json(runner.PREPARATION, plan)
    args.plan_sha = runner.canonical_sha(plan)
    def reject_ci(_):
        raise ValueError('exact_sha_ci_required')
    monkeypatch.setattr(runner, 'verify_public_ci', reject_ci)
    with pytest.raises(ValueError, match='exact_sha_ci_required'):
        runner.run(args)
    assert not runner.RUN_DIRECTORY.exists()
    runner.RUN_DIRECTORY.mkdir()
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(args)


@pytest.mark.parametrize('defect', [None, 'request', 'journal', 'independent', 'usage',
    'missing_journal', 'terminal', 'extra_stream', 'record_verdict', 'expected_verdict'])
def test_seal_binds_actual_wire_raw_review_and_both_host_judgments(prepared, tmp_path, monkeypatch, defect):
    plan, variants = prepared
    run = tmp_path/'run'
    run.mkdir()
    monkeypatch.setattr(runner, 'prepare', lambda: prepared)
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', run)
    monkeypatch.setattr(runner, 'PREPARATION', tmp_path/'preparation.json')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed.json')
    write_new_json(runner.PREPARATION, plan)
    write_new_json(run/'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    for name, inputs, request in variants:
        write_new_json(run/(name+'-source.json'), dict(input_json=inputs.data_json, report=inputs.source.report))
        (run/(name+'-prepared-request.json')).write_bytes(bridge.validate_request(request, transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID))
    def host(path, remaining):
        cell = next(c for c in plan['cells'] if c['id'] == path.parent.name)
        value = dict(response_sha256=runner.sha(path), input_sha256=cell['input_sha256'],
            report_sha256=cell['report_sha256'], accepted=True, defects=[], source_review='Offline source fixture.')
        write_new_json(path.with_name('independent-review.json'), value)
        value = dict(value, independent_sha256=runner.sha(path.with_name('independent-review.json')))
        write_new_json(path.with_name('host-decision.json'), value)
        return value
    result = runner.observe(fake_provider([tool_response(v) for v in replies()]), run, variants, plan,
        inspect_response=runner.inspect_response, adjudicate=host, clock=lambda: 0)
    assert result['pair_accepted']
    for i, row in enumerate(result['cases'], 1):
        stream = run/'transport'/f'stream-{i:03d}'
        stream.mkdir(parents=True)
        write_new_json(stream/'reservation.json', dict(ordinal=i, transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID,
            state='reserved_before_io', request_sha256=row['request_sha256']))
        write_new_json(stream/'result.json', dict(transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID, state='complete'))
        write_new_json(stream/'progress.json', dict(state='complete', **row['observed_usage']))
        write_new_json(stream/'private.json', dict(reasoning_content='PRIVATE_REASONING_MARKER'))
    arm = run/'claim-scope-1'
    if defect == 'request':
        path = arm/'request.raw.json'
        value = runner.read(path)
        value['temperature'] = 1
    elif defect == 'journal':
        path = arm/'journal.json'
        value = runner.read(path)
        value['parsed_review']['score'] = 96
    elif defect == 'independent':
        path = arm/'independent-review.json'
        value = runner.read(path)
        value['accepted'] = False
    elif defect == 'usage':
        path = run/'transport/stream-001/progress.json'
        value = runner.read(path)
        value['input_tokens'] += 1
    elif defect == 'missing_journal':
        (arm/'journal.json').unlink()
    elif defect == 'terminal':
        path = run/'transport/stream-001/result.json'
        value = runner.read(path)
        value['state'] = 'failed'
    elif defect == 'extra_stream':
        (run/'transport/stream-003').mkdir()
    elif defect == 'record_verdict':
        result['cases'][0]['verdict'] = 'needs_revision'
        path = run/'result.json'
        value = result
        (arm/'accounting.json').write_text(json.dumps(result['cases'][0]), encoding='utf-8')
    elif defect == 'expected_verdict':
        plan = json.loads(json.dumps(plan))
        plan['cells'][0]['expected_initial'] = 'reject'
        monkeypatch.setattr(runner, 'prepare', lambda: (plan, variants))
        runner.PREPARATION.write_text(json.dumps(plan), encoding='utf-8')
        path = run/'plan.json'
        value = dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan))
    if defect:
        if defect not in ('missing_journal', 'extra_stream'):
            path.write_text(json.dumps(value), encoding='utf-8')
        with pytest.raises(ValueError, match='sampling_seal_'):
            runner.seal()
        assert not runner.CLOSED_RESULT.exists()
    else:
        assert runner.seal()['pair_accepted']
        assert 'PRIVATE_REASONING_MARKER' not in runner.CLOSED_RESULT.read_text()
