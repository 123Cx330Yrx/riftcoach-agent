"""Continue only the two unstarted original15 cases above immutable seals.

Uses the existing fixed-report workflow, transport and native review gate.
Successful parent calls are evidence, never a new execution queue.
"""
import argparse
import sys
from pathlib import Path

from app.evaluation import sol_original15_session as engine, sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, canonical, digest
from scripts import original15_patch_recovery_launch as recovery, sol_original15_launch as original
from scripts import sol_natural_launch as base, windows_reviewer_credentials as credentials
from scripts.reviewer_profile_batch import inventory
from scripts.reviewer_profile_batch import ExactNativeGate
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_natural_duty_development import current_head, verify_ci

VERSION = 'original15-sealed-remaining-two-v1'
KEYS = ['observed:4', 'observed:5']
FIELDS = ('calls', 'tokens', 'reserved_tokens', 'retries')


def read(path):
    return original.read(path)


def source():
    value = recovery.source()
    value['scripts/original15_remaining_launch.py'] = digest(Path(__file__).read_bytes())
    return value


def verify_parents(plan):
    """Reuse sealed acceptance, verifying bytes rather than rerunning old trials."""
    parent = Path(plan['parent_recovery'])
    old = recovery.pinned(parent/'plan.json', plan['parent_recovery_plan_sha256'])
    seal = recovery.pinned(parent/'seal.json', plan['parent_recovery_seal_sha256'])
    recovery.engine.binding(old['proof_file'], old['proof_sha256'])
    actual = inventory(parent)
    if (seal['plan_sha256'] != plan['parent_recovery_plan_sha256']
            or seal['inventory'] != {k:v for k,v in actual.items() if k != 'seal.json'}
            or actual != plan['parent_recovery_inventory']
            or inventory(parent.with_name(parent.name+'-authors')) != plan['parent_recovery_author_inventory']
            or seal['result']['strict_replay'] is not True
            or seal['result']['result'].get('matched') is not True
            or seal['result']['result']['key'] != 'observed:3'
            or plan['historical_accounting'] != seal['result']['result']['cumulative_batch_accounting']):
        raise ValueError('original15_remaining_parent_changed')
    roots = plan['parent_recovery_roots']
    guard = recovery.pinned(parent/'execution/session/guard.json', roots['guard_sha256'])
    checkpoint = recovery.pinned(roots['checkpoint'], roots['checkpoint_sha256'])
    terminal = read(parent/'execution/session/terminal.json')
    if (guard['binding']['control_binding']['plan_sha256'] != plan['parent_recovery_plan_sha256']
            or checkpoint['guard_sha256'] != roots['guard_sha256']
            or checkpoint['inventory'].get('session',{}).get('terminal.json') != digest((parent/'execution/session/terminal.json').read_bytes())
            or terminal.get('value',{}).get('result') != seal['result']['result']):
        raise ValueError('original15_remaining_parent_roots_changed')
    original_parent = Path(old['parent_operator'])
    original_plan = recovery.pinned(original_parent/'plan.json', old['parent_plan_sha256'])
    if (plan['review_plan'] != old['review_plan'] or plan['limits'] != original.ENVELOPE
            or plan['limits'] != old['limits'] or plan['profile'] != original.profile()
            or plan['contract'] != old['contract']
            or plan['parent_runtime_source'] != old['source']
            or any((original_parent/'cases'/engine.case_slug(k)).exists() for k in KEYS)):
        raise ValueError('original15_remaining_original_scope_changed')
    for key in KEYS:
        cell, _ = engine.case_for(key)
        row = next(r for r in original_plan['coverage']['cases'] if r['key'] == key)
        if (plan['inputs'][key] != {f:cell[f] for f in ('input_sha256','report_sha256')}
                or any(row[f] != cell[f] for f in plan['inputs'][key])):
            raise ValueError('original15_remaining_original_inputs_changed')
    # This is evidence inheritance, not a claim that the old version passed 15.
    return old


def authorization(plan, *, active=True):
    return recovery.validate_authorization(verify_parents(plan), active=active)


