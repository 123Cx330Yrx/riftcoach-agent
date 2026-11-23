"""Offline layered failure replay and unchanged-native follow-up preparation.

Analyst field completions are counterexamples, never accepted model responses.
There is intentionally no live execution path in this module.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from pydantic import ValidationError

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts.blind_edit_settlement import validate_settlement
from scripts.native_contract_options import body
from scripts.run_blind_edit_diagnostic import ROOT, frozen, read

RESULT = ROOT/'data/evaluation/results/golden_blind_edit_result_6c22e93.json'


def prepare():
    saved = read(RESULT)
    req, raw, original, *_ = frozen()
    draft = saved['phases'][0]['actual_report']
    revised = native.build_inputs(replace(req, report=draft))
    request = native.request(revised)
    return saved, raw, original, revised, request


def audit():
    saved, raw, original, revised, request = prepare()
    observed = saved['phases'][1]['response']['content']
    try:
        validate_settlement(observed, revised, original, raw)
    except ValidationError as error:
        fields = [dict(type=e['type'], loc=list(e['loc'])) for e in error.errors(include_input=False)]
    else:
        raise ValueError('expected_real_settlement_failure_missing')
    value = native.strict_json(observed)
    completed = deepcopy(value)
    # Diagnostic-only additions; preserve every actual opinion and decision.
    completed['review']['issues'][0].update(block=3,
        suggested_correction='Analyst-only field completion to expose the next validation layer; not a model correction.')
    try:
        validate_settlement(compact(completed), revised, original, raw)
    except ValueError as error:
        inventory_error = str(error)
        if inventory_error != 'native_issue_resolution_inventory':
            raise
    else:
        raise ValueError('expected_resolution_inventory_failure_missing')
    completed['review']['issue_resolutions'] = []
    payload, wire, _ = validate_settlement(compact(completed), revised, original, raw)
    assert wire.decisions[1].original_validity == 'confirmed'
    assert wire.decisions[1].revision_status == 'persists'
    assert payload.verdict == 'needs_revision'
    # Ordinary native request, unchanged policy/schema/complete source data.
    data = body(request)
    assert all(k not in data for k in ('original_review', 'original_source_index', 'previous_review',
        'accepted_review', 'previous_issues', 'decisions', 'previous_settlement_raw'))
    assert request.messages[0].content == native.POLICY
    wire_bytes = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
    return dict(schema_version='blind-edit-failure-audit-v1', evidence_kind='offline_replay_and_request_preparation',
        provider_calls=0, actual_response_sha256=digest(observed), actual_report_sha256=digest(revised.source.report),
        observed_validation_fields=fields, analyst_fields_completed_error=inventory_error,
        analyst_mapping_cleared=dict(structurally_valid=True, verdict=payload.verdict,
            semantic_approval=False, actual_model_response=False,
            observation='The same false original allegation remains confirmed/persists after mechanical completion.'),
        next_request=dict(mode='ordinary_native_review_of_actual_draft', live_status='offline_prepared_only',
            request_sha256=hashlib.sha256(wire_bytes).hexdigest(), input_ceiling=size(request),
            policy_sha256=digest(native.POLICY), source_sha256=digest(revised.data_json),
            request=json_value(wire_bytes), model='glm-5.3-flash', reasoning_effort='high',
            max_calls=1, sdk_retries=0, recovery_allowed=False, production_admitted=False,
            intent='Determine whether unchanged native review correctly assesses this exact actual draft without prior opinions.',
            limits=['Changes whole task context as well as opinion exposure; not causal identification.',
                'A pass does not automatically clear original findings or qualify a product pipeline.',
                'No live call is authorized by this preparation artifact alone; exact implementation checks and bounded plan still apply.']),
        semantic_approval=False, initial_reviewer_qualified=False, production_admitted=False)


def json_value(raw):
    return native.strict_json(raw.decode('utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit()
    write_new_json(args.output, value)
    print(compact(dict(path=str(args.output), provider_calls=0,
        input_ceiling=value['next_request']['input_ceiling'])))
