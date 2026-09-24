"""Preview the closed historical Flash comparison; execute is permanently closed.

Plans retain the historical candidate and requests. Preview serialization has
its own digest; it cannot reopen the old batch or qualify current behavior.
"""
import argparse
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, frozen_cases
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from scripts.diagnose_block_review_route import route_environment
from scripts.prepare_role_qualification import prepare_comparison
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_review_model_comparison import observe

EXPERIMENT = 'role-explicit-source-flash-comparison-v1'
RUN_ROOT = ROOT / 'data/runs/model_comparison'
RUN_DIRECTORY = RUN_ROOT / EXPERIMENT
LIMITS = dict(max_calls=2, max_seconds_total=600, max_seconds_per_call=300,
              total_token_reservation=154846)


def prepare_pair():
    """Rebuild and compare exact frozen requests before credentials or IO."""
    plan, prepared_bytes = prepare_comparison()
    sources = {frozen['key']: source for frozen, source in frozen_cases()[0]}
    if (plan['experiment'] != EXPERIMENT or plan['model'] != 'glm-5.3-flash'
            or plan['reasoning_effort'] != 'high' or plan['sdk_retries'] != 0
            or plan['transport_id'] != CAPACITY_TRANSPORT_ID
            or any(plan['proposed_diagnostic_budget'][key] != value for key, value in LIMITS.items())
            or [cell['source_case'] for cell in plan['cells']] != ['attribution:1', 'claim-scope:1']):
        raise ValueError('flash_source_comparison_plan_identity')
    variants = []
    for cell in plan['cells']:
        inputs = review.native.build_inputs(sources[cell['source_case']])
        request = RoleReviewWorkflow.make_request(inputs)
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        if (raw != prepared_bytes[cell['id']]
                or hashlib.sha256(raw).hexdigest() != cell['request_sha256']
                or digest(inputs.data_json) != cell['input_sha256']
                or request.max_tokens != cell['output_cap']
                or request.timeout_s != 300):
            raise ValueError('flash_source_comparison_input_changed')
        variants.append((cell['id'], inputs, request))
    return variants, plan


def run(args):
    if args.execute:
        raise ValueError('flash_source_comparison_batch_closed')
    variants, plan = prepare_pair()
    plan_sha = digest(compact(plan))
    summary = dict(experiment=EXPERIMENT, preparation_plan_sha256=plan_sha,
        candidate_program_sha256=plan['candidate']['program_sha256'],
        budget=plan['proposed_diagnostic_budget'], provider_requests=0,
        execution_enabled=False, production_admitted=False, batch_status='closed',
        plan_representation='public_projection_not_original_plan_bytes',
        request_sha256={cell['id']: cell['request_sha256'] for cell in plan['cells']})
    if not args.execute:
        print(compact(summary), flush=True)
        return summary
    if not args.approval_plan_sha:
        raise ValueError('flash_source_comparison_specific_approval_required')
    if args.approval_plan_sha != plan_sha:
        raise ValueError('flash_source_comparison_approval_plan_mismatch')
    # No user-controlled path or run ID. Reject symlink escapes and any old
    # directory, including an incomplete batch, before credentials or calls.
    directory = RUN_DIRECTORY.resolve()
    if (directory.parent != RUN_ROOT.resolve() or directory.name != EXPERIMENT
            or not RUN_ROOT.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError('flash_source_comparison_output_path')
    if directory.exists():
        raise ValueError('flash_source_comparison_batch_exists')
    head = verify_public_ci(args.ci_run)
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / 'plan.json', dict(preparation_plan=plan,
        declared_approved_plan_sha256=args.approval_plan_sha, execution_head_sha=head,
        ci_run=args.ci_run, host_resume='stdin accept/reject response SHA; deadline never resets'))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model='glm-5.3-flash')
    provider = ReceiptedStreamProvider(settings=settings, directory=directory / 'transport',
        transport_id=CAPACITY_TRANSPORT_ID)
    with route_environment('direct'):
        result = observe(provider, directory, variants, plan,
            reviewer_profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE,
            transport_id=CAPACITY_TRANSPORT_ID)
    print(compact(result), flush=True)
    return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--execute', action='store_true')
    result.add_argument('--approval-plan-sha', default='')
    result.add_argument('--ci-run', default='')
    result.add_argument('--env-file', type=Path)
    return result


if __name__ == '__main__':
    run(parser().parse_args())
