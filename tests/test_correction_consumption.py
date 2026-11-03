"""Executable counterexamples, not claims of automated semantic detection."""
import socket

import pytest

from scripts import audit_correction_consumption as subject


def test_real_h5_and_whole_text_control_do_not_make_structure_semantic(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('offline audit attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    result = subject.audit()
    assert len(result['rows']) == 14
    assert result['historical_host_rejection_unchanged']
    assert result['lower_level_fault_injection_bypasses_host_gate']
    assert len(result['actual_free_form_edit_failures']) == 4
    assert not any(row['semantic_approval'] for row in result['rows'])


@pytest.mark.parametrize('protocol', ['block_keyed', 'source_cited'])
def test_anchor_failure_is_structural_and_atomic(protocol):
    inputs, wire = subject.synthetic_coach_case()
    original = inputs.source.report
    with pytest.raises(ValueError, match='anchor_not_unique'):
        subject.assemble(protocol, inputs, wire, subject.CORRECT, before='NONEXISTENT-ANCHOR')
    assert inputs.source.report == original


def test_valid_source_does_not_prove_edit_but_invalid_source_is_rejected():
    inputs, wire = subject.synthetic_coach_case()
    result = subject.assemble('source_cited', inputs, wire, subject.BAD_SEPARATION)
    assert result.report != inputs.source.report
    with pytest.raises(ValueError, match='not_citable'):
        subject.assemble('source_cited', inputs, wire, subject.BAD_SEPARATION, refs=(99999,))