def verify_parent_native(plan, events):
    """Re-read accepted inherited/current native originals at their old paths."""
    parent=Path(plan['parent_recovery']);old=verify_parents(plan)
    original_parent=Path(old['parent_operator'])
    gates={}
    for root in (parent,original_parent):
        saved=read(root/'plan.json')
        workspace=HostReviewWorkspace(cwd=saved['cwd'],python=saved['python'],
            answers=root.with_name(root.name+'-authors'),evidence_roots=[root])
        gates[root]=ExactNativeGate(saved['review_plan'],workspace,events)
    for path in sorted((parent/'execution/session/operations').glob('*-intent.json')):
        if read(path)['kind']!='host-task':continue
        handle=read(path.with_name(path.name.replace('-intent','-result')))['value']
        root=original_parent if Path(handle['folder']).is_relative_to(original_parent) else parent
        if gates[root].replay(handle) is not True:
            raise ValueError('original15_remaining_parent_native_changed')


def historical_active(plan):
    parent=Path(plan['parent_recovery']);old=read(parent/'plan.json')
    original_parent=Path(old['parent_operator']);seal=read(original_parent/'seal.json')
    total=0.0
    for key,roots in seal['original_roots'].items():
        folder=original_parent/'cases'/engine.case_slug(key)/'session/checkpoints'
        matches=[p for p in folder.glob('*.json') if digest(p.read_bytes())==roots['checkpoint_sha256']]
        if len(matches)!=1:raise ValueError('original15_remaining_original_time_roots_required')
        if key!='observed:3':total+=read(matches[0])['active_seconds']
    return total+read(plan['parent_recovery_roots']['checkpoint'])['active_seconds']


def prepare(operator, parent, parent_plan_sha, seal_sha, roots):
    operator, parent = Path(operator).absolute(), Path(parent).absolute()
    old = recovery.pinned(parent/'plan.json', parent_plan_sha)
    seal = recovery.pinned(parent/'seal.json', seal_sha)
    forbidden = (parent, parent.with_name(parent.name+'-authors'),
                 Path(old['parent_operator']), contract.ROOT)
    if (operator.resolve() != operator or operator.exists()
            or any(operator.is_relative_to(p) or p.is_relative_to(operator) for p in forbidden)):
        raise ValueError('original15_remaining_new_external_operator_required')
    plan = dict(version=VERSION, operator=str(operator), cwd=str(contract.ROOT.resolve()),
        python=str(Path(sys.executable).resolve()), codex=str(base.CODEX.resolve()),
        head=current_head(), source=source(), parent_runtime_source=old['source'],
        parent_recovery=str(parent), parent_recovery_plan_sha256=parent_plan_sha,
        parent_recovery_seal_sha256=seal_sha, parent_recovery_roots=roots,
        parent_recovery_inventory=inventory(parent),
        parent_recovery_author_inventory=inventory(parent.with_name(parent.name+'-authors')),
        historical_accounting=seal['result']['result']['cumulative_batch_accounting'],
        review_plan=old['review_plan'], limits=old['limits'], profile=original.profile(),
        contract=old['contract'], keys=KEYS, coverage=dict(cases=[dict(key=k) for k in KEYS]),
        inputs={k:{f:engine.case_for(k)[0][f] for f in ('input_sha256','report_sha256')} for k in KEYS},
        stored_key_target=credentials.TARGET, reset_accounting=False, automatic_retry=False,
        qualified=False, publication_allowed=False)
    authorization(plan, active=False)
    plan['historical_active_seconds']=historical_active(plan)
    current = source()
    if any(current.get(k) != v for k,v in old['source'].items()):
        raise ValueError('original15_remaining_runtime_equivalence_required')
    operator.mkdir(parents=True)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=digest((operator/'plan.json').read_bytes()), provider_requests=0, key_reads=0)


def load(operator, pin, *, frozen=False):
    plan = recovery.pinned(Path(operator)/'plan.json', pin)
    if (plan['version'] != VERSION or plan['operator'] != str(Path(operator).absolute())
            or plan['cwd'] != str(contract.ROOT.resolve()) or Path.cwd().resolve() != contract.ROOT.resolve()
            or plan['python'] != str(Path(sys.executable).resolve())
            or plan['codex'] != str(base.CODEX.resolve()) or plan['keys'] != KEYS
            or plan['stored_key_target'] != credentials.TARGET
            or plan['reset_accounting'] is not False or plan['automatic_retry'] is not False
            or plan['qualified'] is not False or plan['publication_allowed'] is not False):
        raise ValueError('original15_remaining_launch_binding_changed')
    authorization(plan, active=False)
    if plan['historical_active_seconds']!=historical_active(plan):
        raise ValueError('original15_remaining_historical_time_changed')
    if frozen and (plan['head'] != current_head() or plan['source'] != source()):
        raise ValueError('original15_remaining_frozen_source_changed')
    return plan


