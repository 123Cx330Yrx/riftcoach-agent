"""Candidate native handoff and read-only receipt replay; never grant admission."""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import uuid

from pydantic import ValidationError

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.role_qualification import read_role_calls
from app.harness.steps import RevisionRequest
from scripts import host_review_task_checkpoint as checkpoint
from scripts import run_full15_resumption_candidate as runner
from scripts.review_independence_contract import make_primary_attestation
from scripts.role_development_host_clock import TIMING_MODE, TIMING_SCHEMA
from scripts.run_scope_resolution_diagnostic import submission_close_gate


def read(path):
    return runner.strict_json(Path(path).read_text(encoding='utf-8'))


def load_plan(directory):
    saved = read(Path(directory) / 'plan.json')
    plan = saved['preparation_plan']
    expected = runner.prepare(root_thread_id=plan['root_thread_id'],
        independent_thread_id=plan['review_principals']['independent']['principal_id'])
    if plan != expected or saved['plan_sha256'] != runner.canonical_sha(plan):
        raise ValueError('full15_replay_plan_changed')
    return plan


def ensure_open(directory, folder):
    if ((Path(directory) / 'result.json').exists() or (folder.parent / 'case-result.json').exists()
            or any((folder / name).exists() for name in
                ('host-reviews.json', 'review-submission.json', 'operator-abort.json'))):
        raise ValueError('full15_handoff_closed')


def role(request):
    _, model = runner.candidate.request_identity(request)
    return 'revision' if model == 'glm-5.3-flash' else 'review'


def calls_for(directory, key):
    arm = Path(directory) / key.replace(':', '-')
    calls = read_role_calls(Path(directory) / 'transport' / arm.name, request_role=role)
    issued = [s for s in runner.STAGES if (arm / s / 'issued-request.json').exists()]
    if issued != list(runner.STAGES[:len(issued)]) or len(calls) > len(issued):
        raise ValueError('full15_replay_call_inventory')
    if len(calls) < len(issued):
        if len(issued) != len(calls) + 1:
            raise ValueError('full15_replay_receiptless_inventory')
        raw = (arm / issued[-1] / 'issued-request.json').read_bytes()
        value = runner.strict_json(raw.decode())
        request = REQUEST.validate_json(raw, strict=True)
        request = replace(request, **{k: value[k] for k in ('temperature', 'timeout_s', 'top_p')})
        calls.append(dict(request=request, response=None, completed=False, usage=None,
            receipt_missing=True, binding=dict(request_sha256=runner._bytes_sha(raw))))
    for name, call in zip(issued, calls, strict=True):
        folder = arm / name
        transport = runner.CAPACITY_TRANSPORT_ID if name == 'revision' else runner.REVIEW_MODEL_TRANSPORT_ID
        raw = runner.validate_request(call['request'], transport_id=transport)
        if (role(call['request']) != ('revision' if name == 'revision' else 'review')
                or raw != (folder / 'issued-request.json').read_bytes()
                or runner._bytes_sha(raw) != call['binding']['request_sha256']):
            raise ValueError('full15_replay_issued_changed')
        response_path = folder / 'response.json'
        if response_path.exists() and (call['response'] is None or read(response_path)
                != runner.public_response(json.loads(runner.RESPONSE.dump_json(call['response'])))):
            raise ValueError('full15_replay_response_changed')
    return calls


class PendingTransport(ValueError):
    pass


