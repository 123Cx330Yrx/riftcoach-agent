"""Real failure regression; analyst probes cannot become runtime successes."""
import socket

import pytest
from pydantic import ValidationError

from scripts import check_blind_edit_failure as check
from scripts import run_blind_edit_diagnostic as runner
from scripts.native_contract_options import body


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k): pytest.fail('offline audit reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def test_original_failure_stays_rejected_after_analyst_diagnostic():
    saved, raw, original, revised, _ = check.prepare()
    observed = saved['phases'][1]['response']['content']
    value = check.audit()
    assert value['analyst_fields_completed_error'] == 'native_issue_resolution_inventory'
    assert value['analyst_mapping_cleared']['structurally_valid']
    assert not value['analyst_mapping_cleared']['semantic_approval']
    assert not value['analyst_mapping_cleared']['actual_model_response']
    with pytest.raises(ValidationError): check.validate_settlement(observed, revised, original, raw)
    assert runner.LIVE_STATUS != 'bounded_frozen_diagnostic_after_exact_ci'


def test_followup_is_existing_request_for_actual_report_with_complete_sources():
    saved, _, _, revised, request = check.prepare()
    assert revised.source.report == saved['phases'][0]['actual_report']
    assert request == check.native.request(revised)
    value = body(request)
    assert 'original_review' not in value and 'previous_review' not in value
    assert 'original_source_index' not in value
    assert check.audit()['next_request']['input_ceiling'] < 63936


def test_saved_offline_failure_audit_is_reproducible():
    assert check.audit() == check.read(check.ROOT/'data/evaluation/results/golden_blind_edit_failure_audit_6c22e93.json')
