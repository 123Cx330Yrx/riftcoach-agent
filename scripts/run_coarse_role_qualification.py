"""Bounded original-15 observation under the explicit coarse runtime.

Reuse the existing continuous executor, durable completions and strict source
reviews. Only the separate sealed audit may grant original-set qualification.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path

from app.evaluation import coarse_role_qualification as qualification
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.role_qualification import ROOT
from app.evaluation.role_task_outcome import VERSION
from app.runtime.coach_contract import COARSE_ROLE_COACH_CONTRACT as CONTRACT
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_qualification_pair import observe
from scripts.run_role_remaining_qualification import StrictObserver
from scripts.run_role_task_observation import Observer, adjudicate_file, await_case_ready
from scripts.qualify_role_observations import _stage, _sha

EXPERIMENT = 'coarse-role-qualification-v1'
RUN_DIRECTORY = ROOT / 'data/runs/role_task_observation' / EXPERIMENT
PREPARATION = ROOT / 'data/evaluation/results/golden_coarse_qualification_preparation_v1.json'
CLOSED_RESULT = ROOT / 'data/evaluation/results/golden_coarse_qualification_result_v1.json'


class CoarseObserver(StrictObserver):
    @staticmethod
    def finish(plan, row, calls, decisions):
        return Observer.finish_with_backend(plan, row, calls, decisions, backend=qualification)


def replay(frozen, source, calls):
    return qualification.replay_case(frozen, source, calls, include_stage_evidence=False)


def validate_handoff(path, decision, plan, *, directory):
    """Check both source inspections before permitting the next paid call."""
    stage = json.loads(path.read_bytes())
    row = next(r for r in plan['cases'] if r['key'] == stage['key'])
    if not CoarseObserver.validate_stage(plan, row, path, decision):
        return decision
    transport = directory/'transport'/row['key'].replace(':', '-')
    calls = qualification.read_calls(transport)
    expected_roles = ['review'] if stage['stage']=='initial' else (
        ['review', 'revision'] if stage['stage']=='revision' else ['review', 'revision', 'review'])
    if ([c['binding']['role'] for c in calls] != expected_roles
            or not all(c['completed'] for c in calls)):
        raise ValueError('coarse_qualification_stage_call_inventory')
    _stage(path.parent, {k:stage[k] for k in ('stage','report','journal')}, row,
        digest(compact(plan['identity'])), _sha(path.parent/'source.json'),
        calls[-1], transport, pending_host=decision)
    return decision


def prepare():
    original, requests = qualification.prepare_qualification()
    rows = original['cases']
    budgets = []
    for row in rows:
        calls = 1 if row['expected_initial'] == 'accept' else 3
        if row['first_input_ceiling'] + 32768 > 96768:
            raise ValueError('coarse_qualification_input_capacity')
        budgets.append(dict(max_calls=calls, max_tokens=calls * 96768,
            max_seconds=300 if calls == 1 else 900))
    totals = {k: sum(b[k] for b in budgets) for k in budgets[0]}
    price = CONTRACT.pricing_profiles[('zhipu', 'glm-5.3')]
    cost = totals['max_calls'] * (Decimal(64000) * price.input_cost_per_million
        + Decimal(32768) * price.output_cost_per_million) / 1_000_000
    paths = ('scripts/run_coarse_role_qualification.py', 'scripts/run_role_qualification_pair.py',
        'scripts/run_role_task_observation.py', 'scripts/run_role_remaining_qualification.py',
        'scripts/qualify_role_observations.py', 'app/evaluation/role_task_outcome.py',
        'app/evaluation/role_qualification.py', 'app/evaluation/coarse_role_qualification.py')
    plan = dict(experiment=EXPERIMENT, observation_version=VERSION, identity=original['identity'],
        original15_plan_sha256=digest(compact(original)), original15_keys=[r['key'] for r in rows],
        cases=rows, case_budgets=budgets, source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        batch_budget=dict(totals, estimated_uncached_cny=str(cost), hard_billing_cap=False),
        labels_sent_to_model=False, sdk_retries=0, allow_reassessment=False,
        stop_rule='Stop on the first rejected stage, wrong verdict, protocol, source, identity, transport or budget failure. No retry, reassessment or incidental-error exception.',
        success_scope='Fresh continuous original15 controls; no natural generation, product consumption or production admission.',
        failure_decision='Preserve the earliest divergence and all charges. Diagnose before further paid work; no automatic new batch or prompt variant.',
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False)
    return plan, requests


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('coarse_qualification_closed_or_exists')
    plan, requests = prepare()
    sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output, plan)
        return dict(plan_sha256=sha, budget=plan['batch_budget'], cases=len(plan['cases']),
            provider_requests=0, execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha != sha
            or plan != json.loads(PREPARATION.read_bytes())):
        raise ValueError('coarse_qualification_preparation_required')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json', dict(preparation_plan=plan, plan_sha256=sha,
        head_sha=head, ci_run=args.ci_run))
    for key, raw in requests.items():
        (RUN_DIRECTORY/(key.replace(':', '-')+'-prepared-request.json')).write_bytes(raw)
    generator, reviewer = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=generator, reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport', source_projection=PROJECTION)
    def adjudicate(path, remaining):
        return validate_handoff(path, adjudicate_file(path, remaining), plan, directory=RUN_DIRECTORY)
    with route_environment('direct'):
        return observe(factory, RUN_DIRECTORY, plan, adjudicate=adjudicate, workflow_type=Workflow,
            replay=replay, success_field='tasks_observed', task_observer=CoarseObserver,
            coach_contract=CONTRACT, before_case=await_case_ready,
            before_send=lambda: require_unchanged_checkout(head))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    result = run(args)
    print(compact(result), flush=True)
    if args.execute and not result['tasks_observed']:
        raise SystemExit(1)
