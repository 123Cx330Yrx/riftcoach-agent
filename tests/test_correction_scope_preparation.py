"""A new responsibility hypothesis cannot delete prior issue meaning or inputs."""
from dataclasses import replace

from scripts.prepare_correction_scope_diagnostic import prepare, variant, RULE
from app.evaluation.coarse_role_qualification import frozen_cases
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as W


def test_all_original_inputs_keep_full_sources_schema_and_settings():
    for frozen,source in frozen_cases()[0]:
        original, changed = variant(W.build_inputs(source))
        assert replace(changed, messages=original.messages) == original
        assert changed.messages[1:] == original.messages[1:]
        assert changed.messages[0].content == original.messages[0].content+'\n'+RULE
        problem=changed.tools[0].input_schema['$defs']['Problem']
        assert 'suggested_correction' in problem['required']
        assert 'explanation' in problem['required']
    assert all(term not in RULE for term in ('经济','辅助','ShowMaker','attribution:1'))


def test_preparation_cannot_claim_execution_or_qualification():
    plan,requests=prepare()
    assert len(plan['cases'])==15 and set(requests)=={'attribution:1','claim-scope:1'}
    assert plan['provider_requests']==0 and not plan['execution_enabled']
    assert not plan['review_controls_qualified'] and not plan['actual_product_task_qualified']
    assert not plan['production_admitted']
    for raw in requests.values():
        assert b'expected_initial' not in raw and b'prior_failure_export_sha256' not in raw
