"""Exercise actual request binding and stop decisions without model IO."""
from dataclasses import replace
import json
from types import SimpleNamespace as NS

import pytest

from scripts import run_correction_scope_diagnostic as runner
from tests.test_review_model_comparison import fake_provider, decision
from tests.test_role_review_notes import tool_response
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID


@pytest.fixture(scope='module')
def prepared():
    return runner.prepare()


def replies():
    bad = dict(score=70, verdict='needs_revision', issues=[dict(block=10, severity='high',
        category='unsupported_comparison', source_ids=[22], explanation='Synthetic attribution error.',
        suggested_correction='Synthetic bounded correction.')], issue_resolutions=[], advisories=[])
    good = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
    return bad, good


@pytest.mark.parametrize('failure', [None, 'host', 'source', 'schema', 'request', 'head'])
def test_same_transport_and_full_host_stop_before_second_request(prepared, tmp_path, failure):
    plan, variants = prepared
    bad, good = replies()
    if failure == 'source':
        bad['issues'][0]['source_ids'] = [9999]
    if failure == 'schema':
        bad['issues'][0].pop('suggested_correction')
    provider = fake_provider([tool_response(bad), tool_response(good)])
    def inspect(request, exchange, inputs):
        if failure == 'request':
            request = replace(request, messages=(replace(request.messages[0], content='wrong policy'), *request.messages[1:]))
        return runner.inspect_response(request, exchange, inputs)
    def before_send():
        if failure == 'head':
            raise ValueError('changed_checkout')
    result = runner.observe(provider, tmp_path, variants, plan,
        inspect_response=inspect, adjudicate=decision(failure != 'host'),
        before_send=before_send, clock=lambda: 0)
    assert result['pair_accepted'] is (failure is None)
    assert provider._calls == (2 if failure is None else 0 if failure == 'head' else 1)
    assert result['unknown_usage_calls'] == 0 and not result['production_admitted']
    if failure not in ('head', 'source', 'schema', 'request'):
        journal = json.loads((tmp_path/'attribution-1/journal.json').read_bytes())
        assert journal['parsed_review'] == bad  # No deletion/repair of model advice.
        assert journal['policy_sha256'] != journal['validator_policy_sha256']


def test_preparation_and_closed_run_gates_precede_credentials(prepared, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path/'run')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed')
    monkeypatch.setattr(runner, 'load_role_settings', lambda *_: pytest.fail('credentials accessed'))
    monkeypatch.setattr(runner, 'verify_public_ci', lambda *_: pytest.fail('CI accessed'))
    with pytest.raises(ValueError, match='preparation_required'):
        runner.run(NS(execute=True, env_file=tmp_path/'unused', ci_run='1', plan_sha='bad'))
    (tmp_path/'run').mkdir()
    monkeypatch.setattr(runner, 'prepare', lambda: pytest.fail('closed batch prepared'))
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))


@pytest.mark.parametrize('defect', [None, 'request', 'journal', 'independent', 'usage'])
def test_seal_replays_actual_request_journal_dual_review_and_usage(prepared, tmp_path, monkeypatch, defect):
    plan, variants = prepared
    run = tmp_path/'run'
    run.mkdir()
    frozen = tmp_path/'preparation.json'
    closed = tmp_path/'closed.json'
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', run)
    monkeypatch.setattr(runner, 'PREPARATION', frozen)
    monkeypatch.setattr(runner, 'CLOSED_RESULT', closed)
    write_new_json(frozen, plan)
    write_new_json(run/'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    for name, inputs, request in variants:
        write_new_json(run/(name+'-source.json'), dict(input_json=inputs.data_json, report=inputs.source.report))
        (run/(name+'-prepared-request.json')).write_bytes(validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID))
    provider = fake_provider([tool_response(r) for r in replies()])
    def host(path, remaining):
        cell = next(c for c in plan['cells'] if c['id'] == path.parent.name)
        value = dict(response_sha256=runner.sha(path), input_sha256=cell['input_sha256'],
            report_sha256=cell['report_sha256'], accepted=True, defects=[], source_review='Offline full-source fixture.')
        write_new_json(path.with_name('independent-review.json'), value)
        value = dict(value, independent_sha256=runner.sha(path.with_name('independent-review.json')))
        write_new_json(path.with_name('host-decision.json'), value)
        return value
    result = runner.observe(provider, run, variants, plan,
        inspect_response=runner.inspect_response, adjudicate=host, clock=lambda: 0)
    for i, row in enumerate(result['cases'], 1):
        stream = run/'transport'/f'stream-{i:03d}'
        stream.mkdir(parents=True)
        write_new_json(stream/'reservation.json', dict(ordinal=i, transport_id=REVIEW_MODEL_TRANSPORT_ID,
            state='reserved_before_io', request_sha256=row['request_sha256']))
        write_new_json(stream/'result.json', dict(transport_id=REVIEW_MODEL_TRANSPORT_ID, state='complete'))
        write_new_json(stream/'progress.json', dict(state='complete', **row['observed_usage']))
        write_new_json(stream/'private.json', dict(reasoning_content='PRIVATE_REASONING_MARKER'))
    arm = run/'attribution-1'
    if defect == 'request':
        path = arm/'request.raw.json'
        value = json.loads(path.read_bytes())
        value['timeout_s'] = 301
    elif defect == 'journal':
        path = arm/'journal.json'
        value = json.loads(path.read_bytes())
        value['parsed_review']['issues'][0]['suggested_correction'] = 'changed'
    elif defect == 'independent':
        path = arm/'independent-review.json'
        value = json.loads(path.read_bytes())
        value['accepted'] = False
    elif defect == 'usage':
        path = run/'transport/stream-001/progress.json'
        value = json.loads(path.read_bytes())
        value['input_tokens'] += 1
    if defect:
        path.write_text(json.dumps(value), encoding='utf-8')
        with pytest.raises(ValueError, match='correction_scope_seal_'):
            runner.seal()
        assert not closed.exists()
    else:
        assert runner.seal()['pair_accepted']
        exported = closed.read_text()
        assert 'PRIVATE_REASONING_MARKER' not in exported
        assert 'transport/stream-001/private.json' in exported  # Hash only.
