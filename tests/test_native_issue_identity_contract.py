"""Test projection information loss, not model semantic success."""
from copy import deepcopy
import socket
import pytest
from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import compact
from scripts.check_native_issue_identity_contract import run, witnesses
from scripts.check_native_contract_options import assert_complete
from scripts.issue_identity_contract import projected_request


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs): pytest.fail('identity audit reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def test_same_block_scope_in_suggestions_survives_only_complete_projection():
    _, _, cases = witnesses()
    a, b = cases
    assert a['expected_host_only'] == b['expected_host_only'][::-1]
    for mode in ('locator_only', 'without_suggestion'):
        assert a['projected'][mode]['issues'] == b['projected'][mode]['issues']
        assert a['projected'][mode]['review_sha256'] != b['projected'][mode]['review_sha256']
    assert a['projected']['complete']['issues'] != b['projected']['complete']['issues']


def test_actual_requests_retain_full_report_sources_and_editor_output_contract():
    req, raw, _ = witnesses()
    inputs = native.build_inputs(req)
    for mode in ('locator_only', 'without_suggestion', 'complete'):
        request = projected_request(inputs, raw, mode=mode)
        assert_complete(request, inputs)
        assert request.response_contract.name == 'offline_issue_adjudicating_editor'
        assert request.max_tokens == 32768 and request.timeout_s == 300


@pytest.mark.parametrize('damage', ['unknown_block', 'unknown_source', 'security', 'unmapped_previous', 'pass'])
def test_projection_cannot_bypass_native_acceptance(damage):
    req, raw, _ = witnesses()
    inputs = native.build_inputs(req)
    value = deepcopy(native.strict_json(raw))
    kwargs = {}
    if damage == 'unknown_block': value['issues'][0]['block'] = 64
    elif damage == 'unknown_source': value['issues'][0]['source_ids'] = [999999]
    elif damage == 'security': value['issues'][0]['category'] = 'prompt_injection'
    elif damage == 'unmapped_previous': kwargs['previous_raw'] = raw
    else: value.update(verdict='pass', score=95, issues=[])
    with pytest.raises(ValueError):
        projected_request(inputs, compact(value), mode='without_suggestion', **kwargs)


def test_audit_rejects_paid_admission_without_relabelling_real_pair():
    result = run()
    assert result['provider_calls'] == 0 and not result['paid_candidate_eligible']
    assert not result['semantic_approval'] and not result['production_admitted']
