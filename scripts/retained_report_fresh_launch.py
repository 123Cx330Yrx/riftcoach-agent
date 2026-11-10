"""Two fixed-report fresh reviews using the existing session/provider/native gates.

This diagnostic does not resume, qualify or alter the sealed natural workflow.
Administrative operations never read credentials. Each run sends at most one
new request; recoverable failures pause for an explicit same-item retry.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from app.evaluation import sol_review_contract as contract
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from app.evaluation.sol_original15_session import SignalRecorder, last_budget
from app.evaluation.golden_journal import write_new_json
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.sol_session_runtime import SessionBudget, SessionWorkflow
from scripts import sol_original15_launch as original, sol_natural_launch as base
from scripts import windows_reviewer_credentials as credentials
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.review_independence_contract import freeze_v2_identity, MODE_V2, FINAL_POLICY
from scripts.reviewer_profile_batch import inventory
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.run_boundary_examples_v2 import verify_native_principals

ROOT = contract.ROOT
VERSION = 'retained-report-fresh-diagnostic-v1'
LIMITS = dict(logical_reviews=2, max_requests=6, max_reserved_tokens=482304,
              active_seconds=3600, per_request_seconds=300, manual_retries=4)
REPORT = '7fb7e784b3822a8e0ad7d502342a339d853ea59ad09de3715ab65ae4de59ce51'


def read(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.stat().st_nlink != 1:
        raise ValueError('fresh_redirected_file')
    return digest(path.read_bytes())


def source():
    value = original.source()
    value['scripts/retained_report_fresh_launch.py'] = pin(Path(__file__))
    return value


def inputs(plan):
    folder = Path(plan['materials'])
    if inventory(folder) != plan['material_inventory']:
        raise ValueError('fresh_material_changed')
    manifest = read(folder/'manifest.json')
    values = []
    for name in ('facts', 'completion'):
        context = read(folder/f'{name}-validation-context.json')
        current = contract.restore_context(context)
        request = contract.make_request(current, name, 'fresh')
        business = read(folder/f'{name}-request.json')
        contract.validate_business(business, context)
        row = next(r for r in manifest['requests'] if r['duty'] == name)
        if (context['stage'] != 'fresh' or context['duty'] != name
                or digest(current.source.report.encode()) != REPORT
                or contract.request_sha(request) != row['candidate_request_sha256']
                or business != visible(json_value(request))):
            raise ValueError('fresh_request_binding')
        values.append(current)
    if values[0] != values[1]:
        raise ValueError('fresh_reports_differ')
    return values[0]


def parent_unchanged(plan):
    for path, expected in plan['parent_inventories'].items():
        if inventory(Path(path)) != expected:
            raise ValueError('fresh_parent_evidence_changed')


def prepare(operator, materials, primary, independent):
    operator, materials = Path(operator).absolute(), Path(materials).absolute()
    origin = materials.parent
    parents = read(origin/'content-audit-original-inventories.json')
    forbidden = [ROOT, origin, *map(Path, parents)]
    if (operator.resolve() != operator or operator.exists()
            or any(operator.is_relative_to(p) or p.is_relative_to(operator) for p in forbidden)):
        raise ValueError('fresh_new_external_operator_required')
    audit = read(origin/'content-audit-result.json')
    if (audit['report_sha256'] != REPORT or not audit['primary_accepted']
            or not audit['independent_accepted'] or audit['normal_dispatch_and_final_import'] is not False):
        raise ValueError('fresh_original_diagnostic_scope_changed')
    review = freeze_v2_identity(dict(host_review_submission_mode=MODE_V2,
        host_review_evidence_policy=FINAL_POLICY), root_thread_id=primary,
        primary_id=primary, independent_id=independent)
    plan = dict(version=VERSION, operator=str(operator), materials=str(materials),
        material_inventory=inventory(materials), parent_inventories=parents,
        content_audit_file=str(origin/'content-audit-result.json'),
        content_audit_sha256=pin(origin/'content-audit-result.json'),
        original_strict_dispatch_import=False, report_sha256=REPORT,
        head=base.current_head(), cwd=str(ROOT.resolve()), python=str(Path(sys.executable).resolve()),
        codex=str(base.CODEX.resolve()), source=source(), limits=LIMITS,
        contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        review_plan=review, review_profile=original.profile(),
        estimated_first_two_cny='0.14592', estimated_envelope_cny='0.43776', hard_billing_cap=False,
        historical_accounting=dict(http_requests=5, known_tokens=67065, unknown_reserved_tokens=73756, retries=1),
        scope='Fresh-only diagnostic of retained corrected text; no formal original application or qualification.',
        execution_authorized=False, qualified=False, publication_allowed=False)
    inputs(plan); parent_unchanged(plan)
    operator.mkdir(parents=True, exist_ok=False)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=pin(operator/'plan.json'), provider_requests=0, key_reads=0)


def load(operator, plan_sha, *, frozen=False):
    operator = Path(operator).absolute()
    if pin(operator/'plan.json') != plan_sha:
        raise ValueError('fresh_original_plan_required')
    plan = read(operator/'plan.json')
    if (plan['version'] != VERSION or plan['operator'] != str(operator)
            or plan['cwd'] != str(ROOT.resolve()) or Path.cwd().resolve() != ROOT.resolve()
            or plan['python'] != str(Path(sys.executable).resolve())
            or plan['codex'] != str(base.CODEX.resolve()) or plan['limits'] != LIMITS
            or plan['review_profile'] != original.profile()
            or plan['contract'] != contract.CONTRACT.snapshot().model_dump(mode='json')
            or plan['review_plan'].get('host_review_evidence_policy') != FINAL_POLICY
            or pin(plan['content_audit_file']) != plan['content_audit_sha256']):
        raise ValueError('fresh_execution_binding_changed')
    inputs(plan); parent_unchanged(plan)
    if frozen and (base.current_head() != plan['head'] or source() != plan['source']
            or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()):
        raise ValueError('fresh_clean_frozen_source_required')
    return plan


def grant_binding(plan, plan_sha):
    return dict(version=VERSION+'-authorization', plan_sha256=plan_sha, head=plan['head'],
        report_sha256=REPORT, limits=LIMITS, review_profile=plan['review_profile'],
        estimated_envelope_cny=plan['estimated_envelope_cny'], manual_retry_only=True,
        qualified=False, publication_allowed=False)


def validate_grant(grant, plan, plan_sha, *, now=None):
    now = now or datetime.now(timezone.utc)
    start, end = (datetime.fromisoformat(grant[k]) for k in ('issued_at','expires_at'))
    if (any(grant.get(k) != v for k,v in grant_binding(plan,plan_sha).items())
            or start.utcoffset() is None or end.utcoffset() is None
            or not start <= now < end or not timedelta(0) < end-start <= timedelta(days=1)
            or not isinstance(grant.get('user_authorization_evidence'),str)
            or not grant['user_authorization_evidence'].strip()):
        raise ValueError('fresh_specific_unexpired_authorization_required')


def open_session(plan, plan_sha, events, *, authorization_sha=None, preflight=False,
                 guard=None, checkpoint=None, before=None, sink=base.emit, **kwargs):
    operator = Path(plan['operator'])
    folder = operator/('native-preflight' if preflight else 'execution')
    session = CandidateSession(folder/'session', binding=dict(version=VERSION,
        candidate_contract=contract.VERSION, plan_sha256=plan_sha, report_sha256=REPORT,
        authorization_sha256=authorization_sha, fixture_only=preflight,
        review_plan_sha256=digest(canonical(plan['review_plan']))),
        transport_root=folder/'transport', journal_root=folder/'journal',
        guard_sha=guard, checkpoint_sha=checkpoint, before_new_model=before,
        checkpoint_sink=sink, contract_module=contract, **kwargs)
    workspace = HostReviewWorkspace(cwd=ROOT, python=plan['python'],
        answers=operator.with_name(operator.name+'-authors'), evidence_roots=[operator])
    gate = SessionReviewGate(session, plan=plan['review_plan'], workspace=workspace, event_source=events)
    return session, gate


def run_reviews(session, router, fixed):
    observed = ObservedLLMProvider(delegate=router, observer=SignalRecorder(session.root/'signals'),
                                  request_identity=contract.request_identity)
    budget = SessionBudget(observed, session=session, coach_contract=contract.CONTRACT)
    workflow = SessionWorkflow(SharedBudgetReviewSender(budget), session=session,
                              journal_root=session.journal_root, contract_module=contract)
    for duty in ('facts','completion'):
        _, value = workflow._review(fixed, duty, 'fresh')
        if value.verdict != 'pass' or value.score < 85:
            return dict(outcome='fresh_'+duty+'_not_pass', both_fresh_pass=False,
                        report_sha256=REPORT, accounting=budget.snapshot(), qualified=False)
    return dict(outcome='retained_text_fresh_pass_diagnostic_only', both_fresh_pass=True,
                report_sha256=REPORT, accounting=budget.snapshot(), qualified=False)


def preflight_task(plan, plan_sha, events):
    verify_native_principals(events.client, plan['review_plan'])
    session, gate = open_session(plan,plan_sha,events,preflight=True)
    try:
        with session:
            report = 'Administrative fresh-only startup check. No business acceptance or Provider call.'
            gate.require('startup-preflight','opinion',dict(fixture_only=True,
                administrative_preflight=True,report=report,responses=[],
                instructions='Verify author-file/check-answer/native-final import only. The prospectively frozen policy permits opaque input but proves route and exact final, not encrypted input equivalence.'),report)
    except SessionPaused:
        pass
    return dict(provider_requests=0,key_reads=0)


def verify_preflight(plan, plan_sha, events, proof):
    session, gate = open_session(plan,plan_sha,events,preflight=True,read_only=True,
        guard=proof['guard_sha256'],checkpoint=proof['checkpoint_sha256'])
    with session:
        handles=list(gate.handles())
        if len(handles)!=1 or handles[0]['binding']['key']!='startup-preflight' or not gate.native.replay(handles[0]):
            raise ValueError('fresh_native_preflight_required')


def execute(plan, plan_sha, events, *, authorization_file, authorization_sha, preflight_proof,
            ci_run=None, guard=None, checkpoint=None, manual_retry=False, host_only=False,
            sink=base.emit, key_reader=None, sender=None):
    load(plan['operator'],plan_sha,frozen=True)
    if (Path(plan['operator'])/'seal.json').exists():
        raise SessionBlocked('fresh_sealed_no_run')
    if pin(authorization_file)!=authorization_sha:
        raise ValueError('fresh_original_authorization_required')
    grant=read(authorization_file)
    # Historical consent remains inspectable after expiry. Only the actual
    # provider boundary below requires current UTC validity.
    validate_grant(grant,plan,plan_sha,now=datetime.fromisoformat(grant['issued_at']))
    verify_preflight(plan,plan_sha,events,preflight_proof)
    verify_native_principals(events.client,plan['review_plan'])
    ci=None
    def before():
        if host_only or ci is None:
            raise SessionBlocked('fresh_send_boundary_required')
        load(plan['operator'],plan_sha,frozen=True)
        if pin(authorization_file)!=authorization_sha:
            raise SessionBlocked('fresh_authorization_changed')
        validate_grant(grant,plan,plan_sha)
        budget=last_budget(session)
        if (budget['calls']>=LIMITS['max_requests']
                or budget['tokens']+budget['reserved_tokens']+80384>LIMITS['max_reserved_tokens']
                or budget['retries']>LIMITS['manual_retries']
                or session.active_seconds>=LIMITS['active_seconds']):
            raise SessionPaused('fresh_remaining_budget_required')
    session,gate=open_session(plan,plan_sha,events,authorization_sha=authorization_sha,
        guard=guard,checkpoint=checkpoint,before=before,manual_retry=manual_retry,sink=sink)
    try:
        with session:
            status=session.status()
            if status['closed'] or status['unresolved']:
                raise SessionBlocked('fresh_closed_or_unresolved_no_send')
            waiting=status['timeout_waiting'] or status['format_waiting']
            if manual_retry and not waiting:
                raise SessionBlocked('fresh_manual_retry_requires_failed_attempt')
            if waiting and not manual_retry:
                raise SessionPaused('fresh_awaiting_manual_retry')
            session.max_new_models=0
            def deny(*a,**k):
                raise AssertionError('fresh_offline_provider_forbidden')
            fixed=inputs(plan)
            try:
                result=run_reviews(session,original.router_for(session,'OFFLINE_NO_SEND',deny),fixed)
            except SessionPaused as error:
                if str(error)!='session_model_boundary' or host_only:
                    raise
                ci=base.verify_ci(ci_run,plan['head'])
                before()
                verify_native_principals(events.client,plan['review_plan'])
                gate.verify_prior()
                checks=session.root/'launch-checks'
                checks.mkdir(exist_ok=True)
                write_new_json(checks/f'{len(list(checks.iterdir()))+1:04d}.json',
                    dict(plan_sha256=plan_sha,authorization_sha256=authorization_sha,ci=ci))
                session._checkpoint('launch_verified')
                key=(key_reader or credentials.read_key)()
                try:
                    before()
                    session.cursor=0
                    session.max_new_models=1
                    result=run_reviews(session,original.router_for(session,key,sender),fixed)
                finally:
                    key=None
            session.close(dict(result=result))
            return dict(phase='completed',result=result,provider_calls=last_budget(session)['calls'])
    except SessionPaused as error:
        return dict(phase='paused',reason=str(error),provider_calls=last_budget(session)['calls'],
                    qualified=False,publication_allowed=False)


def replay(plan,plan_sha,events,*,authorization_sha,guard,checkpoint):
    load(plan['operator'],plan_sha,frozen=True)
    before=inventory(Path(plan['operator'])),inventory(Path(plan['operator']+'-authors'))
    session,gate=open_session(plan,plan_sha,events,authorization_sha=authorization_sha,
        guard=guard,checkpoint=checkpoint,read_only=True)
    with session:
        def deny(*a,**k): raise AssertionError('fresh_replay_cannot_send')
        result=run_reviews(session,original.router_for(session,'OFFLINE_NO_SEND',deny),inputs(plan))
        if read(session.root/'terminal.json')!=dict(value=dict(result=result),publication_allowed=False,production_admitted=False):
            raise ValueError('fresh_terminal_mismatch')
        accounting=original.audit_transport(session)
    if before!=(inventory(Path(plan['operator'])),inventory(Path(plan['operator']+'-authors'))):
        raise ValueError('fresh_replay_changed_evidence')
    checked=dict(result=result,accounting=accounting,readonly=True,qualified=False,publication_allowed=False)
    sealed=Path(plan['operator'])/'seal.json'
    if sealed.exists():
        record=read(sealed)
        if (record['plan_sha256']!=plan_sha or record['authorization_sha256']!=authorization_sha
                or record['guard_sha256']!=guard or record['checkpoint_sha256']!=checkpoint
                or record['result']!=checked or record['historical_accounting']!=plan['historical_accounting']
                or before[0]!={**record['inventory'],'seal.json':pin(sealed)}
                or before[1]!=record['author_inventory']):
            raise ValueError('fresh_seal_changed')
    return checked


def seal(plan,plan_sha,events,*,authorization_sha,guard,checkpoint):
    operator=Path(plan['operator'])
    if (operator/'seal.json').exists():
        raise ValueError('fresh_already_sealed')
    checked=replay(plan,plan_sha,events,authorization_sha=authorization_sha,guard=guard,checkpoint=checkpoint)
    value=dict(version=VERSION+'-seal',plan_sha256=plan_sha,authorization_sha256=authorization_sha,
        guard_sha256=guard,checkpoint_sha256=checkpoint,inventory=inventory(operator),
        author_inventory=inventory(operator.with_name(operator.name+'-authors')),
        historical_accounting=plan['historical_accounting'],result=checked,
        original_workflow_requalified=False,publication_allowed=False)
    write_new_json(operator/'seal.json',value)
    return dict(seal_sha256=pin(operator/'seal.json'),**checked)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','preflight','task','submit','run','replay','seal'))
    parser.add_argument('--operator',required=True,type=Path)
    for name in ('materials','authorization-file','preflight-proof','primary-file'):
        parser.add_argument('--'+name,type=Path)
    for name in ('primary','independent','plan-sha','authorization-sha','guard-sha','checkpoint-sha','ci-run','event-id','key'):
        parser.add_argument('--'+name)
    parser.add_argument('--administrative',action='store_true')
    parser.add_argument('--manual-retry',action='store_true')
    parser.add_argument('--host-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.action=='prepare':
            base.emit(prepare(args.operator,args.materials,args.primary,args.independent));return
        plan=load(args.operator,args.plan_sha)
        with CodexReadOnlyClient(base.CODEX) as client:
            events=CodexHostReviewEventSource(client,plan['review_plan'])
            kw=dict(authorization_sha=args.authorization_sha,guard=args.guard_sha,checkpoint=args.checkpoint_sha)
            if args.action=='preflight': value=preflight_task(plan,args.plan_sha,events)
            elif args.action in ('task','submit'):
                session,gate=open_session(plan,args.plan_sha,events,preflight=args.administrative,
                    read_only=args.action=='task',**kw)
                with session:
                    handle=list(gate.handles())[-1]
                    if args.action=='task':
                        if (Path(handle['folder'])/'submission.json').exists():
                            raise ValueError('fresh_task_already_submitted')
                        print((Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8'));return
                    value=dict(accepted=gate.submit(args.key,read(args.primary_file),args.event_id),provider_requests=0)
            elif args.action=='run':
                value=execute(plan,args.plan_sha,events,authorization_file=args.authorization_file,
                    preflight_proof=read(args.preflight_proof),ci_run=args.ci_run,
                    manual_retry=args.manual_retry,host_only=args.host_only,**kw)
            else: value=(seal if args.action=='seal' else replay)(plan,args.plan_sha,events,**kw)
            base.emit(value)
    except (Exception,KeyboardInterrupt) as error:
        code=str(error)
        base.emit(dict(ok=False,code=code if re.fullmatch(r'(fresh|session|codex_review_host)_[a-z0-9_]+',code) else type(error).__name__,
                       publication_allowed=False,qualified=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
