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
