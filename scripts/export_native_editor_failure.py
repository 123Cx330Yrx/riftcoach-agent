"""Reproduce the single stopped editor diagnostic's public evidence, offline.

Only complete public responses and body-free receipts are exported. Original
Provider response files (which can carry private reasoning) are hashed only.
"""
import argparse
from dataclasses import replace
import difflib
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from scripts.native_contract_options import validate_editor, editor_request
from scripts.check_native_claim_scope import load_controls
from scripts.run_native_editor_diagnostic import (read, sha, subject,
    validate_saved_exchange, ROOT)

PLAN=ROOT/'data/evaluation/results/golden_native_editor_diagnostic_plan_v2.json'


def build(batch):
    binding=read(batch/'batch.json')
    case=read(PLAN)['cases'][0]
    req=load_controls()[1][2]
    directory=batch/case['id']
    plan=read(directory/'plan.json')
    result=read(directory/'edit/result.json')
    response=read(directory/'edit/response-001.json')
    adjudication=read(directory/'edit/adjudication.json')
    if (binding['head_sha']!=plan['head_sha'] or binding['frozen_plan_sha256']!=sha(PLAN)
            or plan['frozen_plan_sha256']!=sha(PLAN)
            or adjudication['subject_sha256']!=subject(directory,'edit')
            or adjudication['accepted'] or result['protocol_success']
            or result['completed_calls']!=1 or result['unknown_usage_calls']):
        raise ValueError('editor_failed_batch_identity_mismatch')
    if any((batch/name/'edit').exists() for name in binding['order'][1:]) or (directory/'recheck').exists():
        raise ValueError('editor_failed_batch_continued')
    validate_saved_exchange(directory,'edit',1,receipted=True)
    issued=read(directory/'edit/request-001.json')
    # v1 policy is preserved verbatim in the actual request. Verify its frozen
    # policy hash, then reconstruct every other request field from live builders.
    policy=issued['messages'][0]['content']
    if digest(policy)!=case['system_policy_sha256'] or digest(native.build_inputs(req).data_json)!=case['input_sha256']:
        raise ValueError('editor_frozen_v1_policy_or_source_changed')
    prepared=editor_request(native.build_inputs(req),case['proposed_review_raw'])
    prepared=replace(prepared,messages=(replace(prepared.messages[0],content=policy),*prepared.messages[1:]))
    if hashlib.sha256(validate_request(prepared,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()!=case['request_sha256']:
        raise ValueError('editor_frozen_v1_request_changed')
    # Reproduce both budget-owned transformations; no model input may change.
    actual=validate_request(replace(prepared,timeout_s=issued['timeout_s'],
        metadata={**prepared.metadata,'coach_budget_contract':'coach-bounded-review-v2'}),
        transport_id=CAPACITY_TRANSPORT_ID)
    if not 0<issued['timeout_s']<=300 or actual!=(directory/'edit/request-001.wire.json').read_bytes():
        raise ValueError('editor_actual_request_reconstruction_failed')
    if any(m.get('reasoning_content') for m in issued['messages']):
        raise ValueError('editor_private_reasoning_in_request')
    wire,journal=validate_editor(response['content'],native.build_inputs(req),case['proposed_review_raw'])
    if (journal!=read(directory/'edit/editor-journal.json')
            or wire.report!=(directory/'edit/report.md').read_bytes().decode('utf-8')
            or result['report_sha256']!=digest(wire.report)):
        raise ValueError('editor_failed_report_identity_changed')
    transport=directory/'transport-edit/stream-001'
    progress=read(transport/'progress.json')
    if any(response['usage'][key]!=result[key] or result[key]!=progress[key]
           for key in ('input_tokens','output_tokens')):
        raise ValueError('editor_failed_usage_mismatch')
    return dict(schema_version='native-editor-diagnostic-result-v1',
        batch_id=batch.name,implementation_sha=plan['head_sha'],ci_run=plan['ci_run'],
        frozen_plan_sha256=sha(PLAN),case_id=case['id'],provenance=case['provenance'],
        prepared_request_sha256=case['request_sha256'],actual_request_sha256=hashlib.sha256(actual).hexdigest(),
        proposed_review_sha256=case['proposed_review_sha256'],input_sha256=case['input_sha256'],
        original_report=req.report,proposed_review_raw=case['proposed_review_raw'],
        actual_request=issued,response=response,editor_journal=journal,actual_report=wire.report,
        actual_report_sha256=digest(wire.report),
        report_diff=''.join(difflib.unified_diff(req.report.splitlines(True),wire.report.splitlines(True))),
        expected_dispositions_host_only=case['expected_dispositions_host_only'],
        observed_dispositions=[d.disposition for d in wire.decisions],
        schema_source_identity_valid=True,semantic_approval=False,production_admitted=False,
        initial_reviewer_qualified=False,editor_candidate_accepted=False,
        semantic_failure='generic_mean_read_as_universal_and_applied',
        causal_limit='Single observation cannot distinguish suggestion anchoring from shared scope bias.',
        true_error_corrected=True,final_review_executed=False,remaining_cases_executed=False,
        execution_result=result,manual_adjudication=adjudication,
        independent_review=read(directory/'independent-review.json'),
        transport_receipts={n:read(transport/n) for n in ('reservation.json','result.json','progress.json')},
        file_hashes={str(p.relative_to(batch)).replace('\\','/'):sha(p) for p in sorted(batch.rglob('*')) if p.is_file()},
        usage=dict(provider_requests=1,known_input_tokens=result['input_tokens'],
            known_output_tokens=result['output_tokens'],known_total_tokens=result['input_tokens']+result['output_tokens'],
            unknown_usage_calls=0,historical_provider_requests_at_least=273))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,default=ROOT/'data/runs/editor_diagnostic/editor-diagnostic-685993d-v1')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=build(args.batch)
    write_new_json(args.output,value)
    print(json.dumps(dict(path=str(args.output),sha256=sha(args.output),usage=value['usage'])))
