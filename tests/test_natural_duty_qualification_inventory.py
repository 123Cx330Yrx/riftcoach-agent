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


def test_saved_inventory_rebuilds_without_fresh_or_qualification_credit():
    value = inventory.audit()
    path = inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_dispatch_fix_20261015.json'
    assert value == json.loads(path.read_bytes())
    previous = json.loads((inventory.ROOT/'data/evaluation/results/natural_duty_qualification_inventory_20261015.json').read_bytes())
    assert {k: v for k, v in value.items() if k not in ('component_fingerprints', 'program_sha256')} == {
        k: v for k, v in previous.items() if k not in ('component_fingerprints', 'program_sha256')}
    old_rows = {r['component_id']: r for r in previous['component_fingerprints']}
    new_rows = {r['component_id']: r for r in value['component_fingerprints']}
    assert old_rows.keys() == new_rows.keys()
    assert {k for k in old_rows if old_rows[k] != new_rows[k]} == {
        'app.runtime.coach_budget', 'app.runtime.observed_provider'}
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


@pytest.mark.parametrize('changed', ['input_sha256', 'report_sha256', 'expected_initial'])
def test_changed_frozen_binding_or_label_is_rejected(monkeypatch, changed):
    cases, aliases = inventory.frozen.frozen_cases()
    altered = deepcopy(cases)
    cell = altered[0][0]
    cell[changed] = ('accept' if cell[changed] != 'accept' else 'reject') if changed == 'expected_initial' else '0'*64
    monkeypatch.setattr(inventory.frozen, 'frozen_cases', lambda: (altered, aliases))
    with pytest.raises(ValueError, match='natural_duty_(frozen_input|original15_labels)_changed'):
        inventory.audit()