def session_for(plan, pin, events, key, **kwargs):
    old = verify_parents(plan)
    if key not in KEYS:
        raise ValueError('original15_remaining_case_only')
    return engine.open_case(plan['operator'], key, plan['review_plan'], events,
        plan_sha=pin, authorization_sha=old['authorization_sha256'], python=plan['python'], **kwargs)


def replay_case(plan, pin, events, key, roots):
    before = original.evidence_inventory(plan), inventory(Path(plan['operator']+'-authors'))
    session, gate = session_for(plan, pin, events, key, read_only=True, **original.roots_for(roots,key))
    with session:
        terminal = read(session.root/'terminal.json')
        if terminal.get('reason') == 'semantic_rejected':
            handles = list(gate.handles())
            decisions = [gate.native.replay(h) for h in handles]
            if (not decisions or decisions[-1] is not False or not all(decisions[:-1])
                    or handles[-1]['binding']['key'] != terminal['key']):
                raise ValueError('original15_remaining_rejection_changed')
            result = dict(reason='session_semantic_rejected',key=key)
        else:
            gate.verify_prior()
            def deny(*a, **kw):
                raise AssertionError('original15_remaining_replay_no_send')
            result = engine.run_case(session,original.router_for(session,'OFFLINE_NO_SEND',deny))
            if terminal.get('value',{}).get('result') != result or session.cursor != session.status()['operations']:
                raise ValueError('original15_remaining_replay_result_changed')
        transport = original.audit_transport(session)
        budget = engine.last_budget(session)
    if before != (original.evidence_inventory(plan),inventory(Path(plan['operator']+'-authors'))):
        raise ValueError('original15_remaining_replay_changed_evidence')
    return dict(strict_replay=True,result=result,transport=transport,
        accounting={f:budget[f] for f in FIELDS})


def prefix(plan, pin, events, key, roots):
    if key not in KEYS or set(roots)-set(KEYS):
        raise ValueError('original15_remaining_case_only')
    folder = Path(plan['operator'])/'cases'
    if folder.exists() and {p.name for p in folder.iterdir()}-{engine.case_slug(k) for k in KEYS}:
        raise ValueError('original15_remaining_unexpected_case')
    completed = []
    for k in KEYS[:KEYS.index(key)]:
        row = replay_case(plan,pin,events,k,roots)
        if row['result'].get('matched') is not True:
            raise ValueError('original15_remaining_accepted_prefix_required')
        completed.append(row)
    if any((folder/engine.case_slug(k)).exists() for k in KEYS[KEYS.index(key)+1:]):
        raise ValueError('original15_remaining_out_of_order')
    totals={f:plan['historical_accounting'][f]+sum(r['accounting'][f] for r in completed) for f in FIELDS}
    totals['active_seconds']=plan['historical_active_seconds']
    for k in KEYS[:KEYS.index(key)]:
        checkpoints=Path(plan['operator'])/'cases'/engine.case_slug(k)/'session/checkpoints'
        paths=[p for p in checkpoints.glob('*.json') if digest(p.read_bytes())==roots[k]['checkpoint_sha256']]
        if len(paths)!=1:raise ValueError('original15_remaining_preserved_time_root_required')
        totals['active_seconds']+=read(paths[0])['active_seconds']
    return totals


