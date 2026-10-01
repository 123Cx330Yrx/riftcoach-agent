"""Bounded necessary-edit capability diagnostic; no original15 qualification.

Two immutable historical initial reviews are explicit inputs, not newly issued
calls. One necessary edit, a conditional fresh review, then a correct keep control.
Every completed stage needs genuine independent and primary full-source review.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time

from app.evaluation import coarse_revision_editor as editor
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_boundary_examples import RoleBoundaryExamplesReviewWorkflow as Current
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, RESPONSE
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import ROOT, frozen_cases
from app.evaluation.role_task_outcome import StageAssessment, ReportAssessment, stage_identity
from app.evaluation.source_patch_editor import report_inputs
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT as CONTRACT
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.review_sender import SharedBudgetReviewSender
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.diagnose_role_context import canonical_sha
from scripts.export_partitioned_review import public_response
from scripts.review_independence_contract import (MODE_V2, FINAL_POLICY, freeze_v2_identity,
    require_execution_event_source, required_binding, validate_independent_event, validate_primary_attestation)
from scripts.role_development_host_clock import DevelopmentHostClock
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.diagnose_block_review_route import route_environment

EXPERIMENT = 'coarse-necessary-edit-diagnostic-20261001'
FIXTURE = 'tests/fixtures/coarse_edit_initial_reviews_20261001.json'
KEYS = ('claim-scope:4','claim-scope:1')
SOURCE_FILES = (
    __file__, editor.__file__, 'app/evaluation/source_patch_editor.py',
    'app/evaluation/golden_role_boundary_examples.py','app/evaluation/golden_role_correction_scope.py',
    'app/evaluation/golden_role_coarse.py','app/evaluation/golden_coarse_source_projection.py',
    'app/evaluation/golden_native_business_policy.py','app/evaluation/golden_semantic_review.py',
    'app/runtime/coach_budget.py','app/runtime/reviewer_roles.py','app/runtime/review_sender.py',
    'scripts/review_independence_contract.py','scripts/codex_review_event_source.py',
    'scripts/role_development_host_clock.py',FIXTURE)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def controls():
    sources={row['key']:req for row,req in frozen_cases()[0]}
    rows=json.loads((ROOT/FIXTURE).read_bytes())['cases']
    if tuple(row['key'] for row in rows)!=KEYS:
        raise ValueError('coarse_diagnostic_control_inventory')
    result=[]
    for row in rows:
        req=sources[row['key']]
        inputs=Current.build_inputs(req)
        if digest(req.report)!=row['report_sha256'] or digest(inputs.data_json)!=row['input_sha256']:
            raise ValueError('coarse_diagnostic_control_identity')
        _,accepted,_=Current.validate_review(row['initial_raw'],inputs)
        if accepted.verdict!=('needs_revision' if row['key']==KEYS[0] else 'pass'):
            raise ValueError('coarse_diagnostic_initial_verdict')
        result.append((row,inputs,accepted,editor.edit_request(inputs,accepted)))
    return result


def prepare(*,root_thread_id,independent_thread_id):
    cells=[]
    for row,inputs,accepted,request in controls():
        cells.append(dict(key=row['key'],report_sha256=digest(inputs.source.report),
            input_sha256=digest(inputs.data_json),historical_initial_raw_sha256=digest(row['initial_raw']),
            request_sha256=hashlib.sha256(validate_request(request,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
            input_reservation=size(request),output_cap=request.max_tokens))
    roles={'glm-5.3-flash':2,'glm-5.3':1}
    cost=sum(count*(Decimal(64000)*CONTRACT.pricing_profiles['zhipu',model].input_cost_per_million
        +Decimal(32768)*CONTRACT.pricing_profiles['zhipu',model].output_cost_per_million)/1_000_000
        for model,count in roles.items())
    paths=[Path(p) if Path(p).is_absolute() else ROOT/p for p in SOURCE_FILES]
    plan=dict(experiment=EXPERIMENT,adapter=editor.VERSION,cells=cells,
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        host_review_submission_mode=MODE_V2,host_review_evidence_policy=FINAL_POLICY,
        max_host_seconds=86400,budget=dict(max_calls=3,max_tokens=290304,max_active_seconds=900,
            per_request_output=32768,per_request_seconds=300,estimated_uncached_cny=str(cost),hard_billing_cap=False),
        role_calls=roles,historical_initial_inputs=2,sdk_retries=0,
        product_contract_used_for_limits_only=True,product_admitted=False,original15_qualified=False,
        execution_authorized=False,
        sequence=['necessary-edit','conditional-fresh','correct-keep'],
        stop_rule='First host, semantic, protocol, source, identity, transport or budget failure stops; no retry or restart.',
        acceptance='Full source-supported repair and preserved correct content; current fresh pass with score>=85; correct keep is byte-identical.',
        diagnostic_scope='Fixed accepted issues test editing; keep is a capability control, not a product edit-after-pass state.',
        success_decision='Prepare prospective registration and same-identity coverage; no product or original15 admission.',
        failure_decision='Preserve earliest divergence and charges; no automatic variant or new batch.')
    return freeze_v2_identity(plan,root_thread_id=root_thread_id,primary_id=root_thread_id,
                              independent_id=independent_thread_id)


def validate_reviews(submission, stage, bound, plan, event_source):
    """Use the existing native independence contract, not two root-authored files."""
    accepted=[]
    for role in ('primary','independent'):
        review=submission[role]
        if review.get('binding')!=required_binding(bound):
            raise ValueError('coarse_diagnostic_host_binding')
        assessment=StageAssessment.model_validate(review['stage_assessment'])
        report=ReportAssessment.model_validate(review['report_assessment'])
        principal=plan['review_principals'][role]['principal_id']
        if (assessment.stage!=stage['stage'] or assessment.stage_sha256!=stage_identity(stage)
                or report.report_sha256!=bound['report_sha256']
                or assessment.reviewer!=principal or report.reviewer!=principal):
            raise ValueError('coarse_diagnostic_host_scope')
        if assessment.accepted and not all((report.facts_and_sources_correct,report.correct_content_preserved,
                                            report.identity_and_goal_preserved,report.true_errors_fixed)):
            raise ValueError('coarse_diagnostic_host_contradiction')
        if role=='primary':
            validate_primary_attestation(review,plan=plan,bound=bound)
        else:
            validate_independent_event(review,plan=plan,bound=bound,event_source=event_source)
        accepted.append(assessment.accepted)
    return all(accepted)


def wait_reviews(path,remaining):
    submission=path.with_name('review-submission.json')
    print(compact(dict(host_review_required=str(path),submission=str(submission),remaining_host_seconds=remaining)),flush=True)
    deadline=time.monotonic()+remaining
    while time.monotonic()<deadline:
        if submission.exists():
            return json.loads(submission.read_bytes())
        time.sleep(.25)
    raise ValueError('coarse_diagnostic_host_deadline')


def observe(factory,directory,plan,*,event_source,adjudicate=wait_reviews,before_send=lambda:None):
    """One non-restartable process; no paid response can bypass the host gate."""
    require_execution_event_source(plan,event_source)
    clock=DevelopmentHostClock(directory,max_host_seconds=plan['max_host_seconds'])
    router=factory('diagnostic')
    budget=_ReceiptForwardingCoachBudgetedProvider(router,coach_contract=CONTRACT,clock=clock)
    send=SharedBudgetReviewSender(budget)
    ledger=[]
    result=dict(experiment=EXPERIMENT,diagnostic_accepted=False,product_admitted=False,original15_qualified=False)
    plan_sha=canonical_sha(plan)

    def call(name,key,phase,inputs,request,parse):
        clock.before_send()
        before_send()
        remaining=plan['budget']['max_active_seconds']-clock()
        request=replace(request,timeout_s=min(request.timeout_s,remaining))
        if (remaining<=0 or budget.calls>=plan['budget']['max_calls']
                or budget.tokens+budget.reserved_tokens+size(request)+request.max_tokens>plan['budget']['max_tokens']):
            raise ValueError('coarse_diagnostic_budget')
        arm=Path(directory)/name
        arm.mkdir(exist_ok=False)
        write_new_json(arm/'source.json',dict(input_json=inputs.data_json,report=inputs.source.report))
        exchange=send(request)
        transport=(CAPACITY_TRANSPORT_ID if phase=='revision' else REVIEW_MODEL_TRANSPORT_ID)
        write_new_json(arm/'request.json',json.loads(validate_request(exchange.issued_request,transport_id=transport)))
        write_new_json(arm/'response.json',public_response(json.loads(RESPONSE.dump_json(exchange.response))))
        parsed=parse(request,exchange)
        stage=dict(stage=phase,report=parsed[0],journal=parsed[1])
        write_new_json(arm/'stage.json',stage)
        bound=dict(plan_sha256=plan_sha,key=key,stage=phase,response_sha256=sha(arm/'response.json'),
            report_sha256=digest(stage['report']),request_sha256=exchange.receipt_request_sha256)
        write_new_json(arm/'review-required.json',dict(binding=bound,stage_sha256=stage_identity(stage),
            scope='All operations, selected sources, complete report, preserved correct content and all reviewer claims.'))
        submitted=clock.adjudicate(arm/'review-required.json',plan['budget']['max_active_seconds']-clock(),adjudicate)
        write_new_json(arm/'host-reviews.json',submitted)
        accepted=validate_reviews(submitted,stage,bound,plan,event_source)
        ledger.append(dict(name=name,binding=bound,host_accepted=accepted))
        if not accepted:
            raise ValueError('coarse_diagnostic_host_rejected')
        if clock()>=plan['budget']['max_active_seconds']:
            raise ValueError('coarse_diagnostic_budget')
        before_send()
        return stage

    try:
        bad,good=controls()
        row,inputs,accepted,prepared=bad
        if hashlib.sha256(validate_request(prepared,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()!=plan['cells'][0]['request_sha256']:
            raise ValueError('coarse_diagnostic_request_changed')
        def inspect_edit(request,exchange):
            assembly=editor.inspect_edit_exchange(prepared,exchange,inputs,accepted)
            return assembly.report,assembly.journal
        edited=call('necessary-edit',row['key'],'revision',inputs,prepared,inspect_edit)
        final_inputs=report_inputs(inputs,edited['report'])
        def inspect_final(request,exchange):
            raw=tool_result(request,exchange)
            _,wire,journal=Current.validate_review(raw,final_inputs)
            if wire.verdict!='pass' or wire.score<85:
                raise ValueError('coarse_diagnostic_fresh_not_pass')
            return final_inputs.source.report,journal
        call('conditional-fresh',row['key'],'final',final_inputs,Current.make_request(final_inputs),inspect_final)
        row,inputs,accepted,prepared=good
        if hashlib.sha256(validate_request(prepared,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()!=plan['cells'][1]['request_sha256']:
            raise ValueError('coarse_diagnostic_request_changed')
        def inspect_keep(request,exchange):
            assembly=editor.inspect_edit_exchange(prepared,exchange,inputs,accepted)
            if assembly.report!=inputs.source.report:
                raise ValueError('coarse_diagnostic_correct_report_changed')
            return assembly.report,assembly.journal
        call('correct-keep',row['key'],'revision',inputs,prepared,inspect_keep)
        result['diagnostic_accepted']=True
    except BaseException as error:
        code=getattr(error,'code',None) or (str(error) if isinstance(error,ValueError) else None)
        result.update(error_type=type(error).__name__)
        if isinstance(code,str) and re.fullmatch('[a-z_]{1,100}',code):
            result['error_code']=code
    finally:
        result.update(stages=ledger,calls=budget.calls,known_tokens=budget.tokens,
            unknown_reserved_tokens=budget.reserved_tokens,attempts=router.attempts,timing=clock.summary())
        write_new_json(Path(directory)/'result.json',result)
    return result


def run(args):
    plan=prepare(root_thread_id=args.root_thread_id,independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output: write_new_json(args.output,plan)
        return dict(plan_sha256=canonical_sha(plan),preparation=plan,provider_calls=0)
    directory=ROOT/'data/runs/model_comparison'/EXPERIMENT
    if directory.exists(): raise ValueError('coarse_diagnostic_closed_or_exists')
    if (not args.preparation or not args.env_file or not args.codex_executable
            or args.plan_sha!=canonical_sha(plan) or plan!=json.loads(args.preparation.read_bytes())):
        raise ValueError('coarse_diagnostic_preparation_required')
    head=verify_public_ci(args.ci_run)
    require_unchanged_checkout(head)
    with CodexReadOnlyClient(args.codex_executable) as client:
        verify_native_principals(client,plan)
        event_source=CodexHostReviewEventSource(client,plan)
        require_execution_event_source(plan,event_source)
        generator,reviewer=load_role_settings(args.env_file)
        factory=RunScopedRoleReceiptedProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
            transport_root=directory/'transport',source_projection=CONTRACT.descriptor()['source_projection'])
        directory.mkdir(parents=True,exist_ok=False)
        write_new_json(directory/'plan.json',dict(preparation_plan=plan,plan_sha256=canonical_sha(plan),
            approved_plan_sha256=args.plan_sha,execution_head_sha=head,ci_run=args.ci_run))
        with route_environment('direct'):
            return observe(factory,directory,plan,event_source=event_source,
                before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root-thread-id',required=True)
    p.add_argument('--independent-thread-id',required=True)
    p.add_argument('--output',type=Path)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--preparation',type=Path)
    p.add_argument('--plan-sha')
    p.add_argument('--ci-run')
    p.add_argument('--env-file',type=Path)
    p.add_argument('--codex-executable',type=Path)
    result=run(p.parse_args())
    print(compact(result),flush=True)
    if 'diagnostic_accepted' in result and not result['diagnostic_accepted']:
        raise SystemExit(1)
