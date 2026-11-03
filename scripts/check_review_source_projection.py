"""Reproduce the addressing correction with frozen controls and a mock SDK.

No credentials, execution flag or live Provider. Keeps original failed evidence
and prepares complete reviewable wire requests, without reopening its batch.
"""
from copy import deepcopy
from decimal import Decimal
import json

from app.evaluation import golden_explicit_source_projection as projection
from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts.diagnose_review_target_layout import prepare, ROOT
from scripts.prepare_review_model_comparison import mock_wire, sdk_arguments

OUTPUT = ROOT / 'data/evaluation/results/golden_explicit_source_projection_v1.json'
ACTUAL = ROOT / 'data/evaluation/results/golden_review_model_comparison_result_b6b30f8.json'
FROZEN = ROOT / 'data/evaluation/results/golden_review_target_layout_plan_v1.json'


def build_evidence():
    variants, old_plan = prepare()
    if old_plan != json.loads(FROZEN.read_text(encoding='utf-8')):
        raise ValueError('source_projection_frozen_baseline_changed')
    actual = json.loads(ACTUAL.read_text(encoding='utf-8'))
    arguments = actual['original_json_contents']['attribution_original-baseline/response.json']['tool_calls'][0]['arguments']
    baselines = [row for row in variants if row[0].endswith('-baseline')]
    cells = []
    for name, inputs, request in baselines:
        projected = projection.project_request(request, inputs)
        restored = projection.restore_request(projected, inputs)
        original_args = sdk_arguments(request)
        original_args['model'] = 'glm-5.3'
        projected_args = sdk_arguments(projected)
        projected_args['model'] = 'glm-5.3'
        restored_args = sdk_arguments(restored)
        restored_args['model'] = 'glm-5.3'
        before, after, restored_wire = map(mock_wire, (original_args, projected_args, restored_args))
        if restored_wire != before:
            raise ValueError('source_projection_sdk_restore_loss')
        changed_fields = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        changed_messages = [i for i, (a, b) in enumerate(zip(before['messages'], after['messages'], strict=True)) if a != b]
        if changed_fields != ['messages'] or changed_messages != [0, 1]:
            raise ValueError('source_projection_sdk_unexpected_change')
        _, data = projection._unpack(projected)
        _, old_data = projection._unpack(request)
        if ({k: v for k, v in data.items() if k != 'source_index'}
                != {k: v for k, v in old_data.items() if k != 'source_index'}):
            raise ValueError('source_projection_non_index_data_changed')
        cells.append(dict(id=name, input_sha256=digest(inputs.data_json),
            report_sha256=digest(inputs.source.report), source_digest=inputs.source.source_digest,
            catalog_sha256=data['source_roots']['catalog_sha256'],
            original_sdk_sha256=digest(compact(before)), projected_sdk_sha256=digest(compact(after)),
            changed_sdk_fields=changed_fields, changed_message_indices=changed_messages,
            roundtrip_exact=True, original_input_ceiling=size(request), projected_input_ceiling=size(projected),
            explicit_evidence_ids=data['source_index']['evidence_by_id'], sdk_body=after))

    # Replay the actual failure independently of request representation.
    # Never adjust/delete its IDs, opinions or original accounting.
    raw = compact(arguments)
    try:
        review.validate(raw, baselines[0][1])
    except ValueError as error:
        failure = str(error)
    else:
        raise ValueError('source_projection_original_failure_was_accepted')
    if failure != 'semantic_source_id_unknown':
        raise ValueError('source_projection_original_failure_changed')
    catalog = review.native.request_data(baselines[0][1])['source_index']['evidence_keys']
    coordinate_audit = []
    for kind in ('issues', 'advisories'):
        for item in arguments[kind]:
            coordinate_audit.append(dict(kind=kind, block=item['block'],
                original_ids=item['source_ids'],
                literal_one_based=[catalog[n-1] if 1 <= n <= len(catalog) else None for n in item['source_ids']],
                hypothetical_zero_based_NOT_APPLIED=[catalog[n] if 0 <= n < len(catalog) else None for n in item['source_ids']]))
    input_total = sum(c['projected_input_ceiling'] for c in cells)
    output_total = 2 * 32768
    return dict(version=projection.VERSION, status='offline_contract_checked',
        provider_requests=0, production_admitted=False, live_entry=False,
        original_evidence_canonical_sha256=digest(compact(actual)),
        original_rejection=failure, original_response_arguments=deepcopy(arguments),
        coordinate_audit=coordinate_audit, cells=cells,
        future_pair_reservation_only=dict(calls=2, input_tokens=input_total, output_tokens=output_total,
            total_tokens=input_total+output_total, total_seconds=600, per_call_seconds=300,
            estimated_uncached_cny=str((Decimal(input_total)*8 + Decimal(output_total)*28)/1_000_000),
            paid_execution_authorized=False, hard_billing_cap=False),
        limits=[
            'Internal table IDs and resolver were already one-based; this corrects ambiguous model-facing navigation.',
            'Block14 zero-based alignment is evidence for a mechanism, not proof of model causality.',
            'Advisory sources are still irrelevant after hypothetical +1; explicit IDs cannot certify entailment.',
            'Original responses/receipts, catalog IDs and source values are unchanged; new wire identity is distinct.',
            'No model capability, edit/final-review workflow or15-case qualification was completed.',
        ])


if __name__ == '__main__':
    result = build_evidence()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(compact(dict(output=OUTPUT.as_posix(), cells=len(result['cells']),
        original_rejection=result['original_rejection'],
        reservation=result['future_pair_reservation_only'], provider_requests=0)))
