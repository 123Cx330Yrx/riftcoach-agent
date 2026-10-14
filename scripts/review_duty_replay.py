"""Read-only reconstruction of a closed development chain; no restart or send.

The closure digest is an operator-supplied trust root, not read from the run.
Only the optional external, create-only seal is written. Native events are
refetched; the recorded accepted flags never replace that check.
"""
import argparse
import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from scripts import review_duty_execution as execution
from scripts.review_duty_host_gate import sha


def read(path):
    return json.loads(Path(path).read_bytes())


def issued_request(folder, prepared):
    raw = (folder/'issued-request.json').read_bytes()
    parsed = REQUEST.validate_json(raw)
    execution.check_issued(prepared,parsed)
    value = json.loads(raw)
    issued = replace(prepared,timeout_s=value['timeout_s'],metadata=value['metadata'])
    if execution.request_bytes(issued) != raw:
        raise ValueError('duty_replay_issued_bytes')
    return issued


class IncompleteTail(Exception):
    pass


class Reader(execution.DevelopmentChain):
    def _call(self, slot, prepared):
        index = len(self.consumed_attempts)
        if index >= len(self.attempts):
            raise IncompleteTail()
        attempt = self.attempts[index]
        folder = self.directory/slot
        if attempt['slot'] != slot or Path(attempt['folder']) != folder:
            raise ValueError('duty_replay_call_order')
        if (folder/'prepared-request.json').read_bytes() != execution.request_bytes(prepared):
            raise ValueError('duty_replay_prepared_request')
        self.consumed_attempts.append(slot)
        if not attempt['complete']:
            raise IncompleteTail()
        issued = issued_request(folder,prepared)
        receipt = read(folder/'receipt.json')
        pin = sha(folder/'issued-request.json')
        if receipt != dict(issued_request_sha256=pin, receipt_request_sha256=pin,
                           response_sha256=sha(folder/'response.json')):
            raise ValueError('duty_replay_receipt')
        response = RESPONSE.validate_json((folder/'response.json').read_bytes())
        return Exchange(issued,response,pin)

    def _host(self, key, kind, stage, material, request_sha, response_sha, report):
        folder = self.directory/('host-'+key)
        if folder.exists() and read(folder/'material.json') != material:
            raise ValueError('duty_replay_material')
        if not (folder/'submission.json').exists():
            raise IncompleteTail()
        index = len(self.consumed_handles)
        if index >= len(self.handles):
            raise ValueError('duty_replay_host_inventory')
        handle = self.handles[index]
        bound = dict(plan_sha256=self.pin,key=key,stage=stage,request_sha256=request_sha,
            response_sha256=response_sha,report_sha256=execution.digest(report))
        if (handle['folder'] != str(folder) or handle['binding'] != bound or handle['kind'] != kind):
            raise ValueError('duty_replay_host_order_binding')
        self.consumed_handles.append(key)
        return self.gate.replay(handle)


def check_ledger(session, result):
    totals = dict(calls=0,known_tokens=0,unknown_reserved_tokens=0)
    last_active = 0
    for attempt in session.attempts:
        folder = Path(attempt['folder'])
        state = read(folder/'call-state.json')
        start, end = state['active_started'], state['active_finished']
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end))
                or not last_active <= start <= end or state['before'] != totals):
            raise ValueError('duty_replay_call_clock')
        last_active = end
        count = state['after']['calls']-totals['calls']
        if count not in (0,1):
            raise ValueError('duty_replay_call_count')
        issued_path = folder/'issued-request.json'
        if count:
            issued = REQUEST.validate_json(issued_path.read_bytes())
            prepared = REQUEST.validate_json((folder/'prepared-request.json').read_bytes())
            execution.check_issued(prepared,issued)
            ceiling = estimate_runtime_request_input_ceiling(issued)
            reservation = ceiling + issued.max_tokens
            if (totals['calls'] >= execution.LIMITS['max_calls'] or ceiling > 64000
                    or totals['known_tokens']+totals['unknown_reserved_tokens']+reservation > execution.LIMITS['total_tokens']
                    or issued.timeout_s > min(prepared.timeout_s,2700-start)+.001):
                raise ValueError('duty_replay_call_budget')
            totals['calls'] += 1
            totals['unknown_reserved_tokens'] += reservation
            if (folder/'response.json').exists():
                response = RESPONSE.validate_json((folder/'response.json').read_bytes())
                if (response.provider,response.model) == ('zhipu',execution.model_for(issued)):
                    totals['known_tokens'] += response.usage.input_tokens+response.usage.output_tokens
                    totals['unknown_reserved_tokens'] -= reservation
                    if attempt['complete'] and (response.usage.input_tokens > ceiling
                            or response.usage.output_tokens > issued.max_tokens or end >= 2700):
                        raise ValueError('duty_replay_completed_budget')
        elif issued_path.exists() or attempt['complete']:
            raise ValueError('duty_replay_unsent_call')
        if state['after'] != totals:
            raise ValueError('duty_replay_ledger_settlement')
    if any(result[key] != value for key,value in totals.items()):
        raise ValueError('duty_replay_ledger_totals')
    return last_active


