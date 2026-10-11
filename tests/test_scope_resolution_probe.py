"""Guard diagnostic isolation; no model behavior is simulated as acceptance."""
import json

import pytest

from scripts.prepare_scope_resolution_probe import prepare, ROOT, SEAL


def _data(cell):
    text = cell['request']['messages'][1]['content']
    return json.loads(text.split('\n', 1)[1].rsplit('\n', 1)[0])


def test_counterfactual_changes_only_asserted_scope_and_derived_hashes():
    result = prepare()
    actual, explicit = result['cells']
    a, b = _data(actual), _data(explicit)
    assert actual['synthetic_report'] is False and explicit['synthetic_report'] is True
    assert [x['block'] for x, y in zip(a['source_index']['blocks'], b['source_index']['blocks']) if x != y] == [4]
    assert a['source_index']['blocks'][13] == b['source_index']['blocks'][13]
    assert a['previous_review'] == b['previous_review']
    for key in a:
        if key not in ('source_index', 'source_roots', 'computed_evidence'):
            assert a[key] == b[key], key
    for key in a['computed_evidence']:
        if key != 'source_digest':
            assert a['computed_evidence'][key] == b['computed_evidence'][key]


def test_expectations_are_outside_requests_and_all_prior_issues_accounted_for():
    result = prepare()
    assert result['provider_requests'] == 0
    assert result['execution_enabled'] is False and result['paid_plan_frozen'] is False
    for cell in result['cells']:
        request = json.dumps(cell['request'], ensure_ascii=False)
        assert 'host_only_expected' not in request
        assert 'authored_fixture_validation' not in request
        assert cell['missing_mapping_rejected']
        assert len(_data(cell)['previous_issues']) == 2
    assert result['cells'][0]['host_only_expected_dispositions'] == ['withdrawn', 'replaced']
    assert result['cells'][1]['host_only_expected_dispositions'] == ['replaced', 'replaced']


def test_changed_seal_fails_before_building_probe(tmp_path):
    target = tmp_path / SEAL
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / SEAL).read_bytes() + b'\n')
    with pytest.raises(ValueError, match='scope_probe_original_seal_changed'):
        prepare(tmp_path)
