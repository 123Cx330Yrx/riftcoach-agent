"""Closed previews keep their original identity without masking request drift."""
from dataclasses import replace

import pytest

from scripts import run_flash_knowledge_time_review_pair as flash
from scripts import run_independent_edit_pair as independent
from scripts import run_source_patch_pair as patch


@pytest.mark.parametrize("runner", [flash, independent, patch])
def test_closed_preview_rejects_changed_budget(runner, monkeypatch):
    original = runner.size
    monkeypatch.setattr(runner, "size", lambda request: original(request) + 1)
    with pytest.raises(ValueError, match="closed_preview_request_or_plan_changed"):
        runner.prepare()


@pytest.mark.parametrize("runner", [flash, independent, patch])
def test_closed_preview_rejects_tampered_export(runner, monkeypatch, tmp_path):
    changed = tmp_path / "closed.json"
    changed.write_bytes(runner.CLOSED_EVIDENCE.read_bytes() + b"\n")
    monkeypatch.setattr(runner, "CLOSED_EVIDENCE", changed)
    with pytest.raises(ValueError, match="closed_preview_evidence_changed"):
        runner.prepare()


def test_closed_preview_rejects_changed_serialized_request(monkeypatch):
    original = independent.edit_request
    monkeypatch.setattr(independent, "edit_request", lambda inputs:
        replace(original(inputs), max_tokens=16384))
    with pytest.raises(ValueError, match="closed_preview_request_or_plan_changed"):
        independent.prepare()
