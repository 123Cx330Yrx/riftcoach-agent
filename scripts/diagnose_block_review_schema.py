"""Frozen full-report pair with one authoritative tool schema, no text duplicate.

This diagnoses whether redundant output instructions are necessary for the new
failure. One observation per report cannot prove causality or reviewer stability.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts import diagnose_block_review_route as base

EXPERIMENT = 'block-review-single-schema-v1'


def prepare():
    archived, _ = base.prepare()
    data = json.loads((base.ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json').read_text(encoding='utf-8'))
    _, _, source = base.load_controls()
    variants, conditions = [], []
    for case in data['cases']:
        inputs = base.review.native.build_inputs(replace(source, report=case['report'], user_utterance=data['user_utterance']))
        original = replace(base.review.request(inputs), metadata=archived.metadata)
        header = base.review.native.schema_notation(original.tools[0].input_schema) + '\n'
        if not original.messages[1].content.startswith(header):
            raise ValueError('single_schema_header_changed')
        request = replace(original, messages=(original.messages[0],
            replace(original.messages[1], content=original.messages[1].content[len(header):]),
            *original.messages[2:]))
        raw = base.validate_request(request, transport_id=base.CAPACITY_TRANSPORT_ID)
        variants.append((case['id'], request, inputs))
        conditions.append(dict(id=case['id'], request_sha256=hashlib.sha256(raw).hexdigest(),
            original_request_sha256=hashlib.sha256(base.validate_request(original,
                transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest(),
            input_ceiling=size(request), removed_chars=len(header), report_sha256=case['report_sha256']))
    plan = dict(experiment=EXPERIMENT, conditions=conditions, route='direct',
        model='glm-5.3-flash', reasoning_effort='high', max_calls=2,
        max_output_per_call=32768, max_seconds_per_call=300, max_seconds=900,
        total_token_limit=401920, full_reservation=sum(c['input_ceiling']+32768 for c in conditions),
        sdk_retries=0, no_reassessment_or_revision=True, labels_sent_to_model=False,
        production_admitted=False, intervention='Remove only the redundant text schema/header; keep tool schema, business policy, full report and sources.',
        decisions={
            'both_semantically_correct': 'Proceed to same-version autonomous workflow coverage; pair is not product admission.',
            'valid_but_semantically_wrong': 'Do not adopt the mechanism; repeated schema changes do not fix the substantive reviewer.',
            'duplicate_keys_again': 'Reject redundant text schema as a sufficient explanation; replay exact new fragments offline.',
            'other_protocol_or_execution_failure': 'Stop pair; preserve concrete cause and usage, no retries.'})
    if plan['full_reservation'] > plan['total_token_limit'] or len(variants) != 2:
        raise ValueError('single_schema_pair_budget_invalid')
    return variants, plan


def run(args):
    variants, plan = prepare()
    experiment = EXPERIMENT
    if args.buffered_tools:
        experiment = 'block-review-buffered-tools-v1'
        plan.update(experiment=experiment, stream_tool_arguments=False,
            baseline_experiment=EXPERIMENT,
            intervention='Same single-schema requests and SSE stream; only omit vendor extra_body.tool_stream. Default product unchanged.',
            decisions={
                'valid_full_pair': 'Inspect semantics, not just JSON; this is not product admission or proof of deterministic causality.',
                'duplicate_keys_again': 'Tool token streaming is not necessary for the malformed JSON; stop this transport hypothesis.',
                'semantic_error': 'Retain failure; transport success cannot qualify substantive judgment.',
                'other_protocol_or_execution_failure': 'Stop pair without retry; inspect saved completion evidence.'})
    else:
        plan['stream_tool_arguments'] = True
    if not args.execute:
        print(json.dumps(plan))
        return plan
    head = base.verify_public_ci(args.ci_run)
    directory = base.ROOT / 'data/runs/schema_diagnostic' / experiment
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / 'plan.json', dict(plan, head_sha=head, ci_run=args.ci_run))
    for name, request, _ in variants:
        write_new_json(directory / f'prepared-{name}.json', json.loads(base.validate_request(
            request, transport_id=base.CAPACITY_TRANSPORT_ID)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    rows = []
    try:
        for name, request, inputs in variants:
            arm = directory / name
            arm.mkdir(exist_ok=False)
            result = base.observe(arm, request, inputs, lambda path: base.ReceiptedStreamProvider(
                settings=settings, directory=path, transport_id=base.CAPACITY_TRANSPORT_ID,
                stream_tool_arguments=not args.buffered_tools),
                argument_diagnostic=True, experiment=experiment)
            rows.append(dict(id=name, result=result))
            if not result['cases'][0]['valid']:
                break
    finally:
        write_new_json(directory / 'result.json', dict(experiment=experiment, cases=rows,
            production_admitted=False, manual_semantic_acceptance=False,
            **{key:sum(r['result'][key] for r in rows)
                for key in ('reserved_calls', 'input_tokens', 'output_tokens', 'unknown_usage_calls')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--buffered-tools', action='store_true')
    run(parser.parse_args())
