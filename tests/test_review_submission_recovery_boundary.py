"""Proposal diagnosis only; it must not require local run files or a model."""
from pathlib import Path

from scripts.check_review_submission_shapes import audit_recovery_boundary


def test_existing_consumer_cannot_keep_both_positional_issues_and_raw_identity(monkeypatch):
    original_open = Path.open
    def committed(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix(), 'Use committed public fixtures'
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', committed)
    result = audit_recovery_boundary()
    raw, projected = result['observations']
    assert raw['actual_issues'] == 0 and raw['preserves_original_raw_identity']
    assert projected['enumerated_issues_equal'] and not projected['preserves_original_raw_identity']
    assert result['malformed_opinions_preserved_by_projection'] == ['null', 'text', 'bad_source']
    assert result['live_requests'] == 0 and not result['production_admitted']
