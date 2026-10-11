"""Prepare/run the original fifteen with the tested review-bound revision protocol.

Shares the v2 CI/native identity/budget/host gates. No fixture injection or
historical success transfer; a new paid batch requires its frozen authorization.
"""
import argparse
from pathlib import Path

from app.evaluation import review_bound_qualification as backend
from app.evaluation.golden_review_experiment import compact
from scripts import run_boundary_examples_v2 as base
from scripts.review_independence_contract import FINAL_POLICY

EXPERIMENT = 'review-bound-original15-20261008'


def prepare(*, root_thread_id, independent_thread_id, experiment=EXPERIMENT,
            max_host_seconds=86400):
    return base.prepare(root_thread_id=root_thread_id,
        independent_thread_id=independent_thread_id, experiment=experiment,
        max_host_seconds=max_host_seconds, host_review_evidence_policy=FINAL_POLICY,
        backend=backend)


def run(args):
    if args.host_review_evidence_policy != FINAL_POLICY:
        raise ValueError('review_bound_evidence_policy')
    return base.run(args, backend=backend)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--experiment', default=EXPERIMENT)
    parser.add_argument('--max-host-seconds', type=int, default=86400)
    parser.set_defaults(host_review_evidence_policy=FINAL_POLICY)
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
    if args.execute and not result['tasks_observed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