def execute(plan,pin,events,key,roots,*,ci_run,host_only=False,manual_retry=False,
            sink=base.emit,key_reader=None,patch_coordination=None):
    load(plan['operator'],pin,frozen=True)
    if (Path(plan['operator'])/'seal.json').exists():
        raise SessionBlocked('original15_remaining_sealed_no_run')
    verify_native_principals(events.client,plan['review_plan'])
    with recovery.native_view(events) as view:
        prior = prefix(plan,pin,events,key,roots)
        ci = None
        def before():
            view.responses.clear()
            load(plan['operator'],pin,frozen=True)
            authorization(plan)
            verify_native_principals(events.client,plan['review_plan'])
            verify_parent_native(plan,events)
            # Current authors/materials/native events are rechecked at each send.
            session.review_gate.verify_prior()
            budget = engine.last_budget(session)
            status = session.status()
            pending = f'{session.cursor+1:04d}-intent.json'
            own = status['unresolved']==[pending] and read(session.root/'operations'/pending)['kind']=='model'
            limits=plan['limits']
            if (host_only or ci is None or status['closed'] or (status['unresolved'] and not own)
                    or budget['calls']>=limits['max_requests_per_case']
                    or prior['calls']+budget['calls']>=limits['max_requests']
                    or prior['tokens']+prior['reserved_tokens']+budget['tokens']+budget['reserved_tokens']+80384>limits['max_reserved_tokens']
                    or session.active_seconds>=limits['per_case_active_seconds']
                    or prior['active_seconds']+session.active_seconds>=limits['maximum_active_seconds']):
                raise SessionBlocked('original15_remaining_original_budget_required')
        folder=Path(plan['operator'])/'cases'/engine.case_slug(key)
        selected=original.roots_for(roots,key) if folder.exists() else {}
        if not folder.exists() and key in roots:
            raise ValueError('original15_remaining_roots_without_case')
        session,gate=session_for(plan,pin,events,key,before=before,sink=sink,
            manual_retry=manual_retry,**selected)
        try:
            with session:
                controls=dict(plan_sha256=pin,parent_seal_sha256=plan['parent_recovery_seal_sha256'],
                    inherited_accounting=prior)
                if not (session.root/'launch.json').exists():
                    write_new_json(session.root/'launch.json',controls)
                    session._checkpoint('sealed_parent_continuation_bound')
                elif read(session.root/'launch.json')!=controls:
                    raise SessionBlocked('original15_remaining_controls_changed')
                status=session.status()
                if status['closed'] or status['unresolved']:
                    raise SessionBlocked('original15_remaining_closed_or_unresolved_no_send')
                waiting=status['timeout_waiting'] or status['format_waiting']
                if manual_retry and not waiting:
                    raise SessionBlocked('original15_remaining_retry_requires_failure')
                if waiting and not manual_retry:
                    raise SessionPaused('original15_remaining_awaiting_manual_retry')
                session.max_new_models=0
                def deny(*a,**kw):
                    raise AssertionError('original15_remaining_offline_no_send')
                try:
                    result=engine.run_case(session,original.router_for(session,'OFFLINE_NO_SEND',deny),patch_coordination=patch_coordination)
                except SessionPaused as error:
                    if str(error)!='session_model_boundary' or host_only:
                        raise
                    authorization(plan)
                    ci=verify_ci(ci_run,plan['head'])
                    ci_folder=session.root/'ci-checks';ci_folder.mkdir(exist_ok=True)
                    write_new_json(ci_folder/f'{len(list(ci_folder.iterdir()))+1:04d}.json',ci)
                    session._checkpoint('exact_successor_head_ci_verified')
                    before()
                    with session.waiting_for_credentials():
                        api_key=(key_reader or credentials.read_key)()
                    before()
                    session.cursor=0;session.max_new_models=1
                    try:
                        result=engine.run_case(session,original.router_for(session,api_key),patch_coordination=patch_coordination)
                    finally:
                        api_key=None;view.responses.clear()
                session.close(dict(result=result))
                return dict(phase='case_closed',result=result,publication_allowed=False)
        except SessionPaused as error:
            return dict(phase='paused',reason=str(error),key=key,publication_allowed=False)
        except (Exception,SessionBlocked) as error:
            return dict(phase='stopped',reason=original.safe_code(error),error_type=type(error).__name__,key=key,publication_allowed=False)


