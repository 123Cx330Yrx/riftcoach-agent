"""Receipt-rebuilt task/material and native submit for isolated accepted tails."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid

from app.harness.steps import RevisionRequest
from scripts import run_document_accepted_tails as runner
from scripts.codex_review_event_source import review_task
from scripts.document_review_host_task import with_policies
from scripts.review_independence_contract import make_primary_attestation
from scripts.run_scope_resolution_diagnostic import submission_close_gate

base = runner.base


def material(directory, key, stage, *, closed=False, variants=None):
    directory = Path(directory)
    if key not in runner.KEYS or stage not in runner.STAGES:
        raise ValueError('accepted_tail_handoff_key_stage')
    arm = directory/key.replace(':','-')
    folder = arm/stage
    if not closed and ((directory/'result.json').exists() or (arm/'case-result.json').exists()
            or (folder/'host-reviews.json').exists()):
        raise ValueError('accepted_tail_handoff_closed')
    saved = json.loads((directory/'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if plan != runner.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id']) or saved['plan_sha256'] != base.canonical_sha(plan):
        raise ValueError('accepted_tail_handoff_plan_changed')
    variants = variants or runner.controls()
    row,source,inputs,initial,historical,edit = next(r for r in variants if r[0]['key'] == key)
    if json.loads((arm/'source.json').read_bytes()) != dict(input_json=inputs.data_json,report=source.report):
        raise ValueError('accepted_tail_handoff_source_changed')
    calls = runner.backend.read_calls(directory/'transport'/key.replace(':','-'))
    count = runner.STAGES.index(stage)+1
    if len(calls) < count or (not closed and len(calls) != count) or not all(c['completed'] for c in calls[:count]):
        raise ValueError('accepted_tail_handoff_receipts')
    remaining = iter(calls[:count])
    injected = False
    def send(request):
        nonlocal injected
        if not injected:
            if request != initial:raise ValueError('accepted_tail_handoff_initial_changed')
            injected = True
            return historical
        call = next(remaining)
        issued = call['request']
        metadata = dict(issued.metadata)
        if (metadata.pop('coach_budget_contract',None) != 'coach-bounded-review-v2'
                or not 0 < issued.timeout_s <= request.timeout_s
                or replace(issued,timeout_s=request.timeout_s,metadata=metadata) != request):
            raise ValueError('accepted_tail_handoff_request_changed')
        return runner.Exchange(issued,call['response'],call['binding']['request_sha256'])
    flow = runner.backend.Workflow(send)
    first = flow.evaluate(source)
    if json.loads((arm/'historical-initial-journal.json').read_bytes()) != dict(flow.last_journal,
            historical_input=True,initial_review_accepted=True,new_provider_call=False):
        raise ValueError('accepted_tail_handoff_historical_changed')
    draft = flow.revise(RevisionRequest(source.player_summary,source.deterministic_report,
        source.knowledge,source.report,first))
    stages = [dict(stage='revision',report=draft.report,journal=flow.last_edit_journal)]
    if stage == 'final':
        # Require genuine accepted edit before any fresh stage can be imported.
        previous = json.loads((arm/'revision/host-reviews.json').read_bytes())
        required = json.loads((arm/'revision/review-required.json').read_bytes())
        for role in ('primary','independent'):
            if previous[role]['binding'] != required['binding'] or not previous[role]['stage_assessment']['accepted']:
                raise ValueError('accepted_tail_handoff_rejected_edit')
        flow.evaluate(replace(source,report=draft.report))
        stages.append(dict(stage='final',report=draft.report,journal=flow.last_journal))
    if next(remaining,None) is not None:raise ValueError('accepted_tail_handoff_unused_call')
    for name,value,call in zip(runner.STAGES,stages,calls[:count],strict=False):
        target = arm/name
        transport_id = base.CAPACITY_TRANSPORT_ID if name == 'revision' else base.REVIEW_MODEL_TRANSPORT_ID
        if ((target/'issued-request.json').read_bytes() != base.validate_request(call['request'],transport_id=transport_id)
                or json.loads((target/'stage.json').read_bytes()) != value
                or json.loads((target/'response.json').read_bytes()) != base.public_response(json.loads(base.RESPONSE.dump_json(call['response'])))):
            raise ValueError('accepted_tail_handoff_stage_changed')
    value = stages[-1]
    bound = dict(plan_sha256=saved['plan_sha256'],key=key,stage=stage,
        request_sha256=calls[count-1]['binding']['request_sha256'],response_sha256=base.sha(folder/'response.json'),
        report_sha256=base.digest(value['report']))
    if json.loads((folder/'review-required.json').read_bytes()) != dict(binding=bound,
            stage_sha256=base.stage_identity(value),scope=plan['acceptance']):
        raise ValueError('accepted_tail_handoff_binding_changed')
    return plan,value,bound


def task(directory,key,stage):
    plan,value,bound = material(directory,key,stage)
    arm = Path(directory)/key.replace(':','-')
    principal = plan['review_principals']['independent']['principal_id']
    instructions = (f'Independently read full source.json, historical-initial-journal.json, '
        f'and all stage/response files in {arm}. Inspect complete original and edited reports, '
        'sources, citations, every change/retained statement, editor reason, issues and advisories. '
        'The sealed accepted initial opinion is historical input, not a new signed stage. '
        'No Provider calls, edits or private reasoning access. Return ONLY JSON {binding: exact six '
        'task fields, review: {binding: same fields, stage_assessment: {stage: "'+stage+'", '
        'stage_sha256: "'+base.stage_identity(value)+'", reviewer: "'+principal+'", '
        'source_review: detailed source-based judgment, accepted: boolean, defects: [{kind,detail}]}, '
        'report_assessment: {report_sha256: "'+bound['report_sha256']+'", reviewer: "'+principal+'", '
        'source_review: full-report judgment, facts_and_sources_correct: boolean, '
        'correct_content_preserved: boolean, identity_and_goal_preserved: boolean, true_errors_fixed: boolean}}}. '
        'accepted=true requires empty defects and all four report flags true; rejection needs concrete defects. '
        'Do not supply events/attestations. Defect kinds: missed_error,false_positive,unsupported_explanation,'
        'wrong_correction,unsupported_source,internal_contradiction,wrong_final_report,correct_content_lost,identity_or_goal_changed.')
    raw = (arm/stage/'issued-request.json').read_bytes()
    kwargs = {}
    if stage == 'revision':
        initial_raw = (runner.HISTORICAL_RUN/key.replace(':','-')/'issued-request.json').read_bytes()
        row = next(r for r in plan['cells'] if r['key'] == key)
        kwargs = dict(initial_raw=initial_raw,initial_sha256=row['historical_raw_request_sha256'])
    return with_policies(review_task(bound,instructions),raw,**kwargs)


def submit(directory,key,stage,notes,event_id,event_source):
    plan,value,bound = material(directory,key,stage)
    if set(notes) != {'stage_assessment','report_assessment'}:
        raise ValueError('accepted_tail_primary_notes_fields')
    principal = plan['review_principals']['primary']['principal_id']
    primary = dict(binding=bound,stage_assessment=dict(notes['stage_assessment'],stage=stage,
        stage_sha256=base.stage_identity(value),reviewer=principal),report_assessment=dict(
        notes['report_assessment'],report_sha256=bound['report_sha256'],reviewer=principal))
    primary['primary_attestation'] = make_primary_attestation(primary,plan=plan,bound=bound)
    event = event_source.fetch(event_id=event_id,binding=bound)
    submission = dict(primary=primary,independent=dict(event['review'],independent_source_event=event))
    base.validate_reviews(submission,value,bound,plan,event_source)
    folder = Path(directory)/key.replace(':','-')/stage
    temp = folder/('.submission-'+uuid.uuid4().hex+'.tmp')
    with submission_close_gate(directory):
        arm = folder.parent
        if ((Path(directory)/'result.json').exists() or (arm/'case-result.json').exists()
                or (folder/'host-reviews.json').exists()):
            raise ValueError('accepted_tail_handoff_closed')
        try:
            base.write_new_json(temp,submission)
            os.link(temp,folder/'review-submission.json')
        finally:
            temp.unlink(missing_ok=True)
    return dict(submitted=True,key=key,stage=stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('task','material','submit'))
    parser.add_argument('--directory',type=Path,default=base.ROOT/'data/runs/model_comparison'/runner.EXPERIMENT)
    parser.add_argument('--key',required=True,choices=runner.KEYS)
    parser.add_argument('--stage',required=True,choices=runner.STAGES)
    parser.add_argument('--notes',type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--codex-executable',type=Path)
    args = parser.parse_args()
    if args.action == 'task':print(task(args.directory,args.key,args.stage))
    elif args.action == 'material':print(base.compact(material(args.directory,args.key,args.stage)))
    else:
        if not args.notes or not args.event_id or not args.codex_executable:parser.error('submit needs notes, event-id and codex-executable')
        plan,_,_ = material(args.directory,args.key,args.stage)
        with base.CodexReadOnlyClient(args.codex_executable) as client:
            source = base.CodexHostReviewEventSource(client,plan)
            print(base.compact(submit(args.directory,args.key,args.stage,json.loads(args.notes.read_bytes()),args.event_id,source)))


if __name__ == '__main__':main()
