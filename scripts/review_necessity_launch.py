"""Three pinned development reviews, reusing the owned worker and native gate.

No automatic sends/retries, secret discovery, product admission or old-run writes.
Every command requires the last stdout checkpoint; crashes after a claim cannot
resend. A recovered timeout leaves earlier reviews intact and can be retried once
by an explicit command under a new, plan-bound human authorization.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version as installed_version
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

from app.evaluation.sol_natural_session import exclusive
from scripts import review_necessity_candidate as candidate
from scripts import reviewer_responses_nonstream as codec
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.review_independence_contract import MODE_V2, FINAL_POLICY, freeze_v2_identity
from scripts.reviewer_profile_batch import ExactNativeGate, inventory, sha
from scripts.reviewer_responses_process import read_json, write_json, run_once, valid_saved_usage
from scripts.reviewer_responses_transport import Profile, digest, TOOL
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_natural_duty_development import current_head, verify_ci
from scripts.sol_reasoning_single import hidden_key, CODEX

ROOT = candidate.PACKAGE.parents[3]
VERSION = 'review-necessity-launch-v1'
LIMITS = dict(logical_reviews=3, max_attempts=4, max_retries=1, input_per_request=64000,
              output_per_request=16384, reserved_per_request=80384,
              total_reserved_tokens=321536, timeout_s=300, automatic_retries=0)
PROFILE = Profile(group='GPT-pro', route='proxy-12000')
HISTORY_ROOT = Path('C:/Users/33502/Documents/Agent/outputs/riftcoach-sol-reasoning-single-20261022')
HISTORY_SEAL_SHA = 'da687ba3c9ff2a483c8bc5f2ed021e7c57e79fd8f038a9301474a82d2cce8153'
CALL_FILES = ('request.json', 'validation-context.json', 'profile.json', 'usage.json',
              'worker-result.json', 'receipt.json', 'observation/observation.json')
REVIEW_FILES = ('material.json', 'independent-task.json', 'task-checkpoint.json', 'dispatch.txt')


def require(value, code):
    if not value:
        raise ValueError('necessity_launch_' + code)


def source_identity():
    """Only tracked execution inputs; never open unrelated untracked files."""
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    selected = [n for n in names if n and (
        n.startswith(('app/', 'scripts/')) and n.endswith('.py') or
        n.startswith(('skills/', 'examples/runtime_profiles/')) or
        n in ('pyproject.toml', 'uv.lock', 'requirements.txt'))]
    files = {}
    for name in selected:
        path = ROOT/name
        require(path.resolve() == path and path.stat().st_nlink == 1, 'redirected_source')
        files[name] = sha(path)
    return dict(files=files, python_version=sys.version,
        packages={n: installed_version(n) for n in ('openai', 'httpx', 'pydantic', 'jsonschema')})


def historical_evidence():
    require(sha(HISTORY_ROOT/'seal.json') == HISTORY_SEAL_SHA, 'historical_seal')
    closed = read_json(HISTORY_ROOT/'seal.json')
    require(inventory(HISTORY_ROOT) == {**closed['inventory'], 'seal.json':HISTORY_SEAL_SHA}, 'historical_inventory')
    return dict(operator=str(HISTORY_ROOT), seal_sha256=HISTORY_SEAL_SHA,
        http_requests=7, known_tokens=111392, unknown_reserved_tokens=145824, retries=1)


def prepare(operator, *, primary, independent):
    """Create-only proposal. Does not authorize, query CI/native, or read a Key."""
    head = current_head()
    operator = Path(operator).absolute()
    require(operator.resolve() == operator and not operator.exists() and
            not (operator.is_relative_to(ROOT) or ROOT.is_relative_to(operator)), 'operator_path')
    files = candidate.prepare()
    plan = freeze_v2_identity(dict(version=VERSION, candidate=candidate.VERSION,
        operator=str(operator), head=head, source=source_identity(), limits=LIMITS,
        profile=asdict(PROFILE), history=historical_evidence(), package_inventory=inventory(candidate.PACKAGE),
        requests={n: hashlib.sha256(raw).hexdigest() for n, raw in files.items()},
        workspace=dict(cwd=str(ROOT), python=str(Path(sys.executable).resolve()),
            answers=str(operator.with_name(operator.name+'-authors'))),
        host_review_submission_mode=MODE_V2, host_review_evidence_policy=FINAL_POLICY,
        identity_conflict_policy='review_diagnostic_then_stop_no_retry',
        estimated_uncached_cny='0.233472', execution_authorized=False,
        qualified=False, publication_allowed=False), root_thread_id=primary,
        primary_id=primary, independent_id=independent)
    operator.mkdir(parents=True, exist_ok=False)
    (operator/'requests').mkdir()
    (operator/'checkpoints').mkdir()
    (operator/'attempts').mkdir()
    write_json(operator/'plan.json', plan)
    for name, raw in files.items():
        with (operator/'requests'/name).open('xb') as stream:
            stream.write(raw)
    state = dict(phase='ready', next_case='a', attempts=[], reason=None)
    return dict(save(operator, state, None, inventory(operator)), key_read=False, provider_requests=0)


def save(operator, state, previous, expected):
    require(inventory(operator) == expected, 'unexpected_inventory')
    path = operator/'checkpoints'/f'{len(list((operator/"checkpoints").iterdir()))+1:04}.json'
    write_json(path, dict(version=VERSION, previous_sha256=previous, state=state, inventory=expected))
    return dict(plan_sha256=sha(operator/'plan.json'), checkpoint=str(path),
        checkpoint_sha256=sha(path), status=status(state))


def status(state):
    known = unknown = not_sent = http_known = http_unknown = 0
    for row in state['attempts']:
        receipt = row.get('receipt', {})
        if receipt.get('usage_state') == 'known':
            known += receipt['usage']['total_tokens']
        elif receipt.get('usage_state') == 'not_sent':
            not_sent += 1
        else:
            unknown += LIMITS['reserved_per_request']
        count = receipt.get('http_requests')
        if type(count) is int:
            http_known += count
        else:
            http_unknown += 1
    return dict(phase=state['phase'], reason=state['reason'], next_case=state['next_case'],
        attempts=len(state['attempts']), known_tokens=known, unknown_reserved_tokens=unknown,
        not_sent=not_sent, http_requests_known=http_known, http_requests_unknown=http_unknown,
        unreviewed_calls=sum('handle' in row and not row.get('reviewed') for row in state['attempts']),
        qualified=False, publication_allowed=False)


def closed_status(state):
    return dict(status(state), phase='closed', stopped_at=state['phase'],
                pending_case=state['next_case'], next_case=None)


def load(operator, plan_sha, checkpoint_sha, *, sources=True, pending=False, sealed=False):
    operator = Path(operator).absolute()
    require(operator.resolve() == operator and sha(operator/'plan.json') == plan_sha, 'plan_root')
    plan = read_json(operator/'plan.json')
    require(plan['version'] == VERSION and plan['operator'] == str(operator) and
            plan['limits'] == LIMITS and plan['profile'] == asdict(PROFILE), 'plan_scope')
    previous = None
    expected = None
    state = None
    for i, path in enumerate(sorted((operator/'checkpoints').iterdir()), 1):
        require(path.name == f'{i:04}.json', 'checkpoint_order')
        row = read_json(path)
        require(row and row['version'] == VERSION and row['previous_sha256'] == previous, 'checkpoint_chain')
        if expected is not None:
            require(all(row['inventory'].get(k) == v for k, v in expected.items()), 'historical_evidence_changed')
        previous = sha(path)
        expected = {**row['inventory'], path.relative_to(operator).as_posix(): previous}
        state = row['state']
    actual = inventory(operator)
    if sealed:
        actual.pop('seal.json', None)
    if pending and state['phase'] == 'in_flight':
        prefix = Path(state['attempts'][-1]['folder']).relative_to(operator).as_posix()+'/call/'
        require(all(actual.get(k) == v for k, v in expected.items()) and
                set(actual)-set(expected) <= {prefix+n for n in CALL_FILES}, 'pending_inventory')
    else:
        require(actual == expected, 'checkpoint_or_inventory')
    require(previous == checkpoint_sha, 'stale_checkpoint')
    if sources:
        require(Path.cwd().resolve() == ROOT and plan['workspace']['cwd'] == str(ROOT) and
                plan['workspace']['python'] == str(Path(sys.executable).resolve()), 'actual_execution_paths')
        require(current_head() == plan['head'] and source_identity() == plan['source'] and
                inventory(candidate.PACKAGE) == plan['package_inventory'] and
                historical_evidence() == plan['history'], 'frozen_inputs')
        require(plan['requests'] == {n: hashlib.sha256(raw).hexdigest()
                                    for n, raw in candidate.prepare().items()}, 'request_reconstruction')
    return plan, deepcopy(state), expected


def authorization(path, pin, plan_sha, *, now=None):
    require(path is not None and pin is not None and sha(path) == pin, 'new_authorization_required')
    value = read_json(path)
    require(value and value.get('version') == VERSION+'-authorization' and
            value.get('plan_sha256') == plan_sha and value.get('limits') == LIMITS and
            value.get('profile') == asdict(PROFILE) and value.get('approved') is True and
            value.get('account_group_confirmed') == 'GPT-pro' and
            value.get('price_cny_per_million') == {'input':'0.4', 'output':'2'} and
            isinstance(value.get('user_evidence'), str) and bool(value['user_evidence'].strip()), 'authorization_scope')
    start, end = (datetime.fromisoformat(value[k]) for k in ('issued_at', 'expires_at'))
    require(start.tzinfo is not None and end.tzinfo is not None and
            start <= (now or datetime.now(timezone.utc)) < end and
            0 < (end-start).total_seconds() <= 86400, 'authorization_expired')
    return value


def native_gate(plan, client):
    workspace = HostReviewWorkspace(**plan['workspace'], evidence_roots=[plan['operator']])
    return ExactNativeGate(plan, workspace, CodexHostReviewEventSource(client, plan))


def replay_reviews(plan, state, client):
    gate = native_gate(plan, client)
    for row in state['attempts']:
        if row.get('reviewed'):
            require(gate.replay(row['handle']) == row['accepted'], 'review_changed')
    return gate


def preflight(operator, plan_sha, checkpoint_sha, grant, grant_sha, ci_run, client):
    plan, state, expected = load(operator, plan_sha, checkpoint_sha)
    require(state['phase'] in ('ready', 'retry_available'), 'not_ready')
    authorization(grant, grant_sha, plan_sha)
    ci = verify_ci(ci_run, plan['head'])
    native = verify_native_principals(client, plan)
    replay_reviews(plan, state, client)
    with socket.create_connection(('127.0.0.1', 12000), timeout=3):
        pass
    # Host and CI queries do not extend the human authorization deadline.
    approval = authorization(grant, grant_sha, plan_sha)
    load(operator, plan_sha, checkpoint_sha)
    return plan, state, expected, dict(ci=ci, native=native,
        authorization_sha256=grant_sha, authorization_document=approval)


def inspect_receipt(folder, business, context):
    """Treat identity-conflicting public text only as a diagnostic, never accepted IO."""
    receipt, worker, obs = (read_json(folder/n) for n in
        ('receipt.json', 'worker-result.json', 'observation/observation.json'))
    require(receipt and receipt.get('request_sha256') == digest(business) and
            receipt.get('wire_sha256') == digest(codec.build_wire(business)) and
            receipt.get('validation_context_sha256') == digest(context) and
            receipt.get('profile') == asdict(PROFILE) and
            receipt.get('response_mode') == 'necessity-candidate-v1' and
            read_json(folder/'request.json') == business and
            read_json(folder/'validation-context.json') == context, 'receipt_binding')
    expected_profile = dict(**asdict(PROFILE), reasoning_effort='high', api='responses',
        max_output_tokens=16384, max_retries=0, timeout_s=300, group_verified=False,
        upstream_identity_verified=False, response_mode='necessity-candidate-v1')
    require(read_json(folder/'profile.json') == expected_profile, 'profile_binding')
    require(receipt['usage_state'] in ('known', 'unknown', 'not_sent'), 'usage_state')
    if receipt['usage_state'] == 'not_sent':
        require(receipt['http_requests'] == 0 and receipt['worker_exit'] is None and
                receipt['usage'] is None, 'not_sent_receipt')
    if receipt['usage_state'] == 'known':
        usage = receipt['usage']
        require(valid_saved_usage(usage) and not receipt['usage_conflict'] and
                usage['input_tokens'] <= 64000 and usage['output_tokens'] <= 16384 and
                worker and worker['usage'] == usage and read_json(folder/'usage.json') == usage, 'known_usage')
    complete = (receipt['reaped'] is True and receipt['worker_exit'] == 0 and
        receipt['usage_state'] == 'known' and receipt['http_requests'] == 1 and obs and
        obs.get('body_free') is True and obs.get('http_requests') == 1 and
        obs.get('response_status') == 200 and obs.get('eof') is True and
        obs.get('closed') is True and obs.get('exception_type') is None and worker and
        obs.get('response_contract') == worker.get('response_observation'))
    contract = worker.get('response_observation', {}) if worker else {}
    complete = (complete and contract.get('response_received') is True and
        contract.get('reported_completed') is True and contract.get('terminal_status') == 'completed' and
        contract.get('function_calls') == 1 and contract.get('model_matches') is True and
        contract.get('output_type_counts', {}).get('message') == 0 and
        contract.get('output_type_counts', {}).get('other') == 0 and
        contract.get('decode', {}).get('identity_fields_equal') is True and
        obs.get('response_decode') == contract.get('decode') and
        0 <= receipt['elapsed_s'] <= 300)
    if complete and ((receipt['ok'] and receipt['code'] == 'ok' and worker['ok'] is True and
                      worker.get('business_validated') is True) or
                     (not receipt['ok'] and receipt['code'] == 'worker_rejected' and
                      worker.get('code') == receipt['worker_code'] == 'reasoning_identity')):
        tool = worker.get('public_tool_call') if receipt['ok'] else worker.get('diagnostic_tool_call')
        require(isinstance(tool, dict) and tool.get('name') == TOOL, 'public_tool')
        candidate.validate_business(business, context)(tool['arguments'])
        return receipt, 'awaiting_review', tool
    retry = (not complete and receipt['reaped'] is True and receipt['http_requests'] == 1 and not receipt['ok'] and
        (receipt['code'] == 'deadline_exceeded' or worker and
         (worker.get('code') == 'http_status_524' or worker.get('failure_category') == 'read_timeout')))
    return receipt, 'retry_available' if retry else 'stopped', None


def send(operator, plan_sha, checkpoint_sha, grant, grant_sha, ci_run, client, *, retry=False):
    operator = Path(operator).absolute()
    with exclusive(operator.with_name(operator.name+'.lock')):
        plan, state, expected, proof = preflight(operator, plan_sha, checkpoint_sha,
                                               grant, grant_sha, ci_run, client)
        require((state['phase'] == 'retry_available') == retry, 'explicit_retry_required')
        require(len(state['attempts']) < LIMITS['max_attempts'] and
                (not retry or sum(r['retry'] for r in state['attempts']) == 0), 'attempt_budget')
        key = hidden_key()  # no active worker/deadline while waiting; cancellation creates no claim
        try:
            plan, state, expected, proof = preflight(operator, plan_sha, checkpoint_sha,
                                                   grant, grant_sha, ci_run, client)
            case = state['next_case']
            folder = operator/'attempts'/f'{len(state["attempts"])+1:02}-{case}'
            folder.mkdir(exist_ok=False)
            write_json(folder/'claim.json', dict(case=case, retry=retry, plan_sha256=plan_sha,
                checkpoint_sha256=checkpoint_sha, claimed_at=datetime.now(timezone.utc).isoformat(), **proof))
            expected[folder.relative_to(operator).as_posix()+'/claim.json'] = sha(folder/'claim.json')
            state['attempts'].append(dict(case=case, retry=retry, folder=str(folder)))
            state['phase'] = 'in_flight'
            boundary = save(operator, state, checkpoint_sha, expected)
            print(json.dumps(dict(phase='claimed', **boundary), ensure_ascii=True), flush=True)
            checkpoint_sha = boundary['checkpoint_sha256']
            _, _, expected = load(operator, plan_sha, checkpoint_sha)
            business = read_json(operator/'requests'/f'{case}-facts.json')
            context = read_json(operator/'requests'/f'{case}-validation-context.json')
            run_once(business, profile=PROFILE, api_key=key, directory=folder/'call',
                response_mode='necessity-candidate-v1', validation_context=context, timeout_s=300)
        finally:
            key = None
        return finish_pending(operator, plan_sha, checkpoint_sha, client)


def finish_pending(operator, plan_sha, checkpoint_sha, client):
    # Read/reconcile only an existing completed receipt, never execute IO again.
    plan, state, _ = load(operator, plan_sha, checkpoint_sha, pending=True)
    require(state['phase'] == 'in_flight', 'no_pending_claim')
    row = state['attempts'][-1]
    folder, case = Path(row['folder']), row['case']
    business = read_json(operator/'requests'/f'{case}-facts.json')
    context = read_json(operator/'requests'/f'{case}-validation-context.json')
    receipt, phase, tool = inspect_receipt(folder/'call', business, context)
    row['receipt'] = receipt
    state['phase'], state['reason'] = phase, None if tool else (
        'evidence_incomplete' if receipt['code'] == 'ok' else receipt['code'])
    if phase == 'retry_available' and (len(state['attempts']) == 4 or any(r['retry'] for r in state['attempts'])):
        state['phase'], state['reason'] = 'stopped', 'retry_budget_exhausted'
    if state['phase'] == 'stopped':
        state['next_case'] = None
    expected = inventory(operator)
    if tool:
        gate = replay_reviews(plan, state, client)
        bound = dict(plan_sha256=plan_sha, key=f'{case}-facts', stage='initial',
            response_sha256=sha(folder/'call/worker-result.json'),
            report_sha256=hashlib.sha256(candidate.materials()[case].source.report.encode('utf-8')).hexdigest(),
            request_sha256=digest(business))
        row['handle'] = gate.publish(folder/'review', bound, 'opinion', dict(
            report=candidate.materials()[case].source.report, complete_request=business,
            public_tool_call=tool, transport_accepted=receipt['ok'],
            instruction='Inspect every source, claim, issue and repair, including missed errors and false positives. '
                'Necessary revisions must change a substantive unsupported claim/action. Optional wording is not '
                'a necessary factual defect. Reject this candidate on real semantic errors. '
                'A diagnostic opinion cannot establish reasoning identity or product admission.'))
        actual = inventory(operator)
        permitted = {f'{folder.relative_to(operator).as_posix()}/review/{n}' for n in REVIEW_FILES}
        require(all(actual.get(k) == v for k, v in expected.items()) and
                set(actual)-set(expected) <= permitted, 'review_inventory')
        expected = actual
    result = save(operator, state, checkpoint_sha, expected)
    if tool:
        result['dispatch_file'] = str(folder/'review/dispatch.txt')
    return result


def submit(operator, plan_sha, checkpoint_sha, client, decision, event_id):
    operator = Path(operator).absolute()
    with exclusive(operator.with_name(operator.name+'.lock')):
        plan, state, expected = load(operator, plan_sha, checkpoint_sha)
        require(state['phase'] == 'awaiting_review', 'no_pending_review')
        row = state['attempts'][-1]
        gate = replay_reviews(plan, state, client)
        accepted = gate.submit(row['handle'], decision, event_id)
        row.update(reviewed=True, accepted=accepted)
        if not accepted:
            state.update(phase='stopped', reason='semantic_rejection', next_case=None)
        elif not row['receipt']['ok']:
            state.update(phase='stopped', reason='identity_conflict_diagnostic_only', next_case=None)
        elif row['case'] == 'c':
            state.update(phase='complete', reason=None, next_case=None)
        else:
            state.update(phase='ready', reason=None, next_case=candidate.CASES[candidate.CASES.index(row['case'])+1])
        submitted = Path(row['handle']['folder'])/'submission.json'
        expected[submitted.relative_to(operator).as_posix()] = sha(submitted)
        replay_reviews(plan, state, client)
        return save(operator, state, checkpoint_sha, expected)


def seal(operator, plan_sha, checkpoint_sha, client):
    operator = Path(operator).absolute()
    with exclusive(operator.with_name(operator.name+'.lock')):
        plan, state, expected = load(operator, plan_sha, checkpoint_sha)
        require(state['phase'] != 'in_flight', 'incomplete_claim_requires_receipt_reconciliation')
        replay_reviews(plan, state, client)
        require(inventory(operator) == expected, 'closure_inventory')
        write_json(operator/'seal.json', dict(version=VERSION, plan_sha256=plan_sha,
            checkpoint_sha256=checkpoint_sha, inventory=expected, result=closed_status(state)))
        return dict(seal_sha256=sha(operator/'seal.json'), status=closed_status(state), readonly=False)


def replay(operator, plan_sha, checkpoint_sha, seal_sha, client):
    operator = Path(operator).absolute()
    before = inventory(operator)
    require(sha(operator/'seal.json') == seal_sha, 'original_seal_required')
    closed = read_json(operator/'seal.json')
    require(closed['plan_sha256'] == plan_sha and closed['checkpoint_sha256'] == checkpoint_sha and
            before == {**closed['inventory'], 'seal.json':seal_sha} and
            sha(operator/'plan.json') == plan_sha, 'sealed_inventory')
    # Validate the checkpoint chain without writing or regenerating a trust root.
    plan, state, _ = load(operator, plan_sha, checkpoint_sha, sources=False, sealed=True)
    replay_reviews(plan, state, client)
    require(closed['result'] == closed_status(state) and inventory(operator) == before, 'replay_changed')
    return dict(readonly=True, status=closed['result'], seal_sha256=seal_sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'send', 'retry', 'reconcile', 'submit', 'seal', 'replay'])
    parser.add_argument('--operator', required=True, type=Path)
    for name in ('plan-sha', 'checkpoint-sha', 'authorization-sha', 'ci-run', 'primary', 'independent',
                 'event-id', 'seal-sha'):
        parser.add_argument('--'+name)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--decision', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            result = prepare(args.operator, primary=args.primary, independent=args.independent)
        else:
            with CodexReadOnlyClient(CODEX) as client:
                if args.action == 'check':
                    plan, state, _ = load(args.operator, args.plan_sha, args.checkpoint_sha)
                    replay_reviews(plan, state, client)
                    result = dict(status=status(state), native=verify_native_principals(client, plan),
                                  key_read=False, provider_requests=0)
                elif args.action in ('send', 'retry'):
                    result = send(args.operator, args.plan_sha, args.checkpoint_sha, args.authorization,
                        args.authorization_sha, args.ci_run, client, retry=args.action == 'retry')
                elif args.action == 'reconcile':
                    with exclusive(args.operator.with_name(args.operator.name+'.lock')):
                        result = finish_pending(args.operator, args.plan_sha, args.checkpoint_sha, client)
                elif args.action == 'submit':
                    result = submit(args.operator, args.plan_sha, args.checkpoint_sha, client,
                                    read_json(args.decision), args.event_id)
                elif args.action == 'seal':
                    result = seal(args.operator, args.plan_sha, args.checkpoint_sha, client)
                else:
                    result = replay(args.operator, args.plan_sha, args.checkpoint_sha, args.seal_sha, client)
    except KeyboardInterrupt:
        result = dict(ok=False, code='cancelled_inspect_last_checkpoint_before_resume')
    except Exception as error:
        fixed = {'natural_clean_checkout_required', 'natural_exact_head_required',
                 'natural_exact_head_public_ci_required', 'session_executor_active'}
        code = str(error) if type(error) is ValueError and (
            str(error).startswith('necessity_launch_') or str(error) in fixed) else 'necessity_launch_preflight_or_storage_failed'
        result = dict(ok=False, code=code)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 1 if result.get('ok') is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
