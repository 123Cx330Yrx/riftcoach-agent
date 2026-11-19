"""Offline request preservation and real control flow, never model quality."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.product.native_coach_composition import _build_coach_application, CORRECTION_SCOPE_ASSETS
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.store import RuntimeTraceStore
from scripts import run_review_boundary_examples_diagnostic as runner
from scripts.review_boundary_examples import EXAMPLES, DiagnosticWorkflow
from tests.test_native_editor_product_budget import offline, SummaryBuilder
from tests.test_reviewer_role_proposal import providers
from tests.test_role_coach_application import run
from tests.test_correction_scope_runtime import coarse_script_sources
from tests.test_review_model_comparison import fake_provider, decision
from tests.test_role_review_notes import tool_response, request_data


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def pass_response():
    return dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])


def test_frozen_preparation_rebuilds_without_local_runs(prepared):
    assert prepared[0] == runner.read(runner.PREPARATION)


def test_full_inputs_all_phases_and_only_sdk_messages_change(prepared):
    plan, variants = prepared
    assert len(plan['all15_input_audit']) == 15
    assert [c['expected_initial'] for c in plan['cells']] == ['accept', 'reject']
    prior = compact(pass_response())
    for row, source in runner.frozen_cases()[0]:
        inputs = runner.Workflow.build_inputs(source)
        for kwargs in ({}, {'previous_raw': prior, 'diagnostics': {'reason': 'fixture'}}):
            base = runner.Workflow.make_request(inputs, **kwargs)
            actual = runner.request_for(inputs, **kwargs)
            assert actual.messages[1:] == base.messages[1:]
            assert actual.messages[0].content == base.messages[0].content + '\n' + EXAMPLES
            assert replace(actual, messages=base.messages) == base
            assert runner.size(actual) <= 64000
        _, accepted, _ = runner.Workflow.validate_review(prior, inputs)
        assert runner.request_for(inputs, accepted=accepted) == runner.Workflow.make_request(inputs, accepted=accepted)
    for _, inputs, actual in variants:
        before = runner.sdk_wire(runner.Workflow.make_request(inputs))
        after = runner.sdk_wire(actual)
        assert before.keys() == after.keys()
        assert {k for k in before if before[k] != after[k]} == {'messages'}
        assert after['messages'][1:] == before['messages'][1:]
        assert after['temperature'] == 1 and after['reasoning_effort'] == 'high'


@pytest.mark.parametrize('recover,ceiling', [(False, False), (False, True), (True, False)])
def test_actual_application_initial_edit_fresh_and_shared_budget(tmp_path, coarse_script_sources, recover, ceiling):
    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=runner.Workflow.make_request(
                runner.Workflow.build_inputs(runner.frozen_cases()[0][0][1])).metadata['source_projection'])
            self.created = {}

        def __call__(self, run_id):
            self.created[run_id] = RoleRoutedProvider(*providers(recover=recover, charge_ceiling=ceiling),
                source_projection=self.descriptor.source_projection)
            return self.created[run_id]

    factory = Factory()
    app = _build_coach_application(contract=runner.CONTRACT, assets=CORRECTION_SCOPE_ASSETS,
        workflow_type=DiagnosticWorkflow, summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    result = run(app, 'boundary_offline')
    assert result.publication_status.value == ('rejected' if recover else 'published'), result
    trace = RuntimeTraceStore(tmp_path, 'boundary_offline').read_trace(result.trace_reference)
    delegate = factory.created['boundary_offline']
    assert trace.usage.provider_calls_attempted == 5
    assert [a['role'] for a in delegate.attempts] == (['generation', 'generation', 'review', 'review', 'revision']
        if recover else ['generation', 'generation', 'review', 'revision', 'review'])
    assert all(r.messages[0].content.endswith('\n' + EXAMPLES) for r in delegate.reviewer.requests)
    assert all(EXAMPLES not in r.messages[0].content for r in delegate.generator.requests)
    assert any(m.role.value == 'tool' for m in delegate.generator.requests[1].messages)
    if not recover:
        assert not {'previous_review', 'previous_issues', 'accepted_review'} & request_data(delegate.reviewer.requests[-1]).keys()
    else:
        assert request_data(delegate.reviewer.requests[1])['previous_review']['score'] == '70'
    requests = delegate.generator.requests + delegate.reviewer.requests
    reservation = sum(runner.size(r) + r.max_tokens for r in requests)
    assert reservation <= 401920
    assert all(runner.size(r) <= 64000 for r in requests)
    print(f'boundary_application recover={recover} ceiling={ceiling} reservation={reservation} max_input={max(runner.size(r) for r in requests)}')


@pytest.mark.parametrize('accept', [True, False])
def test_observer_preserves_wire_and_stops_after_rejected_control(prepared, tmp_path, accept):
    plan, variants = prepared
    provider = fake_provider([tool_response(pass_response()), tool_response(pass_response())])
    result = runner.observe(provider, tmp_path, variants, plan,
        inspect_response=runner.inspect_response, adjudicate=decision(accept), clock=lambda: 0)
    assert provider._calls == (2 if accept else 1)
    assert result['pair_accepted'] is accept  # Scripted host only, not semantic acceptance.
    for name, inputs, request in variants[:provider._calls]:
        assert (tmp_path/name/'request.raw.json').read_bytes() == validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)


def test_preview_frozen_ci_and_closed_gates_before_credentials(prepared, tmp_path, monkeypatch):
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
    runner.write_new_json(runner.PREPARATION, plan)
    args.plan_sha = runner.canonical_sha(plan)
    def reject(_):
        raise ValueError('exact_sha_ci_required')
    monkeypatch.setattr(runner, 'verify_public_ci', reject)
    with pytest.raises(ValueError, match='exact_sha_ci_required'):
        runner.run(args)
    assert not runner.RUN_DIRECTORY.exists()
    runner.RUN_DIRECTORY.mkdir()
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(args)


# Exercise the inherited receipt/export boundary against this new request identity.
def seal_replies():
    return [pass_response(), dict(score=75, verdict='needs_revision', issues=[dict(
        block=4, severity='high', category='unsupported_comparison', source_ids=[22],
        explanation='Synthetic error.', suggested_correction='Synthetic correction.')],
        issue_resolutions=[], advisories=[])]

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
    result = runner.observe(fake_provider([tool_response(v) for v in seal_replies()]), run, variants, plan,
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
        value['temperature'] = .2
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
        with pytest.raises(ValueError, match='boundary_examples_seal_'):
            runner.seal()
        assert not runner.CLOSED_RESULT.exists()
    else:
        assert runner.seal()['pair_accepted']
        assert 'PRIVATE_REASONING_MARKER' not in runner.CLOSED_RESULT.read_text()
