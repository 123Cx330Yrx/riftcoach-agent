"""Bounded input-layout comparison, not a new reviewer or product qualification.

Keep policies, full data, report text, schema and transport. Relocate the complete
source_index to the end of the final user message; do not select a suspect block.
The contemporaneous baseline is diagnostic-only and does not reopen its batch.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from pydantic import TypeAdapter

from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, CapacityBridgeObservation, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.providers.models import ChatResponse
from scripts.check_native_claim_scope import load_controls
from scripts.diagnose_block_review_route import route_environment
from scripts.export_partitioned_review import public_response, transport_for
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = 'review-target-layout-v1'
PLAN = ROOT / 'data/evaluation/results/golden_review_target_layout_plan_v1.json'
DATASET = ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json'


def target_last(request):
    """Reorder only; every original JSON value and source path stays intact."""
    if len(request.messages) != 3 or not request.tools:
        raise ValueError('layout_request_shape_changed')
    header = review.native.schema_notation(request.tools[0].input_schema) + '\n[UNTRUSTED DATA]\n'
    suffix = '\n[END UNTRUSTED DATA]'
    message = request.messages[1]
    if not message.content.startswith(header) or not message.content.endswith(suffix):
        raise ValueError('layout_data_envelope_changed')
    data = review.native.strict_json(message.content[len(header):-len(suffix)])
    source_index = data.pop('source_index')
    data['source_index'] = source_index
    moved = replace(message, content=header + compact(data) + suffix)
    return review.native.budget_check(replace(request,
        messages=(request.messages[0], request.messages[2], moved)))


def prepare():
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    _, _, source = load_controls()
    if len(data['cases']) != 2:
        raise ValueError('layout_control_count_changed')
    variants, conditions = [], []
    # Reverse layout order on the positive to avoid a single fixed arm order.
    # One draw per cell is still not a stability estimate or causal proof.
    for case, layouts in zip(data['cases'], [('baseline', 'target_last'), ('target_last', 'baseline')], strict=True):
        if digest(case['report']) != case['report_sha256']:
            raise ValueError('layout_report_changed')
        inputs = review.native.build_inputs(replace(source, report=case['report'], user_utterance=data['user_utterance']))
        baseline = review.request(inputs)
        for layout in layouts:
            request = baseline if layout == 'baseline' else target_last(baseline)
            name = f'{case["id"]}-{layout}'
            variants.append((name, inputs, request))
            conditions.append(dict(id=name, layout=layout, report_sha256=digest(case['report']),
                input_sha256=digest(inputs.data_json), expected_host_only=case['expected_report'],
                request_sha256=hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
                input_ceiling=size(request), policy_sha256=digest(request.messages[0].content)))
    plan = dict(experiment=EXPERIMENT, conditions=conditions,
        dataset_sha256=hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        model='glm-5.3-flash', reasoning_effort='high', stream_tool_arguments=True,
        route='direct', max_calls=4, max_seconds=900, total_token_limit=401920,
        max_seconds_per_call=300, max_output_per_call=32768, sdk_retries=0,
        full_reservation=sum(c['input_ceiling'] + 32768 for c in conditions),
        no_reassessment_or_revision=True, labels_sent_to_model=False, production_admitted=False,
        intervention='Only reorder the source_index JSON member and the two existing user messages; preserve all values, rules and output contract.',
        decisions={
            'target_pair_correct_baseline_not': 'Consider integration of this input layout, then same-version workflow and frozen coverage; not admission or causal proof.',
            'both_pairs_correct': 'Prior miss was not reproduced; cannot attribute an improvement to layout or qualify a candidate.',
            'target_semantic_error': 'Reject layout as a sufficient fix; no follow-up permutations or format changes in this batch.',
            'protocol_or_execution_failure': 'Stop remaining calls; preserve raw evidence and known/unknown usage; no retry.'})
    if plan['full_reservation'] > plan['total_token_limit']:
        raise ValueError('layout_budget_exceeded')
    return variants, plan


def observe(provider, directory, variants):
    if len(variants) != 4:
        raise ValueError('layout_cell_count_invalid')
    sender = BudgetedReviewSender(provider)
    records = []
    result = dict(experiment=EXPERIMENT, protocol_complete=False,
        production_admitted=False, manual_semantic_acceptance=False)
    try:
        for name, inputs, request in variants:
            before = provider._calls
            arm = directory / name
            arm.mkdir(exist_ok=False)
            record = dict(id=name, completed=False, valid=False, reserved_calls=0,
                observed_usage=None, usage_source='unavailable')
            records.append(record)
            try:
                exchange = sender(request)
                response = public_response(json.loads(TypeAdapter(ChatResponse).dump_json(exchange.response)))
                record.update(completed=True, response=response, observed_usage=response['usage'], usage_source='complete_response')
                write_new_json(arm / 'response.json', response)
                write_new_json(arm / 'request.json', json.loads(validate_request(exchange.issued_request, transport_id=CAPACITY_TRANSPORT_ID)))
                raw = review.tool.tool_result(request, exchange)
                _, wire, journal = review.validate(raw, inputs)
                journal.update(experiment=EXPERIMENT, full_report_review=True,
                    request_sha256=exchange.receipt_request_sha256,
                    policy_sha256=digest(request.messages[0].content))
                write_new_json(arm / 'journal.json', journal)
                record.update(valid=True, verdict=wire.verdict, score=wire.score,
                    issue_blocks=[i.block for i in wire.issues], advisory_blocks=[i.block for i in wire.advisories])
            finally:
                record['reserved_calls'] = provider._calls - before
                if record['reserved_calls'] not in (0, 1):
                    raise ValueError('layout_call_accounting_invalid')
                if record['reserved_calls'] and not record['completed']:
                    stream = directory / 'transport' / f'stream-{provider._calls:03d}'
                    if (stream / 'progress.json').exists():
                        transport = transport_for(stream, provider._calls)
                        progress = CapacityBridgeObservation.model_validate(transport['progress'])
                        if progress.input_tokens is not None and progress.output_tokens is not None:
                            record.update(observed_usage=dict(input_tokens=progress.input_tokens, output_tokens=progress.output_tokens),
                                usage_source='normalized_stream_usage')
                record['unknown_usage_calls'] = record['reserved_calls'] - int(record['observed_usage'] is not None)
                write_new_json(arm / 'accounting.json', {k:v for k,v in record.items() if k != 'response'})
            print(compact({k:v for k,v in record.items() if k != 'response'}), flush=True)
        result.update(protocol_complete=True, stop_reason='comparison_requires_manual_adjudication')
    except Exception as error:
        result.update(stop_reason='protocol_or_execution_failure', error_type=type(error).__name__)
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,90}', code):
            result['error_code'] = code
    finally:
        result.update(cases=records, reserved_calls=provider._calls,
            completed_calls=sum(r['completed'] for r in records),
            input_tokens=sum((r['observed_usage'] or {}).get('input_tokens', 0) for r in records),
            output_tokens=sum((r['observed_usage'] or {}).get('output_tokens', 0) for r in records),
            unknown_usage_calls=sum(r.get('unknown_usage_calls', r['reserved_calls']) for r in records))
        write_new_json(directory / 'result.json', result)
    return result


def run(args):
    variants, plan = prepare()
    if plan != json.loads(PLAN.read_text(encoding='utf-8')):
        raise ValueError('layout_plan_changed')
    if not args.execute:
        print(compact(plan))
        return plan
    head = verify_public_ci(args.ci_run)
    directory = ROOT / 'data/runs/layout_diagnostic' / EXPERIMENT
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / 'plan.json', dict(plan, head_sha=head, ci_run=args.ci_run))
    for name, _, request in variants:
        write_new_json(directory / f'prepared-{name}.json', json.loads(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    provider = ReceiptedStreamProvider(settings=settings, directory=directory / 'transport',
        transport_id=CAPACITY_TRANSPORT_ID)
    with route_environment('direct'):
        result = observe(provider, directory, variants)
    print(compact({k:v for k,v in result.items() if k != 'cases'}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    run(parser.parse_args())