def reconstruct(directory, key, calls):
    """Rebuild source, exact requests, assembled text and journals without IO."""
    arm = Path(directory) / key.replace(':', '-')
    cell, source, inputs, _ = next(v for v in runner.controls()[1] if v[0]['key'] == key)
    if read(arm / 'source.json') != dict(input_json=inputs.data_json, report=source.report):
        raise ValueError('full15_replay_source_changed')
    consumed, stages = [], []

    def send(prepared):
        if prepared.metadata.get('review_phase') == 'native_business_reassessment':
            raise ValueError('full15_reassessment_forbidden')
        if len(consumed) >= len(calls):
            raise ValueError('full15_replay_missing_call')
        call = calls[len(consumed)]
        issued = call['request']
        metadata = dict(issued.metadata)
        if (metadata.pop('coach_budget_contract', None) != 'coach-bounded-review-v2'
                or not 0 < issued.timeout_s <= prepared.timeout_s
                or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared):
            raise ValueError('full15_replay_request_changed')
        consumed.append(call)
        if not call['completed']:
            raise PendingTransport('full15_replay_pending_transport')
        return Exchange(issued, call['response'], call['binding']['request_sha256'])

    flow = runner.candidate.ContrastDocumentWorkflow(send)
    error = None
    try:
        if calls:
            first = flow.evaluate(source)
            stages.append(dict(stage='initial', report=source.report, journal=deepcopy(flow.last_journal)))
        if len(calls) >= 2:
            draft = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
                source.knowledge, source.report, first))
            stages.append(dict(stage='revision', report=draft.report, journal=deepcopy(flow.last_edit_journal)))
        if len(calls) >= 3:
            flow.evaluate(replace(source, report=draft.report))
            stages.append(dict(stage='final', report=draft.report, journal=deepcopy(flow.last_journal)))
    except (ValueError, TypeError) as exc:
        # Identity/source contradictions are evidence corruption, never a valid
        # original failure. Schema/anchor failures can be the actual last output.
        if str(exc).startswith('full15_replay_') and not isinstance(exc, PendingTransport):
            raise
        error = exc
    if len(consumed) != len(calls):
        raise ValueError('full15_replay_unused_call')
    return cell, stages, error


def bound_for(directory, key, value, call, plan):
    folder = Path(directory) / key.replace(':', '-') / value['stage']
    bound = dict(plan_sha256=runner.canonical_sha(plan), key=key, stage=value['stage'],
        request_sha256=call['binding']['request_sha256'],
        response_sha256=runner._sha(folder / 'response.json'), report_sha256=runner.digest(value['report']))
    required = dict(binding=bound, stage_sha256=runner.stage_identity(value), scope=plan['acceptance'])
    if read(folder / 'stage.json') != value or read(folder / 'review-required.json') != required:
        raise ValueError('full15_replay_stage_changed')
    return bound


def material(directory, key, stage, *, closed=False):
    directory = Path(directory)
    plan = load_plan(directory)
    if key not in plan['sequence'] or stage not in runner.STAGES:
        raise ValueError('full15_handoff_scope')
    folder = directory / key.replace(':', '-') / stage
    if not closed:
        ensure_open(directory, folder)
    calls = calls_for(directory, key)
    count = runner.STAGES.index(stage) + 1
    if len(calls) < count or not closed and len(calls) != count:
        raise ValueError('full15_handoff_call_inventory')
    _, stages, error = reconstruct(directory, key, calls[:count])
    if error is not None or len(stages) != count:
        raise ValueError('full15_handoff_incomplete_stage')
    for value, call in zip(stages, calls[:count], strict=True):
        bound = bound_for(directory, key, value, call, plan)
    return plan, stages[-1], bound


def task(directory, key, stage, *, closed=False):
    plan, value, bound = material(directory, key, stage, closed=closed)
    arm = Path(directory) / key.replace(':', '-')
    return runner._task(plan, arm, stage, value, bound,
        (arm / stage / 'issued-request.json').read_bytes(),
        initial_raw=(arm / 'initial' / 'issued-request.json').read_bytes() if stage == 'revision' else None)


def validate_checkpoint(folder, submission, expected_task, plan, bound):
    folder = Path(folder)
    pinned_raw = (folder / 'task-checkpoint.json').read_bytes()
    task_raw = (folder / 'independent-task.json').read_bytes()
    pinned = runner.strict_json(pinned_raw.decode())
    expected = dict(checkpoint_sha256=checkpoint.digest(pinned_raw),
        task_sha256=checkpoint.digest(task_raw), reviewer_id=plan['review_principals']['independent']['principal_id'],
        purpose='review')
    if (submission.get('checkpoint_evidence') != expected
            or set(pinned) != {'version', 'purpose', 'reviewer_id', 'task_path', 'task_sha256', 'binding'}
            or pinned['version'] != checkpoint.VERSION or pinned['purpose'] != 'review'
            or pinned['reviewer_id'] != expected['reviewer_id'] or pinned['binding'] != bound
            or pinned['task_sha256'] != expected['task_sha256']
            or pinned['task_path'] != str((folder / 'independent-task.json').resolve())
            or runner.strict_json(task_raw.decode()) != expected_task):
        raise ValueError('full15_checkpoint_changed')


