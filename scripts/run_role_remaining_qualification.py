"""Run the remaining original controls after strict, offline receipt acceptance.

Uses the existing executor and complete bound stage decisions. No incidental
review-defect allowance, reassessment, retries, or production admission.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Workflow
from app.evaluation.role_qualification import ROOT, ASSETS, prepare_qualification, replay_case
from app.evaluation.role_task_outcome import VERSION
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_qualification_pair import observe
from scripts.run_role_task_observation import Observer, adjudicate

EXPERIMENT = 'role-remaining-qualification-v1'
PRIOR_RESULT = ROOT/'data/evaluation/results/golden_role_task_result_v1.json'
PRIOR_SHA = 'ce0a6ab008c3e40ec5c89335bf1c7f7e3c70348ca2d38cc4699d4863bbbe5747'
PRIOR_KEYS = ('claim-scope:1', 'claim-scope:4', 'attribution:1')
PREPARATION = ROOT/'data/evaluation/results/golden_role_remaining_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_role_remaining_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/EXPERIMENT


class StrictObserver(Observer):
    @staticmethod
    def validate_stage(plan, row, path, decision):
        allowed = Observer.validate_stage(plan, row, path, decision)
        initial_error = (decision['assessment']['stage']=='initial' and row['expected_initial']=='reject')
        return (allowed and decision['accepted'] is True and not decision['assessment']['defects']
            and (not initial_error or decision['target_and_correction_valid'] is True))


def prepare():
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs',coach_contract=ROLE_COACH_CONTRACT)
    qualification, requests = prepare_qualification()
    raw = PRIOR_RESULT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA:
        raise ValueError('remaining_prior_evidence_changed')
    previous = json.loads(raw)['public_json_contents']
    prior_plan = previous['plan.json']['preparation_plan']
    # Only receipt provenance establishes the bridge; no task-outcome boolean
    # becomes qualification here. The separate strict audit consumes raw files.
    if prior_plan['identity'] != qualification['identity']:
        raise ValueError('remaining_candidate_identity_changed')
    prior_rows = {r['key']:r for r in prior_plan['cases']}
    if set(prior_rows) != set(PRIOR_KEYS):
        raise ValueError('remaining_prior_inventory_changed')
    current_rows = {r['key']:r for r in qualification['cases']}
    if any(prior_rows[k] != current_rows[k] for k in PRIOR_KEYS):
        raise ValueError('remaining_prior_input_changed')
    cases = [r for r in qualification['cases'] if r['key'] not in PRIOR_KEYS]
    budgets = [dict(max_calls=1 if r['expected_initial']=='accept' else 3,
        max_tokens=96768 if r['expected_initial']=='accept' else 290304,
        max_seconds=300 if r['expected_initial']=='accept' else 900) for r in cases]
    total = {k:sum(b[k] for b in budgets) for k in budgets[0]}
    output = total['max_calls']*32768
    cost = (Decimal(output)*28+Decimal(total['max_tokens']-output)*8)/1_000_000
    plan = dict(experiment=EXPERIMENT,observation_version=VERSION,identity=qualification['identity'],
        cases=cases,case_budgets=budgets,original15_keys=[r['key'] for r in qualification['cases']],
        prior_keys=list(PRIOR_KEYS),prior_evidence_sha256=PRIOR_SHA,
        batch_budget=dict(total,estimated_uncached_cny=str(cost),hard_billing_cap=False),
        source_sha256={p:hashlib.sha256((ROOT/p).read_text(encoding='utf-8').encode()).hexdigest() for p in (
            'scripts/run_role_remaining_qualification.py','scripts/run_role_task_observation.py',
            'scripts/run_role_qualification_pair.py','app/evaluation/role_task_outcome.py',
            'app/evaluation/role_qualification.py','scripts/qualify_role_observations.py')},
        labels_sent_to_model=False,sdk_retries=0,allow_reassessment=False,
        stop_rule='Stop on any rejected stage, wrong verdict, protocol/source/identity/transport/budget failure. No incidental-error exception, retry or reassessment.',
        success_scope='Remaining original12 receipt evidence; strict separate original15 qualification still required.',
        failure_decision='Preserve the earliest divergence; no automatic paid retry or prompt variant. Diagnose full data/control path.',
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)
    return plan,{r['key']:requests[r['key']] for r in cases}


def run(args):
    if args.execute and (CLOSED_RESULT.exists() or RUN_DIRECTORY.exists()):
        raise ValueError('remaining_batch_closed_or_exists')
    plan,requests = prepare()
    sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output,plan)
        return dict(plan_sha256=sha,budget=plan['batch_budget'],provider_requests=0,execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha!=sha
            or plan!=json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('remaining_preparation_required')
    head = verify_public_ci(args.ci_run)
    from scripts.qualify_role_observations import qualify
    # This creates independent acceptance records before any new Provider IO;
    # original observations and their false admission flags remain untouched.
    prior = qualify([ROOT/'data/runs/role_task_observation/role-task-observation-v1'],
        evidence_root=ROOT,output_directory=ROOT/'data/runs/role_task_observation'/('qualification-before-'+EXPERIMENT),
        closed_exports=[(PRIOR_RESULT,PRIOR_SHA)])
    if (prior['status']!='validated_partial' or set(prior['validated_keys'])!=set(PRIOR_KEYS)
            or prior['validated_inputs']!=3 or prior['review_controls_qualified'] is not False):
        raise ValueError('remaining_prior_strict_acceptance_required')
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=sha,head_sha=head,ci_run=args.ci_run))
    for key,raw in requests.items():
        (RUN_DIRECTORY/(key.replace(':','-')+'-prepared-request.json')).write_bytes(raw)
    generator,reviewer = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport')
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,adjudicate=adjudicate,workflow_type=Workflow,
            replay=replay_case,success_field='tasks_observed',task_observer=StrictObserver,
            before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if args.execute and not result['tasks_observed']:
        sys.exit(1)
