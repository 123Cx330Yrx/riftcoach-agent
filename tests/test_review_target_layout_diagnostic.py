"""Isolate the changed input and exercise real budget/validation boundaries."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, CapacityBridgeObservation
from app.providers.errors import ProviderResponseError
from scripts import diagnose_review_target_layout as diagnostic
from tests.test_golden_native_partitioned_tool_review import exchange_provider, tool_response, valid_review


def provider_for(responses):
    provider = exchange_provider(responses)
    original = provider.chat
    provider._calls = 0

    def chat(request):
        provider._calls += 1
        return original(request)

    provider.chat = chat
    return provider


def unpack(message):
    return json.loads(message.content.split('[UNTRUSTED DATA]\n', 1)[1].rsplit('\n[END UNTRUSTED DATA]', 1)[0])


def test_frozen_four_cells_preserve_all_values_rules_and_schema(monkeypatch):
    original_open = Path.open

    def committed_only(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix()
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', committed_only)
    variants, plan = diagnostic.prepare()
    assert plan == json.loads(diagnostic.PLAN.read_text(encoding='utf-8'))
    assert plan['full_reservation'] <= 401920
    assert len(variants) == 4
    for left, right in [(variants[0], variants[1]), (variants[3], variants[2])]:
        _, inputs, base = left
        _, same_inputs, moved = right
        assert inputs == same_inputs
        assert unpack(base.messages[1]) == unpack(moved.messages[2])
        assert list(unpack(moved.messages[2]))[-1] == 'source_index'
        assert base.messages[0] == moved.messages[0]
        assert base.messages[2] == moved.messages[1]
        assert replace(moved, messages=base.messages) == base
        assert 'expected_host_only' not in '\n'.join(m.content for m in moved.messages)
    # No diagnostic direction to a labelled paragraph or one particular metric.
    assert variants[0][2].messages[0] == variants[2][2].messages[0]


def test_reordering_preserves_reassessment_identity_and_malformed_prior_issue():
    _, inputs, _ = diagnostic.prepare()[0][0]
    value = valid_review(issue=True)
    value['issues'][0]['source_ids'] = 'bad source type'
    raw = diagnostic.compact(value)
    baseline = diagnostic.review.request(inputs, previous_raw=raw, diagnostics={'field': 'source_ids'})
    moved = diagnostic.target_last(baseline)
    before, after = unpack(baseline.messages[1]), unpack(moved.messages[2])
    assert before == after
    assert after['previous_raw_sha256'] == diagnostic.digest(raw)
    assert len(after['previous_issues']) == 1
    assert after['previous_issues'][0]['issue']['source_ids'] == 'bad source type'


def test_wrong_semantics_retained_in_all_four_cells_no_edits(tmp_path):
    variants, _ = diagnostic.prepare()
    provider = provider_for([tool_response(valid_review())] * 4)
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['protocol_complete'] and result['completed_calls'] == result['reserved_calls'] == 4
    assert result['unknown_usage_calls'] == 0
    assert result['input_tokens'] == result['output_tokens'] == 40
    assert not result['manual_semantic_acceptance'] and not result['production_admitted']
    assert len(provider.requests) == 4
    for name, _, _ in variants:
        journal = json.loads((tmp_path / name / 'journal.json').read_text(encoding='utf-8'))
        assert journal['full_report_review']
        assert journal['parsed_review']['issues'] == []  # Includes incorrect passes.


def test_invalid_first_response_stops_without_retry(tmp_path):
    variants, _ = diagnostic.prepare()
    provider = provider_for([tool_response({})])
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['stop_reason'] == 'protocol_or_execution_failure'
    assert result['completed_calls'] == result['reserved_calls'] == 1
    assert result['unknown_usage_calls'] == 0
    assert (tmp_path / variants[0][0] / 'response.json').exists()
    assert not (tmp_path / variants[1][0]).exists()


@pytest.mark.parametrize('known', [False, True])
def test_failed_transport_counts_observed_usage_without_fabricating_response(tmp_path, known):
    variants, _ = diagnostic.prepare()
    provider = provider_for([])

    def fail(request):
        provider._calls += 1
        path = tmp_path / 'transport/stream-001'
        path.mkdir(parents=True)
        (path / 'reservation.json').write_text(json.dumps(dict(ordinal=1, transport_id=CAPACITY_TRANSPORT_ID,
            state='reserved_before_io', request_sha256='a' * 64)))
        (path / 'result.json').write_text(json.dumps(dict(state='failed', transport_id=CAPACITY_TRANSPORT_ID)))
        observation = CapacityBridgeObservation(input_tokens=12 if known else None, output_tokens=7 if known else None)
        (path / 'progress.json').write_text(observation.model_dump_json())
        raise ProviderResponseError(provider='zhipu', code='tool_call_arguments')

    provider.chat = fail
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['reserved_calls'] == 1 and result['completed_calls'] == 0
    assert result['unknown_usage_calls'] == int(not known)
    assert result['input_tokens'] == (12 if known else 0)
    assert result['output_tokens'] == (7 if known else 0)
    assert not (tmp_path / variants[0][0] / 'response.json').exists()


def test_budget_rejection_before_io_does_not_invent_unknown_call(tmp_path):
    variants, _ = diagnostic.prepare()
    name, inputs, request = variants[0]
    variants[0] = (name, inputs, replace(request, messages=(replace(request.messages[0], content='x' * 500000),)))
    provider = provider_for([])
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['reserved_calls'] == result['completed_calls'] == result['unknown_usage_calls'] == 0
    assert result['error_code'] in ('token_budget_exhausted', 'stream_request_budget')
    assert not provider.requests


def test_run_requires_exact_ci_before_credentials_or_output(monkeypatch):
    import argparse
    import dotenv
    def blocked(_):
        raise ValueError('exact_sha_public_ci_required')
    def forbidden(*args, **kwargs):
        pytest.fail('credentials loaded before CI')
    monkeypatch.setattr(diagnostic, 'verify_public_ci', blocked)
    monkeypatch.setattr(diagnostic, 'LIVE_STATUS', 'bounded_diagnostic_after_exact_ci')
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    with pytest.raises(ValueError, match='exact_sha_public_ci_required'):
        diagnostic.run(argparse.Namespace(execute=True, ci_run='wrong', env_file=None))


def test_rejected_layout_entry_stops_before_sources_ci_or_secrets(monkeypatch):
    import argparse
    import dotenv
    def forbidden(*args, **kwargs):
        pytest.fail('closed layout diagnostic reached input/CI/credentials')
    monkeypatch.setattr(diagnostic, 'prepare', forbidden)
    monkeypatch.setattr(diagnostic, 'verify_public_ci', forbidden)
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    with pytest.raises(ValueError, match='layout_semantic_failure_no_retry'):
        diagnostic.run(argparse.Namespace(execute=True, ci_run='', env_file=None))
