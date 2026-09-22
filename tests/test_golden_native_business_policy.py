"""Business policy and terminal framing failures, using offline response replay."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import golden_native_business_policy as current
from app.evaluation import golden_native_issues_review as legacy
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import RevisionRequest, EvaluationVerdict
from app.providers.errors import ProviderResponseError
from scripts.check_native_contract_options import OfflineResponses
from scripts.run_golden_native_review import prepare_claim_scope
from tests.test_golden_semantic_review import evaluation_request


def opinion(inputs, *, block=None):
    issues = [] if block is None else [dict(block=block, source_ids=[1], severity='medium',
        category='fact_error', explanation='合成问题见证，不代表真实模型判断。',
        suggested_correction='合成修订见证。')]
    return dict(score=95 if block is None else 70,
        verdict='pass' if block is None else 'needs_revision', issues=issues, issue_resolutions=[])


@pytest.mark.parametrize('phase', ['initial', 'reassessment', 'revision'])
def test_policy_intervention_preserves_entire_input_schema_and_execution_settings(phase):
    _, req = prepare_claim_scope(3)
    inputs = legacy.build_inputs(req)
    raw = compact(opinion(inputs, block=6))
    _, wire, _ = legacy.validate(raw, inputs)
    kwargs = ({'previous_raw': raw, 'diagnostics': {'errors': ['synthetic']}}
              if phase == 'reassessment' else {'accepted': wire} if phase == 'revision' else {})
    old, new = legacy.request(inputs, **kwargs), current.request(inputs, **kwargs)
    assert new.messages[0].content != old.messages[0].content
    assert replace(new, messages=old.messages) == old
    assert new.messages[1:] == old.messages[1:]
    # A schema/contract failure is still rejected before sending, not hidden
    # by the simplified policy; one mode may not impersonate another.
    with pytest.raises(ValueError, match='native_request_mode_conflict'):
        current.request(inputs, previous_raw=raw, accepted=wire)


def test_failed_legacy_request_remains_reconstructable_at_its_actual_issued_hash():
    _, req = prepare_claim_scope(3)
    prepared = legacy.request(legacy.build_inputs(req))
    provider = OfflineResponses(['{}'])
    exchange = BudgetedReviewSender(provider, clock=lambda: 1000)(prepared)
    wire = validate_request(exchange.issued_request, transport_id=CAPACITY_TRANSPORT_ID)
    assert hashlib.sha256(wire).hexdigest() == '52c4ae0846e31ca15f567952f836d26a8b113a7cc9201abbdadc40a1e2d360a4'


def test_existing_workflow_preserves_one_revision_and_full_recheck():
    _, req = prepare_claim_scope(3)
    inputs = legacy.build_inputs(req)
    bad = compact(opinion(inputs, block=1))
    revised_text = req.report + '\n\n合成修订见证。[K1]'
    final = compact(opinion(legacy.build_inputs(replace(req, report=revised_text))))
    provider = OfflineResponses([bad, revised_text, final])
    workflow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    initial = workflow.evaluate(req)
    draft = workflow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
        req.knowledge, req.report, initial))
    result = workflow.evaluate(replace(req, report=draft.report))
    assert result.verdict is EvaluationVerdict.PASS
    assert workflow.calls == 3 and workflow.revisions == 1
    assert workflow.last_journal['experiment'] == current.EXPERIMENT_ID
    assert [r.messages[0].content for r in provider.requests] == [
        current.INITIAL_POLICY, current.REVISION_POLICY, current.INITIAL_POLICY]
    with pytest.raises(ValueError):
        workflow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
            req.knowledge, req.report, initial))


def test_reassessment_still_requires_explicit_disposition_of_old_findings():
    req = evaluation_request()
    inputs = legacy.build_inputs(req)
    malformed = opinion(inputs, block=1)
    malformed['score'] = '70'
    old = compact(malformed)
    # A fresh clean pass silently drops the identifiable old finding: reject.
    provider = OfflineResponses([old, compact(opinion(inputs))])
    workflow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    with pytest.raises(ValueError, match='native_issue_resolution_inventory'):
        workflow.evaluate(req)
    assert len(provider.requests) == 2 and workflow.stopped
    assert provider.requests[1].messages[0].content == current.REASSESSMENT_POLICY


def test_final_policy_size_is_checked_before_provider_io(monkeypatch):
    inputs = legacy.build_inputs(evaluation_request())
    monkeypatch.setattr(current, 'INITIAL_POLICY', '很长的策略' * 100000)
    with pytest.raises(ValueError):
        current.request(inputs)


def test_failed_business_batch_cannot_resume_before_preparation_or_credentials(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_native_review as runner

    def forbidden(*args, **kwargs):
        pytest.fail('failed business policy must stop before preparation or CI')

    monkeypatch.setattr(runner, 'prepare', forbidden)
    monkeypatch.setattr(runner, 'verify_public_ci', forbidden)
    with pytest.raises(ValueError, match='business_policy_reassessment_scope_false_positive_requires_redesign'):
        runner.run(SimpleNamespace(execute=True), candidate_module=current)


@pytest.mark.parametrize('block', [None, 1])
def test_prose_tail_cannot_erase_findings_or_trigger_another_semantic_decision(block):
    req = evaluation_request()
    raw = compact(opinion(legacy.build_inputs(req), block=block)) + '\n另一个真实问题可能存在。'
    provider, recorded = OfflineResponses([raw]), []
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000),
        record=lambda phase, exchange: recorded.append(exchange.response.content))
    with pytest.raises(ProviderResponseError) as error:
        flow.evaluate(req)
    assert error.value.code == 'native_review_non_json_suffix'
    assert recorded == [raw] and len(provider.requests) == 1 and flow.stopped


@pytest.mark.parametrize('index, expected_calls', [(3, 3), (4, 3)])
def test_real_batch_replay_preserves_success_and_stops_tail_before_new_judgment(index, expected_calls):
    artifact = json.loads((Path(__file__).resolve().parents[1] /
        'data/evaluation/results/golden_native_business_result_d41c0bd.json').read_text(encoding='utf-8'))
    saved = artifact['cases'][index - 3]
    _, req = prepare_claim_scope(index)
    assert req.report == saved['original_report']
    recorded = []
    provider = OfflineResponses([call['content'] for call in saved['calls']])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000),
        record=lambda phase, exchange: recorded.append(exchange.response.content))
    initial = flow.evaluate(req)
    revised = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
        req.knowledge, req.report, initial))
    assert revised.report == saved['revised_report']
    recheck = replace(req, report=revised.report)
    if index == 3:
        assert flow.evaluate(recheck).verdict is EvaluationVerdict.PASS
    else:
        with pytest.raises(ProviderResponseError) as error:
            flow.evaluate(recheck)
        assert error.value.code == 'native_review_non_json_suffix'
        assert flow.stopped
    assert len(provider.requests) == flow.calls == expected_calls
    assert recorded == [call['content'] for call in saved['calls'][:expected_calls]]
