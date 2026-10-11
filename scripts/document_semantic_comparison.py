"""Isolated 5x3 comparison runner, native handoff and strict read-only closure.

This is not a full15 workflow or product qualification. The only live action
is run, gated before credentials by exact package, explicit authorization,
same-HEAD public CI and current native principals. All other actions are local
reads or create-only evidence publication; none can resend a request.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

from app.evaluation import document_review_qualification as qualification
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import RESPONSE
from app.evaluation.role_task_outcome import stage_identity
from scripts import document_semantic_host_task as host
from scripts import document_semantic_request as identity
from scripts import document_semantic_transport as transport
from scripts import prepare_document_semantic_comparison as preparation
from scripts import host_review_task_checkpoint as checkpoint
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.diagnose_block_review_route import route_environment
from scripts.export_partitioned_review import public_response
from scripts.full15_resumption_evidence import validate_checkpoint
from scripts.report_timed_document_workflow import TimedDocumentWorkflow
from scripts.review_independence_contract import make_primary_attestation, require_execution_event_source
from scripts.role_development_host_clock import DevelopmentHostClock
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_full15_resumption_candidate import _validate_reviews
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_scope_resolution_diagnostic import submission_close_gate, close_result

ROOT = preparation.ROOT
VERSION = 'document-semantic-comparison-run-v1'
AUTH_VERSION = 'document-semantic-comparison-authorization-v1'


def read(path):
    return strict_json(Path(path).read_text(encoding='utf-8'))


def plan_for(directory):
    value = read(Path(directory)/'plan.json')
    plan = value['preparation_plan']
    rebuilt, rows = preparation.prepare(root_thread_id=plan['root_thread_id'],
        independent_thread_id=plan['review_principals']['independent']['principal_id'])
    if (set(value) != {'preparation_plan','plan_sha256','execution_head','ci_run'}
            or not re.fullmatch(r'[a-f0-9]{40}',value['execution_head'])
            or not isinstance(value['ci_run'],str)
            or plan != rebuilt or value['plan_sha256'] != preparation.sha(preparation.options.canonical(plan))):
        raise ValueError('semantic_frozen_plan_changed')
    return value, rows


def selected(directory, key):
    value, rows = plan_for(directory)
    matches = [row for row in rows if row[0]['key'] == key]
    if len(matches) != 1:
        raise ValueError('semantic_key_unavailable')
    return value, matches[0], Path(directory)/key.replace(':', '-')


def inputs_for(cell, material):
    source = next(s for c, s in qualification.frozen_cases()[0] if c['key'] == cell['source_key'])
    inputs = TimedDocumentWorkflow.build_inputs(replace(source, report=material['report']))
    if inputs.data_json != material['current_input_json']:
        raise ValueError('semantic_complete_inputs_changed')
    return inputs


def reconstruct(directory, key):
    value, (cell, material, request), folder = selected(directory, key)
    raw = identity.request_bytes(request)
    if (folder/'material.json').read_bytes() != preparation.options.canonical(material):
        raise ValueError('semantic_material_changed')
    response = RESPONSE.validate_json((folder/'transport/raw-response.json').read_bytes())
    receipt = transport.validate_complete(folder/'transport', request, response)
    if read(folder/'transport/receipt.json') != receipt:
        raise ValueError('semantic_receipt_changed')
    wire, stage = host.stage_for(cell, inputs_for(cell, material), request, response)
    public_raw = preparation.options.canonical(public_response(json.loads(RESPONSE.dump_json(response))))
    if ((folder/'issued-request.json').read_bytes() != raw
            or (folder/'response.json').read_bytes() != public_raw
            or read(folder/'stage.json') != stage):
        raise ValueError('semantic_stage_changed')
    bound = dict(plan_sha256=value['plan_sha256'], key=key, stage=cell['stage'],
        response_sha256=preparation.sha(public_raw), report_sha256=digest(stage['report']),
        request_sha256=preparation.sha(raw))
    required = dict(binding=bound, stage_sha256=stage_identity(stage))
    if read(folder/'review-required.json') != required:
        raise ValueError('semantic_review_binding_changed')
    return value, cell, material, request, response, wire, stage, bound, folder


def task_for(directory, key):
    value, cell, _, request, _, _, stage, bound, folder = reconstruct(directory, key)
    return host.task(value['preparation_plan'], cell, stage, bound, folder,
                     identity.request_bytes(request), folder/'material.json')


def validate_submission(directory, key, submission, event_source):
    value, cell, _, _, _, _, stage, bound, folder = reconstruct(directory, key)
    plan = value['preparation_plan']
    for role,evidence in (('primary','primary_attestation'),('independent','independent_source_event')):
        if set(submission[role]) != {'binding','stage_assessment','report_assessment',evidence}:
            raise ValueError('semantic_host_review_fields')
    expected_task = json.loads(task_for(directory, key))
    validate_checkpoint(folder, submission, expected_task, plan, bound)
    accepted = _validate_reviews(submission, stage, bound, plan, event_source,
                                initial=cell['stage'] == 'initial')
    pinned_sha = checkpoint.digest((folder/'task-checkpoint.json').read_bytes())
    checkpoint.read(folder/'task-checkpoint.json', pinned_sha)
    independent = submission['independent']
    checkpoint.check_answer(folder/'task-checkpoint.json', pinned_sha,
        preparation.options.canonical(dict(binding=bound, review={k:v for k,v in independent.items()
            if k != 'independent_source_event'})))
    return accepted


def ensure_open(directory, folder):
    if ((Path(directory)/'result.json').exists() or (folder/'cell-result.json').exists()
            or (folder/'operator-abort.json').exists()):
        raise ValueError('semantic_handoff_closed')


def atomic_new(path, value):
    # Readers cannot see a partially written decision. Never replace a record.
    path = Path(path)
    temp = path.with_name('.submission-'+uuid.uuid4().hex+'.tmp')
    try:
        write_new_json(temp, value)
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def submit(directory, key, notes, event_id, event_source, checkpoint_path, checkpoint_sha):
    value, _, _, _, _, _, _, bound, folder = reconstruct(directory, key)
    if Path(checkpoint_path).resolve() != (folder/'task-checkpoint.json').resolve():
        raise ValueError('semantic_checkpoint_path_changed')
    checkpoint.read(checkpoint_path, checkpoint_sha)
    if set(notes) != {'stage_assessment', 'report_assessment'}:
        raise ValueError('semantic_primary_notes_fields')
    plan = value['preparation_plan']
    primary = dict(binding=bound, **deepcopy(notes))
    primary['primary_attestation'] = make_primary_attestation(primary, plan=plan, bound=bound)
    event = event_source.fetch(event_id=event_id, binding=bound)
    checkpoint.check_answer(checkpoint_path, checkpoint_sha,
        preparation.options.canonical(dict(binding=bound, review=event['review'])))
    submission = dict(primary=primary,
        independent=dict(event['review'], independent_source_event=event),
        checkpoint_evidence=dict(checkpoint_sha256=checkpoint_sha,
            task_sha256=checkpoint.digest((folder/'independent-task.json').read_bytes()),
            reviewer_id=plan['review_principals']['independent']['principal_id'], purpose='review'))
    validate_submission(directory, key, submission, event_source)
    with submission_close_gate(directory):
        ensure_open(directory, folder)
        checkpoint.read(checkpoint_path, checkpoint_sha)
        atomic_new(folder/'review-submission.json', submission)
    return dict(submitted=True, key=key)


def validate_abort(value, bound):
    if (set(value) != {'kind','binding','reason'} or value['kind'] != 'semantic-operator-abort-v1'
            or value['binding'] != bound
            or value['reason'] not in ('reviewer_unavailable','routing_failure','operator_stop')):
        raise ValueError('semantic_abort_invalid')


def abort(directory, key, reason):
    *_, bound, folder = reconstruct(directory, key)
    marker = dict(kind='semantic-operator-abort-v1', binding=bound, reason=reason)
    validate_abort(marker, bound)
    with submission_close_gate(directory):
        ensure_open(directory, folder)
        atomic_new(folder/'operator-abort.json', marker)
    return dict(stopped=True, key=key)


def wait_reviews(directory, key, seconds):
    folder = Path(directory)/key.replace(':', '-')
    authorization=read(Path(directory)/'authorization.json')
    available=(datetime.fromisoformat(authorization['expires_at'])-datetime.now(timezone.utc)).total_seconds()
    if available<=0:
        raise ValueError('semantic_authorization_deadline')
    seconds=min(seconds,available)
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        marker = folder/'operator-abort.json'
        if marker.exists():
            validate_abort(read(marker), read(folder/'review-required.json')['binding'])
            raise ValueError('semantic_operator_abort')
        if (folder/'review-submission.json').exists():
            return read(folder/'review-submission.json')
        time.sleep(.25)
    raise ValueError('semantic_host_deadline')


def outcome(cell, wire, bound, submission, accepted):
    matched = (wire.verdict == 'pass' and wire.score >= 85
        if cell['expected_verdict'] == 'accept' else wire.verdict == 'needs_revision')
    pa, ia = (submission[r]['stage_assessment']['accepted'] for r in ('primary','independent'))
    return dict(key=cell['key'], binding=bound, score=wire.score, verdict=wire.verdict,
        expected_verdict=cell['expected_verdict'], verdict_matched=matched,
        primary_accepted=pa, independent_accepted=ia, host_disagreement=pa != ia,
        semantic_accepted=accepted and matched, new_qualification=0)


def observe(directory, plan, rows, provider, event_source, *, adjudicate=wait_reviews,
            before_send=lambda: None, clock_factory=DevelopmentHostClock):
    directory = Path(directory)
    plan_sha = preparation.sha(preparation.options.canonical(plan))
    clock = clock_factory(directory, max_host_seconds=plan['max_host_seconds'], plan_sha256=plan_sha)
    completed, failed, phase = [], None, 'before_send'
    try:
        for cell, material, request in rows:
            failed, phase = cell['key'], 'before_send'
            clock.before_send()
            if (clock() >= plan['budget']['max_active_seconds']
                    or transport.usage(directory)['attempted_calls'] >= plan['budget']['max_calls']
                    or transport.usage(directory)['known_tokens'] + 96768 > plan['budget']['max_tokens']):
                raise ValueError('semantic_batch_budget')
            # Preserve the fixed 600-second request; do not silently truncate it.
            if plan['budget']['max_active_seconds']-clock() < request.timeout_s:
                raise ValueError('semantic_request_time_reservation')
            before_send()
            clock.before_send()
            if plan['budget']['max_active_seconds']-clock() < request.timeout_s:
                raise ValueError('semantic_request_time_reservation')
            folder = directory/cell['key'].replace(':', '-')
            folder.mkdir(exist_ok=False)
            with (folder/'material.json').open('xb') as stream:
                stream.write(preparation.options.canonical(material))
            write_new_json(folder/'started.json', dict(key=cell['key'], plan_sha256=plan_sha,
                active_elapsed_seconds=clock(), ordinal=len(completed)+1))
            phase = 'transport'
            clock.before_send()
            if plan['budget']['max_active_seconds']-clock() < request.timeout_s:
                phase='before_send'
                raise ValueError('semantic_request_time_reservation')
            response = provider.chat(request, folder/'transport')
            phase = 'protocol'
            wire, stage = host.stage_for(cell, inputs_for(cell, material), request, response)
            with (folder/'issued-request.json').open('xb') as stream:
                stream.write(identity.request_bytes(request))
            public_raw = preparation.options.canonical(public_response(json.loads(RESPONSE.dump_json(response))))
            with (folder/'response.json').open('xb') as stream:
                stream.write(public_raw)
            write_new_json(folder/'stage.json', stage)
            bound = dict(plan_sha256=plan_sha, key=cell['key'], stage=cell['stage'],
                response_sha256=preparation.sha(public_raw), report_sha256=digest(stage['report']),
                request_sha256=cell['request_sha256'])
            write_new_json(folder/'review-required.json',dict(binding=bound,stage_sha256=stage_identity(stage)))
            phase = 'host'
            task = task_for(directory, cell['key'])
            with (folder/'independent-task.json').open('x',encoding='utf-8') as stream:
                stream.write(task+'\n')
            pin = checkpoint.publish(folder/'task-checkpoint.json',folder/'independent-task.json',
                plan['review_principals']['independent']['principal_id'])
            with (folder/'dispatch.txt').open('x',encoding='utf-8') as stream:
                stream.write(checkpoint.dispatch(folder/'task-checkpoint.json',pin)+'\n')
            write_new_json(folder/'review-wait-start.json',dict(kind='semantic_review',**bound))
            submission = clock._wait(dict(kind='semantic_review', **bound),
                lambda seconds: adjudicate(directory,cell['key'],seconds))
            accepted = validate_submission(directory,cell['key'],submission,event_source)
            result = outcome(cell,wire,bound,submission,accepted)
            with submission_close_gate(directory):
                ensure_open(directory,folder)
                write_new_json(folder/'cell-result.json',result)
            completed.append(result)
        failed = None
    except BaseException as error:
        code = str(error) if isinstance(error,ValueError) else type(error).__name__
        if not re.fullmatch(r'[a-zA-Z0-9_]{1,160}',code):
            code = type(error).__name__
        write_new_json(directory/'failure.json',dict(key=failed,phase=phase,code=code))
    result = dict(version=VERSION, plan_sha256=plan_sha, completed=completed,
        scan_completed=failed is None, first_deviation=read(directory/'failure.json') if failed else None,
        unexecuted=[c['key'] for c,_,_ in rows if not (directory/c['key'].replace(':','-')/'transport/issued-request.json').exists()],
        accounting=transport.usage(directory), timing=clock.summary(), new_qualification=0)
    close_result(directory,result)
    return result


def validate_clock(directory, result, plan):
    folder = Path(directory)/'development-host-clock'
    policy = read(folder/'policy.json')
    if (set(policy) != {'schema_version','mode','max_host_seconds','process_restart_allowed',
                       'qualification_adopted','plan_sha256','excludes'}
            or policy['schema_version'] != 'development-host-clock-receipt-v1'
            or policy['mode'] != 'separate-development-host-clock-v1'
            or policy['plan_sha256'] != result['plan_sha256'] or policy['qualification_adopted'] is not False
            or policy['max_host_seconds'] != plan['max_host_seconds']
            or policy['process_restart_allowed'] is not False):
        raise ValueError('semantic_clock_policy')
    waits, ends = sorted(folder.glob('*-waiting.json')), sorted(folder.glob('*-finished.json'))
    expected_cells=[c for c in plan['cells'] if (Path(directory)/c['key'].replace(':','-')/'review-wait-start.json').exists()]
    if (len(waits) != len(ends) or len(waits) != len(expected_cells)
            or any(not (Path(directory)/c['key'].replace(':','-')/'review-wait-start.json').exists()
                for c in result['completed'])):
        raise ValueError('semantic_clock_inventory')
    previous_host, previous_active = 0.,0.
    for i,(start,end) in enumerate(zip(waits,ends,strict=True),1):
        if start.name != f'{i:04d}-waiting.json' or end.name != f'{i:04d}-finished.json':
            raise ValueError('semantic_clock_sequence')
        a,b = read(start),read(end)
        if (set(a) != {'binding','active_elapsed_seconds','wall_elapsed_seconds','remaining_host_seconds'}
                or set(b) != {'outcome','binding','host_elapsed_seconds','cumulative_host_seconds',
                              'active_elapsed_seconds','wall_elapsed_seconds'}
                or b['outcome'] not in ('returned','interrupted')
                or any(type(v) not in (int,float) or not math.isfinite(v) or v < 0
                    for k,v in [*a.items(),*b.items()] if k not in ('binding','outcome'))):
            raise ValueError('semantic_clock_fields')
        bound = a['binding']
        cell_folder=Path(directory)/expected_cells[i-1]['key'].replace(':','-')
        expected = read(Path(directory)/bound['key'].replace(':','-')/'review-required.json')['binding']
        if (bound != read(cell_folder/'review-wait-start.json')
                or bound != dict(kind='semantic_review',**expected) or b['binding'] != bound
                or ((cell_folder/'cell-result.json').exists() and b['outcome'] != 'returned')
                or abs(a['active_elapsed_seconds']-b['active_elapsed_seconds']) > .01
                or abs(a['wall_elapsed_seconds']-a['active_elapsed_seconds']-previous_host) > .01
                or abs(b['host_elapsed_seconds']-b['cumulative_host_seconds']+previous_host) > .01
                or abs(b['wall_elapsed_seconds']-b['active_elapsed_seconds']-b['cumulative_host_seconds']) > .01
                or b['host_elapsed_seconds'] < 0 or b['active_elapsed_seconds'] < previous_active
                or a['remaining_host_seconds'] != plan['max_host_seconds']-previous_host):
            raise ValueError('semantic_clock_inconsistent')
        previous_host,previous_active = b['cumulative_host_seconds'],b['active_elapsed_seconds']
    summary = result['timing']
    if (set(summary) != {'mode','active_elapsed_seconds','host_elapsed_seconds','wall_elapsed_seconds',
                        'completed_host_waits','qualification_adopted','plan_sha256'}
            or summary['mode'] != policy['mode']
            or any(type(summary[k]) not in (int,float) or not math.isfinite(summary[k]) or summary[k] < 0
                for k in ('host_elapsed_seconds','active_elapsed_seconds','wall_elapsed_seconds'))
            or summary['host_elapsed_seconds'] != previous_host or summary['completed_host_waits'] != len(waits)
            or summary['plan_sha256'] != result['plan_sha256'] or summary['qualification_adopted'] is not False
            or summary['active_elapsed_seconds'] < previous_active
            or abs(summary['wall_elapsed_seconds']-summary['active_elapsed_seconds']-previous_host) > .01
            or previous_host > plan['max_host_seconds']+.01
            or summary['active_elapsed_seconds'] > plan['budget']['max_active_seconds']+.01):
        raise ValueError('semantic_clock_summary')


def replay(directory, *, event_source):
    """Reconstruct every sent cell and certified native event; never write a run."""
    directory = Path(directory)
    value, rows = plan_for(directory)
    plan,result = value['preparation_plan'],read(directory/'result.json')
    validate_inventory(directory,plan)
    check_authorization(read(directory/'authorization.json'),plan,value['execution_head'],value['ci_run'],
        now=datetime.fromisoformat(read(directory/'authorization.json')['issued_at']))
    preflight=read(directory/'execution-preflight.json')
    readability=preflight.get('input_readability',{})
    if (set(preflight) != {'verified','root_thread_id','independent_thread_id','independent_agent_path','input_readability'}
            or preflight['verified'] is not True or preflight['root_thread_id'] != plan['root_thread_id']
            or preflight['independent_thread_id'] != plan['review_principals']['independent']['principal_id']
            or set(readability) != {'thread_id','turn_id','dispatch_id','current_input_readable',
                'future_input_guaranteed','current_route_and_final_available','host_review_evidence_policy'}
            or readability['thread_id'] != preflight['independent_thread_id']
            or readability['host_review_evidence_policy'] != plan['host_review_evidence_policy']
            or readability['current_route_and_final_available'] is not True
            or readability['future_input_guaranteed'] is not False
            or type(readability['current_input_readable']) is not bool):
        raise ValueError('semantic_replay_preflight')
    completed=[]
    first=None
    missing=False
    for cell,material,request in rows:
        folder=directory/cell['key'].replace(':','-')
        if not folder.exists():
            missing=True
            continue
        if first is not None or missing:
            raise ValueError('semantic_sent_after_hard_stop')
        if (folder/'material.json').read_bytes() != preparation.options.canonical(material):
            raise ValueError('semantic_replay_material')
        started=read(folder/'started.json')
        if (set(started) != {'key','plan_sha256','active_elapsed_seconds','ordinal'}
                or started['key'] != cell['key'] or started['plan_sha256'] != value['plan_sha256']
                or started['ordinal'] != len(completed)+1
                or type(started['active_elapsed_seconds']) not in (int,float)
                or not math.isfinite(started['active_elapsed_seconds'])
                or not 0 <= started['active_elapsed_seconds'] <= result['timing']['active_elapsed_seconds']):
            raise ValueError('semantic_replay_start')
        transport_folder=folder/'transport'
        if transport_folder.exists():
            if (transport_folder/'issued-request.json').read_bytes() != identity.request_bytes(request):
                raise ValueError('semantic_replay_request')
            transport.validate_partial(transport_folder,request)
            if (transport_folder/'receipt.json').exists():
                response=RESPONSE.validate_json((transport_folder/'raw-response.json').read_bytes())
                if read(transport_folder/'receipt.json') != transport.validate_complete(transport_folder,request,response):
                    raise ValueError('semantic_replay_receipt')
        if (folder/'cell-result.json').exists():
            if (folder/'operator-abort.json').exists():
                raise ValueError('semantic_complete_after_abort')
            *_,wire,stage,bound,_ = reconstruct(directory,cell['key'])
            submission=read(folder/'review-submission.json')
            accepted=validate_submission(directory,cell['key'],submission,event_source)
            expected=outcome(cell,wire,bound,submission,accepted)
            if read(folder/'cell-result.json') != expected:
                raise ValueError('semantic_outcome_changed')
            completed.append(expected)
        else:
            first=cell['key']
            if (folder/'review-required.json').exists():
                *_,bound,_=reconstruct(directory,cell['key'])
                if (folder/'operator-abort.json').exists():
                    validate_abort(read(folder/'operator-abort.json'),bound)
                if (folder/'review-submission.json').exists():
                    validate_submission(directory,cell['key'],read(folder/'review-submission.json'),event_source)
    failure=read(directory/'failure.json') if (directory/'failure.json').exists() else None
    if (len(completed)<len(rows)) != (failure is not None):
        raise ValueError('semantic_failure_inventory')
    if failure and (set(failure) != {'key','phase','code'}
            or failure['key'] not in plan['sequence']
            or failure['phase'] not in ('before_send','transport','protocol','host')
            or not re.fullmatch(r'[a-zA-Z0-9_]{1,160}',failure['code'])):
        raise ValueError('semantic_failure_fields')
    if failure:
        tail=directory/failure['key'].replace(':','-')
        sent=(tail/'transport/issued-request.json').exists()
        receipt=(tail/'transport/receipt.json').exists()
        review_required=(tail/'review-required.json').exists()
        host_wait=(tail/'review-wait-start.json').exists()
        if ((failure['phase']=='before_send' and (sent or receipt or review_required or host_wait))
                or (failure['phase']=='transport' and (review_required or host_wait))
                or (failure['phase']=='protocol' and (not receipt or review_required or host_wait))
                or (failure['phase']=='host' and not review_required)):
            raise ValueError('semantic_failure_phase_inventory')
    if failure and first is None:
        # A before-send gate may fail without creating the next cell directory.
        first=rows[len(completed)][0]['key']
    unexecuted=[c['key'] for c,_,_ in rows if not (directory/c['key'].replace(':','-')/'transport/issued-request.json').exists()]
    if (set(result) != {'version','plan_sha256','completed','scan_completed','first_deviation',
                       'unexecuted','accounting','timing','new_qualification'}
            or result['version'] != VERSION or result['plan_sha256'] != value['plan_sha256']
            or result['completed'] != completed or result['accounting'] != transport.usage(directory)
            or result['scan_completed'] != (len(completed) == len(rows) and failure is None)
            or result['first_deviation'] != failure or (failure and failure['key'] != first)
            or result['unexecuted'] != unexecuted or result['new_qualification'] != 0
            or result['accounting']['attempted_calls'] > 15
            or result['accounting']['known_tokens'] > plan['budget']['max_tokens']):
        raise ValueError('semantic_closed_result_changed')
    validate_clock(directory,result,plan)
    return dict(strict_replay=True,native_reviews=len(completed),result=result)


ROOT_NAMES={'plan.json','authorization.json','execution-preflight.json','result.json','failure.json','submission-close.lock'}
CELL_NAMES={'material.json','started.json','issued-request.json','response.json','stage.json','review-required.json',
    'independent-task.json','task-checkpoint.json','review-submission.json','operator-abort.json','cell-result.json',
    'review-wait-start.json','dispatch.txt'}
TRANSPORT_NAMES={'issued-request.json','raw-response.json','receipt.json'}
STREAM_NAMES={'reservation.json','result.json','progress.json','failure.json','progress.tmp','rejected-tool-output.json'}


def validate_inventory(directory,plan):
    allowed=set(ROOT_NAMES)
    for cell in plan['cells']:
        stem=cell['key'].replace(':','-')+'/'
        allowed.update(stem+name for name in CELL_NAMES)
        allowed.update(stem+'transport/'+name for name in TRANSPORT_NAMES)
        allowed.update(stem+'transport/stream-001/'+name for name in STREAM_NAMES)
    for path in Path(directory).rglob('*'):
        if not path.is_file():
            continue
        relative=path.relative_to(directory).as_posix()
        if (relative not in allowed and relative != 'development-host-clock/policy.json'
                and not re.fullmatch(r'development-host-clock/[0-9]{4}-(waiting|finished)\.json',relative)):
            raise ValueError('semantic_unexpected_run_file')


def seal(directory, output, *, event_source):
    directory=Path(directory)
    before={p.relative_to(directory).as_posix():preparation.sha(p.read_bytes())
        for p in directory.rglob('*') if p.is_file()}
    checked=replay(directory,event_source=event_source)
    public={}
    for relative in before:
        path=directory/relative
        if path.suffix == '.json' and path.name not in ('raw-response.json','rejected-tool-output.json'):
            public[relative]=read(path)
        elif path.name == 'raw-response.json':
            public[relative]=public_response(read(path))
        elif path.name not in ('dispatch.txt','submission-close.lock','progress.tmp','rejected-tool-output.json'):
            raise ValueError('semantic_unexpected_seal_file')
    after={p.relative_to(directory).as_posix():preparation.sha(p.read_bytes())
        for p in directory.rglob('*') if p.is_file()}
    if before != after:
        raise ValueError('semantic_seal_mutation')
    sealed=dict(version='document-semantic-comparison-seal-v1',**checked,
        original_file_sha256=before,public_json_contents=public,new_qualification=0)
    write_new_json(Path(output),sealed)
    return dict(sealed=True,native_reviews=checked['native_reviews'],original_files=len(before),
        public_files=len(public),seal_sha256=preparation.sha(Path(output).read_bytes()))


def check_authorization(value, plan, head, ci_run, *, now=None):
    now=now or datetime.now(timezone.utc)
    if (set(value) != {'version','authorized','user_instruction','plan_sha256','budget','head','ci_run','issued_at','expires_at'}
            or value['version'] != AUTH_VERSION or value['authorized'] is not True
            or not value['user_instruction'].strip()
            or value['plan_sha256'] != preparation.sha(preparation.options.canonical(plan))
            or value['budget'] != plan['budget'] or value['head'] != head or value['ci_run'] != ci_run
            or datetime.fromisoformat(value['issued_at']).tzinfo is None
            or datetime.fromisoformat(value['expires_at']).tzinfo is None
            or not 0 < (datetime.fromisoformat(value['expires_at'])-datetime.fromisoformat(value['issued_at'])).total_seconds() <= 86400
            or not datetime.fromisoformat(value['issued_at']) <= now < datetime.fromisoformat(value['expires_at'])):
        raise ValueError('semantic_authorization_invalid_or_expired')


def run(args):
    preparation.verify_package(args.package)
    value=read(args.package/'plan.json')
    plan=value['preparation_plan']
    _,rows=preparation.prepare(root_thread_id=plan['root_thread_id'],
        independent_thread_id=plan['review_principals']['independent']['principal_id'])
    directory=ROOT/'data/runs/model_comparison'/plan['run_id']
    if directory.exists():
        raise ValueError('semantic_run_already_exists')
    head=verify_public_ci(args.ci_run)
    authorization=read(args.authorization)
    check_authorization(authorization,plan,head,args.ci_run)
    require_unchanged_checkout(head)
    with CodexReadOnlyClient(args.codex_executable) as client:
        preflight=verify_native_principals(client,plan)
        event_source=CodexHostReviewEventSource(client,plan)
        require_execution_event_source(plan,event_source)
        directory.mkdir(parents=True,exist_ok=False)
        write_new_json(directory/'plan.json',dict(preparation_plan=plan,plan_sha256=value['plan_sha256'],
            execution_head=head,ci_run=args.ci_run))
        write_new_json(directory/'authorization.json',authorization)
        write_new_json(directory/'execution-preflight.json',preflight)
        # All deterministic gates precede the existing credential loader.
        _,settings=load_role_settings(args.env_file)
        provider=transport.SemanticProvider(settings)
        def before_send():
            require_unchanged_checkout(head)
            check_authorization(authorization,plan,head,args.ci_run)
            verify_native_principals(client,plan)
        with route_environment('direct'):
            return observe(directory,plan,rows,provider,event_source,before_send=before_send)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run','material','submit','abort','replay','seal'))
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--key')
    parser.add_argument('--package',type=Path)
    parser.add_argument('--authorization',type=Path)
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--codex-executable',type=Path)
    parser.add_argument('--notes',type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--reason',choices=('reviewer_unavailable','routing_failure','operator_stop'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    required={'run':('package','authorization','ci_run','env_file','codex_executable'),
        'material':('directory','key'),'abort':('directory','key','reason'),
        'submit':('directory','key','notes','event_id','checkpoint','checkpoint_sha','codex_executable'),
        'replay':('directory','codex_executable'),'seal':('directory','output','codex_executable')}[args.action]
    if any(not getattr(args,name) for name in required):
        parser.error('missing required arguments: '+','.join(required))
    if args.action == 'run':
        result=run(args)
    elif args.action == 'material':
        value,cell,material,_,_,_,stage,bound,folder=reconstruct(args.directory,args.key)
        result=dict(binding=bound,stage=stage,material=material,task=json.loads(task_for(args.directory,args.key)),
            checkpoint_path=str(folder/'task-checkpoint.json'),
            checkpoint_sha256=checkpoint.digest((folder/'task-checkpoint.json').read_bytes()))
    elif args.action == 'abort':
        result=abort(args.directory,args.key,args.reason)
    else:
        value,_=plan_for(args.directory)
        with CodexReadOnlyClient(args.codex_executable) as client:
            source=CodexHostReviewEventSource(client,value['preparation_plan'])
            if args.action == 'submit':
                result=submit(args.directory,args.key,read(args.notes),args.event_id,source,args.checkpoint,args.checkpoint_sha)
            elif args.action == 'replay':
                result=replay(args.directory,event_source=source)
            else:
                result=seal(args.directory,args.output,event_source=source)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if args.action == 'run' and not result['scan_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
