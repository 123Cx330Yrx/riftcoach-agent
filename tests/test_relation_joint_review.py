"""Proposal isolation and complete edit consumption, with no model IO."""
import json
from pathlib import Path
import socket

import pytest

from scripts import prepare_relation_joint_review as subject
from scripts import audit_correction_consumption as historical
from scripts import report_block_keyed_editor as editor
from scripts.report_contrast_review import ContrastDocumentWorkflow as Workflow
from app.evaluation.golden_review_experiment import compact


def test_proposal_keeps_full_sources_and_private_labels_out_of_requests(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError('proposal attempted network IO')
    monkeypatch.setattr(socket.socket, 'connect', forbid)
    original = Path.read_bytes

    def committed_only(path):
        if '/data/runs/' in path.as_posix():
            raise AssertionError('proposal read ignored run')
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', committed_only)
    proposal, files = subject.prepare()
    assert not proposal['execution_ready'] and not proposal['independent_calibration']
    assert len(proposal['cells']) == 4
    assert proposal['proposed_budget']['estimated_uncached_cny'] == '5.718016'
    for name in ('J1', 'J2'):
        baseline = json.loads(files[f'{name}-baseline-initial/prepared-request.json'])
        candidate = json.loads(files[f'{name}-relation-contrast-initial/prepared-request.json'])
        assert baseline['messages'][1:] == candidate['messages'][1:]
        assert baseline['tools'] == candidate['tools']
        assert baseline['messages'][0] != candidate['messages'][0]
        for variant in subject.identity.VARIANTS:
            material = json.loads(files[f'{name}-{variant}-initial/material.json'])
            assert len(subject.source_inputs(material['report']).source.blocks) == 26
            wire = files[f'{name}-{variant}-initial/prepared-request.json'].decode()
            assert 'primary_author_expectations' not in wire
            assert 'blocking_issues' not in wire
            assert 'J1' not in wire and 'J2' not in wire


def test_both_repairs_are_needed_and_only_target_sentences_change():
    _, files = subject.prepare()
    correct = json.loads(files['J1-baseline-initial/material.json'])['report']
    wrong = json.loads(files['J2-baseline-initial/material.json'])['report']
    inputs = subject.source_inputs(wrong)
    replacements = [(14, subject.MEAN_BAD, subject.MEAN_GOOD),
                    (15, subject.ORDER_BAD, subject.ORDER_GOOD)]
    _, wire, _ = Workflow.validate_review(compact(dict(score=80, verdict='needs_revision',
        issues=[dict(block=block, severity='medium', category='fact_error', source_ids=[31, 32],
            explanation='OFFLINE author fixture; inspect complete sources.',
            suggested_correction=after) for block, _, after in replacements],
        issue_resolutions=[], advisories=[])), inputs)
    request = editor.edit_request(inputs, wire)
    for selected in (replacements, replacements[:1], replacements[1:]):
        edits = {f'block_{block}': [dict(before=before, after=after, reason='OFFLINE injected edit')]
                 for block, before, after in selected}
        result = editor.inspect_exchange(request,
            historical.simulated_exchange(request, editor.TOOL, edits), inputs, wire,
            make_final=Workflow.make_request)
        expected = wrong
        for _, before, after in selected:
            expected = expected.replace(before, after, 1)
        assert result.report == expected
        assert (result.report == correct) == (len(selected) == 2)
        assert result.journal['full_final_review_required'] is True
        assert result.journal['semantic_approval'] is False


def test_changed_seed_fails_before_proposal(monkeypatch):
    monkeypatch.setattr(subject, 'SEED_SHA', '0' * 64)
    with pytest.raises(ValueError, match='joint_review_seed_changed'):
        subject.prepare()
