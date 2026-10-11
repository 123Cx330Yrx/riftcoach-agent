"""Reconstruct the completed diagnostic pair without Provider I/O.

Read only public model text and body-free receipts. If raw Provider files exist,
hash them without parsing or exporting their private reasoning. Human adjudication
is a separate, hash-bound record; it never changes the experiment result.
"""
import argparse
from dataclasses import replace
import difflib
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from scripts.native_contract_options import validate_editor
from scripts.run_native_editor_pair import ROOT, PLAN, EXPERIMENT, frozen_pair, read, sha

DEFAULT_RUN = ROOT/'data/runs/editor_pair'/EXPERIMENT


def receipt_hashes(run):
    return {p.relative_to(run).as_posix(): sha(p)
            for p in sorted(run.rglob('*')) if p.is_file()}


def subject(run):
    return digest(compact(receipt_hashes(run)))


def check_identity_witness(value, case, req):
    inputs = native.build_inputs(req)
    if (value['report'] != req.report or value['input_sha256'] != digest(inputs.data_json)
            or value['original_source_review_sha256'] != digest(case['proposed_review_raw'])):
        raise ValueError('pair_identity_witness_source_changed')
    reviews, views = [], []
    for item in value['reviews']:
        native.validate(item['raw'], inputs)
        if digest(item['raw']) != item['review_sha256']:
            raise ValueError('pair_identity_witness_hash_changed')
        review = native.strict_json(item['raw'])
        reviews.append(review)
        views.append({'issues': [{'block': issue['block']} for issue in review['issues']]})
    if (len(reviews) != 2 or reviews[0]['issues'] != reviews[1]['issues'][::-1]
            or reviews[0]['issues'][0] != native.strict_json(case['proposed_review_raw'])['issues'][0]
            or views != value['locator_views'] or views[0] != views[1]
            or views[0] != {'issues': [{'block': 6}, {'block': 6}]}
            or value['reviews'][0]['expected_dispositions_host_only'] != ['apply', 'withdraw']
            or value['reviews'][1]['expected_dispositions_host_only'] != ['withdraw', 'apply']):
        raise ValueError('pair_identity_witness_projection_changed')
    return value