def submit(directory, key, stage, notes, event_id, event_source, checkpoint_sha):
    plan, value, bound = material(directory, key, stage)
    folder = Path(directory) / key.replace(':', '-') / stage
    checkpoint_path = folder / 'task-checkpoint.json'
    checkpoint.read(checkpoint_path, checkpoint_sha)
    if set(notes) != {'stage_assessment', 'report_assessment'}:
        raise ValueError('full15_primary_notes_fields')
    # Preserve the exact opinion including hashes/reviewer; reject, never fix it.
    primary = dict(binding=bound, **deepcopy(notes))
    primary['primary_attestation'] = make_primary_attestation(primary, plan=plan, bound=bound)
    event = event_source.fetch(event_id=event_id, binding=bound)
    checkpoint.check_answer(checkpoint_path, checkpoint_sha,
        json.dumps(dict(binding=bound, review=event['review'])).encode())
    submission = dict(primary=primary, independent=dict(event['review'], independent_source_event=event),
        checkpoint_evidence=dict(checkpoint_sha256=checkpoint_sha,
            task_sha256=runner._sha(folder / 'independent-task.json'),
            reviewer_id=plan['review_principals']['independent']['principal_id'], purpose='review'))
    validate_checkpoint(folder, submission, json.loads(task(directory, key, stage)), plan, bound)
    runner._validate_reviews(submission, value, bound, plan, event_source, initial=stage == 'initial')
    temp = folder / ('.submission-' + uuid.uuid4().hex + '.tmp')
    with submission_close_gate(directory):
        ensure_open(directory, folder)
        checkpoint.read(checkpoint_path, checkpoint_sha)
        try:
            runner._write_json(temp, submission)
            os.link(temp, folder / 'review-submission.json')
        finally:
            temp.unlink(missing_ok=True)
    return dict(submitted=True, key=key, stage=stage)


def abort(directory, key, stage, reason):
    plan = load_plan(directory)
    if key not in plan['sequence'] or stage not in runner.STAGES:
        raise ValueError('full15_abort_scope')
    folder = Path(directory) / key.replace(':', '-') / stage
    bound = read(folder / 'review-required.json')['binding']
    marker = dict(kind='full15-operator-abort-v1', binding=bound, reason=reason)
    runner.validate_abort(marker, bound)
    with submission_close_gate(directory):
        ensure_open(directory, folder)
        runner._write_json(folder / 'operator-abort.json', marker)
    return dict(stopped=True, key=key, stage=stage)


