"""Explicit continuation of a sealed first-review receiver or transport failure.

Parent evidence is immutable. Only completed generation/tool operations are
imported into a new session. The failed review's cost and attempt remain in
the cumulative accounting; its output is never treated as a successful review.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, canonical, digest
from scripts.reviewer_profile_batch import inventory

VERSION = 'sol-natural-receiver-continuation-v1'
# Only these implementation files may differ; prompts, source and generation
# components must remain the parent's exact bytes. Each new plan pins all files.
ALLOWED_CHANGES = frozenset((
    'scripts/reviewer_responses_nonstream.py', 'scripts/sol_natural_launch.py',
    'scripts/sol_natural_continuation.py', 'scripts/prepare_sol_natural.py',
    'app/evaluation/sol_natural_session.py', 'app/evaluation/sol_natural_contract.py',
    'app/runtime/sol_natural_provider.py', 'app/runtime/coach_contract.py',
    'app/prompt_program/resolver.py',
    'examples/runtime_profiles/sol_natural_v1/prompt_programs/recent-form-review/manifest.json',
))


def read(path):
    return json.loads(Path(path).read_bytes())


def parent_state(operator, seal_sha, *, limits_override=None):
    root = Path(operator).absolute()
    seal_raw = (root/'seal.json').read_bytes()
    if digest(seal_raw) != seal_sha:
        raise ValueError('launch_parent_seal_changed')
    seal = json.loads(seal_raw)
    actual = inventory(root)
    actual.pop('seal.json')
    if actual != seal['inventory'] or seal['result'].get('strict_replay') is not True:
        raise ValueError('launch_parent_inventory_or_replay_invalid')
    plan = read(root/'plan.json')
    session_root = root/'execution/session'
    guard = read(session_root/'guard.json')
    roots = seal['original_roots']
    if (digest((root/'plan.json').read_bytes()) != seal['plan_sha256']
            or plan['operator'] != str(root) or plan['run_id'] != guard['binding']['run_id']
            or guard['binding']['plan_sha256'] != seal['plan_sha256']
            or guard['binding']['authorization_sha256'] != roots['authorization_sha']
            or digest((session_root/'authorization.json').read_bytes()) != roots['authorization_sha']
            or guard['transport_root'] != str(root/'execution/transport'/plan['run_id'])
            or guard['journal_root'] != str(root/'execution/journal')):
        raise ValueError('launch_parent_identity_changed')
    parent = CandidateSession(session_root, binding=guard['binding'],
        transport_root=guard['transport_root'], journal_root=guard['journal_root'],
        guard_sha=roots['guard'], checkpoint_sha=roots['checkpoint'], read_only=True,
        continuation=plan.get('continuation'))
    with parent:
        status = parent.status()
        if not status['closed'] or status['unresolved'] or status['operations'] < 5:
            raise ValueError('launch_parent_not_first_review_failure')
        count = status['operations']
        prefix = count - 2
        intents = [read(session_root/f'operations/{n:04d}-intent.json') for n in range(1, count+1)]
        results = [read(session_root/f'operations/{n:04d}-result.json') for n in range(1, count+1)]
        for n, result in enumerate(results, 1):
            if result['intent_sha256'] != digest((session_root/f'operations/{n:04d}-intent.json').read_bytes()):
                raise ValueError('launch_parent_result_binding')
        if ([i['ordinal'] for i in intents] != list(range(1, count+1)) or
                [i['kind'] for i in intents] != ['model'] + ['tool']*(count-4) + ['model', 'model', 'journal']
                or any(i['request'].get('name') != 'knowledge.search' for i in intents[1:prefix-1])
                or any(results[i]['value'].get('ok') is not True for i in (0, prefix-1))
                or any(r['value'].get('success') is not True for r in results[1:prefix-1])):
            raise ValueError('launch_parent_prefix_invalid')
        failed = results[prefix]['value']
        context = intents[prefix]['request'].get('metadata', {}).get(contract.CONTEXT, {})
        if context.get('duty') != 'facts' or context.get('stage') != 'initial':
            raise ValueError('launch_parent_review_stage_invalid')
        budget = failed['budget']
        prior = results[prefix-1]['value']['budget']
        if plan.get('continuation'):
            inherited = plan['continuation']['historical_budget']
            if prior != dict(inherited, stopped=False, failed=False,
                    logical=dict(inherited['logical'], review=0)):
                raise ValueError('launch_parent_imported_budget_changed')
        else:
            inherited = prior
        new_count = budget['calls'] - inherited['calls']
        if (failed.get('ok') is not False or failed.get('error_code') != 'sol_call_failed'
                or not 1 <= new_count <= 2 or budget['router_calls'] != budget['calls']
                or budget['logical'] != {'generation': 2, 'review': 1}
                or len(budget['attempts']) != budget['calls']
                or budget['attempts'][:inherited['calls']] != inherited['attempts']
                or any(row['status'] != 'failed' for row in budget['attempts'][inherited['calls']:])
                or budget['stopped'] is not True or budget['failed'] is not True
                or budget['retries'] != inherited['retries'] + new_count - 1
                or seal['result'].get('native_reviews') != 0
                or seal['result'].get('publication_allowed') is not False
                or seal['result'].get('production_admitted') is not False
                or seal['result']['accounting'] != {k: budget[k] for k in ('calls','tokens','reserved_tokens','retries')}):
            raise ValueError('launch_parent_failure_accounting_invalid')
        known, reserved = inherited['tokens'], inherited['reserved_tokens']
        from scripts.prepare_reviewer_profile_screen import visible
        from scripts.reviewer_responses_transport import digest as wire_digest
        from scripts.reviewer_responses_nonstream import build_wire
        expected_business = visible(intents[prefix]['request'])
        for ordinal in range(inherited['calls']+1, budget['calls']+1):
            receipt_dir = parent.transport_root/f'review/call-{ordinal:03d}'
            receipt, worker = read(receipt_dir/'receipt.json'), read(receipt_dir/'worker-result.json')
            observation = read(receipt_dir/'observation/observation.json')
            if (receipt.get('ok') is not False or receipt.get('reaped') is not True
                    or receipt.get('usage_conflict') is not False or receipt.get('http_requests') != 1
                    or receipt.get('worker_exit') != 0 or receipt.get('usage') != worker.get('usage')
                    or worker.get('public_tool_call') is not None
                    or receipt.get('worker_code') != worker.get('code')
                    or observation.get('eof') is not True or observation.get('closed') is not True
                    or observation.get('http_requests') != 1
                    or read(receipt_dir/'request.json') != expected_business
                    or receipt.get('request_sha256') != wire_digest(expected_business)
                    or receipt.get('wire_sha256') != wire_digest(build_wire(expected_business))):
                raise ValueError('launch_parent_failure_receipt_invalid')
            if receipt['worker_code'] == 'reasoning_identity' and not plan.get('continuation'):
                if (receipt.get('usage_state') != 'known' or observation.get('response_status') != 200
                        or worker.get('response_observation') != observation.get('response_contract')
                        or observation['response_contract'].get('model_matches') is not True):
                    raise ValueError('launch_parent_receiver_failure_invalid')
                known += receipt['usage']['total_tokens']
            elif receipt['worker_code'] in ('http_status_408','http_status_504','http_status_524'):
                if (receipt.get('usage_state') != 'unknown' or receipt.get('usage') is not None
                        or observation.get('response_status') != int(receipt['worker_code'][-3:])
                        or observation.get('response_contract') is not None):
                    raise ValueError('launch_parent_timeout_failure_invalid')
                attempt = read(session_root/f'operations/attempt-{ordinal:03d}.json')
                if (attempt['ordinal'] != ordinal or attempt['intent_sha256'] != digest(
                        (session_root/f'operations/{prefix+1:04d}-intent.json').read_bytes())):
                    raise ValueError('launch_parent_attempt_binding')
                from app.evaluation.golden_stream_bridge import REQUEST
                from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
                issued = REQUEST.validate_json(attempt['issued_raw'])
                reserved += estimate_runtime_request_input_ceiling(issued) + issued.max_tokens
            else:
                raise ValueError('launch_parent_nonrecoverable_failure')
        if (budget['tokens'], budget['reserved_tokens']) != (known, reserved):
            raise ValueError('launch_parent_failure_usage_changed')
        active = parent.active_before
        historical_limits = plan['limits']
        descriptor = limits_override or historical_limits
        old_limits = dict(max_calls=7, total_tokens=498688, execution_timeout_s=1200,
                          transport_retries=1, request_timeout_s=300)
        current_limits = {k: contract.CONTRACT.descriptor()[k] for k in old_limits}
        if (historical_limits not in (old_limits, current_limits)
                or descriptor not in (old_limits, current_limits)
                or any(descriptor[k] < historical_limits[k] for k in old_limits)
                or active >= descriptor['execution_timeout_s']):
            raise ValueError('launch_parent_budget_contract_changed_or_exhausted')
    # Merely entering the read-only parent must not alter any sealed byte.
    if inventory(root) != {**actual, 'seal.json': seal_sha}:
        raise ValueError('launch_parent_changed_during_read')
    remaining = descriptor['max_calls'] - budget['calls']
    result = dict(version=VERSION, operator=str(root), seal_sha256=seal_sha,
        plan_sha256=seal['plan_sha256'], roots=roots, run_id=plan['run_id'],
        prefix_operations=prefix, historical_budget=budget, active_seconds=active,
        remaining_attempts=remaining, max_new_tokens=remaining*(64000+16384),
        estimated_additional_cny=str(Decimal(remaining)*(64000*Decimal('.4')+16384*Decimal('2'))/1_000_000),
        frontier_request_sha256=digest(canonical(intents[prefix]['request'])),
        report_sha256=digest(intents[prefix]['request']['metadata'][contract.CONTEXT]['report'].encode('utf-8')),
        source=plan['source'], first_request_sha256=plan['first_request_sha256'], review_plan=plan['review_plan'])
    if descriptor != historical_limits:
        result['execution_limits'] = descriptor
    return result


def verify_parent(spec):
    if parent_state(spec['operator'], spec['seal_sha256'], limits_override=spec.get('execution_limits')) != spec:
        raise SessionBlocked('launch_parent_binding_changed')


def verify_source(spec, current):
    previous = spec['source']
    if any(current[k] != previous[k] for k in ('python', 'python_version', 'packages')):
        raise ValueError('launch_parent_dependencies_changed')
    changed = {p for p in set(previous['files']) | set(current['files'])
               if previous['files'].get(p) != current['files'].get(p)}
    if changed - ALLOWED_CHANGES:
        raise ValueError('launch_parent_unrelated_source_changed')
    return sorted(changed)


def import_prefix(session):
    """Create explicitly derived imports; original parent files never change."""
    spec = session.continuation
    parent = Path(spec['operator'])/'execution/session/operations'
    for n in range(1, spec['prefix_operations']+1):
        for suffix in ('intent', 'result'):
            name = f'{n:04d}-{suffix}.json'
            raw = (parent/name).read_bytes()
            if n == spec['prefix_operations'] and suffix == 'result':
                value = json.loads(raw)
                budget = deepcopy(spec['historical_budget'])
                budget.update(stopped=False, failed=False)
                budget['logical']['review'] = 0
                value['value']['budget'] = budget
                value['imported_from_sha256'] = digest(raw)
                raw = canonical(value)
            with (session.root/'operations'/name).open('xb') as handle:
                handle.write(raw)
    write_new_json(session.root/'continuation-import.json', dict(
        parent_seal_sha256=spec['seal_sha256'], parent_operator=spec['operator'],
        historical_failure_retained=True, old_review_accepted=False,
        budget_change='carry failed attempt/cost; allow re-execution of unfinished logical review',
        inherited_active_seconds=spec['active_seconds'], new_provider_requests=0))
    session.active_before = spec['active_seconds']
    session._checkpoint('parent_prefix_imported')


def verify_frontier(session, kind, request):
    if session.cursor == session.continuation['prefix_operations'] and (kind != 'model' or digest(canonical(request)) !=
                               session.continuation['frontier_request_sha256']):
        raise SessionBlocked('launch_continuation_frontier_changed')
    if kind == 'model' and session.cursor >= session.continuation['prefix_operations'] and contract.CONTEXT not in request.get('metadata', {}):
        raise SessionBlocked('launch_continuation_generation_forbidden')