def check_clock(session, result, last_call):
    folder = session.directory/'development-host-clock'
    policy = read(folder/'policy.json')
    if (policy['plan_sha256'] != session.pin or policy['max_host_seconds'] != 86400
            or policy['qualification_adopted'] is not False or policy['process_restart_allowed'] is not False):
        raise ValueError('duty_replay_clock_policy')
    starts, ends = sorted(folder.glob('*-waiting.json')), sorted(folder.glob('*-finished.json'))
    if len(starts) != len(ends):
        raise ValueError('duty_replay_clock_unfinished')
    previous_host = previous_active = 0
    for i,(a,b) in enumerate(zip(starts,ends,strict=True),1):
        start,end = read(a),read(b)
        if a.name != f'{i:04d}-waiting.json' or b.name != f'{i:04d}-finished.json':
            raise ValueError('duty_replay_clock_order')
        key = start['binding']['key']
        if (end['binding'] != start['binding'] or start['binding']['plan_sha256'] != session.pin
                or not (session.directory/('host-'+key)/'material.json').is_file()):
            raise ValueError('duty_replay_clock_binding')
        values = (start['active_elapsed_seconds'],start['wall_elapsed_seconds'],start['remaining_host_seconds'],
            end['host_elapsed_seconds'],end['cumulative_host_seconds'],end['active_elapsed_seconds'],end['wall_elapsed_seconds'])
        if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('duty_replay_clock_values')
        active,host = end['active_elapsed_seconds'],end['cumulative_host_seconds']
        if (active < previous_active or abs(start['active_elapsed_seconds']-active) > .01
                or abs(start['wall_elapsed_seconds']-active-previous_host) > .01
                or abs(end['host_elapsed_seconds']-host+previous_host) > .01
                or abs(end['wall_elapsed_seconds']-active-host) > .01
                or abs(start['remaining_host_seconds']-86400+previous_host) > .01):
            raise ValueError('duty_replay_clock_accounting')
        if end['outcome'] != 'returned' and (result['outcome'] != 'hard_failure' or i != len(starts)):
            raise ValueError('duty_replay_clock_interrupted')
        previous_host,previous_active = host,active
    timing = result['timing']
    active,host,wall = (timing[k] for k in ('active_elapsed_seconds','host_elapsed_seconds','wall_elapsed_seconds'))
    if (any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in (active,host,wall))
            or abs(host-previous_host)>.01 or abs(wall-active-host)>.01
            or active < max(previous_active,last_call) or timing['completed_host_waits'] != len(starts)
            or timing['plan_sha256'] != session.pin or timing['qualification_adopted'] is not False
            or result['outcome'] != 'hard_failure' and (active >= 2700 or host >= 86400)):
        raise ValueError('duty_replay_clock_summary')


