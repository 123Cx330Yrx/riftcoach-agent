"""Fresh full-15 v2 entry point; reuse the existing bounded execution chain.

Preview is offline. Explicit execution requires a frozen preparation, exact
plan SHA, same-HEAD public CI, and native independent host identity. It never
resumes an existing directory or borrows a historical qualification.
"""
import argparse
import json
from pathlib import Path
import re

from app.evaluation.golden_review_experiment import compact, digest
from scripts import run_boundary_examples_qualification as runner
from scripts.codex_review_event_source import CodexHostReviewEventSource, CodexReadOnlyClient
from scripts.review_independence_contract import MODE_V2, freeze_v2_identity
from scripts.review_independence_contract import (
    evidence_policy, FINAL_POLICY, DISPATCH_POLICY, EVIDENCE_POLICY_FIELD)

RUN_ROOT = runner.ROOT / 'data/runs/role_task_observation'
EXPERIMENT = 'boundary-examples-independent-v2-20260930'


def prepare(*, root_thread_id, independent_thread_id, experiment=EXPERIMENT,
            max_host_seconds=86400, host_review_evidence_policy=DISPATCH_POLICY, backend=None):
    if (not isinstance(experiment, str)
            or re.fullmatch(r'[a-z0-9][a-z0-9-]{0,100}', experiment) is None):
        raise ValueError('boundary_v2_experiment_invalid')
    plan, requests = runner.prepare_fresh(experiment=experiment, **({'backend': backend} if backend is not None else {}))
    plan['host_review_submission_mode'] = MODE_V2
    policy = evidence_policy({EVIDENCE_POLICY_FIELD: host_review_evidence_policy})
    if policy != DISPATCH_POLICY:
        plan[EVIDENCE_POLICY_FIELD] = policy
    plan = freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)
    plan = runner.adopt_host_timing(plan, max_host_seconds=max_host_seconds)
    # Freeze the new entry and the already-adopted timing / credential / CI
    # boundary as well as the existing request and review implementation.
    for path in ('scripts/run_boundary_examples_v2.py',
                 'scripts/role_development_host_clock.py',
                 'scripts/run_role_coach_development.py',
                 'scripts/run_golden_inference_development.py'):
        plan['source_sha256'][path] = digest((runner.ROOT / path).read_text(encoding='utf-8'))
    return plan, requests


def verify_native_principals(client, plan):
    """Read current host lineage before credentials; not a future availability claim."""
    root = plan['root_thread_id']
    independent = plan['review_principals']['independent']['principal_id']
    primary = plan['review_principals']['primary']['principal_id']
    if primary != root or independent == root:
        raise ValueError('boundary_v2_principals_invalid')
    parent = client.request('thread/read', dict(threadId=root, includeTurns=False)).get('thread', {})
    child = client.request('thread/read', dict(threadId=independent, includeTurns=False)).get('thread', {})
    source = child.get('source')
    spawn = source.get('subAgent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
    if (parent.get('id') != root or child.get('id') != independent
            or child.get('parentThreadId') != root or spawn.get('parent_thread_id') != root):
        raise ValueError('boundary_v2_native_lineage_mismatch')
    policy = evidence_policy(plan)
    readability = (client.check_latest_input(child, evidence_policy=policy)
        if policy == FINAL_POLICY else client.check_latest_input(child))
    return dict(root_thread_id=root, independent_thread_id=independent, verified=True,
        independent_agent_path=spawn.get('agent_path'), input_readability=readability)


def run(args, *, backend=None):
    plan, requests = prepare(root_thread_id=args.root_thread_id,
        independent_thread_id=args.independent_thread_id, experiment=args.experiment,
        max_host_seconds=args.max_host_seconds,
        host_review_evidence_policy=getattr(args, EVIDENCE_POLICY_FIELD, DISPATCH_POLICY),
        **({'backend': backend} if backend is not None else {}))
    directory = RUN_ROOT / plan['experiment']
    if directory.exists():
        raise ValueError('boundary_v2_run_already_exists')
    if not args.execute:
        return runner.execute_prepared(args, plan, requests, directory=directory,
            preparation=args.preparation, **({'backend': backend} if backend is not None else {}))
    if (not args.preparation or not args.env_file or not args.ci_run
            or not args.codex_executable or args.plan_sha != runner.canonical_sha(plan)
            or plan != json.loads(args.preparation.read_bytes())):
        raise ValueError('boundary_v2_frozen_preparation_required')
    # Each completed stage still fetches its own exact native dispatch/final.
    # This early lineage read is not a cached review or a substitute approval.
    with CodexReadOnlyClient(args.codex_executable) as client:
        verify_native_principals(client, plan)
        source = CodexHostReviewEventSource(client, plan)
        return runner.execute_prepared(args, plan, requests, directory=directory,
            preparation=args.preparation, host_timing=plan['host_review_timing'],
            event_source=source, **({'backend': backend} if backend is not None else {}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--experiment', default=EXPERIMENT)
    parser.add_argument('--max-host-seconds', type=int, default=86400)
    parser.add_argument('--host-review-evidence-policy', default=DISPATCH_POLICY,
        choices=(DISPATCH_POLICY, FINAL_POLICY), help='Frozen proof policy; never a runtime fallback.')
    parser.add_argument('--output', type=Path, help='Create-only offline plan output.')
    parser.add_argument('--execute', action='store_true', help='Only after explicit new-batch paid authorization.')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    args = parser.parse_args()
    result = run(args)
    print(compact(result), flush=True)
    if args.execute and not result['tasks_observed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
