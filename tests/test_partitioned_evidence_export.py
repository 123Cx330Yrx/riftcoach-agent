import json
from pathlib import Path

import pytest

from scripts.export_partitioned_review import export_run, public_response


@pytest.fixture
def saved_run(tmp_path):
    # Committed public evidence only: CI must not depend on ignored local runs.
    data = json.loads(Path('data/evaluation/results/golden_native_partitioned_tool_public_8014a56.json').read_text(encoding='utf-8'))['cases'][0]
    run = tmp_path / data['run_id']
    case = run / data['result']['id']
    case.mkdir(parents=True)

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    save(run / 'receipt.json', data['receipt'])
    save(case / 'result.json', data['result'])
    save(case / 'input.json', {'report': data['original_report']})
    for c in data['calls']:
        suffix = f"{c['call']['ordinal']:03d}"
        save(case / f'call-{suffix}.json', c['call'])
        save(case / f'request-{suffix}.json', c['request'])
        save(case / f'response-{suffix}.json', {**c['response'], 'reasoning_content': 'PRIVATE_SENTINEL'})
        for key, value in c['transport'].items():
            save(case / 'streams' / f'stream-{suffix}' / f'{key}.json', value)
    for name, value in data['journals'].items():
        save(case / name, value)
    return run, case


def test_export_retains_public_review_and_excludes_reasoning(saved_run):
    result = export_run(saved_run[0])
    assert result['calls'][0]['response']['tool_calls']
    assert result['journals']['initial-correction-journal.json']['parsed_review']['verdict'] == 'pass'
    assert 'PRIVATE_SENTINEL' not in json.dumps(result)
    assert 'reasoning_content' not in result['calls'][0]['response']


def test_export_binds_json_content_to_original_journal_without_tool_projection(saved_run):
    case = saved_run[1]
    journal = json.loads((case/'initial-correction-journal.json').read_text(encoding='utf-8'))
    response = json.loads((case/'response-001.json').read_text(encoding='utf-8'))
    response.update(content=journal['raw'], tool_calls=[], finish_reason='stop')
    journal['raw_representation'] = 'response_content'
    (case/'response-001.json').write_text(json.dumps(response), encoding='utf-8')
    (case/'initial-correction-journal.json').write_text(json.dumps(journal), encoding='utf-8')
    output = export_run(saved_run[0])
    assert output['calls'][0]['response']['content'] == journal['raw']
    assert 'PRIVATE_SENTINEL' not in json.dumps(output)
    response['content'] += 'unmatched tail'
    (case/'response-001.json').write_text(json.dumps(response), encoding='utf-8')
    with pytest.raises(ValueError, match='journal_response'): export_run(saved_run[0])


@pytest.fixture
def failed_run(tmp_path):
    evidence = json.loads(Path('data/evaluation/results/golden_buffered_phase_failure_da06b5a.json').read_text(encoding='utf-8'))
    receipt = evidence['original_receipt']
    result = evidence['original_result']
    usage = evidence['accounting_correction']
    for key in ('input_tokens', 'output_tokens', 'unknown_usage_calls'):
        receipt[key] = result[key] = usage[key]
    result['unassembled_usage'] = [dict(ordinal=1, input_tokens=usage['input_tokens'],
        output_tokens=usage['output_tokens'], source='normalized_stream_usage')]
    run=tmp_path/'scripted'; case=run/'attribution_original'; stream=case/'streams/stream-001'
    stream.mkdir(parents=True)
    for path,value in [(run/'receipt.json',receipt),(case/'result.json',result),
            (case/'input.json',evidence['original_report'])]:
        path.write_text(json.dumps(value),encoding='utf-8')
    for name in ('reservation','progress','result'):
        (stream/f'{name}.json').write_text(json.dumps(evidence['transport'][name]),encoding='utf-8')
    return run, case, stream


