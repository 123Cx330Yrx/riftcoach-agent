"""Export public run evidence without changing receipts or claiming adoption."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import CapacityBridgeObservation, TRANSPORTS


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_response(value):
    # Explicit allowlist: never serialize reasoning or future private fields.
    return {key: value[key] for key in (
        'content', 'finish_reason', 'model', 'provider', 'tool_calls', 'usage')}


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError('export_count_invalid')
    return value


def reservation_for(stream, ordinal):
    reservation = read(stream / 'reservation.json')
    request_sha = reservation.get('request_sha256')
    if (type(reservation.get('ordinal')) is not int or reservation['ordinal'] != ordinal
            or reservation.get('transport_id') not in TRANSPORTS
            or reservation.get('state') != 'reserved_before_io'
            or not isinstance(request_sha, str) or not re.fullmatch('[a-f0-9]{64}', request_sha)):
        raise ValueError('export_reservation_identity_mismatch')
    return reservation


def transport_for(stream, ordinal):
    reservation = reservation_for(stream, ordinal)
    terminal = read(stream / 'result.json')
    if terminal.get('transport_id') != reservation['transport_id']:
        raise ValueError('export_transport_identity_mismatch')
    return dict(reservation=reservation, result=terminal, progress=read(stream / 'progress.json'))


def export_run(run):
    receipt = read(run / 'receipt.json')
    case_id, = receipt['selected_cases']
    case_dir = run / case_id
    result = read(case_dir / 'result.json')
    original = read(case_dir / 'input.json')
    if digest(original['report']) != receipt['report_sha256']:
        raise ValueError('export_report_identity_mismatch')
    for key, code in (('reserved_calls', 'reserved_count'), ('completed_calls', 'call_count'),
                      ('unknown_usage_calls', 'unknown_usage')):
        if count(result[key]) != count(receipt[key]):
            raise ValueError(f'export_{code}_mismatch')
    calls = []
    for call_file in sorted(case_dir.glob('call-*.json')):
        call = read(call_file)
        suffix = call_file.stem.removeprefix('call-')
        ordinal = len(calls) + 1
        if suffix != f'{ordinal:03d}' or type(call.get('ordinal')) is not int or call['ordinal'] != ordinal:
            raise ValueError('export_call_ordinal_mismatch')
        response = public_response(read(case_dir / f'response-{suffix}.json'))
        request = read(case_dir / f'request-{suffix}.json')
        stream = case_dir / 'streams' / f'stream-{suffix}'
        transport = transport_for(stream, ordinal)
        if transport['result'].get('state') != 'complete':
            raise ValueError('export_completed_transport_mismatch')
        if any(count(response['usage'][k]) != count(call[k]) for k in ('input_tokens', 'output_tokens')):
            raise ValueError('export_call_usage_mismatch')
        if transport['reservation']['request_sha256'] != call['request_sha256']:
            raise ValueError('export_request_receipt_mismatch')
        calls.append(dict(call=call, request=request, response=response, transport=transport))
    if len(calls) != result['completed_calls'] or len(calls) != receipt['completed_calls']:
        raise ValueError('export_call_count_mismatch')
    unassembled = result.get('unassembled_usage', [])
    unassembled_evidence = []
    for item in unassembled:
        ordinal = item['ordinal']
        if (not isinstance(ordinal, int) or isinstance(ordinal, bool)
                or not len(calls) < ordinal <= result['reserved_calls']
                or ordinal in [e['ordinal'] for e in unassembled_evidence]):
            raise ValueError('export_unassembled_ordinal_invalid')
        stream = case_dir / 'streams' / f'stream-{ordinal:03d}'
        transport = transport_for(stream, ordinal)
        observation = CapacityBridgeObservation.model_validate(transport['progress'])
        if (count(item['input_tokens']) != observation.input_tokens or count(item['output_tokens']) != observation.output_tokens
                or item['source'] != 'normalized_stream_usage'):
            raise ValueError('export_unassembled_usage_mismatch')
        unassembled_evidence.append(dict(ordinal=ordinal, progress=observation.model_dump(mode='json'),
            reservation=transport['reservation'], result=transport['result']))
    if result['reserved_calls'] != len(calls) + len(unassembled_evidence) + result['unknown_usage_calls']:
        raise ValueError('export_accounting_balance_mismatch')
    # Every reserved call must have its own pre-I/O receipt, including failures
    # with unknown usage. Do not invent completion or usage for those calls.
    expected_streams = {f'stream-{ordinal:03d}' for ordinal in range(1, result['reserved_calls'] + 1)}
    actual_streams = {p.name for p in (case_dir / 'streams').glob('stream-*') if p.is_dir()}
    if actual_streams != expected_streams:
        raise ValueError('export_reservation_inventory_mismatch')
    for ordinal in range(1, result['reserved_calls'] + 1):
        reservation_for(case_dir / 'streams' / f'stream-{ordinal:03d}', ordinal)
    for key in ('input_tokens', 'output_tokens'):
        total = sum(c['call'][key] for c in calls) + sum(item[key] for item in unassembled)
        if total != count(result[key]) or total != count(receipt[key]):
            raise ValueError('export_total_usage_mismatch')
    journals = {}
    for file in sorted(case_dir.glob('*correction-journal.json')):
        journal = read(file)
        if digest(journal['raw']) != journal['raw_sha256']:
            raise ValueError('export_journal_hash_mismatch')
        matching = [c for c in calls if (any(t['arguments'] == journal['parsed_review']
            for t in c['response']['tool_calls']) or
            (journal.get('raw_representation') == 'response_content'
             and not c['response']['tool_calls'] and c['response']['content'] == journal['raw']))]
        if len(matching) != 1:
            raise ValueError('export_journal_response_mismatch')
        if digest(matching[0]['request']['messages'][0]['content']) != journal['policy_sha256']:
            raise ValueError('export_journal_policy_mismatch')
        journals[file.name] = journal
    revised_file = case_dir / 'revised-report.md'
    revised = revised_file.read_text(encoding='utf-8') if revised_file.exists() else None
    return dict(run_id=run.name, receipt=receipt, result=result,
                original_report=original['report'], revised_report=revised,
                calls=calls, journals=journals, unassembled_usage_evidence=unassembled_evidence,
                file_sha256={p.relative_to(run).as_posix(): sha(p)
                             for p in sorted(run.rglob('*')) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = dict(evidence_kind='public_response_and_original_receipt_projection',
                 production_admitted=False, cases=[export_run(p) for p in args.run])
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps(dict(path=str(args.output), cases=len(value['cases']), sha256=sha(args.output))))