def replay(directory, *, event_source):
    directory = Path(directory)
    plan = load_plan(directory)
    runner.require_execution_event_source(plan, event_source)
    result = read(directory / 'result.json')
    fields = {'experiment', 'cases', 'scan_completed', 'diagnostic_accepted', 'provider_calls',
        'known_tokens', 'unknown_reserved_tokens', 'budget_known_tokens', 'budget_unknown_reserved_tokens',
        'new_qualification', 'original15_qualified', 'product_admitted', 'timing',
        'unexecuted_keys', 'unfinished_keys'}
    if (not fields <= result.keys() or result.keys() - fields -
            {'error_type', 'error_code', 'validation_errors', 'accounting_error_type'}
            or result.get('accounting_error_type')):
        raise ValueError('full15_replay_result_fields')
    if (any(type(result[k]) is not int or result[k] < 0 for k in
            ('provider_calls', 'known_tokens', 'unknown_reserved_tokens', 'budget_known_tokens',
                'budget_unknown_reserved_tokens', 'new_qualification'))
            or any(type(result[k]) is not bool for k in ('scan_completed', 'diagnostic_accepted'))):
        raise ValueError('full15_replay_accounting_types')
    timing = result['timing']
    policy = read(directory / 'development-host-clock/policy.json')
    if (policy['schema_version'] != TIMING_SCHEMA or policy['mode'] != TIMING_MODE or timing['mode'] != TIMING_MODE
            or policy['max_host_seconds'] != plan['max_host_seconds'] or policy['process_restart_allowed'] is not False
            or policy['qualification_adopted'] is not False or policy['plan_sha256'] is not None):
        raise ValueError('full15_replay_clock_policy')
    elapsed = [timing[k] for k in ('active_elapsed_seconds', 'host_elapsed_seconds', 'wall_elapsed_seconds')]
    if (any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in elapsed)
            or abs(elapsed[0] + elapsed[1] - elapsed[2]) > 0.05
            or not result.get('error_type') and (elapsed[0] >= plan['budget']['max_active_seconds']
                or elapsed[1] > plan['max_host_seconds'])):
        raise ValueError('full15_replay_clock_totals')
    waiting = sorted((directory / 'development-host-clock').glob('*-waiting.json'))
    finished = sorted((directory / 'development-host-clock').glob('*-finished.json'))
    if (type(timing['completed_host_waits']) is not int or len(waiting) != len(finished)
            or len(finished) != timing['completed_host_waits']):
        raise ValueError('full15_replay_clock_inventory')
    expected_waits = [directory / case['key'].replace(':', '-') / name / 'review-required.json'
        for case in result['cases'] for name in runner.STAGES
        if (directory / case['key'].replace(':', '-') / name / 'review-required.json').exists()]
    certified_count = sum(len(case['stages']) for case in result['cases'])
    if (not certified_count <= len(waiting) <= len(expected_waits)
            or len(expected_waits) - len(waiting) > 1
            or len(waiting) != len(expected_waits) and not result.get('error_type')):
        raise ValueError('full15_replay_clock_stage_inventory')
    host_elapsed, prior_active, prior_wall = 0, 0, 0
    for ordinal, (start, end) in enumerate(zip(waiting, finished, strict=True), 1):
        first, last = read(start), read(end)
        binding = dict(kind='stage', key=expected_waits[ordinal - 1].parent.name,
            stage='review-required', response_sha256=runner._sha(expected_waits[ordinal - 1]),
            remaining_active_seconds=first['binding']['remaining_active_seconds'])
        values = [first[k] for k in ('active_elapsed_seconds', 'wall_elapsed_seconds', 'remaining_host_seconds')]
        values += [last[k] for k in ('active_elapsed_seconds', 'wall_elapsed_seconds',
            'host_elapsed_seconds', 'cumulative_host_seconds')]
        values.append(binding['remaining_active_seconds'])
        if (start.name != f'{ordinal:04d}-waiting.json' or end.name != f'{ordinal:04d}-finished.json'
                or first['binding'] != binding or last['binding'] != binding
                or any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in values)
                or first['active_elapsed_seconds'] < prior_active
                or first['wall_elapsed_seconds'] < prior_wall
                or last['active_elapsed_seconds'] < first['active_elapsed_seconds']
                or binding['remaining_active_seconds'] <= 0
                or ordinal <= certified_count and last['outcome'] != 'returned'
                or last['outcome'] not in ('returned', 'interrupted')
                or abs(first['remaining_host_seconds'] + host_elapsed - plan['max_host_seconds']) > 0.05
                or abs(first['active_elapsed_seconds'] + binding['remaining_active_seconds']
                    - plan['budget']['max_active_seconds']) > 0.05
                or abs(first['wall_elapsed_seconds'] - first['active_elapsed_seconds'] - host_elapsed) > 0.05):
            raise ValueError('full15_replay_clock_binding')
        host_elapsed += last['host_elapsed_seconds']
        prior_active = last['active_elapsed_seconds']
        prior_wall = last['wall_elapsed_seconds']
        if (abs(host_elapsed - last['cumulative_host_seconds']) > 0.05
                or abs(last['wall_elapsed_seconds'] - last['active_elapsed_seconds'] - host_elapsed) > 0.05):
            raise ValueError('full15_replay_clock_cumulative')
    if (abs(host_elapsed - elapsed[1]) > 0.05 or elapsed[0] + 0.05 < prior_active
            or elapsed[2] + 0.05 < prior_wall):
        raise ValueError('full15_replay_clock_totals')
    keys = [c['key'] for c in result['cases']]
    if (result['experiment'] != runner.RUN_ID or keys != plan['sequence'][:len(keys)]
            or result['unexecuted_keys'] != plan['sequence'][len(keys):]):
        raise ValueError('full15_replay_case_inventory')
    expected_arms = {k.replace(':', '-') for k in keys}
    actual_arms = {p.name for p in directory.iterdir() if p.is_dir()
        and p.name not in ('transport', 'development-host-clock')}
    transport_arms = {p.name for p in (directory / 'transport').iterdir() if p.is_dir()} if (directory / 'transport').exists() else set()
    if actual_arms != expected_arms or not transport_arms <= expected_arms:
        raise ValueError('full15_replay_orphan_case')
    calls, stages, paths, unfinished = [], [], ['plan.json', 'result.json'], []
    for index, case in enumerate(result['cases']):
        key = case['key']
        arm = directory / key.replace(':', '-')
        actual = calls_for(directory, key)
        cell, rebuilt, error = reconstruct(directory, key, actual)
        certified = case['stages']
        if (len(certified) > len(rebuilt) or len(actual) > len(certified) + 1
                or [s['stage'] for s in certified] != list(runner.STAGES[:len(certified)])):
            raise ValueError('full15_replay_stage_inventory')
        expected_case = dict(key=key, stages=[], semantic_accepted=False)
        terminal = None
        for ordinal, value in enumerate(rebuilt):
            name, folder = value['stage'], arm / value['stage']
            bound = bound_for(directory, key, value, actual[ordinal], plan)
            paths += [f'{arm.name}/{name}/{f}' for f in
                ('issued-request.json', 'response.json', 'stage.json', 'review-required.json')]
            if ordinal >= len(certified):
                continue
            if terminal is not None:
                raise ValueError('full15_replay_rejected_case_continued')
            submission = read(folder / 'host-reviews.json')
            if submission != read(folder / 'review-submission.json'):
                raise ValueError('full15_replay_submission_changed')
            accepted = runner._validate_reviews(submission, value, bound, plan, event_source, initial=name == 'initial')
            validate_checkpoint(folder, submission, json.loads(task(directory, key, name, closed=True)), plan, bound)
            record = dict(stage=name, binding=bound, host_accepted=accepted)
            if certified[ordinal] != record:
                raise ValueError('full15_replay_opinion_changed')
            expected_case['stages'].append(record)
            stages.append(dict(key=key, **record))
            paths += [f'{arm.name}/{name}/{f}' for f in
                ('host-reviews.json', 'review-submission.json', 'task-checkpoint.json', 'independent-task.json')]
            if name == 'initial':
                wire = value['journal']['parsed_review']
                expected_case.update(initial_verdict=wire['verdict'], initial_score=wire['score'])
                if not accepted:
                    terminal = 'initial_host_rejected'
                elif not runner.initial_verdict_valid(cell, wire['verdict'], wire['score']):
                    terminal = 'initial_unexpected_verdict'
                elif wire['verdict'] == 'pass':
                    terminal = 'accepted'
            elif name == 'revision' and not accepted:
                terminal = 'revision_host_rejected'
            elif name == 'final':
                wire = value['journal']['parsed_review']
                expected_case.update(final_verdict=wire['verdict'], final_score=wire['score'])
                terminal = ('fresh_host_rejected' if not accepted else
                    'fresh_not_pass' if wire['verdict'] != 'pass' or wire['score'] < 85 else 'accepted')
        if terminal is not None:
            expected_case['semantic_accepted'] = terminal == 'accepted'
            if terminal != 'accepted':
                expected_case['semantic_failure'] = terminal
            if len(actual) != len(certified) or error is not None:
                raise ValueError('full15_replay_terminal_continued')
        closed = (arm / 'case-result.json').exists()
        if closed:
            if terminal is None or read(arm / 'case-result.json') != expected_case:
                raise ValueError('full15_replay_terminal_changed')
            paths.append(f'{arm.name}/case-result.json')
        else:
            if index != len(keys) - 1 or not result.get('error_type') or terminal is not None:
                raise ValueError('full15_replay_unfinished_position')
            unfinished.append(key)
            if error is not None and not isinstance(error, PendingTransport):
                code = 'full15_schema_validation' if isinstance(error, ValidationError) else str(error)
                if result.get('error_code') != code:
                    raise ValueError('full15_replay_failure_changed')
        if case != expected_case:
            raise ValueError('full15_replay_case_changed')
        calls.extend(actual)
        paths.append(f'{arm.name}/source.json')
        for name in runner.STAGES:
            folder = arm / name
            marker = folder / 'operator-abort.json'
            if marker.exists():
                runner.validate_abort(read(marker), read(folder / 'review-required.json')['binding'])
                if (closed or index != len(keys) - 1 or result.get('error_code') != 'full15_operator_abort'
                        or name in [s['stage'] for s in certified]):
                    raise ValueError('full15_replay_abort_changed')
                paths.append(f'{arm.name}/{name}/operator-abort.json')
            for filename in ('issued-request.json', 'response.json', 'stage.json', 'review-required.json'):
                if (folder / filename).exists():
                    paths.append(f'{arm.name}/{name}/{filename}')
    known = sum(sum(c['usage'].values()) for c in calls if c['usage'] is not None)
    reserved = sum(runner.qualification.size(c['request']) + c['request'].max_tokens for c in calls if c['usage'] is None)
    budget_known = sum(c['response'].usage.input_tokens + c['response'].usage.output_tokens
        for c in calls if c['response'] is not None)
    budget_reserved = sum(runner.qualification.size(c['request']) + c['request'].max_tokens
        for c in calls if c['response'] is None)
    complete = len(keys) == 15 and not unfinished and not result.get('error_type')
    if (result['provider_calls'] != len(calls) or result['known_tokens'] != known
            or result['budget_known_tokens'] != budget_known
            or result['budget_unknown_reserved_tokens'] != budget_reserved
            or result['unknown_reserved_tokens'] != reserved or result['unfinished_keys'] != unfinished
            or result['scan_completed'] != complete
            or result['diagnostic_accepted'] != (complete and all(c['semantic_accepted'] for c in result['cases']))
            or result['new_qualification'] != 0 or result['original15_qualified'] is not False
            or result['product_admitted'] is not False or len(calls) > plan['budget']['max_calls']
            or known + reserved > plan['budget']['max_tokens']):
        raise ValueError('full15_replay_accounting_changed')
    cost = Decimal(0)
    for call in calls:
        if call['usage'] is not None:
            price = runner.DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles[runner.candidate.request_identity(call['request'])]
            cost += (Decimal(call['usage']['input_tokens']) * price.input_cost_per_million
                + Decimal(call['usage']['output_tokens']) * price.output_cost_per_million) / 1_000_000
    public = {p: read(directory / p) for p in dict.fromkeys(paths)}
    def inspect(value):
        if isinstance(value, dict):
            if {'api_key', 'authorization', 'access_token'} & value.keys() or value.get('reasoning_content') is not None:
                raise ValueError('full15_replay_private_field')
            for child in value.values(): inspect(child)
        elif isinstance(value, list):
            for child in value: inspect(child)
    inspect(public)
    return dict(kind='full15-resumption-candidate-result-v1', execution_result=result, stages=stages,
        accounting=dict(calls=len(calls), known_tokens=known, unknown_usage_calls=sum(c['usage'] is None for c in calls),
            local_attempts_without_transport_receipt=sum(c.get('receipt_missing', False) for c in calls),
            known_usage_estimated_uncached_cny=str(cost), unknown_usage_is_not_free=True),
        public_json_contents=public, original_file_sha256={p.relative_to(directory).as_posix(): runner._sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()},
        new_qualification=0, original15_qualified=False, production_admitted=False)


