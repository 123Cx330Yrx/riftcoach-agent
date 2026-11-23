"""Versioned overlap recovery above the sealed original15 evidence.

Prepare/task/status/submit/replay and host-only never read credentials. The
remaining fresh reviews use the original unexpired authorization and balances.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path
import sys

from app.evaluation import original15_patch_recovery as engine, sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, canonical, digest
from scripts import sol_original15_launch as original, sol_natural_launch as base
from scripts import windows_reviewer_credentials as credentials
from scripts.original15_authorization_continuation import VERSION as AUTH_VERSION
from scripts.original15_native_snapshot import CaseReplayReadSnapshot
from scripts.reviewer_profile_batch import inventory
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_natural_duty_development import current_head, verify_ci

VERSION = 'original15-overlap-recovery-launch-v1'


def safe_code(error):
    value = str(error)
    return value if re.fullmatch(r'(patch_launch|patch_recovery|session|original15)_[a-z0-9_]+', value) else type(error).__name__


@contextmanager
def native_view(events):
    """A live view for this segment only, invalidated before/after every new IO."""
    client = events.client
    if isinstance(client, CaseReplayReadSnapshot):
        raise ValueError('patch_launch_nested_native_view')
    snapshot = CaseReplayReadSnapshot(client)
    events.client = snapshot
    try:
        yield snapshot
    finally:
        events.client = client
        snapshot.responses.clear()


def source():
    names = original.source()
    # Include these new entry points even before their first index/commit.
    for name in ('app/evaluation/original15_patch_recovery.py',
                 'scripts/original15_patch_recovery_launch.py'):
        names[name] = digest((contract.ROOT/name).read_bytes())
    return names


def pinned(path, sha):
    path = Path(path).absolute()
    if path.resolve() != path or path.stat().st_nlink != 1 or digest(path.read_bytes()) != sha:
        raise ValueError('patch_launch_original_control_required')
    return engine.read(path)


def validate_authorization(plan, *, active=True, now=None):
    old = engine.read(Path(plan['parent_operator'])/'plan.json')
    grant = pinned(plan['authorization_file'], plan['authorization_sha256'])
    case = Path(plan['parent_operator'])/'cases'/engine.original.case_slug(plan['key'])
    if engine.read(case/'session/guard.json')['binding']['authorization_sha256'] != plan['authorization_sha256']:
        raise ValueError('patch_launch_original_case_authorization_required')
    original.validate_grant(grant, old, plan['parent_plan_sha256'],
        now=datetime.fromisoformat(grant['issued_at']))
    continuation = pinned(plan['continuation_file'], plan['continuation_sha256'])
    fixed = dict(version=AUTH_VERSION, original_authorization_sha256=plan['authorization_sha256'],
        original_plan_sha256=plan['parent_plan_sha256'], original_operator=plan['parent_operator'],
        original_envelope=original.grant_binding(old, plan['parent_plan_sha256']),
        scope='remaining_original_batch', reset_accounting=False,
        rewrite_original_authorization=False, automatic_retries=False,
        qualified=False, publication_allowed=False)
    issued, expires = (datetime.fromisoformat(continuation[k]) for k in ('issued_at', 'expires_at'))
    now = now or datetime.now(timezone.utc)
    if (set(continuation) != set(fixed) | {'issued_at', 'expires_at', 'user_authorization_evidence'}
            or any(continuation.get(k) != v for k,v in fixed.items())
            or issued.utcoffset() is None or expires.utcoffset() is None
            or not timedelta(0) < expires-issued <= timedelta(days=1)
            or issued < datetime.fromisoformat(grant['expires_at'])
            or not isinstance(continuation['user_authorization_evidence'], str)
            or not continuation['user_authorization_evidence'].strip()
            or (active and not issued <= now < expires)):
        raise ValueError('patch_launch_original_unexpired_continuation_required')
    if plan['authorization_expires_at'] != continuation['expires_at']:
        raise ValueError('patch_launch_original_expiry_changed')
    return continuation


def prepare(operator, proof_file, proof_sha, choice_file, choice_sha,
            authorization_file, authorization_sha, continuation_file, continuation_sha):
    operator = Path(operator).absolute()
    spec = engine.binding(proof_file, proof_sha)
    proof = spec['proof']; parent = Path(proof['parent_operator'])
    if (operator.resolve() != operator or operator.exists()
            or any(operator.is_relative_to(p) or p.is_relative_to(operator)
                for p in (parent, parent.with_name(parent.name+'-authors'), contract.ROOT))):
        raise ValueError('patch_launch_new_external_operator_required')
    old = engine.read(parent/'plan.json')
    if Path(sys.executable).resolve() != Path(old['python']).resolve():
        raise ValueError('patch_launch_actual_python_required')
    choice = original.load_patch_coordination(choice_file, choice_sha)
    _, inputs = engine.original.case_for(proof['key'])
    proposals = [engine.direct.bind(inputs, duty,
        engine.read(parent/'cases'/engine.original.case_slug(proof['key'])/'journal'/f'{duty}-initial.json')['raw'])
        for duty in ('facts', 'completion')]
    conflicts = engine.direct.conflict_inventory(inputs, proposals)
    assembly = engine.direct.preview(inputs, proposals, coordination=choice)
    if engine.direct.inventory_sha(conflicts) != proof['conflict_inventory_sha256']:
        raise ValueError('patch_launch_original_conflict_changed')
    continuation = pinned(continuation_file, continuation_sha)
    plan = dict(version=VERSION, operator=str(operator), cwd=str(contract.ROOT.resolve()),
        python=str(Path(sys.executable).resolve()), codex=str(base.CODEX.resolve()),
        head=current_head(), source=source(), contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        profile=original.profile(), key=proof['key'], review_plan=old['review_plan'],
        parent_operator=str(parent), parent_plan_sha256=proof['parent_plan_sha256'],
        proof_file=spec['proof_file'], proof_sha256=proof_sha,
        choice_file=str(Path(choice_file).absolute()), choice_sha256=choice_sha,
        actual_preview_sha256=engine.direct.digest(assembly.report),
        authorization_file=str(Path(authorization_file).absolute()), authorization_sha256=authorization_sha,
        continuation_file=str(Path(continuation_file).absolute()), continuation_sha256=continuation_sha,
        authorization_expires_at=continuation['expires_at'],
        limits=old['limits'], historical_case_budget=proof['historical_budget'],
        historical_batch_accounting=proof['historical_batch_accounting'],
        inherited_active_seconds=proof['inherited_active_seconds'],
        sequence=['inherited-facts-initial','inherited-completion-initial','patch-coordination',
                  'compatibility','edit','unique-application','facts-fresh','completion-fresh'],
        extra_requests=0, extra_tokens=0, reset_accounting=False,
        manual_retry_only=True, stored_key_target=credentials.TARGET,
        execution_authorized=False, qualified=False, publication_allowed=False)
    validate_authorization(plan, active=False)
    operator.mkdir(parents=True)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=digest((operator/'plan.json').read_bytes()),
        provider_requests=0, key_reads=0, authorization_expires_at=plan['authorization_expires_at'])


def load(operator, pin, *, frozen=False):
    operator = Path(operator).absolute()
    plan = pinned(operator/'plan.json', pin)
    if (plan['version'] != VERSION or plan['operator'] != str(operator)
            or plan['cwd'] != str(contract.ROOT.resolve()) or Path.cwd().resolve() != contract.ROOT.resolve()
            or plan['python'] != str(Path(sys.executable).resolve())
            or plan['codex'] != str(base.CODEX.resolve()) or plan['profile'] != original.profile()
            or plan['contract'] != contract.CONTRACT.snapshot().model_dump(mode='json')
            or plan['stored_key_target'] != credentials.TARGET):
        raise ValueError('patch_launch_execution_binding_changed')
    spec = engine.binding(plan['proof_file'], plan['proof_sha256'])
    proof = spec['proof']; old = engine.read(Path(proof['parent_operator'])/'plan.json')
    if (plan['review_plan'] != old['review_plan'] or plan['key'] != proof['key']
            or plan['parent_operator'] != proof['parent_operator']
            or plan['parent_plan_sha256'] != proof['parent_plan_sha256']
            or plan['limits'] != old['limits'] or plan['historical_case_budget'] != proof['historical_budget']
            or plan['historical_batch_accounting'] != proof['historical_batch_accounting']
            or plan['inherited_active_seconds'] != proof['inherited_active_seconds']
            or plan['extra_requests'] != 0 or plan['extra_tokens'] != 0
            or plan['reset_accounting'] is not False or plan['manual_retry_only'] is not True):
        raise ValueError('patch_launch_inherited_controls_changed')
    original.load_patch_coordination(plan['choice_file'], plan['choice_sha256'])
    validate_authorization(plan, active=False)
    if frozen and (current_head() != plan['head'] or source() != plan['source']):
        raise ValueError('patch_launch_frozen_source_changed')
    return plan, spec


def session_for(plan, pin, events, *, before_new_model=None, **kwargs):
    _, spec = load(plan['operator'], pin)
    operator = Path(plan['operator'])
    return engine.open_session(operator/'execution', spec, events,
        author_root=operator.with_name(operator.name+'-authors'), evidence_root=operator,
        control_binding=dict(plan_sha256=pin, authorization_sha256=plan['authorization_sha256'],
            continuation_sha256=plan['continuation_sha256']), before_new_model=before_new_model, **kwargs)


def execute(plan, pin, events, *, guard=None, checkpoint=None, ci_run=None,
            manual_retry=False, host_only=False, sink=base.emit, key_reader=None):
    load(plan['operator'], pin, frozen=True)
    if (Path(plan['operator'])/'seal.json').exists():
        raise SessionBlocked('patch_launch_sealed_no_run')
    verify_native_principals(events.client, plan['review_plan'])
    ci = None
    with native_view(events) as view:
        def before():
            # Flush live pages at every new model boundary, preserving validation.
            view.responses.clear()
            load(plan['operator'], pin, frozen=True)
            validate_authorization(plan)
            status = session.status()
            budget = engine.original.last_budget(session)
            old, batch, limits = plan['historical_case_budget'], plan['historical_batch_accounting'], plan['limits']
            # capture_attempt invokes this guard after operation() has written
            # its owned current intent. An unresolved intent found on reopen is
            # still rejected before run_case; do not confuse this live boundary.
            own_intent = f'{session.cursor+1:04d}-intent.json'
            own_pending = (status['unresolved'] == [own_intent]
                and engine.read(session.root/'operations'/own_intent)['kind'] == 'model')
            if (host_only or ci is None or status['closed'] or (status['unresolved'] and not own_pending)
                    or budget['calls'] >= limits['max_requests_per_case']
                    or batch['calls']+budget['calls']-old['calls'] >= limits['max_requests']
                    or batch['tokens']+batch['reserved_tokens']+budget['tokens']+budget['reserved_tokens']
                        -old['tokens']-old['reserved_tokens']+80384 > limits['max_reserved_tokens']
                    or session.active_seconds >= limits['per_case_active_seconds']):
                raise SessionBlocked('patch_launch_original_remaining_budget_required')
        session, gate = session_for(plan, pin, events, before_new_model=before,
            guard=guard, checkpoint=checkpoint, manual_retry=manual_retry, sink=sink)
        choice = original.load_patch_coordination(plan['choice_file'], plan['choice_sha256'])
        try:
            with session:
                controls = dict(plan_sha256=pin, authorization_sha256=plan['authorization_sha256'],
                    continuation_sha256=plan['continuation_sha256'])
                if not (session.root/'launch.json').exists():
                    write_new_json(session.root/'launch.json', controls)
                    session._checkpoint('recovery_launch_bound')
                elif engine.read(session.root/'launch.json') != controls:
                    raise SessionBlocked('patch_launch_original_controls_changed')
                status = session.status()
                if status['closed'] or status['unresolved']:
                    raise SessionBlocked('patch_launch_closed_or_unresolved_no_send')
                waiting = status['timeout_waiting'] or status['format_waiting']
                if manual_retry and not waiting:
                    raise SessionBlocked('patch_launch_retry_requires_failed_attempt')
                if waiting and not manual_retry:
                    raise SessionPaused('patch_launch_awaiting_manual_retry')
                session.max_new_models = 0
                def deny(*args, **kwargs):
                    raise AssertionError('patch_launch_offline_provider_forbidden')
                try:
                    result = engine.run_case(session, original.router_for(session, 'OFFLINE_NO_SEND', deny),
                        patch_coordination=choice)
                except SessionPaused as error:
                    if str(error) != 'session_model_boundary' or host_only:
                        raise
                    validate_authorization(plan)
                    ci = verify_ci(ci_run, plan['head'])
                    folder = session.root/'ci-checks'
                    folder.mkdir(exist_ok=True)
                    write_new_json(folder/f'{len(list(folder.iterdir()))+1:04d}.json', ci)
                    session._checkpoint('exact_recovery_head_ci_verified')
                    before()
                    session.review_gate.verify_prior()
                    # The only credential read is after verified exact pending IO.
                    reader = key_reader or credentials.read_key
                    with session.waiting_for_credentials():
                        key = reader()
                    before()
                    session.cursor = 0
                    session.max_new_models = 1
                    try:
                        result = engine.run_case(session, original.router_for(session, key), patch_coordination=choice)
                    finally:
                        key = None
                        view.responses.clear()
                session.close(dict(result=result))
                return dict(phase='closed', result=result, publication_allowed=False)
        except SessionPaused as error:
            return dict(phase='paused', reason=str(error), publication_allowed=False)
        except (Exception, SessionBlocked) as error:
            return dict(phase='stopped', reason=safe_code(error), error_type=type(error).__name__,
                publication_allowed=False)


def replay(plan, pin, events, *, guard, checkpoint):
    operator = Path(plan['operator'])
    before = inventory(operator), inventory(operator.with_name(operator.name+'-authors'))
    with native_view(events):
        session, gate = session_for(plan, pin, events, guard=guard, checkpoint=checkpoint, read_only=True)
        with session:
            if engine.read(session.root/'launch.json') != dict(plan_sha256=pin,
                    authorization_sha256=plan['authorization_sha256'],
                    continuation_sha256=plan['continuation_sha256']):
                raise ValueError('patch_launch_replay_controls_changed')
            handles = list(gate.handles())
            decisions = [gate.native.replay(h) for h in handles]
            terminal = engine.read(session.root/'terminal.json')
            def deny(*args, **kwargs):
                raise AssertionError('patch_launch_replay_provider_forbidden')
            if terminal.get('reason') == 'semantic_rejected':
                last = engine.read(sorted((session.root/'operations').glob('*-intent.json'))[-1])
                if (not decisions or decisions[-1] is not False or not all(decisions[:-1])
                        or handles[-1]['binding']['key'] != terminal['key']
                        or last['kind'] != 'host-task' or last['request']['key'] != terminal['key']):
                    raise ValueError('patch_launch_rejection_frontier_changed')
                result = dict(reason='session_semantic_rejected',key=terminal['key'])
            else:
                result = engine.run_case(session, original.router_for(session, 'OFFLINE_NO_SEND', deny))
                if (terminal.get('value', {}).get('result') != result
                        or session.cursor != session.status()['operations']):
                    raise ValueError('patch_launch_terminal_replay_changed')
            transport = original.audit_transport(session)
    if before != (inventory(operator), inventory(operator.with_name(operator.name+'-authors'))):
        raise ValueError('patch_launch_replay_changed_evidence')
    return dict(strict_replay=True, result=result, transport=transport,
        parent_failure_retained=True, qualified=False, publication_allowed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','run','task','submit','status','reconcile','replay','seal'))
    for name in ('operator','proof-file','choice-file','authorization-file','continuation-file','primary-file'):
        parser.add_argument('--'+name, type=Path, required=name == 'operator')
    for name in ('plan-sha','proof-sha','choice-sha','authorization-sha','continuation-sha',
                 'guard-sha','checkpoint-sha','ci-run','key','event-id'):
        parser.add_argument('--'+name)
    parser.add_argument('--host-only', action='store_true')
    parser.add_argument('--manual-retry', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        base.emit(prepare(args.operator,args.proof_file,args.proof_sha,args.choice_file,args.choice_sha,
            args.authorization_file,args.authorization_sha,args.continuation_file,args.continuation_sha)); return
    plan, _ = load(args.operator, args.plan_sha, frozen=args.action == 'run')
    roots = dict(guard=args.guard_sha, checkpoint=args.checkpoint_sha)
    if args.action != 'run' and (not args.guard_sha or not args.checkpoint_sha):
        parser.error('existing session requires preserved guard and checkpoint SHA')
    with base.host(plan) as events:
        if args.action == 'run':
            value = execute(plan,args.plan_sha,events,ci_run=args.ci_run,
                manual_retry=args.manual_retry,host_only=args.host_only,**roots)
        elif args.action in ('replay','seal'):
            if args.action == 'seal' and (args.operator/'seal.json').exists():
                raise ValueError('patch_launch_seal_already_exists')
            value = replay(plan,args.plan_sha,events,**roots)
            if args.action == 'seal':
                write_new_json(args.operator/'seal.json',dict(version=VERSION+'-seal',plan_sha256=args.plan_sha,
                    result=value, inventory=inventory(args.operator), qualified=False, publication_allowed=False))
        else:
            with native_view(events):
                session, gate = session_for(plan,args.plan_sha,events,
                    read_only=args.action in ('task','status'), reconcile=args.action=='reconcile',
                    sink=base.emit,**roots)
                with session:
                    gate.verify_prior()
                    if args.action == 'task':
                        handle = list(gate.handles())[-1]
                        if (Path(handle['folder'])/'submission.json').exists():
                            raise ValueError('patch_launch_task_already_submitted')
                        print((Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8'),end=''); return
                    if args.action == 'submit':
                        value = dict(accepted=gate.submit(args.key,engine.read(args.primary_file),args.event_id),
                            provider_requests=0, key_reads=0)
                    elif args.action == 'reconcile':
                        value = session.reconcile_completed()
                    else:
                        value = session.status()
        base.emit(value)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt, SessionBlocked, SessionPaused) as error:
        base.emit(dict(ok=False,code=safe_code(error),error_type=type(error).__name__,publication_allowed=False))
        raise SystemExit(1) from None
