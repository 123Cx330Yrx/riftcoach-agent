"""Prevent paid use of a failed candidate and known impossible corrections."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.evaluation import golden_contextual_admission as admission
from app.evaluation import golden_contextual_first_wire as first
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import fixture, claim
from tests.test_golden_contextual_patch_wire import first_wire
from tests.test_golden_integrated_review import ReplayProvider, request


def duplicate_state():
    inputs, old = fixture("这四场的经济和伤害有差异。[K1]")
    old["audits"][1]["claims"] = [claim(inputs,inputs.source.report)] * 3
    raw = compact(first_wire(old))
    return inputs, raw, first.prepare_state(raw, inputs)


def test_real_entry_rejects_before_input_ci_credentials_or_provider(monkeypatch):
    from scripts import run_golden_integrated_review as runner
    def forbidden(*args, **kwargs): pytest.fail("held candidate reached external/credential path")
    monkeypatch.setattr(runner,"load_inputs",forbidden)
    monkeypatch.setattr(runner,"verify_public_ci",forbidden)
    monkeypatch.setattr(runner,"ReceiptedStreamProvider",forbidden)
    with pytest.raises(ValueError,match=admission.LIVE_BLOCK_REASON):
        runner.run(SimpleNamespace(execute=True),full_context=True)


def test_known_impossible_first_review_never_consumes_second_call():
    inputs, raw, _ = duplicate_state()
    def reply(_, n):
        assert n == 1, "unreachable correction was sent"
        return raw
    provider = ReplayProvider(reply)
    sender = BudgetedReviewSender(provider)
    flow = ContextualCorrectionWorkflow(sender)
    with pytest.raises(ValueError,match="contextual_correction_known_unreachable"):
        flow.evaluate(replace(request(inputs.source.report),deterministic_report="完整来源"))
    assert flow.stopped and sender.budget.calls == flow.calls == len(provider.requests) == 1
    assert flow.last_feedback["code"] == "contextual_correction_known_unreachable"


def test_more_required_updates_than_capacity_are_rejected_before_correction():
    report = "\n\n".join(f"第{n}项经济方向待查。" for n in range(17))
    inputs, old = fixture(report)
    old["audits"][1]["claims"] = [claim(inputs,text) for _,text in inputs.source.blocks]
    state = first.prepare_state(compact(first_wire(old)),inputs)
    blockers = admission.correction_blockers(state.base)
    assert blockers[-1]["code"] == "required_claim_updates_exceed_patch_capacity"
    assert len(blockers[-1]["targets"]) == 17 and blockers[-1]["limit"] == 16
    with pytest.raises(ValueError,match="known_unreachable"): first.build_correction(state)


def test_different_audits_and_distinct_subspans_are_not_mistaken_for_full_duplicates():
    inputs, old = fixture("这四场经济有差异，样本伤害也有差异。")
    row = claim(inputs,inputs.source.report)
    old["audits"][0]["claims"] = [deepcopy(row)]
    old["audits"][1]["claims"] = [deepcopy(row)]
    state = first.prepare_state(compact(first_wire(old)),inputs)
    assert admission.correction_blockers(state.base) == []
    first.build_correction(state)
    # Repeated subspans can still be enlarged within the block; this guard
    # intentionally does not claim to decide their complete repairability.
    old["audits"][1]["claims"] = [claim(inputs,"这四场经济有差异")] * 2
    state = first.prepare_state(compact(first_wire(old)),inputs)
    assert admission.correction_blockers(state.base) == []


def test_guard_does_not_rewrite_the_first_response_or_drop_issues():
    _, raw, state = duplicate_state()
    before = state.base.entries_json
    assert admission.correction_blockers(state.base)[0]["targets"] == ["c001","c002","c003"]
    with pytest.raises(ValueError,match="known_unreachable"): first.build_correction(state)
    assert state.raw == raw and state.base.entries_json == before
