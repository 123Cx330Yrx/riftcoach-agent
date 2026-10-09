"""Offline inventory and privacy boundary, not actual GLM results."""
import json

from scripts import prepare_full15_resumption_candidate as preparation
from scripts.report_contrast_review import CONTRASTS


def test_full_original_inventory_and_complete_diagnostic_budget_have_no_paid_authority():
    manifest, artifacts = preparation.prepare()
    assert len(manifest['cells']) == len(artifacts) == 15
    assert len(manifest['proposed_diagnostic_sequence']) == 10
    assert set(manifest['proposed_diagnostic_sequence']) == {r['key'] for r in manifest['cells']
        if r['selected_for_proposed_diagnostic']}
    assert manifest['proposed_budget']['role_calls'] == {'glm-5.3': 19, 'glm-5.3-flash': 9}
    assert manifest['proposed_budget']['max_calls'] == 28
    assert manifest['provider_calls'] == manifest['new_qualification'] == 0
    assert not manifest['execution_ready'] and not manifest['execution_authorized']
    assert not manifest['historical_reviews_reused']
    for raw in artifacts.values():
        value = json.loads(raw)
        assert value['messages'][0]['content'].count(CONTRASTS) == 1
        assert value['metadata']['review_phase'] == 'native_business_review'
        assert 'host_only_expected_initial' not in value['metadata']
        data = json.loads(value['messages'][2]['content'].split('[UNTRUSTED DATA]\n', 1)[1]
            .rsplit('\n[END UNTRUSTED DATA]', 1)[0])
        assert not {'accepted_review', 'previous_review', 'previous_issues'} & data.keys()
    assert all(r['input_ceiling'] <= 64000 for r in manifest['cells'])
