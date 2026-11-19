"""Exercise actual CLI policy dispatch without reading sources or credentials."""
import runpy
import sys

import pytest

from scripts import run_golden_native_review as runner


@pytest.mark.parametrize('policy,reason', [
    ('legacy', 'native_claim_scope_false_positive_requires_diagnosis'),
    ('business', 'business_policy_reassessment_scope_false_positive_requires_redesign'),
    ('tool', 'tool_review_scope_false_positive_requires_redesign'),
    ('partitioned-tool', 'partitioned_review_attribution_miss_requires_coverage_diagnosis'),
    ('block-tool', 'block_review_stream_interruption_requires_transport_diagnosis'),
    ('buffered-block', 'buffered_tool_arguments_still_duplicate_members'),
    ('json-block', 'json_content_review_no_public_result_before_deadline'),
])
def test_stopped_cli_policies_reject_before_sources_secrets_or_provider(monkeypatch, policy, reason):
    def forbidden(*args, **kwargs):
        pytest.fail('stopped policy reached later-stage work')

    import dotenv
    from app.providers import config
    for name in ('prepare', 'prepare_attribution', 'prepare_scope', 'prepare_claim_scope',
                 'verify_public_ci', 'ReceiptedStreamProvider'):
        monkeypatch.setattr(runner, name, forbidden)
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    monkeypatch.setattr(config, 'load_zhipu_settings', forbidden)
    monkeypatch.setattr(sys, 'argv', ['run_golden_native_issues_review', '--execute', '--policy', policy])
    with pytest.raises(ValueError, match=reason):
        runpy.run_path('scripts/run_golden_native_issues_review.py', run_name='__main__')
