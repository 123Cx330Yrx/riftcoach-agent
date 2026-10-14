"""Real failure witnesses; offline execution must never certify their semantics."""
import socket
from pathlib import Path

import pytest

from scripts import audit_relation_review_failures as subject


def test_complete_missed_error_and_wrong_correction_witnesses(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('offline decision audit attempted network')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    original_read = Path.read_bytes

    def committed_only(path):
        if '/data/runs/' in path.as_posix():
            raise AssertionError('audit depends on ignored local run evidence')
        return original_read(path)
    monkeypatch.setattr(Path, 'read_bytes', committed_only)
    result = subject.audit()
    observed = {v['case']: v for v in result['observed_outputs']}
    assert observed['H5']['issue_blocks'] == [4]
    assert observed['H5']['recorded_semantic_defect'] == 'wrong_correction'
    assert observed['U2-baseline']['issue_blocks'] == []
    assert observed['U2-baseline']['recorded_semantic_defect'] == 'missed_error'
    assert not observed['U2-baseline']['historical_dual_review_certified']
    assert result['paired_input_check']['differing_blocks'] == [14]
    assert result['paired_input_check']['all_nonreport_inputs_identical']
    assert not result['semantic_approval'] and result['new_qualification'] == 0
    assert result['provider_calls'] == result['http_calls'] == result['native_tasks'] == 0
    edits = {v['case']: v for v in result['complete_document_edit_counterexamples']}
    assert len(edits) == 6
    assert edits['correct_relation']['equals_correct_control']
    assert not edits['false_nonseparation']['equals_correct_control']
    assert not edits['wrong_population']['equals_correct_control']
    assert not edits['empty_edit_on_error']['equals_correct_control']
    assert all(not v['semantic_approval'] for v in edits.values())
    assert all(v['other_report_bytes_preserved'] for k, v in edits.items()
               if k != 'correct_control_keep')


@pytest.mark.parametrize('cohort,metric,means,pairs', [
    ('MIDDLE', 'deaths_before_15', ('2.50', '0.50'), 'greater'),
    ('selected', 'deaths_before_15', ('2.50', '2.67'), 'overlap'),
    ('MIDDLE', 'cs_per_min', ('8.81', '9.01'), 'overlap'),
])
def test_opposite_scope_and_overlapping_metric_do_not_share_a_relation(cohort, metric, means, pairs):
    inputs, *_ = subject.historical.load()
    witness = subject.arithmetic(inputs, cohort, metric)
    assert (witness['win_mean'], witness['loss_mean']) == means
    assert witness['all_pairs'] == pairs
    assert not witness['establishes_causality'] and not witness['semantic_approval']
