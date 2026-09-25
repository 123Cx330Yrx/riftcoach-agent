"""Execute only untouched inputs after the sealed remaining-batch interruption.

The prior seven calls and three full case time reservations are charged to the
original cap. No successful or partially executed input is restarted. Decisions
arrive through bounded files, so the process can run without terminal stdin.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.role_qualification import ROOT, ASSETS, prepare_qualification, replay_case
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.qualify_role_observations import qualify, _within
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_qualification_pair import observe
from scripts.run_role_task_observation import Workflow, adjudicate_file
from scripts import run_role_remaining_qualification as prior

EXPERIMENT = 'role-unexecuted-qualification-v1'
RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/EXPERIMENT
PREPARATION = ROOT/'data/evaluation/results/golden_role_unexecuted_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_role_unexecuted_result_v1.json'
CLOSED_SHA = '2c1932f2d769958a2c4f33119e79c60f4b5624058f4af54bd15ded0022a1d62c'


def interruption():
    raw = prior.INTERRUPTION.read_bytes()
    if hashlib.sha256(raw).hexdigest() != prior.INTERRUPTION_SHA:
        raise ValueError('unexecuted_parent_evidence_changed')
    return json.loads(raw)


def prepare():
    if CLOSED_RESULT.exists():
        raw = CLOSED_RESULT.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CLOSED_SHA:
            raise ValueError('unexecuted_historical_evidence_changed')
        evidence = json.loads(raw)
        saved = evidence['public_json_contents']['plan.json']
        plan = saved['preparation_plan']
        if (plan != json.loads(PREPARATION.read_text(encoding='utf-8'))
                or canonical_sha(plan) != saved['plan_sha256']):
            raise ValueError('unexecuted_historical_plan_changed')
        # Closed history retains its sealed identity; current requests must
        # still reconstruct exactly. This does not grant current qualification.
        _, requests = prepare_qualification()
        for row in plan['cases']:
            if hashlib.sha256(requests[row['key']]).hexdigest() != evidence['original_file_sha256'][
                    row['key'].replace(':', '-') + '-prepared-request.json']:
                raise ValueError('unexecuted_historical_request_changed')
        return plan, {r['key']:requests[r['key']] for r in plan['cases']}
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs',coach_contract=ROLE_COACH_CONTRACT)
    evidence = interruption()
    original = evidence['public_json_contents']['plan.json']['preparation_plan']
    current, requests = prepare_qualification()
    if original['identity'] != current['identity']:
        raise ValueError('unexecuted_candidate_changed')
    keys = evidence['unexecuted_keys']
    if (keys != [r['key'] for r in original['cases'][3:]]
            or evidence['incomplete_keys'] != ['scope:3']):
        raise ValueError('unexecuted_parent_inventory_changed')
    rows = [r for r in current['cases'] if r['key'] in keys]
    if rows != original['cases'][3:]:
        raise ValueError('unexecuted_input_changed')
    budgets = original['case_budgets'][3:]
    total = {k:sum(b[k] for b in budgets) for k in budgets[0]}
    # The elapsed counter was lost. Charge each started case its entire time
    # allowance; neither stream times nor wall-clock estimates refund it.
    charge = dict(max_calls=evidence['provider_requests'],
        max_tokens=evidence['input_tokens']+evidence['output_tokens'],
        max_seconds=sum(b['max_seconds'] for b in original['case_budgets'][:3]))
    if evidence['unknown_usage_calls'] or any(total[k]+charge[k]>original['batch_budget'][k] for k in total):
        raise ValueError('unexecuted_original_budget_exceeded')
    output = total['max_calls']*32768
    estimate = (Decimal(output)*28+Decimal(total['max_tokens']-output)*8)/1_000_000
    source_paths = (*original['source_sha256'], 'scripts/run_role_unexecuted_qualification.py')
    plan = dict(original, experiment=EXPERIMENT, identity=current['identity'], cases=rows, case_budgets=budgets,
        parent_interruption_sha256=prior.INTERRUPTION_SHA, parent_plan_sha256=evidence['plan_sha256'],
        charged_prior_budget=charge, original_batch_budget=original['batch_budget'],
        excluded_started_keys=[r['key'] for r in original['cases'][:3]],
        batch_budget=dict(total,estimated_uncached_cny=str(estimate),hard_billing_cap=False),
        host_handoff='bounded_file_decisions',
        source_sha256={p:hashlib.sha256((ROOT/p).read_text(encoding='utf-8').encode()).hexdigest() for p in source_paths},
        success_scope='Nine previously untouched original controls only. No restart or acceptance of interrupted scope:3, no automatic original15/product admission.')
    return plan,{r['key']:requests[r['key']] for r in rows}


def verify_original_seal():
    evidence = interruption()
    run = _within(ROOT,evidence['run_directory'])
    hashes = evidence['original_file_sha256']
    if {p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file()} != set(hashes):
        raise ValueError('unexecuted_parent_inventory_changed')
    if any(hashlib.sha256(_within(run,p).read_bytes()).hexdigest()!=sha for p,sha in hashes.items()):
        raise ValueError('unexecuted_parent_raw_changed')


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('unexecuted_batch_closed_or_exists')
    plan,requests=prepare()
    sha=canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output,plan)
        return dict(plan_sha256=sha,budget=plan['batch_budget'],charged_prior_budget=plan['charged_prior_budget'],
            keys=[r['key'] for r in plan['cases']],provider_requests=0,execution_enabled=False,
            historical_closed=CLOSED_RESULT.exists())
    if (not args.env_file or not args.ci_run or args.plan_sha!=sha
            or plan!=json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('unexecuted_preparation_required')
    verify_original_seal()
    head=verify_public_ci(args.ci_run)
    accepted=qualify([ROOT/'data/runs/role_task_observation/role-task-observation-v1'],evidence_root=ROOT,
        output_directory=ROOT/'data/runs/role_task_observation'/('qualification-before-'+EXPERIMENT),
        closed_exports=[(prior.PRIOR_RESULT,prior.PRIOR_SHA)])
    if accepted['validated_keys'] != ['claim-scope:1','claim-scope:4','attribution:1']:
        raise ValueError('unexecuted_prior_qualification_changed')
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=sha,head_sha=head,ci_run=args.ci_run))
    for key,raw in requests.items():
        with (RUN_DIRECTORY/(key.replace(':','-')+'-prepared-request.json')).open('xb') as f:
            f.write(raw)
    generator,reviewer=load_role_settings(args.env_file)
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport')
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,adjudicate=adjudicate_file,workflow_type=Workflow,
            replay=replay_case,success_field='tasks_observed',task_observer=prior.StrictObserver,
            before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    args=parser.parse_args()
    result=run(args)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if args.execute and not result['tasks_observed']:
        raise SystemExit(1)
