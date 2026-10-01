"""Prepare current qualification inputs and reproduce a closed historical batch.

Offline only. History is not a pending execution queue or current qualification.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, frozen_cases, prepare_qualification
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation import golden_native_partitioned_tool_review as review
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from scripts.prepare_review_model_comparison import sdk_arguments, mock_wire

PAIR_EVIDENCE = ROOT / 'data/evaluation/results/golden_explicit_source_pair_result_0c061b2.json'
FLASH_EVIDENCE = ROOT / 'data/evaluation/results/golden_flash_source_pair_result_346213c.json'


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
    """Exact closed Flash plan; never bind legacy requests to current identity."""
    raw_evidence = FLASH_EVIDENCE.read_bytes()
    # Exported dictionaries are key-sorted, whereas the original plan digest
    # used insertion order. Bind the untouched export, not a new serialization.
    if hashlib.sha256(raw_evidence).hexdigest() != 'a4fd1d69d12a74b20738c573487ef150c8ffe89fa4a2b2b3e68115fd05145e36':
        raise ValueError('role_comparison_frozen_evidence_changed')
    closed = json.loads(raw_evidence)["original_json_contents"]["plan.json"]
    plan = closed["preparation_plan"]
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
    if cells != plan['cells']:
        raise ValueError('role_comparison_frozen_cells_changed')
    return plan, requests


def prepare_all():
    qualification, requests = prepare_qualification()
    comparison, pair_requests = prepare_comparison()
    plan = dict(version='role-next-batches-v2', production_admitted=False, product_execution_enabled=False,
        qualification_plan_sha256=digest(compact(qualification)), batches=[],
        historical_batches=[dict(status='closed', plan=comparison,
            evidence=FLASH_EVIDENCE.relative_to(ROOT).as_posix(),
            evidence_sha256=hashlib.sha256(FLASH_EVIDENCE.read_bytes()).hexdigest())],
        current_product_budget=bounded_product_estimate(),
        next_action='No paid batch selected; see the active work card and canonical execution state.',
        original_15_status='no qualification for current request identity; historical successes and failures remain in their original evidence')
    return qualification, plan, requests, pair_requests


def run(args):
    qualification, batches, requests, pair_requests = prepare_all()
    if args.output_directory is not None:
        root = args.output_directory.resolve()
        root.mkdir(parents=True, exist_ok=False)
        for name, value in [('qualification.json', qualification), ('next-batches.json', batches)]:
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        for section, values in [('qualification-requests', requests), ('historical-comparison-requests', pair_requests)]:
            directory = root / section
            directory.mkdir()
            for name, raw in values.items():
                (directory / (name.replace(':', '-') + '.json')).write_bytes(raw)
    summary = dict(required_inputs=len(qualification['cases']), pending_inputs=len(qualification['cases']),
        qualification_plan_sha256=digest(compact(qualification)),
        next_batches_sha256=digest(compact(batches)),
        planned_paid_batches=len(batches['batches']),
        product_reservation=batches['current_product_budget'], provider_requests=0,
        production_admitted=False, output_directory=str(args.output_directory) if args.output_directory else None)
    print(compact(summary))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path)
    run(parser.parse_args())
