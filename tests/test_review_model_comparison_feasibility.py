"""The proposal must remain reproducible without network or local run files."""
import json
from pathlib import Path
import socket

from scripts import prepare_review_model_comparison as comparison


def test_full_request_comparison_is_offline_and_uses_committed_sources(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('offline comparison attempted network I/O')

    original_open = Path.open

    def committed_sources_only(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix()
        assert path.name != '.env'
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(socket, 'socket', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)
    monkeypatch.setattr(Path, 'open', committed_sources_only)
    result = comparison.build_plan()
    assert result == json.loads(comparison.OUTPUT.read_text(encoding='utf-8'))
    assert result['live_entry_implemented'] is False
    assert all(c['changed_sdk_fields'] == ['model'] for c in result['cells'])


def test_sdk_serialization_drift_is_not_accepted_as_model_only(monkeypatch):
    import pytest

    original = comparison.mock_wire

    def altered_schema(arguments):
        body = original(arguments)
        if arguments['model'] == comparison.ALTERNATIVE:
            body['tools'][0]['function']['description'] = 'silently changed instructions'
        return body

    monkeypatch.setattr(comparison, 'mock_wire', altered_schema)
    with pytest.raises(ValueError, match='comparison_changes_more_than_model'):
        comparison.build_plan()
