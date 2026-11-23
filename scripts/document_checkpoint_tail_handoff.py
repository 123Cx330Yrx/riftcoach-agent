"""Prospective checkpoint handoff, forked to preserve frozen legacy replay.

Receipt/material and native quality checks remain unchanged; checkpoint
publication, required task pins and explicit operator abort are new.
"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid

from app.harness.steps import RevisionRequest
from scripts import run_document_checkpoint_tails as runner
from scripts import host_review_task_checkpoint as checkpoint
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
            or (folder/'host-reviews.json').exists() or (folder/'operator-abort.json').exists()
            or (folder/'review-submission.json').exists()):
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


def task(directory,key,stage,*,closed=False,variants=None):
    plan,value,bound = material(directory,key,stage,closed=closed,variants=variants)
    arm = Path(directory)/key.replace(':','-')
    return task_from_stage(plan,value,bound,arm)


def task_from_stage(plan,value,bound,arm):
    """Rebuild the same delivery from a stage already validated by its caller."""
    arm = Path(arm)
    key,stage = bound['key'],bound['stage']
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


def validate_checkpoint_files(folder,submission,expected_task,plan,bound):
    folder = Path(folder)
    if not isinstance(submission,dict) or 'checkpoint_evidence' not in submission:
        raise ValueError('checkpoint_tail_checkpoint_required')
    pinned_raw = (folder/'task-checkpoint.json').read_bytes()
    task_raw = (folder/'independent-task.json').read_bytes()
    pinned = json.loads(pinned_raw)
    evidence = dict(checkpoint_sha256=checkpoint.digest(pinned_raw),task_sha256=checkpoint.digest(task_raw),
        reviewer_id=plan['review_principals']['independent']['principal_id'],purpose='review')
    if (submission['checkpoint_evidence'] != evidence
            or set(pinned) != {'version','purpose','reviewer_id','task_path','task_sha256','binding'}
            or pinned.get('version') != checkpoint.VERSION or pinned.get('purpose') != 'review'
            or pinned.get('task_sha256') != evidence['task_sha256'] or pinned.get('binding') != bound
            or pinned.get('reviewer_id') != evidence['reviewer_id']
            or json.loads(task_raw) != expected_task):
        raise ValueError('checkpoint_tail_checkpoint_changed')
    return evidence


def submit(directory,key,stage,notes,event_id,event_source,checkpoint_path,checkpoint_sha):
    plan,value,bound = material(directory,key,stage)
    pinned,pinned_task = checkpoint.read(checkpoint_path,checkpoint_sha)
    expected_task = json.loads(task(directory,key,stage))
    if (pinned['purpose'] != 'review' or pinned_task != expected_task
            or pinned['reviewer_id'] != plan['review_principals']['independent']['principal_id']):
        raise ValueError('checkpoint_tail_submit_task')
    if set(notes) != {'stage_assessment','report_assessment'}:
        raise ValueError('accepted_tail_primary_notes_fields')
    principal = plan['review_principals']['primary']['principal_id']
    primary = dict(binding=bound,stage_assessment=dict(notes['stage_assessment'],stage=stage,
        stage_sha256=base.stage_identity(value),reviewer=principal),report_assessment=dict(
        notes['report_assessment'],report_sha256=bound['report_sha256'],reviewer=principal))
    primary['primary_attestation'] = make_primary_attestation(primary,plan=plan,bound=bound)
    event = event_source.fetch(event_id=event_id,binding=bound)
    checkpoint.check_answer(checkpoint_path,checkpoint_sha,json.dumps(dict(binding=bound,review=event['review'])).encode())
    submission = dict(primary=primary,independent=dict(event['review'],independent_source_event=event))
    pinned_raw = Path(checkpoint_path).read_bytes()
    task_raw = Path(pinned['task_path']).read_bytes()
    submission['checkpoint_evidence'] = dict(checkpoint_sha256=checkpoint_sha,
        task_sha256=pinned['task_sha256'],reviewer_id=pinned['reviewer_id'],purpose=pinned['purpose'])
    base.validate_reviews(submission,value,bound,plan,event_source)
    folder = Path(directory)/key.replace(':','-')/stage
    temp = folder/('.submission-'+uuid.uuid4().hex+'.tmp')
    with submission_close_gate(directory):
        arm = folder.parent
        if ((Path(directory)/'result.json').exists() or (arm/'case-result.json').exists()
                or (folder/'host-reviews.json').exists() or (folder/'operator-abort.json').exists()
                or (folder/'review-submission.json').exists()):
            raise ValueError('accepted_tail_handoff_closed')
        try:
            if checkpoint.digest(pinned_raw) != checkpoint_sha or checkpoint.digest(task_raw) != pinned['task_sha256']:
                raise ValueError('checkpoint_tail_submit_checkpoint_changed')
            with (folder/'task-checkpoint.json').open('xb') as f:f.write(pinned_raw)
            with (folder/'independent-task.json').open('xb') as f:f.write(task_raw)
            base.write_new_json(temp,submission)
            os.link(temp,folder/'review-submission.json')
        finally:
            temp.unlink(missing_ok=True)
    return dict(submitted=True,key=key,stage=stage)


def publish_checkpoint(directory,key,stage,output_directory):
    plan,_,_ = material(directory,key,stage)
    output = Path(output_directory)
    output.mkdir(parents=True,exist_ok=True)
    prefix = key.replace(':','-')+'-'+stage
    task_path,checkpoint_path = output/(prefix+'.task.json'),output/(prefix+'.checkpoint.json')
    with task_path.open('x',encoding='utf-8',newline='\n') as f:f.write(task(directory,key,stage)+'\n')
    sha = checkpoint.publish(checkpoint_path,task_path,plan['review_principals']['independent']['principal_id'])
    text = checkpoint.dispatch(checkpoint_path,sha)
    with (output/(prefix+'.dispatch.txt')).open('x',encoding='utf-8',newline='\n') as f:f.write(text+'\n')
    return dict(checkpoint=str(checkpoint_path.resolve()),checkpoint_sha256=sha,dispatch=text)


def abort(directory,key,stage,reason,*,native_event_reference=None):
    # Stopping must remain possible precisely when source/request replay fails.
    # This is a pending-stage operator signal, never a semantic certification.
    directory = Path(directory)
    if key not in runner.KEYS or stage not in runner.STAGES:raise ValueError('checkpoint_tail_abort_scope')
    saved = json.loads((directory/'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if plan.get('run_id') != runner.RUN_ID or saved['plan_sha256'] != base.canonical_sha(plan):
        raise ValueError('checkpoint_tail_abort_plan')
    required = json.loads((directory/key.replace(':','-')/stage/'review-required.json').read_bytes())
    bound = base.required_binding(required['binding'])
    if (bound['plan_sha256'] != saved['plan_sha256'] or bound['key'] != key or bound['stage'] != stage):
        raise ValueError('checkpoint_tail_abort_scope')
    marker = dict(kind=runner.ABORT_KIND,binding=bound,reason=reason,
        native_event_reference=native_event_reference)
    runner.validate_abort(marker,bound)
    folder = Path(directory)/key.replace(':','-')/stage
    temp = folder/('.abort-'+uuid.uuid4().hex+'.tmp')
    with submission_close_gate(directory):
        if (Path(directory)/'result.json').exists() or (folder.parent/'case-result.json').exists() or any(
                (folder/f).exists() for f in ('host-reviews.json','review-submission.json','operator-abort.json')):
            raise ValueError('checkpoint_tail_abort_closed')
        try:
            base.write_new_json(temp,marker)
            os.link(temp,folder/'operator-abort.json')
        finally:temp.unlink(missing_ok=True)
    return dict(aborted=True,key=key,stage=stage,review_submitted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('task','material','checkpoint','submit','abort'))
    parser.add_argument('--directory',type=Path,default=base.ROOT/'data/runs/model_comparison'/runner.RUN_ID)
    parser.add_argument('--key',required=True,choices=runner.KEYS)
    parser.add_argument('--stage',required=True,choices=runner.STAGES)
    parser.add_argument('--output-directory',type=Path)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--notes',type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--codex-executable',type=Path)
    parser.add_argument('--reason',choices=runner.ABORT_REASONS)
    args = parser.parse_args()
    if args.action=='task':print(task(args.directory,args.key,args.stage))
    elif args.action=='material':print(base.compact(material(args.directory,args.key,args.stage)))
    elif args.action=='checkpoint':
        if not args.output_directory:parser.error('checkpoint requires output-directory')
        print(base.compact(publish_checkpoint(args.directory,args.key,args.stage,args.output_directory)))
    elif args.action=='abort':
        if not args.reason:parser.error('abort requires reason')
        print(base.compact(abort(args.directory,args.key,args.stage,args.reason,native_event_reference=args.event_id)))
    else:
        if not all((args.notes,args.event_id,args.codex_executable,args.checkpoint,args.checkpoint_sha)):
            parser.error('submit requires notes, event-id, codex-executable, checkpoint and checkpoint-sha')
        plan,_,_ = material(args.directory,args.key,args.stage)
        with base.CodexReadOnlyClient(args.codex_executable) as client:
            source = base.CodexHostReviewEventSource(client,plan)
            print(base.compact(submit(args.directory,args.key,args.stage,json.loads(args.notes.read_bytes()),
                args.event_id,source,args.checkpoint,args.checkpoint_sha)))


if __name__ == '__main__':main()
