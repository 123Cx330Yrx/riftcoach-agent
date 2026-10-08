"""A sealed initial review is consumed unchanged by actual edit/final wiring."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_boundary_examples_tail as runner
from tests.test_role_review_notes import tool_response, request_data


def test_frozen_tail_request_contract_is_preserved_without_reusing_source_identity():
    plan, _ = runner.prepare()
    frozen = runner.read(runner.PREPARATION)
    closed = runner.read(runner.CLOSED_RESULT)
    assert frozen == closed['public_json_contents']['plan.json']['preparation_plan']
    assert runner.canonical_sha(frozen) == closed['public_json_contents']['plan.json']['plan_sha256']
    # Source-only maintenance must not rewrite a closed plan or masquerade as
    # its source identity. Keep every request/data/policy/budget binding exact.
    assert {k: v for k, v in plan.items() if k != 'source_sha256'} == {
        k: v for k, v in frozen.items() if k != 'source_sha256'}
    assert plan['source_sha256'].keys() == frozen['source_sha256'].keys()
    for path, sha in plan['source_sha256'].items():
        assert sha == runner.digest((runner.ROOT/path).read_text(encoding='utf-8'))
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))
    assert plan['budget']['max_calls'] == 2
    assert plan['budget']['estimated_uncached_cny'] == '1.5724544'
    assert plan['offline_initial_injections'] == 1 and not plan['execution_authorized']


def test_actual_issue_preserved_and_new_policy_is_review_only():
    plan, (source, response, initial, editor) = runner.prepare()
    assert request_data(editor)['accepted_review']['issues'] == response.tool_calls[0].arguments['issues']
    assert runner.RULE not in editor.messages[0].content
    assert initial == runner.request_for(runner.Workflow.build_inputs(source))
    assert not plan['review_controls_qualified'] and not plan['production_admitted']


@pytest.mark.parametrize('failure', [None, 'host', 'malformed', 'timeout'])
def test_real_factory_editor_and_fresh_review_keep_shared_tail_budget(monkeypatch, tmp_path, failure):
    plan, prepared = runner.prepare()
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path)
    monkeypatch.setattr(runner, 'PREPARATION', tmp_path/'frozen-preparation.json')
    write_new_json(runner.PREPARATION, plan)
    write_new_json(tmp_path/'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    write_new_json(tmp_path/'source.json', dict(report=prepared[0].report,
        input_json=runner.Workflow.build_inputs(prepared[0]).data_json))
    correct = next(s.report for f, s in runner.frozen_cases()[0] if f['key'] == 'claim-scope:1')
    final = dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
    if failure == 'malformed':
        del final['score']
    replies = [ChatResponse(content=correct, model='glm-5.3-flash', provider='zhipu',
        finish_reason='stop', usage=TokenUsage(10, 10)), tool_response(final)]
    requests = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        requests.append(json.loads(raw))
        if failure == 'timeout':
            raise TimeoutError('offline')
        response = replies.pop(0)
        assert response.model == environ['LLM_MODEL']
        write_new_json(directory/'result.json', dict(state='complete', transport_id=transport_id))
        write_new_json(directory/'progress.json', dict(state='complete',
            input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))
        return response
    monkeypatch.setattr(bridge, 'run_child', child)
    def settings(model):
        return NS(model=model, api_key='offline', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path/'transport', source_projection=runner.PROJECTION)
    def host(path, remaining):
        value = dict(accepted=failure != 'host', response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            stage=path.stem, defects=[] if failure != 'host' else ['offline rejection'],
            source_review='Offline independent full-source test fixture.')
        independent = path.with_name(path.stem+'-independent.json')
        write_new_json(independent, value)
        value = dict(value, independent_sha256=runner.sha(independent))
        write_new_json(path.with_name(path.stem+'-host-decision.json'), value)
        return value
    result = runner.observe(factory, tmp_path, plan, prepared, workflow_type=runner.Workflow,
        initial_review_accepted=True, coach_contract=runner.CONTRACT, adjudicate=host)
    assert result['tail_accepted'] is (failure is None), result
    assert len(requests) == (1 if failure in ('host', 'timeout') else 2)
    assert result['accounting']['unknown_usage_calls'] == (1 if failure == 'timeout' else 0)
    if len(requests) == 2:
        actual = bridge.REQUEST.validate_json(json.dumps(requests[1]), strict=True)
        expected = runner.Workflow.make_request(runner.Workflow.build_inputs(replace(prepared[0], report=correct)))
        metadata = dict(actual.metadata)
        assert metadata.pop('coach_budget_contract') == 'coach-bounded-review-v2'
        assert replace(actual, metadata=metadata, timeout_s=expected.timeout_s) == expected
        data = request_data(actual)
        assert not {'previous_review', 'accepted_review', 'previous_issues'} & data.keys()
    if failure is None:
        journal = json.loads((tmp_path/'final-journal.json').read_bytes())
        assert journal['policy_sha256'] == runner.digest(expected.messages[0].content)
        from scripts.export_boundary_examples_tail import build
        exported = build()
        assert exported['exact_tail_replay_verified'] and exported['provider_requests'] == 2
        assert not exported['review_controls_qualified'] and not exported['production_admitted']
        for relative, key, replacement, code in (
                ('injected-initial-journal.json', 'raw', '{}', 'export_initial_arguments'),
                ('result.json', 'final_score', 1, 'export_journal'),
                ('result.json', 'final_report_sha256', '0'*64, 'export_model_arguments'),
                ('final.json', 'report', 'changed', 'export_report_hash'),
                ('transport/tail/review/stream-002/progress.json', 'output_tokens', 999, 'export_progress_usage')):
            path = tmp_path/relative
            original = path.read_bytes()
            value = json.loads(original)
            value[key] = replacement
            path.write_text(json.dumps(value), encoding='utf-8')
            with pytest.raises(ValueError, match=code):
                build()
            path.write_bytes(original)
        independent = tmp_path/'final-independent.json'
        value = json.loads(independent.read_bytes())
        value['accepted'] = False
        independent.write_text(json.dumps(value), encoding='utf-8')
        with pytest.raises(ValueError, match='export_dual_review'):
            build()


def test_closed_and_unfrozen_execution_stop_before_ci_or_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path/'run')
    monkeypatch.setattr(runner, 'CLOSED_RESULT', tmp_path/'closed')
    monkeypatch.setattr(runner, 'verify_public_ci', lambda *_: pytest.fail('CI accessed'))
    with pytest.raises(ValueError, match='preparation_required'):
        runner.run(NS(execute=True, env_file=None, ci_run=None, plan_sha=None))
    (tmp_path/'run').mkdir()
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))
