"""Explicit diagnostic continuation; prepare/native/status/replay never load keys.

The run action requires a separate pinned, unexpired grant and exact-head CI.
It resumes original evidence; it does not launch generation or qualify a product.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from app.evaluation import completion_diagnostic_session as engine
from app.evaluation import sol_completion_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, canonical, digest
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider
from scripts import sol_natural_launch as base
from scripts.prepare_completion_diagnostic import NoGenerationProvider
from scripts.reviewer_profile_batch import inventory
from scripts.review_completion_necessity_candidate import PACKAGE
from scripts.run_natural_duty_development import current_head, verify_ci
from scripts.run_boundary_examples_v2 import verify_native_principals

VERSION = 'completion-diagnostic-launch-v1'
ENVELOPE = dict(max_new_attempts=10, max_new_tokens=803840,
    cumulative_max_calls=14, cumulative_max_tokens=870431,
    cumulative_active_seconds=3600, manual_retries=4, generation_requests=0)


def source():
    return dict(runtime=base.source(), controls=inventory(PACKAGE),
                contract=contract.CONTRACT.snapshot().model_dump(mode='json'))


def prepare(operator, proof_file, proof_sha):
    operator = Path(operator).absolute()
    spec = engine.parent_binding(proof_file, proof_sha)
    parent = Path(spec['proof']['parent_operator'])
    if (operator.resolve() != operator or operator.exists()
            or any(operator.is_relative_to(p) or p.is_relative_to(operator)
                   for p in (contract.ROOT, parent, parent.with_name(parent.name+'-authors')))):
        raise ValueError('completion_new_external_operator_required')
    if Path(sys.executable).resolve() != Path(engine.read(parent/'plan.json')['python']).resolve():
        raise ValueError('completion_actual_python_required')
    descriptor = contract.CONTRACT.descriptor()
    if (descriptor['max_calls'], descriptor['total_tokens'], descriptor['execution_timeout_s'],
            descriptor['transport_retries']) != (14, 870431, 3600, 4):
        raise ValueError('completion_envelope_contract_changed')
    plan = dict(version=VERSION, operator=str(operator), cwd=str(contract.ROOT.resolve()),
        python=str(Path(sys.executable).resolve()), codex=str(base.CODEX.resolve()),
        head=current_head(), source=source(), proof_file=str(Path(proof_file).resolve()),
        proof_sha256=proof_sha, review_plan=engine.read(parent/'plan.json')['review_plan'],
        limits=ENVELOPE, estimated_additional_uncached_cny=0.7296,
        review_profile=dict(group=contract.REVIEW_PROFILE.group,route=contract.REVIEW_PROFILE.route,
            model=contract.REVIEW_MODEL,reasoning_effort='high',request_timeout_s=300,
            max_input_tokens=64000,max_output_tokens=16384,
            input_cny_per_million='0.5',output_cny_per_million='2.5'),
        historical_accounting=spec['proof']['strict_parent_replay']['accounting'],
        sequence=['control-b','control-c','control-d','completion-initial','compatibility',
                  'edit','unique-application','facts-fresh','completion-fresh'],
        execution_authorized=False, qualified=False, publication_allowed=False)
    operator.mkdir(parents=True, exist_ok=False)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=digest((operator/'plan.json').read_bytes()), provider_requests=0, key_reads=0)


def load(operator, pin, *, frozen=False):
    operator = Path(operator).resolve()
    if digest((operator/'plan.json').read_bytes()) != pin:
        raise ValueError('completion_original_plan_required')
    plan = engine.read(operator/'plan.json')
    if (plan['version'] != VERSION or plan['operator'] != str(operator)
            or Path.cwd().resolve() != Path(plan['cwd']) or Path(plan['cwd']) != contract.ROOT.resolve()
            or plan['python'] != str(Path(sys.executable).resolve())
            or plan['codex'] != str(base.CODEX.resolve()) or plan['limits'] != ENVELOPE):
        raise ValueError('completion_actual_launch_binding')
    spec = engine.parent_binding(plan['proof_file'], plan['proof_sha256'])
    if engine.read(Path(spec['proof']['parent_operator'])/'plan.json')['review_plan'] != plan['review_plan']:
        raise ValueError('completion_review_plan_changed')
    if frozen and (current_head() != plan['head'] or source() != plan['source']):
        raise ValueError('completion_frozen_source_changed')
    return plan, spec


def grant_binding(plan, pin):
    return dict(version=VERSION+'-authorization', plan_sha256=pin, head=plan['head'],
        parent_proof_sha256=plan['proof_sha256'], limits=ENVELOPE,
        estimated_additional_uncached_cny=plan['estimated_additional_uncached_cny'],
        production_admitted=False)


def validate_grant(value, plan, pin, *, now=None):
    now = now or datetime.now(timezone.utc)
    issued, expires = (datetime.fromisoformat(value[k]) for k in ('issued_at','expires_at'))
    if (any(value.get(k) != v for k,v in grant_binding(plan,pin).items())
            or issued.utcoffset() is None or expires.utcoffset() is None
            or not issued <= now < expires or not timedelta(0) < expires-issued <= timedelta(days=1)
            or not isinstance(value.get('user_authorization_evidence'), str)
            or not value['user_authorization_evidence'].strip()):
        raise ValueError('completion_specific_unexpired_authorization_required')


def session_for(plan, pin, events, *, preflight=False, authorization_sha=None, **kwargs):
    _, spec = load(plan['operator'], pin)
    operator = Path(plan['operator'])
    return engine.open_session(operator/('native-preflight' if preflight else 'execution'), spec, events,
        author_root=operator.with_name(operator.name+'-authors'), evidence_root=operator,
        control_binding=dict(plan_sha256=pin, authorization_sha256=authorization_sha, preflight=preflight),
        **kwargs)


def native_task(plan, pin, events):
    verify_native_principals(events.client, plan['review_plan'])
    session, gate = session_for(plan,pin,events,preflight=True,before_new_model=None,sink=base.emit)
    try:
        with session:
            gate.require('startup-preflight','opinion',dict(fixture_only=True,
                administrative_preflight=True, responses=[],
                report='Administrative author/check-answer/native import preflight; zero provider requests.',
                instructions='Administrative scope only; no candidate semantic approval.'),
                'Administrative author/check-answer/native import preflight; zero provider requests.')
    except SessionPaused:
        pass
    return dict(provider_requests=0,key_reads=0)


def verify_preflight(plan,pin,events,proof):
    session,gate=session_for(plan,pin,events,preflight=True,before_new_model=None,read_only=True,
        guard=proof['guard_sha256'],checkpoint=proof['checkpoint_sha256'])
    with session:
        handles=list(gate.handles())
        if len(handles)!=1 or handles[0]['binding']['key']!='startup-preflight' or not gate.native.replay(handles[0]):
            raise ValueError('completion_live_native_preflight_required')


def router_for(session,key,sender=None):
    kwargs={} if sender is None else dict(sender=sender)
    return SolNaturalProvider(NoGenerationProvider(),SolReviewProvider(api_key=key,
        directory=session.transport_root/'review',task_directory=session.transport_root,
        contract_module=contract,**kwargs),contract_module=contract)


def execute(plan,pin,events,*,authorization_file,authorization_sha,ci_run,preflight,
            guard=None,checkpoint=None,manual_retry=False):
    raw=Path(authorization_file).read_bytes()
    if digest(raw)!=authorization_sha:
        raise ValueError('completion_original_authorization_required')
    grant=json.loads(raw)

    def before():
        validate_grant(grant,plan,pin)
        if Path(authorization_file).read_bytes()!=raw:
            raise SessionBlocked('completion_authorization_changed')
        load(plan['operator'],pin,frozen=True)
        verify_preflight(plan,pin,events,preflight)
        verify_native_principals(events.client,plan['review_plan'])

    before()
    ci=verify_ci(ci_run,plan['head'])
    session,gate=session_for(plan,pin,events,before_new_model=before,guard=guard,checkpoint=checkpoint,
        authorization_sha=authorization_sha,manual_retry=manual_retry,sink=base.emit)
    try:
        with session:
            launch=dict(plan_sha256=pin,authorization_sha256=authorization_sha,ci=ci,native_preflight=preflight)
            if guard is None:
                with (session.root/'authorization.json').open('xb') as stream:
                    stream.write(raw)
                write_new_json(session.root/'launch.json',launch)
                session._checkpoint('launcher_verified')
            elif (engine.read(session.root/'launch.json')!=launch
                    or (session.root/'authorization.json').read_bytes()!=raw):
                raise SessionBlocked('completion_original_launch_controls_changed')
            engine.import_parent(session)
            status=session.status()
            if status['closed'] or status['unresolved']:
                raise SessionBlocked('completion_closed_or_unresolved_no_send')
            if manual_retry and not (status['timeout_waiting'] or status['format_waiting']):
                raise SessionBlocked('completion_manual_retry_requires_paused_failure')
            if (status['timeout_waiting'] or status['format_waiting']) and not manual_retry:
                raise SessionPaused('completion_awaiting_manual_retry')
            handles=list(gate.handles())
            if handles and not (Path(handles[-1]['folder'])/'submission.json').exists():
                raise SessionPaused('session_awaiting_native_review')
            gate.verify_prior()
            with session.waiting_for_credentials():
                _,key=base.continuation_credentials(reviewer_group=contract.REVIEW_PROFILE.group)
            before()
            try:
                result=engine.run_chain(session,router_for(session,key))
            except SessionBlocked as error:
                # A true semantic/identity/integrity rejection is retained, never retried.
                session.close(dict(reason=str(error),publication_allowed=False))
                return dict(phase='closed',reason=str(error),publication_allowed=False)
            except Exception as error:
                session.close(dict(reason='completion_execution_failed',error_type=type(error).__name__,
                                   error_code=getattr(error,'code',None),
                                   publication_allowed=False))
                return dict(phase='closed',reason='completion_execution_failed',publication_allowed=False)
            session.close(dict(result=result,publication_allowed=False))
    except SessionPaused as error:
        return dict(phase='paused',reason=str(error),publication_allowed=False)
    return dict(phase='closed',outcome=result['outcome'],accounting=result['accounting'],publication_allowed=False)


def replay(plan,pin,events,*,guard,checkpoint,authorization_sha):
    operator=Path(plan['operator'])
    before=inventory(operator),inventory(operator.with_name(operator.name+'-authors'))
    session,gate=session_for(plan,pin,events,before_new_model=None,read_only=True,guard=guard,
        checkpoint=checkpoint,authorization_sha=authorization_sha)
    with session:
        terminal=engine.read(session.root/'terminal.json')
        launch=engine.read(session.root/'launch.json')
        if (launch['plan_sha256']!=pin or launch['authorization_sha256']!=authorization_sha
                or digest((session.root/'authorization.json').read_bytes())!=authorization_sha):
            raise ValueError('completion_replay_launch_controls_changed')
        verify_preflight(plan,pin,events,launch['native_preflight'])
        decisions=[gate.native.replay(h) for h in gate.handles()]
        def deny(*args,**kwargs):
            raise AssertionError('completion_replay_provider_forbidden')
        semantic_stop=terminal.get('reason')=='semantic_rejected'
        if semantic_stop:
            last_intent=engine.read(sorted((session.root/'operations').glob('*-intent.json'))[-1])
            if (not decisions or decisions[-1] is not False or not all(decisions[:-1])
                    or terminal['key']!=list(gate.handles())[-1]['binding']['key']
                    or last_intent['kind']!='host-task' or last_intent['request']['key']!=terminal['key']):
                raise ValueError('completion_replay_rejection_missing')
            result=dict(reason='session_semantic_rejected',key=terminal['key'])
        try:
            if semantic_stop:
                raise SessionBlocked('session_semantic_rejected')
            result=engine.run_chain(session,router_for(session,'OFFLINE_NO_SEND',deny))
        except SessionBlocked as error:
            expected=terminal.get('value',{}).get('reason')
            if terminal.get('reason')=='semantic_rejected':
                expected='session_semantic_rejected'
            if str(error)!=expected:
                raise ValueError('completion_replay_first_stop_changed') from None
            if not semantic_stop:
                result=dict(reason=str(error))
        except Exception as error:
            value=terminal.get('value',{})
            if (value.get('reason')!='completion_execution_failed' or value.get('error_type')!=type(error).__name__
                    or value.get('error_code')!=getattr(error,'code',None)):
                raise ValueError('completion_replay_failure_changed') from None
            result=dict(reason=value['reason'],error_type=type(error).__name__)
        else:
            if terminal.get('value',{}).get('result')!=result:
                raise ValueError('completion_replay_result_changed')
        if not semantic_stop and session.cursor!=session.status()['operations']:
            raise ValueError('completion_replay_unconsumed_operations')
        budgets=[engine.read(p)['value']['budget'] for p in sorted((session.root/'operations').glob('*-result.json'))
                 if isinstance(engine.read(p)['value'],dict) and 'budget' in engine.read(p)['value']]
        budget=budgets[-1] if len(budgets)>1 else session.completion_parent['proof']['historical_budget']
    if before!=(inventory(operator),inventory(operator.with_name(operator.name+'-authors'))):
        raise ValueError('completion_replay_changed_originals')
    return dict(strict_replay=True,replay_mode='native-rejection-frontier' if semantic_stop else 'full-workflow',
        result=result,native_reviews=len(decisions),
        accounting={k:budget[k] for k in ('calls','tokens','reserved_tokens','retries')},publication_allowed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','native-task','task','submit','status','run','replay','seal'))
    parser.add_argument('--operator',type=Path,required=True)
    parser.add_argument('--plan-sha')
    parser.add_argument('--proof',type=Path)
    parser.add_argument('--proof-sha')
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--guard-sha')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--authorization-file',type=Path)
    parser.add_argument('--authorization-sha')
    parser.add_argument('--preflight-proof',type=Path)
    parser.add_argument('--ci-run')
    parser.add_argument('--manual-retry',action='store_true')
    parser.add_argument('--key')
    parser.add_argument('--primary-file',type=Path)
    parser.add_argument('--event-id')
    args=parser.parse_args()
    if args.action=='prepare':
        base.emit(prepare(args.operator,args.proof,args.proof_sha)); return
    plan,_=load(args.operator,args.plan_sha,frozen=args.action=='run')
    roots=dict(guard=args.guard_sha,checkpoint=args.checkpoint_sha,authorization_sha=args.authorization_sha)
    with base.host(plan) as events:
        if args.action=='native-task':
            value=native_task(plan,args.plan_sha,events)
        elif args.action=='run':
            value=execute(plan,args.plan_sha,events,authorization_file=args.authorization_file,
                ci_run=args.ci_run,preflight=engine.read(args.preflight_proof),manual_retry=args.manual_retry,**roots)
        elif args.action in ('replay','seal'):
            if args.action=='seal' and (args.operator/'seal.json').exists():
                raise ValueError('completion_seal_already_exists')
            value=replay(plan,args.plan_sha,events,**roots)
            if args.action=='seal':
                write_new_json(args.operator/'seal.json',dict(version=VERSION+'-seal',plan_sha256=args.plan_sha,
                    original_roots=roots,inventory=inventory(args.operator),result=value))
                value=dict(**value,seal_sha256=digest((args.operator/'seal.json').read_bytes()))
        else:
            session,gate=session_for(plan,args.plan_sha,events,preflight=args.preflight,
                before_new_model=None,read_only=args.action in ('task','status'),**roots)
            with session:
                if args.action=='status':
                    value=session.status()
                elif args.action=='submit':
                    value=dict(accepted=gate.submit(args.key,engine.read(args.primary_file),args.event_id))
                else:
                    handle=list(gate.handles())[-1]
                    if (Path(handle['folder'])/'submission.json').exists():
                        raise ValueError('completion_task_already_submitted')
                    print((Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8')); return
    base.emit(value)


if __name__=='__main__':
    main()
