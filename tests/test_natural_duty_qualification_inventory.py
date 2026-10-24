"""No-network inventory checks, with no model or semantic approval fixtures."""
from copy import deepcopy
import json
import socket

import pytest

from scripts import audit_natural_duty_qualification as inventory


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('qualification inventory cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def test_current_inventory_rebuilds_without_changing_historical_qualification():
    value = inventory.audit()
    path = inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_completion_continuation_20261024.json'
    assert value == json.loads(path.read_bytes())
    previous = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_timeout_recovery_20261022.json').read_bytes())
    assert {k:v for k,v in value.items() if k not in ('component_fingerprints','program_sha256')} == {
        k:v for k,v in previous.items() if k not in ('component_fingerprints','program_sha256')}
    assert value['provider_calls'] == value['new_host_tasks'] == value['new_qualification'] == 0
    assert not value['qualified']


def test_historical_inventory_keeps_original_change_boundary():
    path = inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_timeout_recovery_20261022.json'
    value = json.loads(path.read_bytes())
    session = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_session_20261021.json').read_bytes())
    assert {k: v for k, v in value.items() if k not in ('component_fingerprints', 'program_sha256')} == {
        k: v for k, v in session.items() if k not in ('component_fingerprints', 'program_sha256')}
    session_rows = {r['component_id']: r for r in session['component_fingerprints']}
    assert {r['component_id'] for r in value['component_fingerprints']
            if r != session_rows[r['component_id']]} == {'app.runtime.coach_contract'}
    previous = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_transport_20261015.json').read_bytes())
    assert {k: v for k, v in value.items() if k not in ('component_fingerprints', 'program_sha256')} == {
        k: v for k, v in previous.items() if k not in ('component_fingerprints', 'program_sha256')}
    old_rows = {r['component_id']: r for r in previous['component_fingerprints']}
    new_rows = {r['component_id']: r for r in value['component_fingerprints']}
    assert old_rows.keys() == new_rows.keys()
    assert {k for k in old_rows if old_rows[k] != new_rows[k]} == {
        'app.runtime.models', 'app.runtime.recorder', 'app.runtime.observed_provider',
        'app.runtime.runtime', 'app.runtime.coach_budget', 'app.runtime.coach_contract',
        'app.model_runtime', 'app.evaluation.natural_duty_workflow',
        'app.product.natural_duty_candidate'}
    assert value['initial_request_count'] == 30
    assert value['fixed_report_review_slots_if_all_cases_match_labels'] == 50
    assert value['label_counts'] == {'accept': 5, 'reject': 10}
    assert len({r['input_sha256'] for r in value['cases']}) == 15
    assert all(r['fresh_request_sha256'] is None and not r['completed'] for r in value['cases'])
    assert all(req['timeout_s'] == 300 and req['input_ceiling'] <= 64000
        for r in value['cases'] for req in r['initial_requests'].values())
    assert value['provider_calls'] == value['new_host_tasks'] == value['new_qualification'] == 0
    assert not any(value[k] for k in ('qualified', 'execution_ready', 'execution_authorized',
                                    'production_admitted', 'publication_allowed'))


def test_historical_transport_inventory_keeps_its_original_change_boundary():
    value = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_transport_20261015.json').read_bytes())
    previous = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_dispatch_fix_20261015.json').read_bytes())
    assert {k: v for k, v in value.items() if k not in ('component_fingerprints', 'program_sha256')} == {
        k: v for k, v in previous.items() if k not in ('component_fingerprints', 'program_sha256')}
    old_rows = {r['component_id']: r for r in previous['component_fingerprints']}
    new_rows = {r['component_id']: r for r in value['component_fingerprints']}
    assert new_rows.keys() - old_rows.keys() == {'app.runtime.natural_duty_provider_factory'}
    assert not old_rows.keys() - new_rows.keys()
    assert {k for k in old_rows if old_rows[k] != new_rows[k]} == {
        'app.evaluation.golden_stream_bridge', 'app.runtime.receipted_provider_factory',
        'app.evaluation.natural_duty_contract', 'app.product.natural_duty_candidate'}


@pytest.mark.parametrize('changed', ['input_sha256', 'report_sha256', 'expected_initial'])
def test_changed_frozen_binding_or_label_is_rejected(monkeypatch, changed):
    cases, aliases = inventory.frozen.frozen_cases()
    altered = deepcopy(cases)
    cell = altered[0][0]
    cell[changed] = ('accept' if cell[changed] != 'accept' else 'reject') if changed == 'expected_initial' else '0'*64
    monkeypatch.setattr(inventory.frozen, 'frozen_cases', lambda: (altered, aliases))
    with pytest.raises(ValueError, match='natural_duty_(frozen_input|original15_labels)_changed'):
        inventory.audit()
