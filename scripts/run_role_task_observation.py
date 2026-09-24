"""Prospective original-set task observation under ADR0111; no admission.

The first three controls test unchanged correct text, the universal-metrics
error and attribution. A rejected ancillary explanation may continue only via
a fully bound host decision; all other rejected stages stop. No reassessment.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread
import time

from pydantic import BaseModel, ConfigDict

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Workflow
from app.evaluation.role_qualification import ROOT, ASSETS, frozen_cases, prepare_qualification, replay_case
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_task_outcome import (
    VERSION, StageAssessment, ReportAssessment, may_continue_initial,
    prepare_observation, assess_task_outcome, stage_identity,
)
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_qualification_pair import observe

EXPERIMENT = 'role-task-observation-v1'
KEYS = ('claim-scope:1', 'claim-scope:4', 'attribution:1')
PREPARATION = ROOT/'data/evaluation/results/golden_role_task_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_role_task_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/EXPERIMENT


class StageDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    response_sha256: str
    accepted: bool
    candidate_sha256: str
    input_sha256: str
    key: str
    assessment: StageAssessment
    target_and_correction_valid: bool
    final_report: ReportAssessment | None


class Observer:
    @staticmethod
    def validate_stage(plan, row, path, decision):
        if plan.get('observation_version') != VERSION:
            raise ValueError('task_observation_plan_contract')
        host = StageDecision.model_validate(decision)
        stage = json.loads(path.read_text(encoding='utf-8'))
        if (host.response_sha256 != hashlib.sha256(path.read_bytes()).hexdigest()
                or host.key != row['key'] or host.input_sha256 != row['input_sha256']
                or host.candidate_sha256 != digest(compact(plan['identity']))
                or host.assessment.stage != stage['stage']
                or host.assessment.stage_sha256 != stage_identity(stage)
                or host.assessment.accepted != host.accepted):
            raise ValueError('task_observation_host_binding')
        needs_report = stage['stage'] != 'initial' or row['expected_initial']=='accept'
        if needs_report:
            report = host.final_report
            if report is None or report.report_sha256 != digest(stage['report']):
                raise ValueError('task_observation_report_binding')
            if not all((report.facts_and_sources_correct,report.correct_content_preserved,
                        report.identity_and_goal_preserved,report.true_errors_fixed)):
                return False
        if stage['stage']=='initial':
            return may_continue_initial(host.assessment, expected_initial=row['expected_initial'],
                target_and_correction_valid=host.target_and_correction_valid)
        return host.accepted

    @staticmethod
    def finish(plan, row, calls, decisions):
        observed = prepare_observation(row['key'],calls)
        expected = dict(key=row['key'], input_sha256=row['input_sha256'],
            candidate_sha256=digest(compact(plan['identity'])))
        if (any(observed['binding'][k]!=v for k,v in expected.items())
                or any(any(d.get(k)!=v for k,v in expected.items()) for d in decisions)):
            raise ValueError('task_observation_final_identity_drift')
        host = dict(**observed['binding'], stages=[d['assessment'] for d in decisions],
            final_report=decisions[-1]['final_report'])
        return assess_task_outcome(row['key'],calls,host)


def adjudicate(path,remaining):
    print(compact(dict(host_task_assessment_required=path.as_posix(),
        response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        remaining_seconds=round(remaining,3),reply='decision <path-to-bound-stage-decision.json>')),flush=True)
    queue=Queue()
    Thread(target=lambda:queue.put(sys.stdin.readline()),daemon=True).start()
    try:
        line=queue.get(timeout=max(0,remaining)).strip()
    except Empty:
        raise ValueError('task_observation_host_deadline') from None
    if not line.startswith('decision '):
        raise ValueError('task_observation_decision_required')
    supplied=Path(line[len('decision '):]).resolve()
    # Host writes one evidence file beside this exact case; never read arbitrary
    # credentials or a stale decision from a different run via stdin.
    if supplied.parent != path.parent.resolve() or supplied.suffix!='.json':
        raise ValueError('task_observation_decision_path')
    return StageDecision.model_validate_json(supplied.read_text(encoding='utf-8')).model_dump()


def adjudicate_file(path, remaining, *, clock=time.monotonic, sleep=time.sleep):
    """Bounded file handoff: loss of terminal stdin cannot approve or reset it.

    Run this with a detached, hidden process and redirected output. A restart
    remains forbidden; the original monotonic deadline continues while the
    host inspects sources. Partial writes are retried only as local reads.
    """
    deadline = clock() + remaining
    decision_path = path.with_name('decision-' + path.stem + '.json')
    write_new_json(path.with_name(path.stem + '-host-required.json'), dict(
        stage_file=path.name, response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        decision_file=decision_path.name, remaining_seconds=remaining,
        deadline_scope='Original running process monotonic deadline; never a restart allowance.'))
    while True:
        available = deadline - clock()
        if available <= 0:
            raise ValueError('task_observation_host_deadline')
        try:
            value = json.loads(decision_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            # A create-only writer may still be flushing the file. Neither an
            # incomplete file nor a missing one changes the original deadline.
            sleep(min(.25, available))
            continue
        decision = StageDecision.model_validate(value).model_dump()
        if (decision['response_sha256'] != hashlib.sha256(path.read_bytes()).hexdigest()
                or clock() >= deadline):
            raise ValueError('task_observation_file_decision_invalid')
        return decision


def prepare():
    if CLOSED_RESULT.exists():
        raw = CLOSED_RESULT.read_bytes()
        if hashlib.sha256(raw).hexdigest() != 'ce0a6ab008c3e40ec5c89335bf1c7f7e3c70348ca2d38cc4699d4863bbbe5747':
            raise ValueError('task_observation_historical_evidence_changed')
        evidence = json.loads(raw)
        saved = evidence['public_json_contents']['plan.json']
        plan = saved['preparation_plan']
        if (plan != json.loads(PREPARATION.read_text(encoding='utf-8'))
                or canonical_sha(plan) != saved['plan_sha256']
                or [c['key'] for c in plan['cases']] != list(KEYS)):
            raise ValueError('task_observation_historical_plan_changed')
        sources = {f['key']: source for f, source in frozen_cases()[0]}
        requests = {}
        for row in plan['cases']:
            key = row['key']
            request = Workflow.make_request(Workflow.build_inputs(sources[key]))
            raw_request = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
            if (hashlib.sha256(raw_request).hexdigest() != row['request_sha256']
                    or row['request_sha256'] != evidence['original_file_sha256'][
                        key.replace(':', '-') + '-prepared-request.json']):
                raise ValueError('task_observation_historical_request_changed')
            requests[key] = raw_request
        return plan, requests
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs',coach_contract=ROLE_COACH_CONTRACT)
    qualification,requests=prepare_qualification()
    rows={r['key']:r for r in qualification['cases']}
    budgets=[dict(max_calls=1,max_tokens=96768,max_seconds=300),
        dict(max_calls=3,max_tokens=290304,max_seconds=900),
        dict(max_calls=3,max_tokens=290304,max_seconds=900)]
    total={k:sum(b[k] for b in budgets) for k in budgets[0]}
    output=total['max_calls']*32768
    cost=(Decimal(output)*28+Decimal(total['max_tokens']-output)*8)/1_000_000
    plan=dict(experiment=EXPERIMENT,observation_version=VERSION,identity=qualification['identity'],
        original15_plan_sha256=digest(compact(qualification)),
        original15_keys=[r['key'] for r in qualification['cases']],
        cases=[rows[k] for k in KEYS],case_budgets=budgets,
        batch_budget=dict(total,estimated_uncached_cny=str(cost),hard_billing_cap=False),
        source_sha256={p:hashlib.sha256((ROOT/p).read_text(encoding='utf-8').encode()).hexdigest() for p in (
            'scripts/run_role_task_observation.py','scripts/run_role_qualification_pair.py',
            'app/evaluation/role_task_outcome.py','app/evaluation/role_qualification.py')},
        labels_sent_to_model=False,sdk_retries=0,allow_reassessment=False,
        stop_rule='Wrong verdict or any rejected stage stops, except a bound initial incidental-explanation defect with correct target and correction intent. Actual edit and complete final review must pass. No restart/retry/reassessment.',
        success_scope='Three fresh frozen-input task observations. Does not qualify original15, reviewer, generation or production.',
        failure_decision='Preserve first divergence; no paid retry or new wording. Diagnose full request/source/edit path and update the mechanism decision.',
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)
    return plan,{k:requests[k] for k in KEYS}


def run(args):
    if args.execute and (CLOSED_RESULT.exists() or RUN_DIRECTORY.exists()):
        raise ValueError('task_observation_batch_closed_or_exists')
    plan,requests=prepare()
    sha=canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output,plan)
        return dict(plan_sha256=sha,budget=plan['batch_budget'],provider_requests=0,
            execution_enabled=False,historical_closed=CLOSED_RESULT.exists())
    if (not args.env_file or not args.ci_run or args.plan_sha!=sha
            or plan!=json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('task_observation_preparation_required')
    head=verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=sha,head_sha=head,ci_run=args.ci_run))
    for key,raw in requests.items():
        (RUN_DIRECTORY/(key.replace(':','-')+'-prepared-request.json')).write_bytes(raw)
    generator,reviewer=load_role_settings(args.env_file)
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport')
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,adjudicate=adjudicate,
            workflow_type=Workflow,replay=replay_case,success_field='tasks_observed',
            task_observer=Observer,before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    print(compact(run(parser.parse_args())),flush=True)