def replay(directory, *, closure_sha256, inputs, event_source, observe):
    directory = Path(directory).absolute()
    closure_path = directory/'closure.json'
    if sha(closure_path) != closure_sha256:
        raise ValueError('duty_replay_closure_digest')
    closure, plan, result = read(closure_path),read(directory/'plan.json'),read(directory/'result.json')
    if (closure['kind'] != 'review-duty-closure-v1' or closure['directory'] != str(directory)
            or result['production_admitted'] is not False or result['restart_allowed'] is not False):
        raise ValueError('duty_replay_closure_binding')
    def forbidden(*args,**kwargs):
        raise AssertionError('read_only_replay_cannot_execute')
    session = Reader(directory=directory,answers=closure['answers'],observations=closure['observations'],
        inputs=inputs,plan=plan,event_source=event_source,send=forbidden,observe=observe,
        judge=forbidden,before_send=forbidden)
    if session.pin != closure['plan_sha256'] or str(session.workspace.python) != closure['python']:
        raise ValueError('duty_replay_identity')
    session.inventory = {**closure['files'],str(closure_path):closure_sha256}
    session.attempts,session.handles = result['attempts'],result['host_handles']
    session.consumed_attempts,session.consumed_handles = [],[]
    session.check()
    last_call = check_ledger(session,result)
    check_clock(session,result,last_call)
    try:
        outcome = session._run_chain()
    except IncompleteTail:
        if result['outcome'] != 'hard_failure':
            raise ValueError('duty_replay_missing_stage') from None
        outcome = 'hard_failure'
    except (ValueError,TypeError) as error:
        # Only genuine recorded parsing/assembly failures may terminate the chain.
        # Replay's own binding/inventory failures are never accepted as that tail.
        if (result['outcome'] != 'hard_failure' or result['error_type'] != type(error).__name__
                or str(error).startswith('duty_replay_')):
            raise
        outcome = 'hard_failure'
    if (outcome != result['outcome'] or len(session.consumed_attempts) != len(session.attempts)
            or len(session.consumed_handles) != len(session.handles)):
        raise ValueError('duty_replay_early_stop')
    session.check()
    samples = [read(p) for p in session.observations.rglob('observation.json')]
    http = sum(p['http_requests'] for p in samples) if samples else None
    waits = sorted((session.directory/'development-host-clock').glob('*-finished.json'))
    stop_key = None
    if outcome not in ('development_chain_pass','initial_both_pass_no_edit'):
        stop_key = session.consumed_attempts[-1] if session.consumed_attempts else None
        if outcome == 'incompatible_opinions':
            stop_key = 'compatibility'
        elif outcome == 'hard_failure' and waits and read(waits[-1])['outcome'] == 'interrupted':
            stop_key = read(waits[-1])['binding']['key']
    return dict(kind='review-duty-readonly-replay-v1',closure_sha256=closure_sha256,
        plan_sha256=session.pin,outcome=outcome,calls=result['calls'],known_tokens=result['known_tokens'],
        unknown_reserved_tokens=result['unknown_reserved_tokens'],reviewed_stages=len(session.handles),
        http_requests=http, http_count_available=len(samples)==result['calls'],
        http_send_unknown_calls=max(0,result['calls']-len(samples)),
        complete_responses=sum((Path(a['folder'])/'response.json').exists() for a in session.attempts),
        receiptless_attempts=sum(not (Path(a['folder'])/'receipt.json').exists() for a in session.attempts),
        first_stop_key=stop_key,
        unissued_slots=[s for s in execution.SLOTS if not (session.directory/s/'issued-request.json').exists()],
        production_admitted=False,restart_allowed=False)


def seal(output, *, directory, closure_sha256, inputs, event_source, observe):
    output, directory = Path(output).absolute(), Path(directory).absolute()
    record = replay(directory,closure_sha256=closure_sha256,inputs=inputs,
        event_source=event_source,observe=observe)
    closure = read(directory/'closure.json')
    if output.resolve() != output or any(output.is_relative_to(Path(p)) for p in
            (directory,closure['answers'],closure['observations'],execution.ROOT/'data/runs')):
        raise ValueError('duty_replay_seal_outside_evidence')
    if sha(directory/'closure.json') != record['closure_sha256']:
        raise ValueError('duty_replay_closure_changed')
    actual = {str(p):sha(p) if p.is_file() else 'directory' for root in
        (directory,Path(closure['answers']),Path(closure['observations'])) for p in root.rglob('*')}
    if actual != {**closure['files'],str(directory/'closure.json'):closure_sha256}:
        raise ValueError('duty_replay_seal_evidence_changed')
    write_new_json(output,record)
    return record


def main():
    from scripts.prepare_review_duty_execution import load_inputs
    from scripts.review_duty_transport import verify
    from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--closure-sha',required=True)
    parser.add_argument('--codex-executable',type=Path,required=True)
    parser.add_argument('--seal',type=Path)
    args = parser.parse_args()
    with CodexReadOnlyClient(args.codex_executable) as client:
        params = dict(closure_sha256=args.closure_sha,inputs=load_inputs(),
            event_source=CodexHostReviewEventSource(client,read(args.run/'plan.json')),observe=verify)
        if args.seal:
            record = seal(args.seal,directory=args.run,**params)
        else:
            record = replay(args.run,**params)
    print(json.dumps(record,ensure_ascii=True))


if __name__ == '__main__':
    main()
