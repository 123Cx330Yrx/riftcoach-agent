"""Read exact diagnostic stage, dispatch a review task, import a real native final.

This operator helper never invents either source judgment and never sends model
requests. Supply an explicit primary notes file and actual independent event ID.
"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid

from app.evaluation.golden_integrated_runtime import Exchange
from scripts import run_scope_competition_diagnostic as runner
from scripts.codex_review_event_source import review_task
from scripts.review_independence_contract import make_primary_attestation

base = runner.base


def material(directory, key):
    directory = Path(directory)
    if (directory / 'result.json').exists():
        raise ValueError('scope_competition_batch_closed')
    saved = json.loads((directory / 'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if (plan != runner.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id'])
            or saved['plan_sha256'] != base.canonical_sha(plan)):
        raise ValueError('scope_competition_plan_changed')
    index = runner.KEYS.index(key)
    calls = runner.read_completed_calls(directory / 'transport/diagnostic')
    if len(calls) != index + 1 or not calls[index]['completed']:
        raise ValueError('scope_competition_pending_receipt')
    cell, inputs, prepared = runner.controls()[index]
    call = calls[index]
    issued = call['request']
    metadata = dict(issued.metadata)
    if metadata.pop('competition_diagnostic', None) != runner.EXPERIMENT:
        raise ValueError('scope_competition_request_budget_contract')
    if (not 0 < issued.timeout_s <= prepared.timeout_s
            or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared):
        raise ValueError('scope_competition_issued_request')
    arm = directory / key
    source = json.loads((arm / 'source.json').read_bytes())
    if source != dict(input_json=inputs.data_json, report=inputs.source.report,
                      synthetic_report=cell['synthetic_report']):
        raise ValueError('scope_competition_source_changed')
    raw = base.tool_result(prepared, Exchange(issued, call['response'], call['binding']['request_sha256']))
    _, _, journal = runner.prototype.validate(raw, inputs)
    stage = dict(stage='initial', report=inputs.source.report, journal=journal)
    if json.loads((arm / 'stage.json').read_bytes()) != stage:
        raise ValueError('scope_competition_stage_changed')
    if (json.loads((arm / 'request.json').read_bytes()) != json.loads(base.validate_request(
            issued, transport_id=base.REVIEW_MODEL_TRANSPORT_ID))
            or json.loads((arm / 'response.json').read_bytes()) != base.public_response(
                json.loads(base.RESPONSE.dump_json(call['response'])))):
        raise ValueError('scope_competition_public_receipt_changed')
    bound = dict(plan_sha256=saved['plan_sha256'], key=key, stage='initial',
        response_sha256=base.sha(arm / 'response.json'), report_sha256=base.digest(stage['report']),
        request_sha256=call['binding']['request_sha256'])
    required = json.loads((arm / 'review-required.json').read_bytes())
    if required['binding'] != bound or required['stage_sha256'] != base.stage_identity(stage):
        raise ValueError('scope_competition_handoff_changed')
    return plan, stage, bound


def task(directory, key):
    plan, stage, bound = material(directory, key)
    return review_task(bound,
        f'Read the complete actual source.json, response.json and stage.json in {Path(directory) / key}. '
        'Assess all findings, corrections, markers and scope_checks against the complete report and sources. Reject missing scope coverage or wrong evidence relations for genuinely competing scopes. '
        'Use the accepted whole-context standard. A resolved scope is not itself proof of a fact or inference. No previous opinion is supplied. '
        'A host acceptance certifies this full review and its scope audit, NOT the intentionally unrepaired report. '
        'No Provider calls or file edits; do not inspect private reasoning. '
        'Return ONLY valid JSON {binding: exact six fields, review: {binding: same fields, '
        'stage_assessment: {stage: "initial", stage_sha256: "' + base.stage_identity(stage) + '", '
        'reviewer: "' + plan['review_principals']['independent']['principal_id'] + '", '
        'source_review: detailed source-based judgment, accepted: boolean, defects: [{kind,detail}]}, '
        'report_assessment: null}}. Accepted requires empty defects; rejection requires concrete defects. '
        'Do not supply independent_source_event or primary_attestation. '
        'Valid defect kinds: missed_error,false_positive,unsupported_explanation,wrong_correction,'
        'unsupported_source,internal_contradiction,wrong_final_report,correct_content_lost,identity_or_goal_changed.')


def submit(directory, key, notes, event_id, event_source):
    plan, stage, bound = material(directory, key)
    if set(notes) != {'accepted', 'defects', 'source_review'}:
        raise ValueError('scope_competition_primary_notes_fields')
    primary = dict(binding=bound, report_assessment=None, stage_assessment=dict(notes,
        stage='initial', stage_sha256=base.stage_identity(stage),
        reviewer=plan['review_principals']['primary']['principal_id']))
    primary['primary_attestation'] = make_primary_attestation(primary, plan=plan, bound=bound)
    event = event_source.fetch(event_id=event_id, binding=bound)
    independent = dict(event['review'], independent_source_event=event)
    submission = dict(primary=primary, independent=independent)
    runner.previous.validate_reviews(submission, stage, bound, plan, event_source)
    # Publish a complete create-only file so the waiting process cannot read a
    # partially written JSON document. link fails if a decision already exists.
    arm = Path(directory) / key
    temp = arm / ('.submission-' + uuid.uuid4().hex + '.tmp')
    with runner.previous.submission_close_gate(directory):
        if (Path(directory) / 'result.json').exists():
            raise ValueError('scope_competition_batch_closed')
        try:
            base.write_new_json(temp, submission)
            os.link(temp, arm / 'review-submission.json')
        finally:
            temp.unlink(missing_ok=True)
    return dict(submitted=True, key=key,
        primary_accepted=notes['accepted'], independent_accepted=independent['stage_assessment']['accepted'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('task', 'submit'))
    parser.add_argument('--key', required=True, choices=runner.KEYS)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--codex-executable', type=Path)
    args = parser.parse_args()
    directory = base.ROOT / 'data/runs/model_comparison' / runner.EXPERIMENT
    if args.action == 'task':
        print(task(directory, args.key))
        return
    if not args.notes or not args.event_id or not args.codex_executable:
        parser.error('submit requires explicit notes, event-id and codex-executable')
    plan, _, _ = material(directory, args.key)
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        source = base.CodexHostReviewEventSource(client, plan)
        result = submit(directory, args.key, json.loads(args.notes.read_bytes()), args.event_id, source)
    print(base.compact(result))


if __name__ == '__main__':
    main()