def test_export_checks_observed_usage_without_inventing_completed_response(failed_run):
    run, case, _ = failed_run
    exported=export_run(run)
    assert not exported['calls'] and exported['result']['completed_calls'] == 0
    assert exported['result']['unknown_usage_calls'] == 0 and not exported['result']['valid']
    assert len(exported['unassembled_usage_evidence']) == 1
    result = json.loads((case/'result.json').read_text(encoding='utf-8'))
    result['unassembled_usage'][0]['output_tokens'] += 1
    (case/'result.json').write_text(json.dumps(result),encoding='utf-8')
    with pytest.raises(ValueError,match='unassembled_usage'): export_run(run)


@pytest.mark.parametrize('fault,code', [
    ('reservation_ordinal', 'reservation_identity'),
    ('reservation_transport', 'reservation_identity'),
    ('terminal_transport', 'transport_identity'),
    ('unaccounted_call', 'accounting_balance'),
    ('receipt_reserved_count', 'reserved_count'),
    ('boolean_count', 'count_invalid'),
    ('negative_unknown', 'count_invalid'),
    ('duplicate_usage', 'unassembled_ordinal'),
    ('unknown_with_known_usage', 'accounting_balance'),
])
def test_failed_export_rejects_mismatched_call_identity_and_accounting(failed_run, fault, code):
    run, case, stream = failed_run
    paths = dict(receipt=run/'receipt.json', result=case/'result.json',
        reservation=stream/'reservation.json', terminal=stream/'result.json')
    values = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in paths.items()}
    if fault == 'reservation_ordinal': values['reservation']['ordinal'] = 2
    elif fault == 'reservation_transport': values['reservation']['transport_id'] = 'other'
    elif fault == 'terminal_transport': values['terminal']['transport_id'] = 'other'
    elif fault == 'receipt_reserved_count': values['receipt']['reserved_calls'] = 2
    elif fault == 'boolean_count':
        values['receipt']['reserved_calls'] = values['result']['reserved_calls'] = True
    elif fault == 'negative_unknown':
        values['receipt']['unknown_usage_calls'] = values['result']['unknown_usage_calls'] = -1
    elif fault == 'unaccounted_call':
        values['receipt']['reserved_calls'] = values['result']['reserved_calls'] = 2
    elif fault == 'unknown_with_known_usage':
        values['receipt']['unknown_usage_calls'] = values['result']['unknown_usage_calls'] = 1
    else: values['result']['unassembled_usage'] *= 2
    for key, path in paths.items(): path.write_text(json.dumps(values[key]), encoding='utf-8')
    with pytest.raises(ValueError, match=code): export_run(run)


def test_export_keeps_genuinely_unknown_failed_call_without_invented_usage(failed_run):
    run, case, stream = failed_run
    for path in (run/'receipt.json', case/'result.json'):
        value = json.loads(path.read_text(encoding='utf-8'))
        value.update(input_tokens=0, output_tokens=0, unknown_usage_calls=1)
        value.pop('unassembled_usage', None)
        path.write_text(json.dumps(value), encoding='utf-8')
    progress = json.loads((stream/'progress.json').read_text(encoding='utf-8'))
    progress.update(input_tokens=None, output_tokens=None)
    (stream/'progress.json').write_text(json.dumps(progress), encoding='utf-8')
    exported = export_run(run)
    assert exported['result']['unknown_usage_calls'] == 1
    assert exported['result']['input_tokens'] == exported['result']['output_tokens'] == 0
    assert not exported['calls'] and not exported['unassembled_usage_evidence']


def test_completed_export_checks_actual_stream_ordinal(saved_run):
    stream = saved_run[1]/'streams/stream-001/reservation.json'
    value = json.loads(stream.read_text(encoding='utf-8'))
    value['ordinal'] = 2
    stream.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='reservation_identity'): export_run(saved_run[0])