def build(run, adjudication, witness):
    case, req, variants, frozen = frozen_pair()
    binding, result = read(run/'plan.json'), read(run/'outputs/result.json')
    expected = dict(frozen, head_sha=binding['head_sha'], ci_run=binding['ci_run'],
                    frozen_plan_sha256=sha(PLAN))
    if binding != expected:
        raise ValueError('pair_frozen_binding_changed')
    if (not result['protocol_complete'] or result['attempted_calls'] != 2
            or result['responses_received'] != 2 or result['transport_reserved_calls'] != 2
            or result['unknown_usage_calls'] != 0 or result['budget_calls'] != 2
            or any(result[k] for k in ('semantic_approval', 'production_admitted',
                'initial_reviewer_qualified', 'final_review_executed'))):
        raise ValueError('pair_not_complete_diagnostic')
    hashes = receipt_hashes(run)
    if adjudication['subject_sha256'] != digest(compact(hashes)):
        raise ValueError('pair_adjudication_identity_changed')
    inputs, arms = native.build_inputs(req), []
    for ordinal, (condition, prepared) in enumerate(variants, 1):
        arm = run/'outputs'/condition
        transport = run/'transport'/f'stream-{ordinal:03d}'
        issued = read(arm/'request.json')
        prepared_bytes = validate_request(prepared, transport_id=CAPACITY_TRANSPORT_ID)
        if (json.loads(prepared_bytes) != read(run/f'prepared-{condition}.json')
                or hashlib.sha256(prepared_bytes).hexdigest() != frozen['conditions'][ordinal-1]['request_sha256']):
            raise ValueError('pair_prepared_request_changed')
        actual = validate_request(replace(prepared, timeout_s=issued['timeout_s'],
            metadata={**prepared.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'}),
            transport_id=CAPACITY_TRANSPORT_ID)
        if (not 0 < issued['timeout_s'] <= 300 or json.loads(actual) != issued
                or actual != (arm/'request.wire.json').read_bytes()):
            raise ValueError('pair_issued_request_changed')
        response, structure = read(arm/'response.json'), read(arm/'structure-result.json')
        reservation, terminal, progress = [read(transport/f'{name}.json')
                                           for name in ('reservation', 'result', 'progress')]
        actual_sha = hashlib.sha256(actual).hexdigest()
        if (response['request_sha256'] != actual_sha or reservation['request_sha256'] != actual_sha
                or reservation['ordinal'] != ordinal or reservation['transport_id'] != CAPACITY_TRANSPORT_ID
                or terminal['transport_id'] != CAPACITY_TRANSPORT_ID or terminal['state'] != 'complete'
                or not terminal['body_free'] or progress['state'] != 'complete'
                or response['finish_reason'] != 'stop' or progress['finish_reason'] != 'stop'
                or response['condition'] != condition or response['model'] != frozen['model']
                or digest(response['content']) != response['content_sha256']
                or any(response['usage'][k] != progress[k] for k in ('input_tokens', 'output_tokens'))):
            raise ValueError('pair_response_or_receipt_changed')
        wire, journal = validate_editor(response['content'], inputs, case['proposed_review_raw'])
        dispositions = [d.disposition for d in sorted(wire.decisions, key=lambda d: d.issue_id)]
        if (journal != read(arm/'editor-journal.json') or wire.report != (arm/'report.md').read_bytes().decode('utf-8')
                or structure != dict(structure_valid=True, dispositions=dispositions,
                    disposition_match=dispositions == case['expected_dispositions_host_only'],
                    semantic_approval=False, report_sha256=digest(wire.report))):
            raise ValueError('pair_report_or_journal_changed')
        arms.append(dict(condition=condition, prepared_request_sha256=hashlib.sha256(prepared_bytes).hexdigest(),
            actual_request_sha256=actual_sha, actual_request=issued, response=response,
            actual_report=wire.report, editor_journal=journal, structure_result=structure,
            report_diff=''.join(difflib.unified_diff(req.report.splitlines(True), wire.report.splitlines(True))),
            transport_receipts=dict(reservation=reservation, result=terminal, progress=progress)))
    totals = {k: sum(a['response']['usage'][k] for a in arms) for k in ('input_tokens', 'output_tokens')}
    if any(totals[k] != result[k] for k in totals) or sum(totals.values()) != result['budget_tokens']:
        raise ValueError('pair_total_usage_changed')
    return dict(schema_version='native-editor-opinion-pair-result-v1', experiment=EXPERIMENT,
        implementation_sha=binding['head_sha'], ci_run=binding['ci_run'], frozen_plan_sha256=sha(PLAN),
        original_report=req.report, original_review_raw=case['proposed_review_raw'],
        input_sha256=digest(inputs.data_json), arms=arms, execution_result=result,
        manual_adjudication=adjudication, file_hashes=hashes,
        identity_counterexample=check_identity_witness(witness, case, req),
        inference_limit=frozen['inference_limit'], semantic_approval=False,
        editor_candidate_accepted=False, initial_reviewer_qualified=False, production_admitted=False,
        usage=dict(provider_requests=2, known_input_tokens=totals['input_tokens'],
            known_output_tokens=totals['output_tokens'], known_total_tokens=sum(totals.values()),
            unknown_usage_calls=0, historical_provider_requests_at_least=275))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=DEFAULT_RUN)
    parser.add_argument('--adjudication', type=Path, required=True)
    parser.add_argument('--witness', type=Path, default=ROOT/'data/evaluation/results/golden_native_locator_identity_counterexample_v1.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = build(args.run, read(args.adjudication), read(args.witness))
    write_new_json(args.output, value)
    print(json.dumps(dict(path=str(args.output), sha256=sha(args.output), usage=value['usage'])))
