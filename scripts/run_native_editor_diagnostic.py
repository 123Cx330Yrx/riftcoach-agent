"""Frozen editor diagnostic, separate from review qualification and production.

Preview is offline. Execute one phase at a time after exact-SHA CI. An edit
requires manual whole-output adjudication before any recheck, and a recheck
requires manual acceptance before the next case. There is no edit retry/resume.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import time

from pydantic import Field

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_integrated_runtime import (BudgetedReviewSender,
    ReceiptedStreamProvider, validate_exchange)
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from scripts.check_native_claim_scope import load_controls
from scripts.check_native_contract_options import prepare_editor_diagnostic, ROOT
from scripts.native_contract_options import editor_request, validate_editor
from scripts.run_golden_inference_development import verify_public_ci

PLAN = ROOT/'data/evaluation/results/golden_native_editor_diagnostic_plan_v2.json'
EXPERIMENT = 'native-editor-diagnostic-v1'
LIVE_STATUS = 'bounded_editor_diagnostic_after_exact_ci'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(index):
    frozen = read(PLAN)
    if prepare_editor_diagnostic() != frozen:
        raise ValueError('editor_frozen_plan_changed')
    if type(index) is not int or not 1 <= index <= 3:
        raise ValueError('editor_case_index_invalid')
    case = frozen['cases'][index-1]
    _, requests, _ = load_controls()
    req = requests[{1:2, 2:3, 3:0}[index]]
    inputs = native.build_inputs(req)
    if req.report != case['report'] or digest(inputs.data_json) != case['input_sha256']:
        raise ValueError('editor_frozen_source_changed')
    request = editor_request(inputs, case['proposed_review_raw'])
    if hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest() != case['request_sha256']:
        raise ValueError('editor_frozen_request_changed')
    return case, req, request


class Adjudication(Strict):
    subject_sha256: str = Field(pattern='^[0-9a-f]{64}$')
    accepted: bool
    reviewer: str = Field(min_length=1)
    full_report_read: bool
    decisions_and_sources_checked: bool
    changed_content_checked: bool
    reasons: str = Field(min_length=20)


def subject(directory, phase):
    names = ['plan.json', 'input.json', 'edit/result.json',
             'edit/editor-journal.json', 'edit/report.md']
    if phase == 'recheck':
        names += ['edit/adjudication.json', 'recheck/result.json', 'recheck/evaluation-journal.json']
    for part in ('edit', 'recheck') if phase == 'recheck' else ('edit',):
        result = read(directory/part/'result.json')
        for ordinal in range(1, result['completed_calls']+1):
            names += [f'{part}/{stem}-{ordinal:03d}.{suffix}' for stem,suffix in
                      (('request','json'), ('request','wire.json'), ('response','json'))]
        if result['receipted_transport']:
            for ordinal in range(1, result['transport_reserved_calls']+1):
                names += [f'transport-{part}/stream-{ordinal:03d}/{name}.json'
                          for name in ('reservation','result')]
    return digest(compact({n: sha(directory/n) for n in names}))


def validate_saved_exchange(directory, phase, ordinal, *, receipted):
    base = directory/phase
    response = read(base/f'response-{ordinal:03d}.json')
    wire = base/f'request-{ordinal:03d}.wire.json'
    request_sha = sha(wire)
    if (request_sha != response['request_sha256']
            or read(wire) != read(base/f'request-{ordinal:03d}.json')
            or digest(response['content'] or '') != response['content_sha256']):
        raise ValueError('editor_saved_exchange_identity_changed')
    if receipted:
        transport = directory/f'transport-{phase}'/f'stream-{ordinal:03d}'
        reservation, terminal = read(transport/'reservation.json'), read(transport/'result.json')
        if (reservation['request_sha256'] != request_sha or reservation['ordinal'] != ordinal
                or reservation['transport_id'] != CAPACITY_TRANSPORT_ID
                or terminal['transport_id'] != CAPACITY_TRANSPORT_ID or terminal['state'] != 'complete'):
            raise ValueError('editor_saved_transport_identity_changed')


def require_adjudication(directory, phase):
    value = Adjudication.model_validate(read(directory/phase/'adjudication.json'), strict=True)
    if value.subject_sha256 != subject(directory, phase):
        raise ValueError('editor_adjudication_identity_changed')
    if not all((value.accepted, value.full_report_read, value.decisions_and_sources_checked, value.changed_content_checked)):
        raise ValueError('editor_manual_acceptance_required')
    if not read(directory/phase/'result.json')['protocol_success']:
        raise ValueError('editor_previous_phase_failed')
    result = read(directory/phase/'result.json')
    for ordinal in range(1, result['completed_calls']+1):
        validate_saved_exchange(directory, phase, ordinal, receipted=result['receipted_transport'])
    return value


def adjudicate(directory, phase, *, accepted, reviewer, reasons):
    """Called by the reviewing agent after reading full content, never by model output."""
    value = Adjudication(subject_sha256=subject(directory, phase), accepted=accepted,
        reviewer=reviewer, full_report_read=True, decisions_and_sources_checked=True,
        changed_content_checked=True, reasons=reasons)
    write_new_json(directory/phase/'adjudication.json', value.model_dump())
    return value


def restored_edit(directory, case, req):
    result = read(directory/'edit/result.json')
    response = read(directory/'edit/response-001.json')
    if not result['protocol_success'] or result['completed_calls'] != 1 or result['unknown_usage_calls']:
        raise ValueError('editor_completed_edit_required')
    if response['content_sha256'] != digest(response['content']):
        raise ValueError('editor_response_identity_changed')
    if any(result[key] != response['usage'][key] for key in ('input_tokens','output_tokens')):
        raise ValueError('editor_usage_identity_changed')
    validate_saved_exchange(directory, 'edit', 1, receipted=result['receipted_transport'])
    wire, journal = validate_editor(response['content'], native.build_inputs(req), case['proposed_review_raw'])
    if journal != read(directory/'edit/editor-journal.json') or (directory/'edit/report.md').read_bytes().decode('utf-8') != wire.report:
        raise ValueError('editor_saved_report_changed')
    if sorted((d.issue_id,d.disposition) for d in wire.decisions) != list(enumerate(case['expected_dispositions_host_only'],1)):
        raise ValueError('editor_disposition_mismatch')
    return wire, result


def observe(provider, directory, case, req, *, phase, clock=time.time):
    """Single phase, bounded sender, create-only files. Never repeat a failed phase."""
    plan = read(directory/'plan.json')
    initial_tokens = initial_calls = 0
    wire = None
    if phase == 'recheck':
        require_adjudication(directory,'edit')
        wire, prior = restored_edit(directory,case,req)
        initial_tokens, initial_calls = prior['input_tokens']+prior['output_tokens'], prior['attempted_calls']
    if clock() - plan['started_at_unix'] >= 900:
        raise ValueError('editor_report_deadline_exhausted')
    phase_dir = directory/phase
    phase_dir.mkdir(exist_ok=False)
    sender = BudgetedReviewSender(provider, clock=clock)
    sender.budget.started = plan['started_at_unix']
    sender.budget.calls, sender.budget.tokens = initial_calls, initial_tokens
    attempts, records = [], []
    result = dict(id=case['id'], phase=phase, protocol_success=False, semantic_approval=False,
        manual_semantic_acceptance=False, production_admitted=False, initial_reviewer_qualified=False)

    def send(request):
        # A phase gets exactly 1 editor or at most 2 final-review requests.
        if len(attempts) >= (1 if phase=='edit' else 2):
            raise ValueError('editor_phase_call_limit')
        ordinal = len(attempts)+1
        attempt = dict(ordinal=ordinal, phase=request.metadata['review_phase'], state='reserved_before_sender')
        write_new_json(phase_dir/f'attempt-{ordinal:03d}.json',attempt)
        attempts.append(attempt)
        exchange = sender(request)
        response = exchange.response
        # Transport keeps original receipts locally; this public projection never
        # includes provider private reasoning, even if future implementations add it.
        public = dict(content=response.content, content_sha256=digest(response.content or ''),
            model=response.model, provider=response.provider, finish_reason=response.finish_reason,
            usage=dict(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens),
            request_sha256=exchange.receipt_request_sha256)
        write_new_json(phase_dir/f'response-{ordinal:03d}.json',public)
        transport = validate_request(exchange.issued_request,transport_id=CAPACITY_TRANSPORT_ID)
        with (phase_dir/f'request-{ordinal:03d}.wire.json').open('xb') as f:
            f.write(transport)
        write_new_json(phase_dir/f'request-{ordinal:03d}.json', json.loads(transport))
        records.append(public)
        validate_exchange(request,exchange)
        print(compact(dict(phase=phase, ordinal=ordinal, usage=public['usage'])),flush=True)
        return exchange

    try:
        if phase == 'edit':
            request = editor_request(native.build_inputs(req),case['proposed_review_raw'])
            response = send(request).response
            wire, journal = validate_editor(response.content,native.build_inputs(req),case['proposed_review_raw'])
            write_new_json(phase_dir/'editor-journal.json',journal)
            with (phase_dir/'report.md').open('x',encoding='utf-8',newline='') as f:
                f.write(wire.report)
            match = sorted((d.issue_id,d.disposition) for d in wire.decisions) == list(enumerate(case['expected_dispositions_host_only'],1))
            result.update(protocol_success=match, disposition_match=match, report_sha256=digest(wire.report),
                stop_reason='manual_editor_review_required' if match else 'editor_disposition_mismatch')
        else:
            workflow = native.NativeBusinessReviewWorkflow(send)
            final = workflow.evaluate(replace(req,report=wire.report))
            write_new_json(phase_dir/'evaluation-journal.json',workflow.last_journal)
            passed = final.verdict.value=='pass' and final.score>=85 and not final.issues
            result.update(protocol_success=passed, final_verdict=final.verdict.value, final_score=final.score,
                report_sha256=digest(wire.report), stop_reason='manual_final_review_required' if passed else 'final_review_not_passed')
    except Exception as error:
        result.update(stop_reason='protocol_or_execution_failure',error_type=type(error).__name__)
        code = getattr(error,'code',None) or (str(error) if isinstance(error,ValueError) else None)
        if isinstance(code,str) and re.fullmatch('[a-z_]{1,90}',code): result['error_code']=code
    finally:
        reserved = getattr(provider,'_calls', len(attempts))
        result.update(attempted_calls=len(attempts), transport_reserved_calls=reserved,
            receipted_transport=hasattr(provider,'_directory'),
            completed_calls=len(records), unknown_usage_calls=max(0,reserved-len(records)),
            input_tokens=sum(r['usage']['input_tokens'] for r in records),
            output_tokens=sum(r['usage']['output_tokens'] for r in records),
            cumulative_budget_calls=sender.budget.calls, cumulative_budget_tokens=sender.budget.tokens,
            elapsed_seconds=round(clock()-plan['started_at_unix'],3))
        write_new_json(phase_dir/'result.json',result)
    return result


def run(args):
    case, req, request = prepare(args.case_index)
    preview = dict(experiment=EXPERIMENT,case_id=case['id'],phase=args.phase,
        preview_scope='frozen_editor_plan_only; final_review_request_built_from_accepted_actual_edit',
        frozen_plan_sha256=sha(PLAN), request_sha256=case['request_sha256'],
        proposed_review_sha256=case['proposed_review_sha256'], report_sha256=case['report_sha256'],
        input_sha256=case['input_sha256'], input_ceiling=case['input_ceiling'],
        model='glm-5.3-flash', reasoning_effort='high', max_output=32768, request_timeout_s=300,
        max_case_calls=3,max_revisions=1,total_tokens=401920,case_timeout_s=900,sdk_retries=0,
        live_status=LIVE_STATUS,production_admitted=False,initial_reviewer_qualified=False,
        semantic_approval=False,labels_sent_to_model=False)
    if not args.execute:
        print(compact(preview)); return preview
    if LIVE_STATUS != 'bounded_editor_diagnostic_after_exact_ci':
        raise ValueError('editor_diagnostic_offline')
    if not re.fullmatch('editor-diagnostic-[a-z0-9-]{1,48}',args.batch_id):
        raise ValueError('editor_batch_id_invalid')
    head = verify_public_ci(args.ci_run)
    batch_dir = args.output_root/args.batch_id
    binding = dict(experiment=EXPERIMENT, head_sha=head, frozen_plan_sha256=sha(PLAN),
                   max_cases=3, order=[r['id'] for r in read(PLAN)['cases']])
    if not batch_dir.exists():
        if args.case_index!=1 or args.phase!='edit': raise ValueError('editor_batch_start_order')
        batch_dir.mkdir(parents=True,exist_ok=False)
        write_new_json(batch_dir/'batch.json',binding)
    elif read(batch_dir/'batch.json') != binding:
        raise ValueError('editor_batch_identity_changed')
    if args.case_index>1:
        previous=batch_dir/binding['order'][args.case_index-2]
        require_adjudication(previous,'recheck')
    directory = batch_dir/case['id']
    if args.phase=='edit':
        directory.mkdir(exist_ok=False)
        write_new_json(directory/'plan.json',dict(preview,head_sha=head,batch_id=args.batch_id,
            ci_run=args.ci_run,started_at_unix=time.time()))
        write_new_json(directory/'input.json',dict(report=req.report,review_raw=case['proposed_review_raw'],
            provenance=case['provenance'],source_review_sha256=case['source_review_sha256']))
    else:
        saved = read(directory/'plan.json')
        if saved['head_sha']!=head or any(saved[k]!=preview[k] for k in ('frozen_plan_sha256','case_id','input_sha256','request_sha256')):
            raise ValueError('editor_phase_identity_changed')
        require_adjudication(directory,'edit')
        restored_edit(directory,case,req)
        if (directory/'recheck').exists(): raise ValueError('editor_recheck_already_attempted')
        if time.time()-saved['started_at_unix']>=900: raise ValueError('editor_report_deadline_exhausted')
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings=load_zhipu_settings(dotenv_values(args.env_file))
    provider=ReceiptedStreamProvider(settings=settings,directory=directory/('transport-'+args.phase),
        transport_id=CAPACITY_TRANSPORT_ID)
    result=observe(provider,directory,case,req,phase=args.phase)
    print(compact(result),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--case-index',type=int,default=1)
    p.add_argument('--phase',choices=['edit','recheck'],default='edit')
    p.add_argument('--batch-id',default='')
    p.add_argument('--ci-run',default='')
    p.add_argument('--env-file',type=Path)
    p.add_argument('--output-root',type=Path,default=ROOT/'data/runs/editor_diagnostic')
    run(p.parse_args())
