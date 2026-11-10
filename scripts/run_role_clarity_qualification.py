"""First three original qualification controls for the clarity-marker contract.

Reuses the existing staged review/edit executor and role receipts. This batch
cannot qualify all fifteen or the product. Failure closes the batch, not a
request to silently change a correct report or to retry with new wording.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow
from app.evaluation.role_qualification import ROOT, ASSETS, frozen_cases, prepare_qualification, replay_case
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_qualification_pair import observe

EXPERIMENT = 'role-clarity-qualification-v1'
KEYS = ('claim-scope:1', 'claim-scope:4', 'attribution:1')
PREPARATION = ROOT/'data/evaluation/results/golden_role_clarity_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_role_clarity_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/role_qualification'/EXPERIMENT


def prepare():
    if CLOSED_RESULT.exists():
        raw = CLOSED_RESULT.read_bytes()
        if hashlib.sha256(raw).hexdigest() != '2884776f4f866e67738d43bdb9f4966ec37400486ccb1e6706a0f59aee8dcdd9':
            raise ValueError('clarity_historical_evidence_changed')
        evidence = json.loads(raw)
        saved = evidence['public_json_contents']['plan.json']
        plan = saved['preparation_plan']
        if (plan != json.loads(PREPARATION.read_text(encoding='utf-8'))
                or canonical_sha(plan) != saved['plan_sha256']
                or [c['key'] for c in plan['cases']] != list(KEYS)):
            raise ValueError('clarity_historical_plan_changed')
        sources = {f['key']: source for f, source in frozen_cases()[0]}
        requests = {}
        for row in plan['cases']:
            key = row['key']
            request = RoleClarityReviewWorkflow.make_request(
                RoleClarityReviewWorkflow.build_inputs(sources[key]))
            raw_request = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
            if (hashlib.sha256(raw_request).hexdigest() != row['request_sha256']
                    or row['request_sha256'] != evidence['original_file_sha256'][
                        key.replace(':', '-') + '-prepared-request.json']):
                raise ValueError('clarity_historical_request_changed')
            requests[key] = raw_request
        return plan, requests
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    qualification, requests = prepare_qualification()
    rows = {r['key']: r for r in qualification['cases']}
    cases = [rows[k] for k in KEYS]
    assert [r['expected_initial'] for r in cases] == ['accept','reject','reject']
    # Initial review/reassessment for the positive; full product budget for
    # each negative, including actual edit/final review and allowed recovery.
    budgets = [dict(max_calls=2,max_tokens=193536,max_seconds=600),
               dict(max_calls=5,max_tokens=401920,max_seconds=900),
               dict(max_calls=5,max_tokens=401920,max_seconds=900)]
    total = {key:sum(row[key] for row in budgets) for key in budgets[0]}
    output = total['max_calls']*32768
    # Deliberately price every reserved token at GLM rates: actual Flash edits
    # cost less. This is a conservative estimate, not a billing hard limit.
    cost=(Decimal(output)*28+Decimal(total['max_tokens']-output)*8)/1_000_000
    plan=dict(experiment=EXPERIMENT,qualification_version=qualification['qualification_version'],
        qualification_plan_sha256=digest(compact(qualification)),identity=qualification['identity'],
        cases=cases,case_budgets=budgets,batch_budget=dict(total,estimated_uncached_cny=str(cost),
            hard_billing_cap=False,price_scope='Conservative all-GLM reservation; Flash edits priced higher than actual.'),
        script_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        executor_sha256=hashlib.sha256((ROOT/'scripts/run_role_qualification_pair.py').read_text(encoding='utf-8').encode()).hexdigest(),
        original_15_unchanged=True,labels_sent_to_model=False,sdk_retries=0,
        stop_rule='Stop at first rejected stage, unexpected verdict, unsafe/protocol/transport/identity/budget failure; preserve raw output. Inspect malformed review before any allowed recovery.',
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)
    return plan,{k:requests[k] for k in KEYS}


def run(args):
    if args.execute and CLOSED_RESULT.exists():
        raise ValueError('clarity_qualification_batch_closed')
    plan, requests = prepare()
    sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            with args.output.open('x',encoding='utf-8',newline='\n') as f:
                json.dump(plan,f,ensure_ascii=False,indent=2); f.write('\n')
        return dict(plan_sha256=sha,budget=plan['batch_budget'],provider_requests=0,
            historical_closed=CLOSED_RESULT.exists(),execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha != sha
            or plan != json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('clarity_qualification_preparation_required')
    if RUN_DIRECTORY.exists():
        raise ValueError('clarity_qualification_batch_exists')
    head=verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=sha,
        head_sha=head,ci_run=args.ci_run))
    for key,raw in requests.items():
        (RUN_DIRECTORY/(key.replace(':','-')+'-prepared-request.json')).write_bytes(raw)
    generator,reviewer=load_role_settings(args.env_file)
    factory=RunScopedRoleReceiptedProviderFactory(generator_settings=generator,
        reviewer_settings=reviewer,transport_root=RUN_DIRECTORY/'transport')
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,
            workflow_type=RoleClarityReviewWorkflow,replay=replay_case,success_field='batch_accepted',
            before_send=lambda: require_unchanged_checkout(head))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    print(compact(run(parser.parse_args())),flush=True)
