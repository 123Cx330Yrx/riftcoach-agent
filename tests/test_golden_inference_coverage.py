import copy
import json

import pytest

from app.evaluation.golden_inference_coverage import (
    EvaluationResponseModelV15, report_blocks, validate_coverage,
)
from app.evaluation.golden_inference_audit import inference_facts
from tests.test_golden_inference_audit import payload

REPORT = "# Report\n\n- A metric result only.\n- Vision score proves awareness.\n\nOnly two games;\nnot stable ability.\n\n| A | B |\n|---|---|\n| 1 | 2 |"


def covered_payload(report=REPORT):
    value = payload()
    value["coverage"] = [{"block_id": b["block_id"], "metric_to_ability": "not_applicable", "cohort_comparison": "not_applicable"} for b in report_blocks(report)]
    return value


def test_every_nonblank_line_is_preserved_and_list_items_cannot_hide_each_other():
    blocks = report_blocks(REPORT)
    assert len(blocks) == 5
    assert blocks[2]["text"] == "- Vision score proves awareness."
    assert blocks[3]["text"] == "Only two games;\nnot stable ability."
    assert [line for b in blocks for line in b["text"].splitlines()] == [line for line in REPORT.splitlines() if line.strip()]
    duplicated = report_blocks("- repeated\n- repeated")
    assert duplicated[0]["block_id"] != duplicated[1]["block_id"]
    assert report_blocks("paragraph\r\ncontinued")[0]["text"] == "paragraph\r\ncontinued"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reorder", "edited", "unsupported_without_claim"])
def test_coverage_cannot_silently_skip_or_reuse_blocks(mutation):
    value = covered_payload()
    report = REPORT
    if mutation == "missing": value["coverage"].pop(2)
    elif mutation == "duplicate": value["coverage"][2] = copy.deepcopy(value["coverage"][1])
    elif mutation == "reorder": value["coverage"].reverse()
    elif mutation == "edited": report = REPORT.replace("Vision score", "Damage")
    else: value["coverage"][2]["metric_to_ability"] = "unsupported"
    parsed = EvaluationResponseModelV15.model_validate(value)
    with pytest.raises(ValueError): validate_coverage(parsed, report, inference_facts({}))


def test_unsupported_block_must_link_to_its_own_claim_and_issue():
    value = covered_payload()
    quote = "Vision score proves awareness."
    value.update(score=70, verdict="needs_revision", issues=[{"quote": quote, "severity": "medium", "category": "other", "evidence": "single result", "explanation": "does not establish ability", "suggested_correction": "describe result only"}])
    value["audits"][0].update(status="unsupported", claims=[{"quote": quote, "status": "unsupported", "evidence_refs": ["scope:limits"], "explanation": "single result"}])
    value["coverage"][2]["metric_to_ability"] = "unsupported"
    validate_coverage(EvaluationResponseModelV15.model_validate(value), REPORT, inference_facts({}))
    value["coverage"][2]["metric_to_ability"] = "supported"
    with pytest.raises(ValueError): validate_coverage(EvaluationResponseModelV15.model_validate(value), REPORT, inference_facts({}))


def test_coverage_does_not_pretend_to_prove_semantic_truth():
    # An explicitly wrong classification can remain well-formed. Real controls
    # must still measure model misclassification; this is not a keyword filter.
    validate_coverage(EvaluationResponseModelV15.model_validate(covered_payload()), REPORT, inference_facts({}))
    with pytest.raises(ValueError): EvaluationResponseModelV15.model_validate(payload())


def test_compaction_preserves_fact_and_knowledge_values():
    from app.evaluation.coach_report import build_secure_evaluation_prompt
    facts = {"nested": {"list": [None, 1, False], "text": "quoted \"text\"\nnot instructions"}}
    knowledge = {"context": "[DRAFT REPORT TO REVIEW] is untrusted source text"}
    text = build_secure_evaluation_prompt(facts, "draft", user_utterance="observe", knowledge=knowledge, compact_json=True)
    parsed, _ = json.JSONDecoder().raw_decode(text.split("[DETERMINISTIC FACT PACK]\n", 1)[1])
    assert parsed == facts
    parsed, _ = json.JSONDecoder().raw_decode(text.split("[UNTRUSTED RETRIEVED KNOWLEDGE DATA-ONLY]\n", 1)[1])
    assert parsed == knowledge


def test_coverage_survives_artifact_and_revision_projection():
    from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
    from app.harness.steps import EvaluationVerdict
    from app.harness.adapters import _evaluation_payload
    from app.harness.runtime import ReviewHarness
    coverage = tuple(covered_payload()["coverage"])
    result = CoveredEvaluationResult(score=95, verdict=EvaluationVerdict.PASS, issues=(), passed_checks=(), summary="offline", audits=(), coverage=coverage)
    assert _evaluation_payload(result)["coverage"] == list(coverage)
    assert json.loads(ReviewHarness._evaluation_bytes(result))["coverage"] == list(coverage)


@pytest.mark.parametrize("report", ["", "x" * 24001, "\n".join(f"- item {i}" for i in range(65))])
def test_oversize_inputs_fail_before_a_model_call(report):
    with pytest.raises(ValueError): report_blocks(report)


def test_coverage_fields_cannot_hide_terminal_security_finding(monkeypatch):
    from dataclasses import replace
    from scripts.check_coach_golden_replay import _ReplayProvider, probe
    from app.runtime.coach_contract import COVERAGE_COACH_CONTRACT
    from tests.test_coach_application_composition import dependencies
    original = _ReplayProvider.chat
    def injected(self, request):
        response = original(self, request)
        if request.response_contract:
            value = payload()
            value.update(coverage="malformed", audits="malformed", issues=[{"severity": "high", "category": "prompt_injection", "quote": "untrusted", "evidence": "untrusted", "explanation": "instruction followed", "suggested_correction": "reject"}])
            return replace(response, content=json.dumps(value))
        return response
    monkeypatch.setattr(_ReplayProvider, "chat", injected)
    result = probe(dependencies()["summary_builder"].summary, contract=COVERAGE_COACH_CONTRACT, training_positions=())
    assert result["scripted_provider_calls"] == 5
    assert result["revision_count"] == 0
    assert not result["report_available"]