def seal(directory, output, *, event_source):
    output = Path(output).resolve()
    if output.is_relative_to(Path(directory).resolve()):
        raise ValueError('full15_seal_output_inside_run')
    value = replay(directory, event_source=event_source)
    runner._write_json(output, value)
    return dict(sealed=True, path=str(output), sha256=runner._sha(output), provider_calls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('task', 'submit', 'abort', 'replay', 'seal'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--key')
    parser.add_argument('--stage', choices=runner.STAGES)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--reason', choices=('reviewer_unavailable', 'routing_failure', 'operator_stop'))
    parser.add_argument('--codex-executable', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action in ('task', 'submit', 'abort') and not all((args.key, args.stage)):
        parser.error('key and stage required')
    if args.action == 'task':
        print(task(args.directory, args.key, args.stage)); return
    if args.action == 'abort':
        if not args.reason: parser.error('reason required')
        print(runner.compact(abort(args.directory, args.key, args.stage, args.reason))); return
    if not args.codex_executable: parser.error('codex-executable required for native reads')
    plan = load_plan(args.directory)
    with runner.CodexReadOnlyClient(args.codex_executable) as client:
        source = runner.CodexHostReviewEventSource(client, plan)
        if args.action == 'submit':
            if not all((args.notes, args.event_id, args.checkpoint_sha)): parser.error('notes, event-id and checkpoint-sha required')
            value = submit(args.directory, args.key, args.stage, read(args.notes), args.event_id, source, args.checkpoint_sha)
        elif args.action == 'seal':
            if not args.output: parser.error('output required')
            value = seal(args.directory, args.output, event_source=source)
        else:
            value = replay(args.directory, event_source=source)
    print(runner.compact(value))


if __name__ == '__main__': main()
