"""Explicit original15 per-case launcher; preparation never loads credentials.

All existing roots must come from preserved stdout, never recalculated from
checkpoint files. No automatic batch loop, retry, qualification or publication.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from app.evaluation import sol_original15_session as engine, sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, canonical, digest
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider, inventory as transport_inventory
from app.runtime.sol_session_receipts import recover_success, request_from_raw
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.golden_stream_bridge import RESPONSE
from app.providers.errors import ProviderResponseError
from scripts import sol_natural_launch as base
from scripts.audit_sol_review_qualification import audit
from scripts.prepare_completion_diagnostic import NoGenerationProvider
from scripts.review_independence_contract import freeze_v2_identity, MODE_V2, FINAL_POLICY
from scripts.reviewer_profile_batch import inventory
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_nonstream import build_wire
from scripts.reviewer_responses_transport import digest as object_digest
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_natural_duty_development import current_head, verify_ci

VERSION = 'sol-original15-launch-v1'
ROOT = contract.ROOT
ENVELOPE = dict(cases=15, logical_reviews_per_case=4, manual_retries_per_case=4,
    max_requests_per_case=8, max_requests=120, max_reserved_tokens=9646080,
    per_case_active_seconds=3600, maximum_active_seconds=54000,
    per_request_seconds=300, per_request_input_tokens=64000, per_request_output_tokens=16384)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def source():
    # Deliberately exclude unrelated untracked local scripts and secrets.
    names = subprocess.check_output(['git', 'ls-files', '--', 'app', 'scripts',
        'skills', 'examples/runtime_profiles', 'tests/fixtures', 'data/evaluation/datasets',
        'pyproject.toml', 'uv.lock', 'requirements.txt'], cwd=ROOT, text=True).splitlines()
    names += [str(engine.frozen.COVERAGE), 'app/evaluation/sol_original15_session.py',
              'scripts/sol_original15_launch.py']
    files = [name for name in sorted(set(names)) if (ROOT/name).is_file() and '__pycache__' not in name]
    if any((ROOT/name).resolve() != ROOT/name or (ROOT/name).stat().st_nlink != 1 for name in files):
        raise ValueError('original15_redirected_source')
    return {name:digest((ROOT/name).read_bytes()) for name in files}


def profile():
    from dataclasses import asdict
    return dict(**asdict(contract.REVIEW_PROFILE), reasoning_effort='high',
        input_cny_per_million='0.5', output_cny_per_million='2.5',
        upstream_identity_verified=False, group_independently_verified=False)


def prepare(operator, primary, independent):
    operator = Path(operator).absolute()
    if (operator.resolve() != operator or operator.exists()
            or operator.is_relative_to(ROOT) or ROOT.is_relative_to(operator)):
        raise ValueError('original15_new_external_operator_required')
    coverage = audit()
    plan = dict(version=VERSION, operator=str(operator), head=current_head(),
        cwd=str(ROOT.resolve()), python=str(Path(sys.executable).resolve()), codex=str(base.CODEX.resolve()),
        source=source(), contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        coverage=coverage, review_profile=profile(), limits=ENVELOPE,
        estimated_maximum_uncached_cny='8.7552', hard_billing_cap=False,
        review_plan=freeze_v2_identity(dict(host_review_submission_mode=MODE_V2,
            host_review_evidence_policy=FINAL_POLICY), root_thread_id=primary,
            primary_id=primary, independent_id=independent),
        execution_authorized=False, qualified=False, publication_allowed=False)
    operator.mkdir(parents=True, exist_ok=False)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=digest((operator/'plan.json').read_bytes()), provider_requests=0,
        key_reads=0, cases=15, execution_authorized=False)


def load(operator, pin, *, frozen=False):
    operator = Path(operator).absolute()
    if digest((operator/'plan.json').read_bytes()) != pin:
        raise ValueError('original15_original_plan_required')
    plan = read(operator/'plan.json')
    if (plan['version'] != VERSION or operator.resolve() != operator or plan['operator'] != str(operator)
            or plan['cwd'] != str(ROOT.resolve()) or Path.cwd().resolve() != ROOT.resolve()
            or plan['python'] != str(Path(sys.executable).resolve()) or plan['codex'] != str(base.CODEX.resolve())
            or plan['limits'] != ENVELOPE or plan['review_profile'] != profile()
            or plan['contract'] != contract.CONTRACT.snapshot().model_dump(mode='json')):
        raise ValueError('original15_actual_launch_binding')
    if frozen and (current_head() != plan['head'] or source() != plan['source']):
        raise ValueError('original15_frozen_source_changed')
    return plan


def grant_binding(plan, pin):
    return dict(version=VERSION+'-authorization', plan_sha256=pin, head=plan['head'],
        contract=plan['contract'], limits=ENVELOPE, review_profile=plan['review_profile'],
        estimated_maximum_uncached_cny=plan['estimated_maximum_uncached_cny'],
        manual_retry_only=True, production_admitted=False)


def validate_grant(value, plan, pin, *, now=None):
    now = now or datetime.now(timezone.utc)
    issued, expires = (datetime.fromisoformat(value[k]) for k in ('issued_at', 'expires_at'))
    if (any(value.get(k) != v for k,v in grant_binding(plan, pin).items())
            or issued.utcoffset() is None or expires.utcoffset() is None
            or not issued <= now < expires or not timedelta(0) < expires-issued <= timedelta(days=1)
            or not isinstance(value.get('user_authorization_evidence'), str)
            or not value['user_authorization_evidence'].strip()):
        raise ValueError('original15_specific_unexpired_authorization_required')


def open_case(plan, pin, events, key, *, authorization_sha=None, preflight=False, **kwargs):
    return engine.open_case(plan['operator'], key, plan['review_plan'], events,
        plan_sha=pin, authorization_sha=authorization_sha, python=plan['python'], preflight=preflight, **kwargs)


def roots_for(roots, key):
    value = roots.get(key, {})
    if set(value) != {'guard_sha256', 'checkpoint_sha256'} or any(
            not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in value.values()):
        raise ValueError('original15_preserved_stdout_roots_required')
    return dict(guard=value['guard_sha256'], checkpoint=value['checkpoint_sha256'])


def native_task(plan, pin, events):
    verify_native_principals(events.client, plan['review_plan'])
    key = plan['coverage']['cases'][0]['key']
    session, gate = open_case(plan, pin, events, key, preflight=True, sink=base.emit)
    try:
        with session:
            gate.require('startup-preflight', 'opinion', dict(fixture_only=True,
                administrative_preflight=True, responses=[],
                report='Administrative author/check-answer/native import preflight. No business acceptance.'),
                'Administrative author/check-answer/native import preflight. No business acceptance.')
    except SessionPaused:
        pass
    return dict(provider_requests=0, key_reads=0)


def verify_preflight(plan, pin, events, proof):
    key = plan['coverage']['cases'][0]['key']
    session, gate = open_case(plan, pin, events, key, preflight=True, read_only=True,
        **roots_for({'preflight':proof}, 'preflight'))
    with session:
        handles = list(gate.handles())
        if len(handles) != 1 or handles[0]['binding']['key'] != 'startup-preflight' or not gate.native.replay(handles[0]):
            raise ValueError('original15_native_preflight_required')


def router_for(session, key, sender=None):
    options = {} if sender is None else dict(sender=sender)
    return SolNaturalProvider(NoGenerationProvider(), SolReviewProvider(api_key=key,
        directory=session.transport_root/'review', task_directory=session.transport_root,
        contract_module=contract, **options), contract_module=contract)


def evidence_inventory(plan):
    """Hash all evidence; kernel lock bytes are not persisted trial evidence.

    On Windows a held msvcrt byte lock cannot be read. Exclude only the known
    CandidateSession lock paths, after checking they are ordinary local files.
    Arbitrary files with a .lock suffix remain part of the inventory.
    """
    operator = Path(plan['operator'])
    locks = {'native-preflight/session.lock'} | {
        'cases/'+engine.case_slug(row['key'])+'/session.lock' for row in plan['coverage']['cases']}
    result = {}
    for path in sorted(operator.rglob('*')):
        if path.resolve() != path or path.is_symlink():
            raise ValueError('original15_redirected_evidence')
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise ValueError('original15_linked_evidence')
            name = path.relative_to(operator).as_posix()
            if name not in locks:
                result[name] = digest(path.read_bytes())
    return result


def audit_transport(session):
    """Read actual original receipts, including failed usage; never call a sender."""
    session.verify()
    operations = session.root/'operations'
    intents = {digest(p.read_bytes()):read(p) for p in sorted(operations.glob('*-intent.json'))}
    model = {pin:value for pin,value in intents.items() if value['kind']=='model'}
    attempts = [read(p) for p in sorted(operations.glob('attempt-*.json'))]
    provider = router_for(session, 'OFFLINE_NO_SEND').reviewer
    summary = dict(actual_attempts=len(attempts), completed_calls=0, failed_calls=0,
        known_usage_calls=0, unknown_usage_calls=0, known_tokens=0, unknown_reserved_tokens=0,
        http_requests_known=0, http_requests_unknown=0, receiptless_calls=0, not_sent=0)
    seen = set()
    for ordinal, attempt in enumerate(attempts,1):
        pin = attempt['intent_sha256']
        if pin not in model or pin in seen or attempt['ordinal'] != ordinal:
            raise ValueError('original15_original_attempt_binding')
        seen.add(pin)
        intent = model[pin]
        value = read(operations/f"{intent['ordinal']:04d}-result.json")['value']
        request = request_from_raw(attempt['issued_raw'])
        if contract.role_for_request(request) != 'review':
            raise ValueError('original15_unexpected_generation')
        before = attempt['budget_before']
        if (before['calls'] != ordinal-1 or before['tokens'] != summary['known_tokens']
                or before['reserved_tokens'] != summary['unknown_reserved_tokens']):
            raise ValueError('original15_original_budget_prefix')
        folder = session.transport_root/'review'/f'call-{ordinal:03d}'
        receipt = read(folder/'receipt.json')
        observation = read(folder/'observation/observation.json')
        business = visible(json_value(request)); context = request.metadata[contract.CONTEXT]
        if (receipt.get('request_sha256') != object_digest(business)
                or receipt.get('wire_sha256') != object_digest(build_wire(business))
                or receipt.get('validation_context_sha256') != object_digest(context)
                or receipt.get('profile') != asdict(provider.profile)
                or receipt.get('response_mode') != provider.response_mode
                or read(folder/'request.json') != business or read(folder/'validation-context.json') != context
                or read(folder/'profile.json') != provider.expected_profile(request)
                or read(session.transport_root/f'call-{ordinal:03d}.json') != dict(ordinal=ordinal,
                    role='review',provider=provider.provider_name,model=provider.model_name,
                    request_sha256=contract.request_sha(request),state='reserved_before_io')):
            raise ValueError('original15_original_receipt_binding')
        http = observation.get('http_requests')
        if type(http) is int and http in (0,1):
            summary['http_requests_known'] += http
            summary['not_sent'] += int(http == 0)
        else:
            summary['http_requests_unknown'] += 1
        if receipt.get('http_requests') != http:
            raise ValueError('original15_original_http_disagreement')
        if value.get('ok') is True:
            recovered, _, _ = recover_success(session.transport_root,intent,attempt,contract_module=contract)
            if (json.loads(recovered['response_raw']) != json.loads(value['response_raw'])
                    or recovered['issued_raw'] != value['issued_raw']
                    or recovered['receipt_request_sha256'] != value['receipt_request_sha256']):
                raise ValueError('original15_original_response_changed')
            response = RESPONSE.validate_json(value['response_raw'])
            usage = response.usage.input_tokens + response.usage.output_tokens
            summary['completed_calls'] += 1
        else:
            error = ProviderResponseError(provider=value['error_provider'],code=value['error_code'])
            provider.last_failure = (dict(error=error,request=request,directory=folder,
                inventory=transport_inventory(session.transport_root),receipt_sha256=digest((folder/'receipt.json').read_bytes()))
                if receipt.get('ok') is False else None)
            known = provider.failure_usage(error, request)
            usage = known['total_tokens'] if known is not None else None
            summary['failed_calls'] += 1
            for name, predicate in (('reaped_timeout',provider.retryable),
                                    ('recoverable_format',provider.recoverable_format)):
                if name in value and (not predicate(error,request) or value[name] != dict(role='review',
                        ordinal=ordinal,issued_raw=attempt['issued_raw'],
                        receipt_sha256=digest((folder/'receipt.json').read_bytes()))):
                    raise ValueError('original15_original_retry_classification')
        if usage is None:
            summary['unknown_usage_calls'] += 1
            summary['unknown_reserved_tokens'] += estimate_runtime_request_input_ceiling(request)+request.max_tokens
        else:
            summary['known_usage_calls'] += 1
            summary['known_tokens'] += usage
        budget = value['budget']
        if (budget['calls'] != ordinal or budget['tokens'] != summary['known_tokens']
                or budget['reserved_tokens'] != summary['unknown_reserved_tokens']):
            raise ValueError('original15_original_usage_disagreement')
    # A pre-provider budget failure may leave a committed model operation with
    # no attempt, but it cannot manufacture usage, a response or a retry.
    for pin in set(model)-seen:
        intent = model[pin]
        value = read(operations/f"{intent['ordinal']:04d}-result.json")['value']
        if (value.get('ok') is not False or value.get('error_code') not in
                ('external_call_budget_exhausted','timeout','token_budget_exhausted')):
            raise ValueError('original15_original_attempt_missing')
    if set(p.name for p in (session.transport_root/'review').glob('call-*')) != {
            f'call-{i:03d}' for i in range(1,len(attempts)+1)}:
        raise ValueError('original15_unaccounted_transport')
    budget = engine.last_budget(session)
    if (budget['calls'] != len(attempts) or budget['tokens'] != summary['known_tokens']
            or budget['reserved_tokens'] != summary['unknown_reserved_tokens']):
        raise ValueError('original15_final_usage_disagreement')
    return summary


def replay_case(plan, pin, events, key, roots, authorization_sha):
    operator = Path(plan['operator'])
    before = evidence_inventory(plan), inventory(operator.with_name(operator.name+'-authors'))
    session, gate = open_case(plan, pin, events, key, authorization_sha=authorization_sha,
        read_only=True, **roots_for(roots, key))
    with session:
        terminal = read(session.root/'terminal.json')
        launch = read(session.root/'launch.json')
        if (launch['plan_sha256'] != pin or launch['authorization_sha256'] != authorization_sha
                or digest((session.root/'authorization.json').read_bytes()) != authorization_sha):
            raise ValueError('original15_replay_launch_changed')
        verify_preflight(plan, pin, events, launch['native_preflight'])
        decisions = [gate.native.replay(h) for h in gate.handles()]
        def deny(*args, **kwargs):
            raise AssertionError('original15_replay_provider_forbidden')
        semantic_stop = terminal.get('reason') == 'semantic_rejected'
        if semantic_stop:
            handles = list(gate.handles())
            last = read(sorted((session.root/'operations').glob('*-intent.json'))[-1])
            if (not decisions or decisions[-1] is not False or not all(decisions[:-1])
                    or handles[-1]['binding']['key'] != terminal['key']
                    or last['kind'] != 'host-task' or last['request']['key'] != terminal['key']):
                raise ValueError('original15_replay_rejection_frontier')
            result = dict(reason='session_semantic_rejected', key=key)
        else:
            try:
                result = engine.run_case(session, router_for(session, 'OFFLINE_NO_SEND', deny))
            except (Exception, SessionBlocked) as error:
                stop = terminal.get('value', {})
                if (stop.get('reason') != 'case_execution_failed' or stop.get('error_type') != type(error).__name__
                        or stop.get('error_code') != getattr(error, 'code', None)
                        or stop.get('stop_code') != safe_code(error)):
                    raise ValueError('original15_replay_first_stop_changed') from None
                result = dict(reason='case_execution_failed', stop_code=safe_code(error))
            else:
                if terminal.get('value', {}).get('result') != result:
                    raise ValueError('original15_replay_result_changed')
            if session.cursor != session.status()['operations']:
                raise ValueError('original15_replay_unconsumed_operations')
        accounting = engine.last_budget(session)
        transport = audit_transport(session)
    if before != (evidence_inventory(plan), inventory(operator.with_name(operator.name+'-authors'))):
        raise ValueError('original15_replay_changed_originals')
    return dict(strict_replay=True, result=result, native_reviews=len(decisions),
        accounting={k:accounting[k] for k in ('calls', 'tokens', 'reserved_tokens', 'retries')},
        transport=transport)


def frontier(plan, pin, events, roots, authorization_sha):
    rows = plan['coverage']['cases']
    keys = [row['key'] for row in rows]
    if set(roots)-set(keys):
        raise ValueError('original15_unknown_case_roots')
    completed = []
    operator = Path(plan['operator'])
    for row in rows:
        key = row['key']
        folder = operator/'cases'/engine.case_slug(key)
        if not folder.exists():
            if key in roots:
                raise ValueError('original15_roots_without_case')
            next_key = key
            break
        roots_for(roots, key)
        if not (folder/'session/terminal.json').exists():
            next_key = key
            break
        result = replay_case(plan, pin, events, key, roots, authorization_sha)
        completed.append(result)
        if result['result'].get('matched') is not True:
            next_key = None
            break
    else:
        next_key = None
    allowed = {engine.case_slug(r['result']['key']) for r in completed if 'key' in r['result']}
    if next_key:
        allowed.add(engine.case_slug(next_key))
    # Failed/rejected case still belongs to the verified prefix.
    allowed.update(engine.case_slug(row['key']) for row in rows[:len(completed)])
    actual = {p.name for p in (operator/'cases').iterdir()} if (operator/'cases').exists() else set()
    if actual-allowed or set(roots)-{row['key'] for row in rows[:len(completed)+(1 if next_key else 0)]}:
        raise ValueError('original15_nonsequential_case_evidence')
    return dict(next_key=next_key, completed=completed,
        accounting={field:sum(r['accounting'][field] for r in completed)
            for field in ('calls','tokens','reserved_tokens','retries')},
        all_cases_matched=len(completed)==15 and all(r['result'].get('matched') is True for r in completed),
        qualified=False, publication_allowed=False)


def seal(plan,pin,events,roots,authorization_sha,roots_sha):
    operator=Path(plan['operator'])
    if (operator/'seal.json').exists():
        raise ValueError('original15_seal_already_exists')
    value=frontier(plan,pin,events,roots,authorization_sha)
    if value['next_key'] is not None:
        raise ValueError('original15_unfinished_frontier_no_seal')
    write_new_json(operator/'seal.json',dict(version=VERSION+'-seal',plan_sha256=pin,
        original_roots=roots,roots_file_sha256=roots_sha,inventory=evidence_inventory(plan),
        result=value,qualified=False,publication_allowed=False))
    return dict(**value,seal_sha256=digest((operator/'seal.json').read_bytes()))


def safe_code(error):
    value = str(error)
    return value if re.fullmatch(r'(original15|session)_[a-z0-9_]+', value) else type(error).__name__


def execute(plan, pin, events, key, roots, *, authorization_file, authorization_sha,
            ci_run, preflight, manual_retry=False, host_only=False):
    raw = Path(authorization_file).read_bytes()
    if digest(raw) != authorization_sha:
        raise ValueError('original15_original_authorization_required')
    grant = json.loads(raw)
    validate_grant(grant, plan, pin)
    load(plan['operator'], pin, frozen=True)
    ci = verify_ci(ci_run, plan['head'])
    verify_native_principals(events.client, plan['review_plan'])
    verify_preflight(plan, pin, events, preflight)
    prefix = frontier(plan, pin, events, roots, authorization_sha)
    if prefix['next_key'] != key or (Path(plan['operator'])/'seal.json').exists():
        raise ValueError('original15_current_case_only')

    def before():
        validate_grant(grant, plan, pin)
        if Path(authorization_file).read_bytes() != raw:
            raise SessionBlocked('original15_authorization_changed')
        load(plan['operator'], pin, frozen=True)
        verify_native_principals(events.client, plan['review_plan'])
        verify_preflight(plan, pin, events, preflight)
        keys = [row['key'] for row in plan['coverage']['cases']]
        for previous in keys[:keys.index(key)]:
            if replay_case(plan,pin,events,previous,roots,authorization_sha)['result'].get('matched') is not True:
                raise SessionBlocked('original15_prefix_changed')
        if any((Path(plan['operator'])/'cases'/engine.case_slug(future)).exists()
               for future in keys[keys.index(key)+1:]):
            raise SessionBlocked('original15_nonsequential_case_evidence')

    existing = (Path(plan['operator'])/'cases'/engine.case_slug(key)).exists()
    selected_roots = roots_for(roots, key) if existing else {}
    session, gate = open_case(plan, pin, events, key, authorization_sha=authorization_sha,
        before=before, manual_retry=manual_retry, sink=base.emit, **selected_roots)
    try:
        with session:
            launch = dict(plan_sha256=pin, authorization_sha256=authorization_sha, ci=ci, native_preflight=preflight)
            if not existing:
                if manual_retry:
                    raise SessionBlocked('original15_retry_requires_failed_attempt')
                with (session.root/'authorization.json').open('xb') as stream:
                    stream.write(raw)
                write_new_json(session.root/'launch.json', launch)
                session._checkpoint('launcher_verified')
            elif read(session.root/'launch.json') != launch or (session.root/'authorization.json').read_bytes() != raw:
                raise SessionBlocked('original15_original_launch_controls_changed')
            status = session.status()
            if status['closed'] or status['unresolved']:
                raise SessionBlocked('original15_closed_or_unresolved_no_send')
            waiting = status['timeout_waiting'] or status['format_waiting']
            if manual_retry and not waiting:
                raise SessionBlocked('original15_retry_requires_failed_attempt')
            if waiting and not manual_retry:
                raise SessionPaused('original15_awaiting_manual_retry')
            gate.verify_prior()
            # Replay/Host-only work first. Prompt only at a genuinely new send.
            session.max_new_models = 0
            def deny(*args, **kwargs):
                raise AssertionError('original15_offline_frontier_provider_forbidden')
            try:
                result = advance_case(session, router_for(session, 'OFFLINE_NO_SEND', deny))
            except SessionPaused as error:
                if str(error) != 'session_model_boundary' or host_only:
                    raise
                with session.waiting_for_credentials():
                    _, api_key = base.continuation_credentials(reviewer_group=contract.REVIEW_PROFILE.group)
                before()
                session.cursor = 0
                session.max_new_models = None
                try:
                    result = advance_case(session, router_for(session, api_key))
                finally:
                    api_key = None
            session.close(dict(result=result))
            return dict(phase='case_closed', result=result, publication_allowed=False)
    except SessionPaused as error:
        return dict(phase='paused', reason=str(error), key=key, publication_allowed=False)
    except (Exception, SessionBlocked) as error:
        # Do not manufacture closure for pending/unreconciled work or overwrite
        # a native semantic rejection. The preserved frontier remains authority.
        return dict(phase='stopped', reason=safe_code(error), key=key,
            error_type=type(error).__name__, publication_allowed=False)


def advance_case(session, router):
    try:
        return engine.run_case(session, router)
    except (Exception, SessionBlocked) as error:
        status = session.status()
        if (not status['closed'] and not status['unresolved']
                and session.cursor == status['operations']):
            session.close(dict(reason='case_execution_failed',error_type=type(error).__name__,
                error_code=getattr(error,'code',None),stop_code=safe_code(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','native-task','task','submit','status','run','reconcile','replay','seal'))
    parser.add_argument('--operator', type=Path, required=True)
    parser.add_argument('--plan-sha')
    parser.add_argument('--primary')
    parser.add_argument('--independent')
    parser.add_argument('--case')
    parser.add_argument('--roots-file', type=Path)
    parser.add_argument('--roots-sha')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--preflight-proof', type=Path)
    parser.add_argument('--guard-sha')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--authorization-file', type=Path)
    parser.add_argument('--authorization-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--manual-retry', action='store_true')
    parser.add_argument('--host-only', action='store_true')
    parser.add_argument('--key')
    parser.add_argument('--primary-file', type=Path)
    parser.add_argument('--event-id')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.primary or not args.independent:
            parser.error('prepare requires primary and independent')
        base.emit(prepare(args.operator,args.primary,args.independent)); return
    plan = load(args.operator, args.plan_sha, frozen=args.action in ('native-task','run'))
    roots = {}
    if args.roots_file is not None:
        if digest(args.roots_file.read_bytes()) != args.roots_sha:
            raise ValueError('original15_original_roots_file_required')
        roots = read(args.roots_file)
    with base.host(plan) as events:
        if args.action == 'native-task':
            value = native_task(plan,args.plan_sha,events)
        elif args.action == 'run':
            value = execute(plan,args.plan_sha,events,args.case,roots,
                authorization_file=args.authorization_file,authorization_sha=args.authorization_sha,
                ci_run=args.ci_run,preflight=read(args.preflight_proof),
                manual_retry=args.manual_retry,host_only=args.host_only)
        elif args.action in ('replay','seal'):
            if args.action == 'seal':
                value=seal(plan,args.plan_sha,events,roots,args.authorization_sha,args.roots_sha)
            else:
                value = frontier(plan,args.plan_sha,events,roots,args.authorization_sha)
        else:
            key=args.case or plan['coverage']['cases'][0]['key']
            if not args.guard_sha or not args.checkpoint_sha:
                parser.error('existing case requires preserved guard and checkpoint SHA')
            session,gate=open_case(plan,args.plan_sha,events,key,preflight=args.preflight,
                authorization_sha=args.authorization_sha,guard=args.guard_sha,checkpoint=args.checkpoint_sha,
                read_only=args.action in ('task','status'),reconcile=args.action=='reconcile',sink=base.emit)
            with session:
                if args.action=='task':
                    handle=list(gate.handles())[-1]
                    if (Path(handle['folder'])/'submission.json').exists():
                        raise ValueError('original15_task_already_submitted')
                    print((Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8'),end=''); return
                if args.action=='submit':
                    value=dict(accepted=gate.submit(args.key,read(args.primary_file),args.event_id),provider_requests=0)
                elif args.action=='reconcile':
                    gate.verify_prior()
                    value=session.reconcile_completed()
                else:
                    gate.verify_prior()
                    value=session.status()
        base.emit(value)


if __name__=='__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt, SessionBlocked, SessionPaused) as error:
        base.emit(dict(ok=False,code=safe_code(error),error_type=type(error).__name__,publication_allowed=False))
        raise SystemExit(1) from None
