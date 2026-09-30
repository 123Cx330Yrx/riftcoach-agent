"""Continue an interrupted native v2 boundary batch from its durable prefix.

The continuation is a new execution directory. It consumes only untouched
cases, keeps the interrupted parent read-only, and leaves qualification to the
existing full-source auditor over both runs.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import re

from app.evaluation.golden_review_experiment import compact, digest
from scripts import run_boundary_examples_qualification as runner
from scripts import run_boundary_examples_v2 as v2
from scripts import qualify_role_observations as audit
from scripts.role_development_host_clock import validate_adopted_timing
from scripts.codex_review_event_source import CodexHostReviewEventSource, CodexReadOnlyClient
from scripts.review_independence_contract import MODE_V2, freeze_v2_identity

RUN_ROOT = runner.ROOT / 'data/runs/role_task_observation'
EXPERIMENT = 'boundary-examples-independent-v2-continuation-20260930'


def read_parent(prior_run, prior_export, prior_sha, *, root=runner.ROOT):
    root = Path(root).resolve()
    prior_run = audit._within(root, prior_run)
    prior_export = audit._within(root, prior_export)
    audit._seal(prior_run, prior_export, prior_sha, root)
    saved = json.loads((prior_run / 'plan.json').read_bytes())
    prior = saved['preparation_plan']
    if (prior.get('host_review_submission_mode') != MODE_V2
            or saved.get('plan_sha256') != runner.canonical_sha(prior)):
        raise ValueError('boundary_v2_continuation_prior_mode')
    result = json.loads((prior_run/'result.json').read_bytes()) if (prior_run/'result.json').exists() else None
    if result is not None and not any(k in result for k in ('error_code', 'error_type')):
        raise ValueError('boundary_v2_continuation_parent_not_interrupted')
    outcomes, elapsed, boundary = audit._interrupted_prefix(
        prior_run, prior, result, backend=runner.qualification)
    timing = validate_adopted_timing(prior_run, prior,
        saved_plan_sha256=saved['plan_sha256'], allow_unfinished_tail=True)
    completed = [row['key'] for row in outcomes]
    if (completed != ['claim-scope:1'] or boundary['unqualified_started_cases']
            or boundary['unknown_usage_calls'] or 'unfinished_tail' not in timing
            or timing['unfinished_tail']['key'] != prior['cases'][len(completed)]['key']):
        raise ValueError('boundary_v2_continuation_prefix')
    summaries = [runner.qualification.summarize_role_calls(
        prior_run/'transport'/row['key'].replace(':', '-')) for row in prior['cases']]
    charge = dict(max_calls=boundary['full_batch_reserved_calls'],
        max_tokens=boundary['full_batch_charged_tokens'],
        max_seconds=prior['batch_budget']['max_seconds']
            - timing['unfinished_tail']['remaining_active_seconds'])
    if charge['max_seconds'] + .01 < elapsed:
        raise ValueError('boundary_v2_continuation_elapsed_mismatch')
    accounting = dict(reserved_calls=charge['max_calls'], known_tokens=charge['max_tokens'],
        unknown_usage_calls=boundary['unknown_usage_calls'],
        estimated_uncached_cny=str(sum((Decimal(s['known_usage_estimated_uncached_cny'])
            for s in summaries if s.get('known_usage_estimated_uncached_cny') is not None), Decimal(0))))
    return prior_run, prior_export, saved, completed, charge, accounting


def prepare(*, prior_run, prior_export, prior_sha, root_thread_id, independent_thread_id,
            experiment=EXPERIMENT, max_host_seconds=86400, root=runner.ROOT):
    if not isinstance(experiment, str) or re.fullmatch(r'[a-z0-9][a-z0-9-]{0,100}', experiment) is None:
        raise ValueError('boundary_v2_continuation_experiment_invalid')
    prior_run, prior_export, saved, completed, charge, accounting = read_parent(
        prior_run, prior_export, prior_sha, root=root)
    prior = saved['preparation_plan']
    current, all_requests = runner.prepare_fresh(experiment=experiment)
    if (prior['identity'] != current['identity'] or prior['cases'] != current['cases']
            or prior['original15_keys'] != current['original15_keys']
            or prior['original15_plan_sha256'] != current['original15_plan_sha256']):
        raise ValueError('boundary_v2_continuation_candidate_changed')
    for key, raw in all_requests.items():
        if (prior_run/(key.replace(':', '-')+'-prepared-request.json')).read_bytes() != raw:
            raise ValueError('boundary_v2_continuation_request_changed')
    remaining = [key for key in prior['original15_keys'] if key not in completed]
    if len(remaining) != 14:
        raise ValueError('boundary_v2_continuation_case_count')
    plan, requests = runner.prepare_fresh(experiment=experiment, keys=remaining)
    if any(charge[k] + plan['batch_budget'][k] > prior['batch_budget'][k]
           + (0.01 if k == 'max_seconds' else 0) for k in ('max_calls', 'max_tokens', 'max_seconds')):
        raise ValueError('boundary_v2_continuation_cumulative_budget')
    if (root_thread_id != prior['root_thread_id'] or independent_thread_id !=
            prior['review_principals']['independent']['principal_id']):
        raise ValueError('boundary_v2_continuation_principal_changed')
    if not 0 < max_host_seconds <= prior['host_review_timing']['max_host_seconds']:
        raise ValueError('boundary_v2_continuation_host_budget')
    # Keep the original fifteen-case identity so the strict auditor can join
    # this run to the durable accepted prefix without injecting old calls.
    plan['original15_plan_sha256'] = prior['original15_plan_sha256']
    plan['original15_keys'] = list(prior['original15_keys'])
    plan['host_review_submission_mode'] = MODE_V2
    plan = freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)
    plan = runner.adopt_host_timing(plan, max_host_seconds=max_host_seconds)
    plan['prior_interrupted_batch'] = dict(
        run_directory=prior_run.relative_to(Path(root).resolve()).as_posix(),
        closed_export=prior_export.relative_to(Path(root).resolve()).as_posix(),
        closed_export_sha256=prior_sha, plan_sha256=saved['plan_sha256'],
        accepted_prefix_keys=completed, accounting=accounting, charged_budget=charge)
    plan['cumulative_reserved_budget'] = {k: charge[k] + plan['batch_budget'][k]
        for k in ('max_calls', 'max_tokens', 'max_seconds')}
    plan['cumulative_estimated_uncached_cny'] = str(Decimal(accounting['estimated_uncached_cny'])
        + Decimal(plan['batch_budget']['estimated_uncached_cny']))
    plan['authorization_scope'] = (
        'Fresh continuation for the fourteen untouched original controls. '
        'The interrupted parent is read-only; no request or verdict is reused.')
    plan['success_scope'] = (
        'Fourteen new continuous controls joined only with the separately audited '
        'claim-scope:1 prefix; no natural generation or product admission.')
    paths = ('scripts/run_boundary_examples_v2_continuation.py',
             'scripts/run_boundary_examples_v2.py',
             'scripts/role_development_host_clock.py',
             'scripts/run_role_coach_development.py',
             'scripts/run_golden_inference_development.py')
    for path in paths:
        plan['source_sha256'][path] = digest((runner.ROOT / path).read_text(encoding='utf-8'))
    return plan, requests


def verify_native_principals(client, plan):
    return v2.verify_native_principals(client, plan)


def run(args):
    directory = RUN_ROOT / args.experiment
    if directory.exists():
        raise ValueError('boundary_v2_continuation_exists')
    plan, requests = prepare(prior_run=args.prior_run, prior_export=args.prior_export,
        prior_sha=args.prior_sha,
        root_thread_id=args.root_thread_id,
        independent_thread_id=args.independent_thread_id,
        experiment=args.experiment, max_host_seconds=args.max_host_seconds)
    directory = RUN_ROOT / plan['experiment']
    if directory.exists():
        raise ValueError('boundary_v2_continuation_exists')
    if not args.execute:
        return runner.execute_prepared(args, plan, requests, directory=directory,
            preparation=args.preparation)
    if (not args.preparation or not args.env_file or not args.ci_run
            or not args.codex_executable
            or args.plan_sha != runner.canonical_sha(plan)
            or plan != json.loads(args.preparation.read_bytes())):
        raise ValueError('boundary_v2_continuation_preparation_required')
    with CodexReadOnlyClient(args.codex_executable) as client:
        verify_native_principals(client, plan)
        source = CodexHostReviewEventSource(client, plan)
        audited = audit.inspect_runs([args.prior_run], evidence_root=runner.ROOT,
            closed_exports=[(args.prior_export, args.prior_sha)],
            profile='boundary-examples', event_source=source)
        if audited[4] != set(plan['prior_interrupted_batch']['accepted_prefix_keys']):
            raise ValueError('boundary_v2_continuation_parent_not_qualified')
        audit._seal(Path(args.prior_run).resolve(), Path(args.prior_export).resolve(),
            args.prior_sha, runner.ROOT)
        return runner.execute_prepared(args, plan, requests, directory=directory,
            preparation=args.preparation, host_timing=plan['host_review_timing'],
            event_source=source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-run', type=Path, required=True)
    parser.add_argument('--prior-export', type=Path, required=True)
    parser.add_argument('--prior-sha', required=True)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--experiment', default=EXPERIMENT)
    parser.add_argument('--max-host-seconds', type=int, default=86400)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    args = parser.parse_args()
    result = run(args)
    print(compact(result), flush=True)
    if args.execute and not result.get('tasks_observed'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
