"""Actual edit/fresh review after the sealed boundary-example controls.

Reuse the established two-call tail. The initial review is an explicit offline
injection, never counted as another live call or a continuous original15 case.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as BaseWorkflow
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_stream_bridge import RESPONSE, validate_request, CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID
from app.evaluation.coarse_role_qualification import frozen_cases, size
from app.runtime.coach_contract import CORRECTION_SCOPE_COACH_CONTRACT as CONTRACT
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.review_boundary_examples import EXAMPLES as RULE, request_for
from scripts.run_coarse_revision_tail import adjudicate_file
from scripts.run_review_boundary_examples_diagnostic import CLOSED_RESULT as EVIDENCE, sha, read
from scripts.run_role_review_containment import observe
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_golden_inference_development import verify_public_ci
from scripts.diagnose_role_context import canonical_sha
from scripts.diagnose_block_review_route import route_environment

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = 'boundary-examples-revision-tail-v1'
EVIDENCE_SHA = '1a4df090a2d5d1f575b307f90b54e6c25bfc823d9c34db920fca4f8a96635ddc'
PREPARATION = ROOT/'data/evaluation/results/golden_boundary_examples_tail_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_boundary_examples_tail_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/role_containment'/EXPERIMENT


class Workflow(BaseWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs.get('previous_raw') is not None or kwargs.get('diagnostics') is not None:
            raise ValueError('boundary_examples_reassessment_forbidden')
        if kwargs.get('accepted') is not None:
            return BaseWorkflow.make_request(inputs, **kwargs)
        return request_for(inputs)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        if previous_raw is not None:
            raise ValueError('boundary_examples_reassessment_forbidden')
        payload, wire, journal = BaseWorkflow.validate_review(raw, inputs)
        return payload, wire, dict(journal, diagnostic_experiment=EXPERIMENT,
            validator_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(Workflow.make_request(inputs).messages[0].content))


def prepare():
    if sha(EVIDENCE) != EVIDENCE_SHA:
        raise ValueError('boundary_examples_tail_evidence_changed')
    evidence = read(EVIDENCE)
    public = evidence['public_json_contents']
    if not evidence['execution_result']['pair_accepted']:
        raise ValueError('boundary_examples_tail_pair_not_accepted')
    source = next(s for f, s in frozen_cases()[0] if f['key'] == 'scope:3')
    inputs = Workflow.build_inputs(source)
    arm = 'scope-3/'
    journal = public[arm+'journal.json']
    response = RESPONSE.validate_json(compact(public[arm+'response.json']), strict=True)
    initial = Workflow.make_request(inputs)
    initial_sha = hashlib.sha256(validate_request(initial, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
    if (initial_sha != evidence['original_file_sha256']['scope-3-prepared-request.json']
            or digest(inputs.data_json) != journal['input_sha256']
            or digest(source.report) != journal['report_sha256']
            or json.loads(journal['raw']) != response.tool_calls[0].arguments
            or journal['policy_sha256'] != digest(initial.messages[0].content)):
        raise ValueError('boundary_examples_tail_initial_binding')
    for name in ('host-decision.json', 'independent-review.json'):
        host = public[arm+name]
        if (host['accepted'] is not True or host['defects'] != []
                or host['response_sha256'] != evidence['original_file_sha256'][arm+'response.json']
                or host['input_sha256'] != digest(inputs.data_json)
                or host['report_sha256'] != digest(source.report)):
            raise ValueError('boundary_examples_tail_initial_not_accepted')
    payload, wire, _ = Workflow.validate_review(journal['raw'], inputs)
    if payload.verdict != 'needs_revision':
        raise ValueError('boundary_examples_tail_initial_verdict')
    editor = Workflow.make_request(inputs, accepted=wire)
    if size(editor) + 32768 > 96768:
        raise ValueError('boundary_examples_tail_capacity')
    paths = ('scripts/run_boundary_examples_tail.py', 'scripts/review_boundary_examples.py', 'scripts/export_boundary_examples_tail.py',
        'scripts/run_role_review_containment.py', 'scripts/run_coarse_revision_tail.py',
        'app/evaluation/golden_role_correction_scope.py', 'app/evaluation/golden_coarse_source_projection.py')
    cost = sum((Decimal(64000) * p.input_cost_per_million + Decimal(32768) * p.output_cost_per_million)
        / 1_000_000 for p in (CONTRACT.pricing_profiles[('zhipu', model)]
            for model in ('glm-5.3-flash', 'glm-5.3')))
    plan = dict(experiment=EXPERIMENT, fixture_evidence_sha256=EVIDENCE_SHA,
        original_report_sha256=digest(source.report), original_input_sha256=digest(inputs.data_json),
        initial_prepared_request_sha256=initial_sha,
        injected_public_response_sha256=digest(RESPONSE.dump_json(response).decode()),
        editor_request_sha256=hashlib.sha256(validate_request(editor, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
        editor_input_ceiling=size(editor), diagnostic_rule_sha256=digest(RULE),
        source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        budget=dict(max_calls=2, max_tokens=193536, max_seconds=600, max_output_per_call=32768,
            max_seconds_per_call=300, sdk_retries=0, estimated_uncached_cny=str(cost),
            estimate_scope='One Flash edit plus one GLM review, each 64000 input and 32768 output reserved. Uncached estimate, not invoice.'),
        initial_review_accepted=True, offline_initial_injections=1, diagnostic_only=True, execution_authorized=False,
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False,
        stop_rule='Stop on rejected edit, wrong final review, source/identity/transport/budget failure. No retry or reassessment.',
        success_scope='Actual edit and fresh review with the same fixed example policy; not continuous original15 or product qualification.')
    return plan, (source, response, initial, editor)


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('boundary_examples_tail_closed_or_exists')
    plan, prepared = prepare()
    if not args.execute:
        if args.output:
            write_new_json(args.output, plan)
        return dict(plan_sha256=canonical_sha(plan), budget=plan['budget'], provider_requests=0, execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha != canonical_sha(plan)
            or plan != read(PREPARATION)):
        raise ValueError('boundary_examples_tail_preparation_required')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json', dict(preparation_plan=plan, plan_sha256=canonical_sha(plan),
        head_sha=head, ci_run=args.ci_run))
    write_new_json(RUN_DIRECTORY/'source.json', dict(report=prepared[0].report,
        input_json=Workflow.build_inputs(prepared[0]).data_json))
    (RUN_DIRECTORY/'prepared-editor-request.json').write_bytes(validate_request(prepared[3], transport_id=CAPACITY_TRANSPORT_ID))
    generation, reviewer = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=generation, reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport', source_projection=PROJECTION)
    with route_environment('direct'):
        return observe(factory, RUN_DIRECTORY, plan, prepared, workflow_type=Workflow,
            initial_review_accepted=True, coach_contract=CONTRACT, adjudicate=adjudicate_file,
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
    if args.execute and not result['tail_accepted']:
        raise SystemExit(1)
