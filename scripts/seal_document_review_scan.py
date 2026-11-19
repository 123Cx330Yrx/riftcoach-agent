"""Read-only receipt/stage/native replay and create-only public scan export.

Live native event reads are still required: local JSON never substitutes for
an independent author. Public contents use explicit files, not recursive logs.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path

from scripts import run_document_review_scan as runner
from scripts import document_review_scan_handoff as handoff

base = runner.base


def replay(directory, *, event_source):
    directory = Path(directory)
    result = json.loads((directory/'result.json').read_bytes())
    saved = json.loads((directory/'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if (plan != runner.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id'])
            or saved['plan_sha256'] != base.canonical_sha(plan)):
        raise ValueError('document_scan_plan_changed')
    base.require_execution_event_source(plan, event_source)
    calls = runner.read_calls(directory/'transport')
    if len(calls) != result['calls'] or len(calls) > len(runner.KEYS):
        raise ValueError('document_scan_call_inventory')
    variants = runner.controls()[1]
    rows = []
    for index, recorded in enumerate(result['stages']):
        cell, inputs, prepared = variants[index]
        if recorded['key'] != cell['key']:
            raise ValueError('document_scan_stage_inventory')
        _, stage, bound = handoff.material(directory, cell['key'], closed=True, calls=calls)
        arm = directory/runner.arm_name(cell['key'])
        submitted = json.loads((arm/'host-reviews.json').read_bytes())
        if json.loads((arm/'review-submission.json').read_bytes()) != submitted:
            raise ValueError('document_scan_submission_changed')
        runner.shared.validate_reviews(submitted, stage, bound, plan, event_source)
        raw = base.tool_result(prepared, handoff.Exchange(calls[index]['request'],
            calls[index]['response'], calls[index]['binding']['request_sha256']))
        _, wire, _ = runner.workflow.DocumentReviewWorkflow.validate_review(raw, inputs)
        rebuilt = runner.classify(cell, wire, submitted, bound)
        if rebuilt != recorded:
            raise ValueError('document_scan_semantic_record_changed')
        rows.append(rebuilt)
    # Reconstruct pending/failed tail, including a protocol failure after a
    # completed response. It stays unadjudicated and cannot gain a semantic pass.
    expected_unadjudicated = list(runner.KEYS[len(rows):len(calls)])
    expected_unexecuted = list(runner.KEYS[len(calls):])
    unverified_host_files = []
    if len(expected_unadjudicated) > 1 or (expected_unadjudicated and not result.get('error_type')):
        raise ValueError('document_scan_hard_failure_tail_changed')
    for index in range(len(rows),len(calls)):
        cell,inputs,prepared=variants[index]
        arm=directory/runner.arm_name(cell['key'])
        if json.loads((arm/'source.json').read_bytes()) != dict(input_json=inputs.data_json,
                report=inputs.source.report,synthetic_report=False):
            raise ValueError('document_scan_failed_source_changed')
        if (arm/'request.json').exists() and json.loads((arm/'request.json').read_bytes()) != json.loads(
                base.validate_request(calls[index]['request'],transport_id=base.REVIEW_MODEL_TRANSPORT_ID)):
            raise ValueError('document_scan_failed_request_changed')
        if (arm/'response.json').exists() and (calls[index]['response'] is None or
                json.loads((arm/'response.json').read_bytes()) != base.public_response(
                    json.loads(base.RESPONSE.dump_json(calls[index]['response'])))):
            raise ValueError('document_scan_failed_response_changed')
        if (arm/'stage.json').exists():
            raw=base.tool_result(prepared,handoff.Exchange(calls[index]['request'],calls[index]['response'],
                calls[index]['binding']['request_sha256']))
            _,_,journal=runner.workflow.DocumentReviewWorkflow.validate_review(raw,inputs)
            if json.loads((arm/'stage.json').read_bytes()) != dict(stage='initial',report=inputs.source.report,journal=journal):
                raise ValueError('document_scan_failed_stage_changed')
            if (arm/'review-required.json').exists():
                # It is a dispatch binding, not an accepted host judgment.
                handoff.material(directory,cell['key'],closed=True,calls=calls)
        elif (arm/'review-required.json').exists():
            raise ValueError('document_scan_orphan_review_required')
        # An identity/native/availability failure may leave invalid host
        # artifacts. Preserve their raw digests privately, never publish or
        # certify their JSON contents as an authentic source review.
        unverified_host_files += [p.relative_to(directory).as_posix() for p in
            (arm/'host-reviews.json',arm/'review-submission.json') if p.exists()]
    known = sum(sum(c['usage'].values()) for c in calls if c['usage'] is not None)
    unknown = sum(c['usage'] is None for c in calls)
    complete = len(rows) == len(runner.KEYS) and not result.get('error_type')
    if (result['unadjudicated_keys'] != expected_unadjudicated
        or result['unexecuted_keys'] != expected_unexecuted
        or result['known_tokens'] != known
        or result['scan_completed'] != complete
        or result['diagnostic_accepted'] != (complete and all(r['semantic_accepted'] for r in rows))
        or result['unknown_reserved_tokens'] != sum(base.size(c['request']) + c['request'].max_tokens
            for c in calls if c['usage'] is None)
        or any(result[k] is not False for k in ('product_admitted', 'original15_qualified'))
        or result['historical_credit'] != 0):
        raise ValueError('document_scan_result_accounting_changed')
    attempts = result['attempts']
    if len(attempts) != len(calls):
        raise ValueError('document_scan_attempt_inventory')
    for index, (attempt, call) in enumerate(zip(attempts, calls), 1):
        if (attempt['ordinal'] != index or attempt['transport_ordinal'] != 1
            or call['binding']['ordinal'] != 1 or attempt['request_sha256'] != call['binding']['request_sha256']
            or attempt['model'] != 'glm-5.3' or attempt['role'] != 'review'
            or (attempt['status'] == 'completed') != call['completed']):
            raise ValueError('document_scan_attempt_changed')
    price = base.CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    input_tokens = sum(c['usage']['input_tokens'] for c in calls if c['usage'] is not None)
    output_tokens = sum(c['usage']['output_tokens'] for c in calls if c['usage'] is not None)
    estimate = (Decimal(input_tokens)*price.input_cost_per_million
        + Decimal(output_tokens)*price.output_cost_per_million)/1_000_000
    return dict(kind='document-remaining11-initial-scan-v1', plan_sha256=base.canonical_sha(plan),
        historical_evidence_sha256=runner.SEAL_SHA, historical_credit=0,
        scan_completed=complete, stages=rows, unadjudicated_keys=expected_unadjudicated,
        unexecuted_keys=expected_unexecuted,
        unverified_tail_host_files=unverified_host_files,
        unverified_tail_host_contents_exported=False,
        accounting=dict(calls=len(calls), known_tokens=known, unknown_usage_calls=unknown,
            transport_receipt_calls=sum(not c.get('receipt_missing',False) for c in calls),
            local_attempts_without_transport_receipt=sum(c.get('receipt_missing',False) for c in calls),
            input_tokens=input_tokens, output_tokens=output_tokens,
            known_usage_estimated_uncached_cny=str(estimate), unknown_usage_is_not_free=True),
        execution_result=result, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False)


def public_contents(directory, result):
    directory = Path(directory)
    paths = ['plan.json', 'result.json']
    for row in result['stages']:
        arm = runner.arm_name(row['key'])
        paths += [arm+'/'+name for name in ('source.json', 'issued-request.json', 'request.json', 'response.json',
            'stage.json', 'review-required.json', 'review-submission.json', 'host-reviews.json')]
    # Pending stage files are useful failure evidence too, but logs and raw
    # transport responses can contain private reasoning and are never public.
    for key in result['unadjudicated_keys']:
        arm = runner.arm_name(key)
        paths += [arm+'/'+name for name in ('source.json','issued-request.json','request.json','response.json','stage.json',
            'review-required.json') if (directory/arm/name).exists()]
    values = {p:json.loads((directory/p).read_bytes()) for p in paths}
    def inspect(value):
        if isinstance(value, dict):
            if ({'api_key','access_token','authorization'} & value.keys()
                    or value.get('reasoning_content') is not None):
                raise ValueError('document_scan_public_private_field')
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(values)
    return values


def seal(directory, output, *, event_source):
    result = replay(directory, event_source=event_source)
    result['public_json_contents'] = public_contents(directory, result)
    # All originals are hashed, including native private evidence and failed
    # streams; only explicitly allowed JSON contents above are published.
    result['original_file_sha256'] = {p.relative_to(directory).as_posix():base.sha(p)
        for p in sorted(Path(directory).rglob('*')) if p.is_file()}
    base.write_new_json(output, result)
    return dict(sealed=True, path=str(output), sha256=base.sha(output),
        scan_completed=result['scan_completed'], provider_requests=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=base.ROOT/'data/runs/model_comparison'/runner.EXPERIMENT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--codex-executable', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((args.directory/'plan.json').read_bytes())['preparation_plan']
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        source = base.CodexHostReviewEventSource(client, plan)
        result = (seal(args.directory, args.output, event_source=source) if args.output
                  else replay(args.directory, event_source=source))
    print(base.compact(result), flush=True)


if __name__ == '__main__':
    main()
