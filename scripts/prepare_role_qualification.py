"""Prepare the original 15 controls and the next bounded comparison offline.

Only writes reviewable plans and request artifacts, never credentials/provider
IO. These plans do not reopen either completed GLM diagnostic batch.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, frozen_cases, prepare_qualification, candidate_identity
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation import golden_native_partitioned_tool_review as review
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from scripts.prepare_review_model_comparison import sdk_arguments, mock_wire

PAIR_EVIDENCE = ROOT / 'data/evaluation/results/golden_explicit_source_pair_result_0c061b2.json'


def bounded_product_estimate():
    """Conservative uncached ceiling over legal generation/review paths.

    A task needs >=1 generation; a revision costs another Flash call and must
    be followed by review. With five shared calls, at most three GLM reviews
    fit (one reassessment). Never reserve 5 calls separately per model.
    """
    limits = ROLE_COACH_CONTRACT.descriptor()
    prices = ROLE_COACH_CONTRACT.pricing_profiles
    flash, glm = [prices['zhipu', model] for model in ('glm-5.3-flash', 'glm-5.3')]
    # Pay expensive categories first within the shared token ceiling. The
    # five-call path is generation, review, reassessment, revision, final review.
    envelopes = [
        (3 * limits['max_output_tokens'], glm.output_cost_per_million),
        (3 * limits['max_input_tokens'], glm.input_cost_per_million),
        (2 * limits['max_output_tokens'], flash.output_cost_per_million),
        (2 * limits['max_input_tokens'], flash.input_cost_per_million),
    ]
    remaining, cost = limits['total_tokens'], Decimal(0)
    for cap, rate in envelopes:
        reserved = min(remaining, cap)
        cost += Decimal(reserved) * rate / 1_000_000
        remaining -= reserved
    return dict(max_calls=limits['max_calls'], max_seconds=limits['execution_timeout_s'],
        max_tokens=limits['total_tokens'], max_revisions=limits['max_revisions'],
        max_seconds_per_call=limits['request_timeout_s'], max_output_per_call=limits['max_output_tokens'],
        sdk_retries=0, worst_legal_role_path=['generation', 'review', 'review', 'revision', 'review'],
        estimated_uncached_cny=str(cost), price_snapshot='ADR0108/2026-09-22', hard_billing_cap=False,
        estimate_scope='shared-token ceiling; includes one review reassessment, not an actual bill')


def prepare_comparison():
    """Same explicit-ID inputs as the two completed GLM calls, Flash only."""
    previous = json.loads(PAIR_EVIDENCE.read_text(encoding='utf-8'))
    sources = {f['key']: (f, req) for f, req in frozen_cases()[0]}
    cells, requests = [], {}
    for index, (key, name) in enumerate([('attribution:1', 'attribution_original-baseline'),
                      ('claim-scope:1', 'attribution_corrected-baseline')], 1):
        frozen, source = sources[key]
        request = RoleReviewWorkflow.make_request(review.native.build_inputs(source))
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        saved = previous['original_json_contents'][name + '/request.json']
        prior_reservation = previous['original_json_contents'][f'transport/stream-{index:03d}/reservation.json']
        if (json.loads(raw) != saved
                or hashlib.sha256(raw).hexdigest() != prior_reservation['request_sha256']):
            raise ValueError('role_comparison_same_input_changed')
        sdk_body = mock_wire(sdk_arguments(request))
        if sdk_body['model'] != 'glm-5.3-flash':
            raise ValueError('role_comparison_model_mismatch')
        requests[name] = raw
        cells.append(dict(id=name, source_case=key, input_sha256=frozen['input_sha256'],
            report_sha256=frozen['report_sha256'], request_sha256=hashlib.sha256(raw).hexdigest(),
            input_reservation=size(request),
            output_cap=32768, expected_host_only=frozen['expected_initial'], sdk_body=sdk_body,
            same_request_as_glm=True))
    total_input = sum(c['input_reservation'] for c in cells)
    plan = dict(experiment='role-explicit-source-flash-comparison-v1', model='glm-5.3-flash',
        reasoning_effort='high', sdk_retries=0, transport_id=CAPACITY_TRANSPORT_ID,
        candidate=candidate_identity(),
        comparison_evidence_sha256=hashlib.sha256(PAIR_EVIDENCE.read_bytes()).hexdigest(), cells=cells,
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600, max_seconds_per_call=300,
            total_token_reservation=total_input + 65536,
            estimated_uncached_cny=str((Decimal(total_input)*Decimal('0.8') + Decimal(65536)*Decimal('2.8')) / 1_000_000),
            hard_billing_cap=False),
        stop_rule='Stop on the first protocol, identity, citation or semantic failure; inspect complete issue/advisory sources.',
        production_admitted=False, labels_sent_to_model=False, execution_enabled=False,
        paid_execution_authorized=False,
        runner_reuse=dict(module='scripts.run_review_model_comparison', function='observe',
            development_cli='scripts.run_flash_source_review_pair',
            preview_command='python -m scripts.run_flash_source_review_pair',
            execute_arguments=['--execute', '--approval-plan-sha', 'PLAN_SHA256', '--ci-run', 'EXACT_HEAD_CI_RUN', '--env-file', 'AUTHORIZED_ENV_FILE'],
            continuation='Within the same live session, inspect every issue/advisory against full report and sources, then type accept RESPONSE_FILE_SHA256 or reject RESPONSE_FILE_SHA256. Host time counts toward 600 seconds; restart is refused.',
            paid_execution_requires='Specific unconsumed two-call authorization; flags and hashes do not grant permission.',
            implemented=True),
        causal_limit='Two same-input controls are a discriminating comparison, not a stability estimate.')
    return plan, requests


def prepare_all():
    qualification, requests = prepare_qualification()
    comparison, pair_requests = prepare_comparison()
    plan = dict(version='role-next-batches-v1', production_admitted=False, product_execution_enabled=False,
        qualification_plan_sha256=digest(compact(qualification)),
        batches=[dict(order=1, purpose='Same-input Flash comparison', plan=comparison),
            dict(order=2, purpose='Actual role application generation/tools/review/revision/final review',
                composition='flash-glm-review', budget=bounded_product_estimate(), paid_execution_authorized=False,
                prerequisite='Inspect comparison and exact-HEAD CI; any paid execution needs its own already-scoped authorization.',
                development_cli='scripts.run_role_coach_development',
                preview_command='python -m scripts.run_role_coach_development --run-id role-development-FRESH_ID --source-now FIXED_TIME_WITH_TIMEZONE --request-output NEW_FIRST_REQUEST.json',
                execute_arguments=['--execute', '--run-id', 'role-development-FRESH_ID',
                    '--source-now', 'EXACT_PREVIEW_SOURCE_NOW', '--approval-plan-sha', 'PREPARATION_PLAN_SHA256',
                    '--ci-run', 'EXACT_HEAD_CI_RUN', '--env-file', 'AUTHORIZED_ENV_FILE'],
                preparation_binding='Reuse the same fresh run ID, source_now and preparation_plan_sha256 from the preview. Do not pass --request-output on execute; the runner reserves its own original request artifact.',
                development_execution_available=True, product_execution_enabled=False, production_admitted=False,
                evidence_scope='One bounded development application run; neither permission to spend nor original-15, semantic, product or production qualification.')],
        original_15_status='all pending for this composition; no old acceptance inherited')
    return qualification, plan, requests, pair_requests


def run(args):
    qualification, batches, requests, pair_requests = prepare_all()
    if args.output_directory is not None:
        root = args.output_directory.resolve()
        root.mkdir(parents=True, exist_ok=False)
        for name, value in [('qualification.json', qualification), ('next-batches.json', batches)]:
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        for section, values in [('qualification-requests', requests), ('comparison-requests', pair_requests)]:
            directory = root / section
            directory.mkdir()
            for name, raw in values.items():
                (directory / (name.replace(':', '-') + '.json')).write_bytes(raw)
    summary = dict(required_inputs=len(qualification['cases']), pending_inputs=len(qualification['cases']),
        qualification_plan_sha256=digest(compact(qualification)),
        next_batches_sha256=digest(compact(batches)),
        comparison_reservation=batches['batches'][0]['plan']['proposed_diagnostic_budget'],
        product_reservation=batches['batches'][1]['budget'], provider_requests=0,
        production_admitted=False, output_directory=str(args.output_directory) if args.output_directory else None)
    print(compact(summary))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path)
    run(parser.parse_args())
