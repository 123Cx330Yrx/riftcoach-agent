"""Seal actual tail receipts and source-bound judgments, without private text."""
from dataclasses import replace
import json

from app.evaluation.coarse_role_qualification import read_calls
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from scripts.export_partitioned_review import public_response
from scripts.run_role_coach_development import summarize_calls
from scripts import run_correction_scope_tail as runner


def build():
    run = runner.RUN_DIRECTORY
    plan, prepared = runner.prepare()
    saved = runner.read(run/'plan.json')
    if (saved['preparation_plan'] != plan or plan != runner.read(runner.PREPARATION)
            or saved['plan_sha256'] != runner.canonical_sha(plan)):
        raise ValueError('correction_tail_export_plan')
    source, response, initial, editor = prepared
    if runner.read(run/'source.json') != dict(report=source.report,
            input_json=runner.Workflow.build_inputs(source).data_json):
        raise ValueError('correction_tail_export_source')
    result = runner.read(run/'result.json')
    initial_path = run/'injected-initial-journal.json'
    if initial_path.exists():
        injected = runner.read(initial_path)
        if json.loads(injected['raw']) != response.tool_calls[0].arguments:
            raise ValueError('correction_tail_export_initial_arguments')
        _, _, original_journal = runner.Workflow.validate_review(injected['raw'], runner.Workflow.build_inputs(source))
        if injected != dict(original_journal, fixture_only=True, initial_review_accepted=True, new_provider_call=False):
            raise ValueError('correction_tail_export_initial_journal')
    elif result['tail_accepted']:
        raise ValueError('correction_tail_export_initial_missing')
    calls = read_calls(run/'transport/tail')
    if result['accounting'] != summarize_calls(run/'transport/tail', coach_contract=runner.CONTRACT):
        raise ValueError('correction_tail_export_accounting')
    if len(calls) > 2:
        raise ValueError('correction_tail_export_call_count')
    accepted_stages = []
    for ordinal, call in enumerate(calls, 1):
        stage = 'revision' if ordinal == 1 else 'final'
        actual = call['request']
        if ordinal == 1:
            expected = editor
        else:
            revised = runner.read(run/'revision.json')['report']
            expected = runner.Workflow.make_request(runner.Workflow.build_inputs(replace(source, report=revised)))
        metadata = dict(actual.metadata)
        if (metadata.pop('coach_budget_contract', None) != 'coach-bounded-review-v2'
                or not 0 < actual.timeout_s <= expected.timeout_s
                or replace(actual, timeout_s=expected.timeout_s, metadata=metadata) != expected):
            raise ValueError('correction_tail_export_actual_request')
        if not call['completed']:
            continue
        progress = runner.read(run/'transport/tail'/call['binding']['raw_directory']/f'stream-{ordinal:03d}'/'progress.json')
        if (progress['state'] != 'complete'
                or any(progress[k] != call['usage'][k] for k in ('input_tokens', 'output_tokens'))):
            raise ValueError('correction_tail_export_progress_usage')
        path = run/(stage+'.json')
        if not path.exists():
            if result['tail_accepted']:
                raise ValueError('correction_tail_export_missing_stage')
            continue
        material = runner.read(path)
        if material['report_sha256'] != digest(material['report']):
            raise ValueError('correction_tail_export_report_hash')
        if stage == 'revision':
            if material['report'] != call['response'].content:
                raise ValueError('correction_tail_export_edit')
        else:
            journal = material['journal']
            if (material['report'] != revised or result['final_report_sha256'] != digest(revised)
                    or json.loads(journal['raw']) != call['response'].tool_calls[0].arguments):
                raise ValueError('correction_tail_export_model_arguments')
            _, wire, rebuilt = runner.Workflow.validate_review(journal['raw'],
                runner.Workflow.build_inputs(replace(source, report=material['report'])))
            if (rebuilt != journal or journal != runner.read(run/'final-journal.json')
                    or result['final_verdict'] != wire.verdict or result['final_score'] != wire.score):
                raise ValueError('correction_tail_export_journal')
        host_path = run/(stage+'-host.json')
        if host_path.exists():
            host = runner.read(host_path)
            other_path = run/(stage+'-independent.json')
            other = runner.read(other_path)
            if (host != runner.read(run/(stage+'-host-decision.json'))
                    or host['independent_sha256'] != runner.sha(other_path)
                    or any(r['response_sha256'] != runner.sha(path) or r['stage'] != stage
                           or not r['source_review'].strip() for r in (host, other))
                    or type(host['accepted']) is not bool or other['accepted'] is not host['accepted']
                    or host['accepted'] and any(r['defects'] != [] for r in (host, other))):
                raise ValueError('correction_tail_export_dual_review')
            if host['accepted']:
                accepted_stages.append(stage)
    if result['tail_accepted'] and (accepted_stages != ['revision', 'final']
            or [c['binding']['role'] for c in calls] != ['revision', 'review']
            or not all(c['completed'] for c in calls)):
        raise ValueError('correction_tail_export_completion')
    files = sorted(p for p in run.rglob('*') if p.is_file())
    public = {}
    for path in files:
        relative = path.relative_to(run).as_posix()
        if path.suffix != '.json':
            continue
        # Child output is private, even if it happens to use a JSON suffix.
        if '/stream-' in relative and path.name not in ('reservation.json', 'progress.json', 'result.json'):
            continue
        value = runner.read(path)
        public[relative] = public_response(value) if path.name.startswith('response-') else value
    return dict(kind='correction_scope_tail_result_v1', execution_result=result,
        original_file_sha256={p.relative_to(run).as_posix(): runner.sha(p) for p in files},
        public_json_contents=public, exact_tail_replay_verified=True,
        initial_fixture_sha256=runner.EVIDENCE_SHA, offline_initial_injections=1,
        provider_requests=len(calls), unknown_usage_calls=result['accounting']['unknown_usage_calls'],
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False)


if __name__ == '__main__':
    output = build()
    write_new_json(runner.CLOSED_RESULT, output)
    print(compact(dict(export_sha256=runner.sha(runner.CLOSED_RESULT),
        provider_requests=output['provider_requests'],
        tail_accepted=output['execution_result']['tail_accepted'])))
