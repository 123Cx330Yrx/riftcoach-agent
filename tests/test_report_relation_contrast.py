"""Source/contract identity and actual shared-budget flow with scripted IO."""
from dataclasses import replace

import pytest

from app.evaluation.golden_review_experiment import digest
from app.evaluation.role_qualification import frozen_cases
from scripts import report_relation_contrast as candidate
from scripts.report_contrast_review import ContrastDocumentWorkflow as Parent
from tests.test_report_block_keyed_editor import run_flow


def test_original_fifteen_sources_schema_limits_and_exact_restoration():
    rows = frozen_cases()[0]
    assert len(rows) == 15
    for _, source in rows:
        inputs = Parent.build_inputs(source)
        original = Parent.make_request(inputs)
        new = candidate.RelationContrastWorkflow.make_request(inputs)
        assert candidate.restore(new) == original
        assert new.messages[1:] == original.messages[1:]
        assert new.tools == original.tools
        assert (new.timeout_s, new.max_tokens, new.temperature, new.top_p) == (
            original.timeout_s, original.max_tokens, original.temperature, original.top_p)
        assert candidate.request_identity(new) == ('zhipu', 'glm-5.3')


@pytest.mark.parametrize('fault', ['policy', 'marker', 'report', 'schema'])
def test_changed_identity_is_rejected(fault):
    _, source = frozen_cases()[0][0]
    new = candidate.RelationContrastWorkflow.make_request(Parent.build_inputs(source))
    if fault == 'policy':
        new = replace(new, messages=(replace(new.messages[0], content=new.messages[0].content+' drift'), *new.messages[1:]))
    if fault == 'marker':
        new = replace(new, metadata={**new.metadata, candidate.METADATA: 'other'})
    if fault == 'report':
        new = replace(new, messages=(new.messages[0], replace(new.messages[1],
            content=new.messages[1].content.replace('[HOST_BLOCK:', '[WRONG_BLOCK:')), *new.messages[2:]))
    if fault == 'schema':
        new = replace(new, tools=())
    with pytest.raises(ValueError):
        candidate.request_identity(new)


@pytest.mark.parametrize('mode', ['pass', 'reject_fresh', 'bad_edit', 'empty_edit'])
def test_actual_initial_edit_final_shared_budget_and_stop(monkeypatch, mode):
    flow = run_flow(monkeypatch, mode, workflow_type=candidate.RelationContrastWorkflow,
        router_type=candidate.RelationDiagnosticRouter, contract=candidate.RelationDiagnosticLimits())
    if flow is not None:
        assert flow.last_journal['relation_teaching_candidate'] == candidate.VERSION
        assert flow.last_journal['policy_sha256'] == digest(
            flow.make_request(flow._expected_recheck).messages[0].content)
        assert not flow.last_edit_journal['semantic_approval']


def test_editor_receives_identical_full_review_without_teaching_delta():
    from tests.test_coarse_revision_editor import cases
    _, inputs, wire, _ = cases()['claim-scope:4']
    assert candidate.RelationContrastWorkflow.make_request(inputs, accepted=wire) == Parent.make_request(inputs, accepted=wire)


def test_example_arithmetic_is_a_counterexample_not_a_semantic_classifier():
    from decimal import Decimal
    pairs = [([3, 2], [0, 1], '2.5', '0.5', True),
             ([4, 0], [3, 1], '2', '2', False),
             ([5, 0], [3, 1], '2.5', '2', False)]
    for wins, losses, wm, lm, all_wins_greater in pairs:
        assert sum(map(Decimal, wins))/len(wins) == Decimal(wm)
        assert sum(map(Decimal, losses))/len(losses) == Decimal(lm)
        assert (min(wins) > max(losses)) is all_wins_greater


def test_preparation_preserves_disconfirming_history_and_has_no_network(monkeypatch):
    import socket
    from scripts.check_relation_contrast import audit
    def forbid(*args, **kwargs):
        raise AssertionError('offline preparation attempted network')
    monkeypatch.setattr(socket.socket, 'connect', forbid)
    result = audit()
    assert not result['execution_ready'] and not result['production_admitted']
    assert result['provider_calls'] == 0 and len(result['cells']) == 15
    assert result['prior_source_edit_failure']['source_patch_remaining_unsupported_block'] == 18