def test_completed_call_followed_by_unknown_failure_keeps_separate_accounting(saved_run):
    run, case = saved_run
    for path in (run/'receipt.json', case/'result.json'):
        value = json.loads(path.read_text(encoding='utf-8'))
        value.update(reserved_calls=2, unknown_usage_calls=1)
        path.write_text(json.dumps(value), encoding='utf-8')
    # A process may fail after reservation but before a progress record exists.
    second = case/'streams/stream-002'
    second.mkdir()
    reservation = json.loads((case/'streams/stream-001/reservation.json').read_text(encoding='utf-8'))
    reservation.update(ordinal=2, request_sha256='1'*64)
    (second/'reservation.json').write_text(json.dumps(reservation), encoding='utf-8')
    exported = export_run(run)
    assert len(exported['calls']) == exported['result']['completed_calls'] == 1
    assert exported['result']['unknown_usage_calls'] == 1
    assert not exported['unassembled_usage_evidence']
    for key in ('input_tokens', 'output_tokens'):
        assert exported['result'][key] == exported['calls'][0]['call'][key]
    (second/'reservation.json').unlink()
    second.rmdir()
    with pytest.raises(ValueError, match='reservation_inventory'): export_run(run)


@pytest.mark.parametrize('filename,key,value,error', [
    ('result.json', 'completed_calls', 2, 'call_count'),
    ('call-001.json', 'input_tokens', 1, 'call_usage'),
    ('call-001.json', 'request_sha256', 'incorrect', 'request_receipt'),
])
def test_export_rejects_inconsistent_receipt(saved_run, filename, key, value, error):
    file = saved_run[1] / filename
    content = json.loads(file.read_text(encoding='utf-8'))
    content[key] = value
    file.write_text(json.dumps(content), encoding='utf-8')
    with pytest.raises(ValueError, match=error):
        export_run(saved_run[0])


def test_coverage_accounts_for_attribution_not_just_unique_ids(monkeypatch):
    from dataclasses import replace
    import hashlib
    from scripts import run_golden_native_review as runner
    from scripts.check_native_claim_scope import load_controls
    from tests.test_golden_native_reassessment import recorded_failure
    from app.evaluation import golden_native_partitioned_tool_review as review
    from app.evaluation.golden_review_experiment import digest

    original_open = Path.open

    def committed_only(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix(), 'coverage must not depend on ignored local runs'
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', committed_only)
    # Existing committed actual-request fixtures preserve the complete sources.
    # Recompile each report and compare the frozen live-input hash; do not mock
    # the source checks or replace missing sources with invented data.
    _, _, attribution_source = load_controls()
    _, observed_source = recorded_failure()
    plan = json.loads(Path('data/evaluation/results/golden_native_partitioned_tool_coverage_v2.json').read_text(encoding='utf-8'))
    all_cases = plan['completed'] + plan['cases']
    manifests = {'claim-scope': runner.CLAIM_SCOPE_DATASET, 'scope': runner.SCOPE_DATASET,
                 'attribution': runner.ATTRIBUTION_DATASET, 'observed': runner.DATASET}
    for item in all_cases:
        path = manifests[item['suite']]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['manifest_sha256']
        dataset = json.loads(path.read_text(encoding='utf-8'))
        case = dataset['cases'][item['index'] - 1]
        source = observed_source if item['suite'] == 'observed' else attribution_source
        req = replace(source, report=case['report'], user_utterance=dataset['user_utterance'])
        assert item['id'] == case['id']
        assert item['expected_initial'] == case['expected_report']
        assert item['report_sha256'] == digest(req.report)
        assert item['input_sha256'] == digest(review.native.build_inputs(req).data_json)
    data = json.loads(runner.ATTRIBUTION_DATASET.read_text(encoding='utf-8'))
    attribution = replace(attribution_source, report=data['cases'][0]['report'], user_utterance=data['user_utterance'])
    assert digest(review.native.build_inputs(attribution).data_json) in {i['input_sha256'] for i in plan['cases']}
    assert len({i['input_sha256'] for i in all_cases}) == 15
