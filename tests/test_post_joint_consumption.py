"""Committed real reviews, offline author edits, no qualification promotion."""
from copy import deepcopy
from pathlib import Path
import socket

import pytest

from scripts import audit_post_joint_consumption as subject


def test_real_reviews_reach_editor_and_complete_final_without_network_or_runs(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline audit attempted network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def public_only(method):
        def read(path, *args, **kwargs):
            assert '/data/runs/' not in path.as_posix()
            return method(path, *args, **kwargs)
        return read
    monkeypatch.setattr(Path, 'read_bytes', public_only(read_bytes))
    monkeypatch.setattr(Path, 'read_text', public_only(read_text))
    result = subject.audit()
    assert len(result['original15_same_inputs']) == 15
    assert len({v['key'] for v in result['original15_same_inputs']}) == 15
    assert all(v['legacy_identity_rejection'] for v in result['original15_same_inputs'])
    for name, item in result['actual_review_consumption'].items():
        scenarios = {v['scenario']: v for v in item['scenarios']}
        if name.startswith('J1'):
            assert item['issue_blocks'] == []
            assert scenarios['correct_keep']['equals_correct_control']
        else:
            assert sorted(item['issue_blocks']) == [14, 15]
            assert scenarios['correct_both']['equals_correct_control']
            assert not any(scenarios[k]['equals_correct_control'] for k in ('only_14', 'only_15', 'empty'))
        assert all(v['full_final_required'] and not v['semantic_approval'] for v in scenarios.values())
        assert all(not v['old_opinion_in_final'] for v in scenarios.values())
    assert result['provider_calls'] == result['http_calls'] == result['actual_model_edits'] == 0
    assert result['new_qualification'] == 0 and not result['execution_ready']


@pytest.mark.parametrize('path', subject.EXPECTED)
def test_changed_committed_evidence_is_rejected(monkeypatch, path):
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda p: original(p) + (b' ' if p == subject.ROOT / path else b''))
    with pytest.raises(ValueError, match='post_joint_original_changed'):
        subject.audit()


@pytest.mark.parametrize('field', ['current_input_json', 'source_message', 'report'])
def test_material_must_bind_full_sent_input(field):
    files = subject.checked(subject.SEAL)['public_json_contents']
    material = deepcopy(files['J2-baseline-initial/material.json'])
    material[field] += ' changed'
    with pytest.raises(ValueError):
        subject.material_inputs(material, files['J2-baseline-initial/issued-request.json'])


def test_corrupted_actual_edit_receipt_cannot_reach_final(monkeypatch):
    real_exchange = subject.Exchange
    monkeypatch.setattr(subject, 'Exchange', lambda req, response, sha: real_exchange(req, response, '0' * 64))
    with pytest.raises(ValueError, match='block_keyed_exchange_identity'):
        subject.audit()
