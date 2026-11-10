"""Source addressing/recovery regressions; no live or semantic qualification."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from app.evaluation import golden_explicit_source_projection as projection
from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_bounded_correction_requests import restore_generation
from app.evaluation.golden_contextual_requests import restore as restore_tables
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from scripts.diagnose_review_target_layout import prepare, ROOT
from tests.test_golden_contextual_recovery import request as external_request
from tests.test_golden_review_source_catalog import source_input
from tests.test_golden_native_partitioned_tool_review import tool_response, valid_review


@pytest.fixture(scope='module')
def baselines():
    return [row for row in prepare()[0] if row[0].endswith('-baseline')]


@pytest.fixture(scope='module')
def actual_arguments():
    evidence = json.loads((ROOT / 'data/evaluation/results/golden_review_model_comparison_result_b6b30f8.json')
                          .read_text(encoding='utf-8'))
    return evidence['original_json_contents']['attribution_original-baseline/response.json']['tool_calls'][0]['arguments']


def change_data(request, edit):
    header, data = projection._unpack(request)
    edit(data)
    return replace(request, messages=(request.messages[0], replace(request.messages[1],
        content=header + compact(data) + projection.END), request.messages[2]))


@pytest.mark.parametrize('kind', ['wrong_control', 'correct_control', 'typed_sources', 'external_snapshot'])
def test_all_original_sources_and_addresses_survive_roundtrip(kind, baselines):
    inputs = (baselines[0 if kind == 'wrong_control' else 1][1] if kind.endswith('control')
              else source_input() if kind == 'typed_sources'
              else review.native.build_inputs(external_request()))
    before = deepcopy(inputs)
    request = review.request(inputs)
    projected = projection.project_request(request, inputs)
    assert projected != request and inputs == before
    assert projection.restore_request(projected, inputs) == request
    _, data = projection._unpack(projected)
    assert 'evidence_keys' not in data['source_index']
    lookup = data['source_index']['evidence_by_id']
    assert '0' not in lookup
    # The literal table IDs (including provenance) locate the original keys.
    pack = json.loads(inputs.pack_json)
    for field, tables in [('facts', 'fact_tables'), ('provenance', 'provenance_tables')]:
        for table in data[tables]:
            for number, values in table['rows']:
                assert dict(zip(table['columns'], values, strict=True)) == pack[field][lookup[str(number)]]
    ids = [row[0] for row in data['source_roots']['legacy'] + data['source_roots']['additional']]
    resolved = review.native.resolve_refs(inputs, ids)
    assert {row['source_id'] for row in resolved} == set(ids)
    assert all(row['catalog_sha256'] == data['source_roots']['catalog_sha256']
               and row['input_sha256'] == digest(inputs.data_json) for row in resolved)
    _, original_data = projection._unpack(projection.restore_request(projected, inputs))
    original_data.pop('source_roots')
    original_data.pop('computed_evidence')
    original_data['deterministic_source_facts'] = json.loads(inputs.data_json)['deterministic_source_facts']
    restored = restore_tables(original_data)
    restored['generation_facts'] = restore_generation(restored.pop('generation_view'),
                                                       restored['facts_and_provenance']['facts'])
    assert restored == json.loads(inputs.data_json)
    if kind == 'external_snapshot':
        assert list(data['external_fact_paths'].values()) == [[0, 0]]  # Physical paths stay zero-based.


def test_reassessment_keeps_every_actual_bad_opinion_and_original_identity(baselines, actual_arguments):
    _, inputs, _ = baselines[0]
    # This remains rejected. Its invalid IDs must still reach the recovery input.
    raw = compact(actual_arguments)
    before = deepcopy(actual_arguments)
    request = review.request(inputs, previous_raw=raw, diagnostics=['semantic_source_id_unknown'])
    projected = projection.project_request(request, inputs)
    _, data = projection._unpack(projected)
    _, old_data = projection._unpack(request)
    for field in ('previous_review', 'previous_issues', 'previous_raw_sha256', 'diagnostics'):
        assert data[field] == old_data[field]
    assert data['previous_review'] == actual_arguments
    assert data['previous_raw_sha256'] == digest(raw)
    assert actual_arguments == before
    assert projection.restore_request(projected, inputs) == request
    with pytest.raises(ValueError, match='semantic_source_id_unknown'):
        review.validate(raw, inputs)


def test_revision_preserves_editor_input_and_does_not_add_advice(baselines):
    _, inputs, _ = baselines[0]
    accepted = review.PartitionedReview.model_validate(valid_review(issue=True, advisory=True))
    request = review.request(inputs, accepted=accepted)
    projected = projection.project_request(request, inputs)
    assert not projected.tools and projected.response_contract is None
    _, data = projection._unpack(projected)
    _, before = projection._unpack(request)
    assert data['accepted_review'] == before['accepted_review']
    assert 'advisories' not in data['accepted_review']
    assert projection.restore_request(projected, inputs) == request


@pytest.mark.parametrize('edit', [
    lambda d: d['source_index']['evidence_by_id'].update({'0': 'facts:recent_aggregate'}),
    lambda d: d['source_index']['evidence_by_id'].pop('1'),
    lambda d: d['source_index']['evidence_by_id'].update({'1': 'facts:scope'}),
    lambda d: d['source_index']['evidence_by_id'].update({'01': 'facts:recent_aggregate'}),
    lambda d: d['source_index'].update(evidence_keys=[]),
    lambda d: d['source_roots'].update(catalog_sha256='0' * 64),
    lambda d: d['source_index']['blocks'][0].update(text='another report'),
    lambda d: d['fact_tables'][0]['rows'][0][1].__setitem__(0, None),
])
def test_wrong_ids_and_changed_sources_cannot_be_restored(baselines, edit):
    _, inputs, request = baselines[0]
    projected = projection.project_request(request, inputs)
    with pytest.raises(ValueError, match='explicit_source_'):
        projection.restore_request(change_data(projected, edit), inputs)


def test_map_order_is_not_a_second_coordinate_system(baselines):
    _, inputs, request = baselines[0]
    projected = projection.project_request(request, inputs)
    changed = change_data(projected, lambda d: d['source_index'].update(
        evidence_by_id=dict(reversed(list(d['source_index']['evidence_by_id'].items())))))
    assert projection.restore_request(changed, inputs) == request


def test_no_reprojection_or_policy_drift_or_reuse_on_other_report(baselines):
    _, inputs, request = baselines[0]
    projected = projection.project_request(request, inputs)
    with pytest.raises(ValueError, match='explicit_source_'):
        projection.project_request(projected, inputs)
    with pytest.raises(ValueError, match='explicit_source_'):
        projection.restore_request(projected, baselines[1][1])
    changed = replace(request, messages=(replace(request.messages[0],
        content=request.messages[0].content + projection.OLD_ADDRESS), *request.messages[1:]))
    with pytest.raises(ValueError, match='projection_conflict'):
        projection.project_request(changed, inputs)


def test_new_receipt_required_and_actual_bad_output_still_rejected(baselines, actual_arguments):
    _, inputs, old_request = baselines[0]
    request = projection.project_request(old_request, inputs)
    response = tool_response(actual_arguments)
    sha = hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
    old_sha = hashlib.sha256(validate_request(old_request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
    assert sha != old_sha
    exchange = Exchange(request, response, sha)
    with pytest.raises(ValueError, match='integrated_issued_input_mismatch'):
        review.tool.tool_result(old_request, exchange)
    with pytest.raises(ValueError, match='integrated_receipt_mismatch'):
        review.tool.tool_result(request, replace(exchange, receipt_request_sha256=old_sha))
    raw = review.tool.tool_result(request, exchange)
    assert json.loads(raw) == actual_arguments
    with pytest.raises(ValueError, match='semantic_source_id_unknown'):
        review.validate(raw, inputs)
