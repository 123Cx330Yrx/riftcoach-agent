"""Rebuild public diagnostic evidence; hash private files without opening text."""
import argparse
from dataclasses import replace
import difflib
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError

from app.evaluation import golden_native_issues_review as native
from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from scripts.blind_edit_settlement import settlement_request, validate_settlement
from scripts.export_native_editor_pair import receipt_hashes, subject
from scripts.run_blind_edit_diagnostic import ROOT, PLAN, EXPERIMENT, frozen, read, sha

DEFAULT_RUN = ROOT/'data/runs/blind_edit_diagnostic'/EXPERIMENT


def build(run, adjudication):
    req, original_raw, original, prepared, plan = frozen()
    binding, result = read(run/'plan.json'), read(run/'outputs/result.json')
    if binding != dict(plan, head_sha=binding['head_sha'], ci_run=binding['ci_run'], frozen_plan_sha256=sha(PLAN)):
        raise ValueError('blind_frozen_binding_changed')
    hashes = receipt_hashes(run)
    if adjudication['subject_sha256'] != digest(compact(hashes)):
        raise ValueError('blind_adjudication_identity_changed')
    phases = []
    for ordinal, phase in enumerate(('edit', 'settlement'), 1):
        arm = run/'outputs'/phase
        if not (arm/'response.json').exists():
            break
        response = read(arm/'response.json')
        actual = (arm/'request.wire.json').read_bytes()
        issued = json.loads(actual)
        expected = validate_request(replace(prepared, timeout_s=issued['timeout_s'],
            metadata={**prepared.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'}),
            transport_id=CAPACITY_TRANSPORT_ID)
        if not 0 < issued['timeout_s'] <= 300 or actual != expected:
            raise ValueError('blind_issued_request_changed')
        transport = run/'transport'/f'stream-{ordinal:03d}'
        reservation, terminal, progress = [read(transport/f'{n}.json') for n in ('reservation', 'result', 'progress')]
        actual_sha = hashlib.sha256(actual).hexdigest()
        if (response['request_sha256'] != actual_sha or reservation['request_sha256'] != actual_sha
                or reservation['ordinal'] != ordinal or reservation['transport_id'] != CAPACITY_TRANSPORT_ID
                or terminal['transport_id'] != CAPACITY_TRANSPORT_ID or terminal['state'] != 'complete'
                or not terminal['body_free'] or progress['state'] != 'complete'
                or response['finish_reason'] != 'stop' or progress['finish_reason'] != 'stop'
                or response['model'] != plan['model'] or response['provider'] != 'zhipu'
                or digest(response['content']) != response['content_sha256']
                or any(response['usage'][k] != progress[k] for k in ('input_tokens', 'output_tokens'))):
            raise ValueError('blind_response_or_receipt_changed')
        row = dict(phase=phase, actual_request=issued, actual_request_sha256=actual_sha, response=response,
            transport_receipts=dict(reservation=reservation, result=terminal, progress=progress))
        phases.append(row)
        if phase == 'edit' and (arm/'report.md').exists():
            draft = (arm/'report.md').read_bytes().decode('utf-8')
            if draft != response['content']:
                raise ValueError('blind_actual_report_changed')
            validate_revised_report(draft, req.report)
            revised = native.build_inputs(replace(req, report=draft))
            prepared = settlement_request(revised, original, original_raw)
            row.update(actual_report=draft, report_diff=''.join(difflib.unified_diff(
                req.report.splitlines(True), draft.splitlines(True))))
        elif phase == 'edit':
            break
        else:
            try:
                payload, wire, journal = validate_settlement(response['content'], revised, original, original_raw)
            except (ValueError, TypeError) as error:
                if (arm/'journal.json').exists() or result['protocol_complete']:
                    raise ValueError('blind_invalid_settlement_marked_complete') from error
                row['validation_failure'] = dict(error_type=type(error).__name__)
                if isinstance(error, ValidationError):
                    row['validation_failure']['fields'] = [dict(type=e['type'], loc=list(e['loc']))
                        for e in error.errors(include_input=False)]
                else:
                    row['validation_failure']['code'] = str(error)
            else:
                if (journal != read(arm/'journal.json') or not result['protocol_complete']
                        or result['final_verdict'] != payload.verdict
                        or result['original_decisions'] != [d.model_dump(mode='json') for d in wire.decisions]):
                    raise ValueError('blind_settlement_journal_changed')
                row['settlement_journal'] = journal
    totals = {k: sum(p['response']['usage'][k] for p in phases) for k in ('input_tokens', 'output_tokens')}
    known_tokens = sum(totals.values())
    # A fresh complete response can precede budget accounting on interrupt.
    # A schema ValidationError, however, happens after sender return/accounting.
    ledger_complete = result['protocol_complete'] or result.get('error_type') == 'ValidationError'
    if (any(totals[k] != result[k] for k in totals) or result['responses_received'] != len(phases)
            or not 0 <= len(phases) <= result['transport_reserved_calls'] <= result['budget_calls'] <= result['attempted_calls'] <= 2
            or not 0 <= result['budget_tokens'] <= known_tokens
            or (ledger_complete and result['budget_tokens'] != known_tokens)
            or result['unknown_usage_calls'] != max(0, result['transport_reserved_calls']-len(phases))
            or any(result[k] for k in ('semantic_approval', 'production_admitted', 'initial_reviewer_qualified'))
            or result['recovery_calls'] != 0
            or (result['protocol_complete'] and (len(phases) != 2 or 'settlement_journal' not in phases[-1]))):
        raise ValueError('blind_execution_totals_changed')
    return dict(schema_version='blind-edit-diagnostic-result-v1', experiment=EXPERIMENT,
        implementation_sha=binding['head_sha'], ci_run=binding['ci_run'], frozen_plan_sha256=sha(PLAN),
        original_report=req.report, original_review_raw=original_raw, source_sha256=digest(original.data_json),
        phases=phases, execution_result=result, manual_adjudication=adjudication, file_hashes=hashes,
        semantic_approval=False, initial_reviewer_qualified=False, production_admitted=False,
        usage=dict(provider_requests=result['transport_reserved_calls'], known_input_tokens=totals['input_tokens'],
            known_output_tokens=totals['output_tokens'], known_total_tokens=sum(totals.values()),
            unknown_usage_calls=result['unknown_usage_calls'],
            historical_provider_requests_at_least=275+result['transport_reserved_calls']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=DEFAULT_RUN)
    parser.add_argument('--adjudication', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = build(args.run, read(args.adjudication))
    write_new_json(args.output, value)
    print(compact(dict(path=str(args.output), sha256=sha(args.output), usage=value['usage'])))
