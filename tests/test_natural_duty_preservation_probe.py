"""Input/identity evidence only; no model semantic success is synthesized."""
from dataclasses import replace
import json
import socket

import pytest

from app.evaluation.golden_review_experiment import compact
from app.evaluation.natural_duty_contract import make_request, request_bytes
from app.evaluation.source_patch_editor import report_inputs
from scripts import probe_natural_duty_preservation as probe
from scripts import review_duty_direct_patch as direct
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER
from tests.test_review_duty_direct_patch import pair, repaired


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('preservation probe cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


@pytest.fixture(scope='module')
def sample():
    _, inputs, _, raw = cases()['claim-scope:4']
    return inputs, json.loads(raw)


@pytest.mark.parametrize('name', probe.duty.DUTIES)
def test_actual_patch_preview_preserves_full_final_sources_and_original(sample, name):
    inputs, value = sample
    assembly = direct.preview(inputs, pair(inputs, repaired(value)))
    revised = report_inputs(inputs, assembly.report)
    base = make_request(revised, name, 'fresh')
    request = probe.comparison_request(inputs, revised, name)
    assert request.messages[1:-1] == base.messages[1:]
    assert request.tools == base.tools and request.timeout_s == 300 and request.max_tokens == 32768
    original_message = request.messages[-1]
    original = json.loads(original_message.content[len(probe.ORIGINAL_HEADER):-len(probe.ORIGINAL_END)])
    assert original == dict(report=inputs.source.report, report_sha256=probe.digest(inputs.source.report))
    assert BEFORE not in revised.source.report and AFTER in revised.source.report
    assert original_message.role.value == 'user'
    assert 'OFFLINE authored replacement.' not in str(request.messages)
    assert 'accepted_review' not in original and 'previous_review' not in original
    assert 'repairs' not in request.tools[0].input_schema['properties']
    with pytest.raises(ValueError, match='natural_duty_review_identity'):
        request_bytes(request)


@pytest.mark.parametrize('name', probe.duty.DUTIES)
def test_same_final_loses_original_history_in_current_request(sample, name):
    original, _ = sample
    removed = original.source.blocks[5][1]
    final = report_inputs(original, original.source.report.replace(removed, '', 1))
    other_original = report_inputs(original, final.source.report)
    assert original != other_original
    assert make_request(report_inputs(original, final.source.report), name, 'fresh') == make_request(
        report_inputs(other_original, final.source.report), name, 'fresh')
    assert probe.comparison_request(original, final, name).messages != probe.comparison_request(
        other_original, final, name).messages


@pytest.mark.parametrize('mutation', ['knowledge', 'report_index'])
def test_changed_context_is_rejected_before_comparison(sample, mutation):
    original, _ = sample
    revised = report_inputs(original, original.source.report.replace(BEFORE, AFTER))
    data = json.loads(revised.data_json)
    if mutation == 'knowledge':
        data['knowledge']['context'] += ' changed context'
    else:
        data['source_index']['blocks'] = []
    with pytest.raises(ValueError, match='preservation_probe_sources_changed'):
        probe.comparison_request(original, replace(revised, data_json=compact(data)), 'facts')


def test_large_legal_reports_reject_instead_of_truncating(sample):
    original, _ = sample
    # Each report is within the existing 24000-character report envelope.
    large = report_inputs(original, original.source.report + '\n\n' + '测' * 3000)
    assert len(large.source.report) < 24000
    # The existing final-only request must fit; the added original causes the
    # rejection, rather than an already invalid baseline request.
    assert probe.frozen.size(make_request(large, 'facts', 'fresh')) <= 64000
    with pytest.raises(ValueError, match='budget|ceiling|input'):
        probe.comparison_request(large, large, 'facts')


def test_saved_probe_rebuilds_without_execution_or_semantic_credit():
    result = probe.audit()
    path = probe.ROOT/'data/evaluation/results/natural_duty_preservation_probe_20261015.json'
    assert result == json.loads(path.read_bytes())
    assert result['same_report_shape_probe_count'] == 30
    assert len(result['cases']) == 15
    assert result['maximum_comparison_input_ceiling'] <= 64000
    assert result['provider_calls'] == result['new_host_tasks'] == 0
    assert not any(result[k] for k in ('qualified', 'execution_ready', 'execution_authorized',
        'production_admitted', 'publication_allowed', 'semantic_detection_proven',
        'actual_application_or_fresh_evidence'))
