"""Full source/label separation controls; no synthetic model quality claims."""
from copy import deepcopy
import json
import socket

import pytest

from app.evaluation.natural_duty_contract import request_bytes
from app.evaluation.source_patch_editor import report_inputs
from scripts import audit_natural_duty_preservation_pairs as pairs


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('paired materials cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def test_full_sources_are_preserved_and_same_final_controls_are_real():
    data = pairs.read_dataset()
    source = pairs.source_inputs(data)
    materials = {p.case_id: p for p in pairs.material_pairs(data)}
    for p in materials.values():
        assert report_inputs(source, p.original.source.report) == p.original
        assert report_inputs(source, p.final.source.report) == p.final
        for name, arms in pairs.requests(p).items():
            base = pairs.probe.make_request(p.final, name, 'fresh')
            assert arms['baseline'] == base
            assert arms['comparison'].messages[1:-1] == base.messages[1:]
            assert arms['comparison'].tools == base.tools
            with pytest.raises(ValueError, match='natural_duty_review_identity'):
                request_bytes(arms['comparison'])
    assert materials['p01'].final == materials['p02'].final == materials['p03'].final
    assert len({materials[k].original.data_json for k in ('p01','p02','p03')}) == 3
    assert materials['p03'].original == materials['p03'].final
    assert materials['p06'].original == materials['p06'].final
    assert materials['p05'].original.source.report.count(data['segments']['correct']) == 2
    assert materials['p05'].final.source.report.count(data['segments']['correct']) == 1


def test_evaluation_labels_ids_and_rationales_cannot_change_requests():
    original = pairs.read_dataset()
    altered = deepcopy(original)
    sentinel = 'EVALUATOR_ONLY_FORBIDDEN_SENTINEL'
    for index, c in enumerate(altered['cases']):
        c['id'] = sentinel+str(index)
        c['evaluation'] = {'invented_label':sentinel, 'basis':sentinel}
    for before, after in zip(pairs.material_pairs(original), pairs.material_pairs(altered)):
        assert before.case_id != after.case_id
        assert pairs.requests(before) == pairs.requests(after)
        assert sentinel not in str(pairs.requests(after))


def test_rounding_and_cohort_premises_come_from_all_actual_rows():
    data = pairs.read_dataset()
    values = pairs.arithmetic_evidence(pairs.source_inputs(data), data['evaluation_sources'])
    assert values['win']['values'] == [3,2] and values['win']['mean_2dp'] == '2.50'
    assert values['loss']['values'] == [7,0,1] and values['loss']['mean_2dp'] == '2.67'
    assert values['middle_loss']['values'] == [0,1] and values['middle_loss']['mean_2dp'] == '0.50'


@pytest.mark.parametrize('field', ['source_input_sha256','source_report_sha256','pack_sha256','dataset_sha256'])
def test_changed_source_binding_is_rejected(field):
    data = pairs.read_dataset()
    data['source_binding'][field] = '0'*64
    with pytest.raises(ValueError, match='preservation_pairs_source_binding_changed'):
        pairs.material_pairs(data)


def test_wrong_cohort_cannot_validate_the_numeric_fixture_premise():
    data = pairs.read_dataset()
    data['evaluation_sources']['loss_rows'] = data['evaluation_sources']['middle_loss_rows']
    with pytest.raises(ValueError, match='preservation_pairs_arithmetic_changed'):
        pairs.arithmetic_evidence(pairs.source_inputs(data), data['evaluation_sources'])


def test_saved_audit_rebuilds_without_semantic_or_execution_credit():
    result = pairs.audit()
    path = pairs.ROOT/'data/evaluation/results/natural_duty_preservation_pairs_20261015.json'
    assert result == json.loads(path.read_bytes())
    assert result['request_shape_count'] == 24
    assert {arm: len({c['requests'][duty][arm]['sha256'] for c in result['cases']
                     for duty in ('facts','completion')})
            for arm in ('baseline','comparison')} == {'baseline':8, 'comparison':12}
    assert result['maximum_input_ceiling'] <= 64000
    assert all(c['model_result'] is c['independent_result'] is None for c in result['cases'])
    assert result['provider_calls'] == result['new_host_tasks'] == 0
    assert not any(result[k] for k in ('qualified','execution_ready','execution_authorized',
        'publication_allowed','actual_application_or_fresh_evidence','semantic_detection_proven',
        'independent_review_completed'))
