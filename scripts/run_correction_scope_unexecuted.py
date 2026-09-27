"""Continue only untouched controls after the sealed host-quota interruption.

No started case is retried and no deadline is restarted. Prior charges remain
inside the original batch cap. Strict qualification still lacks the interrupted
case even if all thirteen untouched controls pass.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation import correction_scope_qualification as qualification
from app.evaluation.golden_review_experiment import digest, compact
from app.evaluation.role_qualification import ROOT
from scripts import run_correction_scope_qualification as prior
from scripts.qualify_role_observations import inspect_runs

EXPERIMENT = 'correction-scope-unexecuted-v1'
RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/EXPERIMENT
PREPARATION = ROOT/'data/evaluation/results/golden_correction_scope_unexecuted_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_correction_scope_unexecuted_result_v1.json'


def prepare():
    raw = prior.CLOSED_RESULT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != prior.CLOSED_SHA:
        raise ValueError('correction_scope_parent_seal_changed')
    evidence = json.loads(raw)
    plan = evidence['public_json_contents']['plan.json']['preparation_plan']
    result = evidence['public_json_contents']['result.json']
    current, requests = qualification.prepare_qualification()
    if (plan['identity'] != current['identity'] or plan['cases'] != current['cases']
            or plan['original15_plan_sha256'] != digest(compact(current))):
        raise ValueError('correction_scope_parent_identity_changed')
    if (result.get('error_code') != 'task_observation_host_deadline'
            or evidence['completed_keys'] != ['claim-scope:1']
            or evidence['incomplete_keys'] != ['claim-scope:4']
            or evidence['unexecuted_keys'] != [r['key'] for r in plan['cases'][2:]]
            or evidence['unknown_usage_calls'] != 0):
        raise ValueError('correction_scope_parent_boundary_changed')
    budgets = plan['case_budgets'][2:]
    totals = {k: sum(b[k] for b in budgets) for k in budgets[0]}
    charged = dict(max_calls=evidence['provider_requests'],
        max_tokens=evidence['input_tokens'] + evidence['output_tokens'],
        max_seconds=evidence['actual_batch_elapsed_seconds'])
    if any(charged[k] + totals[k] > plan['batch_budget'][k] for k in totals):
        raise ValueError('correction_scope_original_budget_exceeded')
    paths = (*plan['source_sha256'], 'scripts/run_correction_scope_unexecuted.py')
    output = totals['max_calls'] * 32768
    estimate = (Decimal(output)*28 + Decimal(totals['max_tokens']-output)*8)/1_000_000
    continuation = dict(plan, experiment=EXPERIMENT, cases=plan['cases'][2:], case_budgets=budgets,
        parent_seal_sha256=prior.CLOSED_SHA, parent_plan_sha256=evidence['plan_sha256'],
        charged_prior_budget=charged, original_batch_budget=plan['batch_budget'],
        excluded_started_keys=['claim-scope:1', 'claim-scope:4'],
        source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        batch_budget=dict(totals, estimated_uncached_cny=str(estimate), hard_billing_cap=False),
        success_scope='Thirteen untouched controls only. Prior valid prefix is separate; interrupted claim-scope:4 remains unqualified. No retry or complete original15/product admission.')
    return continuation, {r['key']: requests[r['key']] for r in continuation['cases']}


def verify_parent():
    # Execution inspects raw files and durable completion, not summary flags.
    _, rebuilt, _, accepted, keys, _ = inspect_runs([prior.RUN_DIRECTORY],
        evidence_root=ROOT, closed_exports=[(prior.CLOSED_RESULT, prior.CLOSED_SHA)],
        profile='correction-scope')
    current, _ = qualification.prepare_qualification()
    if rebuilt != current or keys != {'claim-scope:1'} or len(accepted) != 1:
        raise ValueError('correction_scope_parent_prefix_invalid')


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('correction_scope_unexecuted_closed_or_exists')
    plan, requests = prepare()
    if args.execute:
        verify_parent()
    return prior.execute_prepared(args, plan, requests, directory=RUN_DIRECTORY,
        preparation=PREPARATION)


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
