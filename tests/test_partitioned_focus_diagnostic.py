"""Diagnostic isolation and stop behavior; scripted replies are not quality evidence."""
import json
from pathlib import Path

from scripts import run_partitioned_focus_diagnostic as diagnostic
from tests.test_golden_native_partitioned_tool_review import exchange_provider, tool_response, valid_review


def test_focus_preserves_full_input_and_schema_without_sending_labels(monkeypatch):
    original_open = Path.open

    def committed_only(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix()
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', committed_only)
    variants, plan = diagnostic.prepare()
    assert plan == json.loads(diagnostic.PLAN.read_text(encoding='utf-8'))
    assert plan['full_reservation'] <= 401920
    for _, inputs, focused in variants:
        base = diagnostic.review.request(inputs)
        assert focused.messages[1:] == base.messages[1:]
        assert focused.tools == base.tools
        assert focused.max_tokens == base.max_tokens == 32768
        assert focused.timeout_s == base.timeout_s == 300
        assert 'expected_host_only' not in '\n'.join(m.content for m in focused.messages)
    assert variants[0][2].messages[0] == variants[1][2].messages[0]


def test_wrong_semantic_verdict_still_completes_frozen_pair_without_edit(tmp_path):
    variants, _ = diagnostic.prepare()
    # The first pass is the known wrong label; do not erase it or trigger edits.
    provider = exchange_provider([tool_response(valid_review()), tool_response(valid_review())])
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['protocol_complete'] and result['completed_calls'] == 2
    assert not result['manual_semantic_acceptance'] and not result['production_admitted']
    assert len(provider.requests) == 2
    for case_id, _, request in variants:
        journal = json.loads((tmp_path / case_id / 'journal.json').read_text(encoding='utf-8'))
        assert journal['policy_sha256'] == diagnostic.digest(request.messages[0].content)
        assert journal['full_report_review'] is False


def test_protocol_failure_stops_pair_without_reassessment(tmp_path):
    variants, _ = diagnostic.prepare()
    provider = exchange_provider([tool_response({})])
    result = diagnostic.observe(provider, tmp_path, variants)
    assert result['stop_reason'] == 'protocol_or_execution_failure'
    assert result['completed_calls'] == len(provider.requests) == 1
    assert result['unknown_usage_calls'] == 0
    assert (tmp_path / variants[0][0] / 'response.json').exists()
    assert not (tmp_path / variants[1][0]).exists()
