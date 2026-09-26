"""Prepared two-call source-address diagnostic; requires a separate user decision.

The approval-plan hash binds that decision to exact prepared inputs; it is not
itself permission to spend. The previous stopped batch can never be resumed.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from app.evaluation.golden_explicit_source_projection import project_request
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID
from scripts.check_review_source_projection import build_evidence, OUTPUT, ROOT
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_review_target_layout import prepare
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_review_model_comparison import observe

EXPERIMENT = 'review-explicit-source-pair-v1'
LIVE_STATUS = 'completed_pair_requires_role_decision'
RUN_DIRECTORY = ROOT / 'data/runs/model_comparison' / EXPERIMENT


def prepare_pair():
    evidence = build_evidence()
    if evidence != json.loads(OUTPUT.read_text(encoding='utf-8')):
        raise ValueError('explicit_source_frozen_evidence_changed')
    variants = [(name, inputs, project_request(request, inputs))
                for name, inputs, request in prepare()[0] if name.endswith('-baseline')]
    reservation = evidence['future_pair_reservation_only']
    plan = dict(experiment=EXPERIMENT, preparation_sha256=digest(compact(evidence)),
        cells=[dict(id=c['id'], input_reservation=c['projected_input_ceiling'], output_cap=32768)
               for c in evidence['cells']],
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600,
            max_seconds_per_call=300, total_token_reservation=reservation['total_tokens']))
    return variants, plan


def run(args):
    if args.execute and LIVE_STATUS != 'approved_bounded_pair_after_exact_ci':
        raise ValueError('completed_source_pair_no_retry')
    if args.execute and not args.approval_plan_sha:
        raise ValueError('explicit_source_specific_approval_required')
    variants, plan = prepare_pair()
    if not args.execute:
        print(compact(plan), flush=True)
        return plan
    if args.approval_plan_sha != plan['preparation_sha256']:
        raise ValueError('explicit_source_approval_plan_mismatch')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY / 'plan.json', dict(plan, execution_head_sha=head,
        ci_run=args.ci_run, approved_plan_sha256=args.approval_plan_sha))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model='glm-5.3')
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY / 'transport',
                                      transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        result = observe(provider, RUN_DIRECTORY, variants, plan)
    print(compact(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approval-plan-sha', default='')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    run(parser.parse_args())