def replay_batch(plan,pin,events,roots):
    if set(roots)-set(KEYS):raise ValueError('original15_remaining_unknown_roots')
    rows=[];stopped=None
    for key in KEYS:
        folder=Path(plan['operator'])/'cases'/engine.case_slug(key)
        if not folder.exists():
            if key in roots:raise ValueError('original15_remaining_roots_without_case')
            break
        row=replay_case(plan,pin,events,key,roots);rows.append(row)
        if row['result'].get('matched') is not True:
            stopped=key
            break
    used=set(KEYS[:len(rows)])
    folders=Path(plan['operator'])/'cases'
    if (set(roots)!=used or (folders.exists() and {p.name for p in folders.iterdir()}!={engine.case_slug(k) for k in used})):
        raise ValueError('original15_remaining_out_of_order')
    return dict(strict_replay=True,cases=rows,first_stopped_case=stopped,
        complete=len(rows)==2 and stopped is None,terminal_boundary=stopped is not None or len(rows)==2,
        cumulative_accounting={f:plan['historical_accounting'][f]+sum(r['accounting'][f] for r in rows) for f in FIELDS},
        qualified=False,publication_allowed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','task','submit','status','reconcile','replay','seal'))
    for name in ('operator','parent','roots-file','primary-file','choice-file'):
        parser.add_argument('--'+name,type=Path,required=name=='operator')
    for name in ('plan-sha','parent-plan-sha','seal-sha','roots-sha','key','stage','event-id','ci-run','choice-sha'):
        parser.add_argument('--'+name)
    parser.add_argument('--manual-retry',action='store_true')
    parser.add_argument('--host-only',action='store_true')
    args=parser.parse_args()
    roots=recovery.pinned(args.roots_file,args.roots_sha)
    if args.action=='prepare':
        base.emit(prepare(args.operator,args.parent,args.parent_plan_sha,args.seal_sha,roots));return
    plan=load(args.operator,args.plan_sha,frozen=args.action=='run')
    with base.host(plan) as events:
        if args.action=='run':
            choice=original.load_patch_coordination(args.choice_file,args.choice_sha)
            if choice is not None and not (args.operator/'cases'/engine.case_slug(args.key)/'journal/patch-conflicts.json').is_file():
                raise ValueError('original15_patch_conflicts_required')
            value=execute(plan,args.plan_sha,events,args.key,roots,ci_run=args.ci_run,
                manual_retry=args.manual_retry,host_only=args.host_only,patch_coordination=choice)
        elif args.action in ('replay','seal'):
            if args.action=='seal' and (args.operator/'seal.json').exists():
                raise ValueError('original15_remaining_seal_already_exists')
            before=original.evidence_inventory(plan),inventory(Path(plan['operator']+'-authors'))
            with recovery.native_view(events):
                verify_parent_native(plan,events)
                value=replay_batch(plan,args.plan_sha,events,roots)
            if before!=(original.evidence_inventory(plan),inventory(Path(plan['operator']+'-authors'))):
                raise ValueError('original15_remaining_replay_changed_evidence')
            if args.action=='seal':
                if not value['terminal_boundary']:
                    raise ValueError('original15_remaining_unfinished_no_seal')
                write_new_json(args.operator/'seal.json',dict(version=VERSION+'-seal',plan_sha256=args.plan_sha,
                    original_roots=roots,inventory=original.evidence_inventory(plan),
                    author_inventory=inventory(Path(plan['operator']+'-authors')),result=value))
        else:
            with recovery.native_view(events):
                verify_parent_native(plan,events)
                session,gate=session_for(plan,args.plan_sha,events,args.key,
                    read_only=args.action in ('task','status'),reconcile=args.action=='reconcile',
                    sink=base.emit,**original.roots_for(roots,args.key))
                with session:
                    gate.verify_prior()
                    if args.action=='task':
                        handle=list(gate.handles())[-1]
                        if (Path(handle['folder'])/'submission.json').exists():
                            raise ValueError('original15_remaining_task_already_submitted')
                        print((Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8'),end='');return
                    if args.action=='submit':
                        value=dict(accepted=gate.submit(args.stage,read(args.primary_file),args.event_id),provider_requests=0,key_reads=0)
                    elif args.action=='reconcile':
                        value=session.reconcile_completed()
                    else:
                        value=session.status()
        base.emit(value)


if __name__=='__main__':
    try:
        main()
    except (Exception,KeyboardInterrupt,SessionBlocked,SessionPaused) as error:
        base.emit(dict(ok=False,code=original.safe_code(error),error_type=type(error).__name__,publication_allowed=False))
        raise SystemExit(1) from None
