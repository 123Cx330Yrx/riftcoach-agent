"""Actual five-call control flow with scripted transport, not model quality."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.evaluation.golden_comparison_workflow import ComparisonReassessmentWorkflow
from app.evaluation.golden_provisional_reassessment import ProvisionalReassessmentWorkflow
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_bounded_correction import issue
from tests.test_golden_comparison_reassessment import inputs_for, assessment
from tests.test_golden_integrated_review import ReplayProvider
from app.evaluation.golden_inference_scope_v5 import strict_json


def make_request(inputs):
    # The deterministic source is irrelevant to this scripted control-flow
    # test, but the complete facts must match the independently built inputs.
    from tests.test_golden_fact_candidate import summary
    source = summary()
    source["matches"] = [v for k, v in strict_json(inputs.pack_json)["facts"].items()
        if k.startswith("facts:recent_match:")]
    return EvaluationRequest(source, "来源", KnowledgeEvidence.empty(), inputs.source.report, "检查观摩报告")


@pytest.mark.parametrize("workflow", [ComparisonReassessmentWorkflow, ProvisionalReassessmentWorkflow])
def test_full_reassessment_revision_and_recheck_keep_bindings_and_five_call_budget(workflow):
    bad = "所有未来输局的经济都会更低。"
    fixed = "这四场中单中经济的赢局逐行高于输局。"
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n" + bad + "\n\n建议核对单局。[K1]"
    inputs = inputs_for(report=report)
    req = make_request(inputs)
    # Derive every source identity through the actual selected workflow.
    inputs = ComparisonReassessmentWorkflow.build_inputs(req)
    before, after = assessment(inputs, metrics=("gold_per_min",))
    target = after["audits"][1]["claims"][0]
    target.update(decision="beyond_sample", scope_source=None, explanation="本样本不支持未来断言。")
    after.update(issues=[issue(inputs, bad)], score=70, verdict="needs_revision")
    # The knowledge-only paragraph does not use a complete outcome comparison.
    after["audits"][1]["claims"][1].update(decision="direct_supported", comparisons=[],
        explanation="核对所给知识建议。")
    revised = report.replace(bad, fixed)
    corrected_inputs = ComparisonReassessmentWorkflow.build_inputs(replace(req, report=revised))
    next_first, next_final = assessment(corrected_inputs, metrics=("gold_per_min",))
    next_final["audits"][1]["claims"][1].update(decision="direct_supported", comparisons=[],
        explanation="核对所给知识建议。")
    replies = [compact(before), compact(after), revised, compact(next_first), compact(next_final)]
    provider = ReplayProvider(lambda _, n: replies[n - 1])
    sender = BudgetedReviewSender(provider)
    phases = []
    flow = workflow(sender, record=lambda phase, _: phases.append(phase))
    initial = flow.evaluate(req)
    assert initial.verdict.value == "needs_revision"
    journal = deepcopy(flow.last_journal)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, report, initial))
    assert "comparison_review" in provider.requests[2].messages[1].content
    with pytest.raises(ValueError, match="recheck_source_changed"):
        flow.evaluate(replace(req, report=draft.report, deterministic_report="changed"))
    assert len(provider.requests) == 3
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == "pass"
    assert flow.calls == sender.budget.calls == len(provider.requests) == 5
    assert phases == ["first_review", "comparison_reassessment", "revision", "first_review", "comparison_reassessment"]
    assert journal["final_raw"] == compact(after) and flow.last_journal["final_raw"] == compact(next_final)
    assert sender.budget.tokens == 100
    with pytest.raises(ValueError): flow.evaluate(req)


def test_bad_operands_stop_after_second_call_without_revision_or_retry():
    inputs = inputs_for(report="这四场中单只作本样本比较。[K1]")
    req = make_request(inputs)
    inputs = ComparisonReassessmentWorkflow.build_inputs(req)
    before, after = assessment(inputs)
    after["audits"][1]["claims"][0]["comparisons"][0]["operand_refs"].pop()
    provider = ReplayProvider(lambda _, n: compact(before if n == 1 else after))
    flow = ComparisonReassessmentWorkflow(BudgetedReviewSender(provider))
    with pytest.raises(ValueError, match="operand_set_mismatch"): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 2
    with pytest.raises(ValueError): flow.evaluate(req)
    assert len(provider.requests) == 2


@pytest.mark.parametrize("case_index", [1, 2])
@pytest.mark.parametrize("mode", ["comparison", "provisional"])
def test_preview_is_one_frozen_case_with_no_ci_secrets_or_provider(monkeypatch, tmp_path, case_index, mode):
    from types import SimpleNamespace
    from scripts import run_golden_integrated_review as runner
    from scripts import run_golden_contextual_review as controls
    inputs = inputs_for(report="这四场中单只作本样本比较。[K1]")
    req = make_request(inputs)
    cases = [dict(id=f"contextual_0{i}", source_case_id=f"source_{i}", report=req.report,
        pair="explicit_definition", report_sha256="0" * 64) for i in (1, 2)]
    monkeypatch.setattr(runner, "load_inputs", lambda *_: (req.player_summary, req.deterministic_report, req.knowledge, cases))
    monkeypatch.setattr(controls, "select_cases", lambda c: c)
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("preview called CI"))
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", lambda **_: pytest.fail("preview constructed Provider"))
    args = SimpleNamespace(source_run=tmp_path, base_report=tmp_path, pair=1, execute=False, case_index=case_index)
    result = runner.run(args, **{mode: True})
    assert result["selected_cases"] == [f"contextual_0{case_index}"]
    assert result["max_calls"] == 5 and result["manual_between_cases"]
    assert result["reasoning_effort"] == "high" and not result["production_admitted"]
    assert result["experiment_id"] == f"golden-{mode}-review-v1"
    if mode == "provisional":
        assert result["live_status"] == "offline_only"
        assert "app/evaluation/golden_provisional_reassessment.py" in result["implementation"]


def test_failed_live_candidate_stops_before_inputs_ci_or_credentials(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_integrated_review as runner
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    with pytest.raises(ValueError, match="provisional_first_contract_requires_qualification"):
        runner.run(SimpleNamespace(execute=True), comparison=True)


def test_provisional_runner_uses_new_workflow_after_ci_without_opening_retired_entry(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import dotenv
    from app.providers import config
    from app.evaluation import golden_comparison_workflow as retired
    from app.evaluation import golden_provisional_workflow as held
    from scripts import run_golden_integrated_review as runner
    from scripts import run_golden_contextual_review as controls
    inputs = inputs_for(report="这四场中单只作本样本比较。[K1]")
    req = make_request(inputs)
    case = dict(id="contextual_01", source_case_id="source_1", report=req.report,
        pair="explicit_definition", report_sha256="0" * 64)
    events = []
    # Replay dispatch only; the actual failed candidate remains blocked.
    monkeypatch.setattr(held, "require_live_qualification", lambda: None)
    monkeypatch.setattr(runner, "load_inputs", lambda *_: (req.player_summary, req.deterministic_report, req.knowledge, [case]))
    monkeypatch.setattr(controls, "select_cases", lambda c: c)
    monkeypatch.setattr(retired, "require_live_qualification", lambda: pytest.fail("retired entry used"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: events.append("ci") or "test_sha")
    monkeypatch.setattr(dotenv, "dotenv_values", lambda *_: events.append("credentials") or {})
    monkeypatch.setattr(config, "load_zhipu_settings", lambda _: None)
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", lambda **_: events.append("provider"))
    def observe(*args, workflow_factory):
        assert workflow_factory is ProvisionalReassessmentWorkflow
        events.append("observe")
        return dict(id="contextual_01", stop_reason="scripted_terminal")
    monkeypatch.setattr(runner, "observe_report", observe)
    args = SimpleNamespace(source_run=tmp_path, base_report=tmp_path, pair=1, execute=True,
        case_index=1, run_id="provisional-review-scripted", ci_run="test", output_root=tmp_path, env_file=tmp_path/"unused")
    runner.run(args, provisional=True)
    assert events == ["ci", "credentials", "provider", "observe"]


def test_provisional_failure_hold_precedes_inputs_ci_credentials_and_provider(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_integrated_review as runner
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    with pytest.raises(ValueError, match="provisional_final_comparison_and_scope_failed"):
        runner.run(SimpleNamespace(execute=True), provisional=True)
