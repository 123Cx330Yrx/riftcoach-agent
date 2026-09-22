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


def test_coverage_accounts_for_attribution_not_just_unique_ids():
    from scripts import run_golden_native_review as runner
    from app.evaluation import golden_native_partitioned_tool_review as review
    from app.evaluation.golden_review_experiment import digest
    plan = json.loads(Path('data/evaluation/results/golden_native_partitioned_tool_coverage_v2.json').read_text(encoding='utf-8'))
    all_cases = plan['completed'] + plan['cases']
    loaders = {'claim-scope': runner.prepare_claim_scope, 'scope': runner.prepare_scope,
               'attribution': runner.prepare_attribution, 'observed': runner.prepare}
    for item in all_cases:
        case, req = loaders[item['suite']](item['index'])
        assert item['id'] == case['id']
        assert item['input_sha256'] == digest(review.native.build_inputs(req).data_json)
    attribution = runner.prepare_attribution(1)[1]
    assert digest(review.native.build_inputs(attribution).data_json) in {i['input_sha256'] for i in plan['cases']}
    assert len({i['input_sha256'] for i in all_cases}) == 15
