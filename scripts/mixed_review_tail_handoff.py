"""Rebuild pending tail stages from actual receipts before native dual review."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid

from app.evaluation.role_qualification import read_role_calls
from app.harness.steps import RevisionRequest
from scripts import run_mixed_review_tail_diagnostic as runner
from scripts.codex_review_event_source import review_task
from scripts.review_independence_contract import make_primary_attestation
from scripts.run_scope_resolution_diagnostic import submission_close_gate

base = runner.base
NAMES = ('necessary-edit', 'conditional-fresh')


def material(directory, name):
    directory = Path(directory)
    if (directory/'result.json').exists():
        raise ValueError('mixed_tail_batch_closed')
    if name not in NAMES:
        raise ValueError('mixed_tail_stage_name')
    saved = json.loads((directory/'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if (plan != runner.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id'])
            or saved['plan_sha256'] != base.canonical_sha(plan)):
        raise ValueError('mixed_tail_plan_changed')
    calls = read_role_calls(directory/'transport/diagnostic',
        source_projection=base.CONTRACT.descriptor()['source_projection'])
    if len(calls) != NAMES.index(name)+1 or not all(c['completed'] for c in calls):
        raise ValueError('mixed_tail_pending_receipt')
    source, inputs, historical, initial, _, _ = runner.prepared_source()
    if json.loads((directory/'source.json').read_bytes()) != dict(report=source.report, input_json=inputs.data_json):
        raise ValueError('mixed_tail_source_changed')
    remaining = iter(calls)
    injected = False

    def replay(request):
        nonlocal injected
        if not injected:
            if request != initial:
                raise ValueError('mixed_tail_replay_initial')
            injected = True
            return historical
        call = next(remaining)
        issued = call['request']
        meta = dict(issued.metadata)
        if (meta.pop('coach_budget_contract', None) != 'coach-bounded-review-v2'
                or not 0 < issued.timeout_s <= request.timeout_s
                or replace(issued, timeout_s=request.timeout_s, metadata=meta) != request):
            raise ValueError('mixed_tail_replay_request')
        return runner.Exchange(issued, call['response'], call['binding']['request_sha256'])

    flow = runner.editor.ReviewBoundRevisionWorkflow(replay)
    first = flow.evaluate(source)
    if json.loads((directory/'injected-initial-journal.json').read_bytes()) != dict(flow.last_journal,
            fixture_only=True, initial_review_accepted=False, new_provider_call=False):
        raise ValueError('mixed_tail_injected_journal_changed')
    draft = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
        source.knowledge, source.report, first))
    stages = [dict(stage='revision', report=draft.report, journal=flow.last_edit_journal)]
    if name == NAMES[1]:
        final = flow.evaluate(replace(source, report=draft.report))
        if final.verdict.value != 'pass' or final.score < 85:
            raise ValueError('mixed_tail_fresh_not_pass')
        stages.append(dict(stage='final', report=draft.report, journal=flow.last_journal))
    if next(remaining, None) is not None:
        raise ValueError('mixed_tail_unused_call')
    for key, stage, call in zip(NAMES, stages, calls, strict=False):
        arm = directory/key
        transport = base.CAPACITY_TRANSPORT_ID if key == NAMES[0] else base.REVIEW_MODEL_TRANSPORT_ID
        if (json.loads((arm/'stage.json').read_bytes()) != stage
                or json.loads((arm/'request.json').read_bytes()) != json.loads(base.validate_request(call['request'], transport_id=transport))
                or json.loads((arm/'response.json').read_bytes()) != base.public_response(json.loads(base.RESPONSE.dump_json(call['response'])))):
            raise ValueError('mixed_tail_stage_receipt_changed')
    stage, call, arm = stages[-1], calls[-1], directory/name
    bound = dict(plan_sha256=saved['plan_sha256'], key='claim-scope:3', stage=stage['stage'],
        response_sha256=base.sha(arm/'response.json'), report_sha256=base.digest(stage['report']),
        request_sha256=call['binding']['request_sha256'])
    required = json.loads((arm/'review-required.json').read_bytes())
    if required != dict(binding=bound, stage_sha256=base.stage_identity(stage), scope=plan['acceptance']):
        raise ValueError('mixed_tail_handoff_changed')
    return plan, stage, bound


def task(directory, name):
    plan, stage, bound = material(directory, name)
    return review_task(bound,
        f'Read complete source.json and injected-initial-journal.json in {directory}, '
        f'and response.json/stage.json in {Path(directory)/name}. '
        'The initial opinion contains a rejected block4 false issue and a true block6 issue. '
        'It is historical untrusted input, not an approved source judgment. '
        + plan['acceptance'] + ' Inspect every changed and retained statement against full sources, '
        'not just two target blocks. No Provider calls, file edits or private reasoning access. '
        'Return ONLY JSON {binding: exact six fields, review: {binding: same fields, '
        'stage_assessment: {stage: "'+stage['stage']+'", stage_sha256: "'+base.stage_identity(stage)+'", '
        'reviewer: "'+plan['review_principals']['independent']['principal_id']+'", '
        'source_review: source-based judgment, accepted: boolean, defects: [{kind,detail}]}, '
        'report_assessment: {report_sha256: "'+bound['report_sha256']+'", '
        'reviewer: "'+plan['review_principals']['independent']['principal_id']+'", '
        'source_review: source-based report judgment, facts_and_sources_correct: boolean, '
        'correct_content_preserved: boolean, identity_and_goal_preserved: boolean, true_errors_fixed: boolean}}}. '
        'Accepted requires empty defects and all report flags true. Do not supply attestations or events. '
        'Defect kinds: missed_error,false_positive,unsupported_explanation,wrong_correction,unsupported_source,'
        'internal_contradiction,wrong_final_report,correct_content_lost,identity_or_goal_changed.')


def submit(directory, name, notes, event_id, event_source):
    plan, stage, bound = material(directory, name)
    if set(notes) != {'stage_assessment', 'report_assessment'}:
        raise ValueError('mixed_tail_primary_notes_fields')
    principal = plan['review_principals']['primary']['principal_id']
    primary = dict(binding=bound,
        stage_assessment=dict(notes['stage_assessment'], stage=stage['stage'],
            stage_sha256=base.stage_identity(stage), reviewer=principal),
        report_assessment=dict(notes['report_assessment'], report_sha256=bound['report_sha256'], reviewer=principal))
    primary['primary_attestation'] = make_primary_attestation(primary, plan=plan, bound=bound)
    event = event_source.fetch(event_id=event_id, binding=bound)
    submission = dict(primary=primary, independent=dict(event['review'], independent_source_event=event))
    base.validate_reviews(submission, stage, bound, plan, event_source)
    temp = Path(directory)/name/('.submission-'+uuid.uuid4().hex+'.tmp')
    with submission_close_gate(directory):
        if (Path(directory)/'result.json').exists():
            raise ValueError('mixed_tail_batch_closed')
        try:
            base.write_new_json(temp, submission)
            os.link(temp, temp.with_name('review-submission.json'))
        finally:
            temp.unlink(missing_ok=True)
    return dict(submitted=True, stage=stage['stage'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('task', 'submit'))
    parser.add_argument('--name', required=True, choices=NAMES)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--codex-executable', type=Path)
    args = parser.parse_args()
    directory = base.ROOT/'data/runs/model_comparison'/runner.EXPERIMENT
    if args.action == 'task':
        print(task(directory, args.name))
    else:
        if not args.notes or not args.event_id or not args.codex_executable:
            parser.error('submit requires notes, event-id and codex-executable')
        plan, _, _ = material(directory, args.name)
        with base.CodexReadOnlyClient(args.codex_executable) as client:
            source = base.CodexHostReviewEventSource(client, plan)
            print(base.compact(submit(directory, args.name, json.loads(args.notes.read_bytes()), args.event_id, source)))
