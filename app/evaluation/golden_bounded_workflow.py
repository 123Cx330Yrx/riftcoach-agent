"""Isolated development workflow; actual usage is settled by BudgetedReviewSender.

Two assessment calls, one optional revision, then two recheck calls. This is not
a production Coach registration or a guarantee of semantic correctness.
"""
from dataclasses import replace
import re

from app.evaluation.golden_bounded_correction import prepare_state, apply_correction
from app.evaluation.golden_bounded_correction_requests import first_request, correction_request
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_integrated_runtime import IntegratedReviewWorkflow, _result
from app.harness.steps import EvaluationVerdict


EXPERIMENT_ID = "golden-bounded-review-v1"


class BoundedCorrectionWorkflow(IntegratedReviewWorkflow):
    """Reuse the existing receipt, five-call, revision and source-binding guards."""

    def evaluate(self, request):
        if self.stopped or self.evaluations >= 2 or (self.evaluations == 1 and self.revisions != 1):
            raise ValueError("bounded_evaluation_order_invalid")
        inputs = self.build_inputs(request)
        if self.evaluations == 1 and inputs != self._expected_recheck:
            raise ValueError("bounded_recheck_source_changed")
        self.evaluations += 1
        try:
            first_raw = self._call(self.build_first(inputs), "first_review")
            state = self.prepare_state(first_raw, inputs)
            prepared = self.build_correction(state)
            raw = self._call(prepared.request, "bounded_correction")
            # _call verifies the budget-transformed request and real receipt
            # before returning content. Never accept a partial patch by itself.
            payload, self.last_journal = self.merge_correction(state, raw, inputs=inputs)
            result = _result(payload)
        except Exception as error:
            self.stopped = True
            code = str(error)
            self.last_feedback = {"phase": "bounded_review", "error_type": type(error).__name__,
                "code": code if re.fullmatch(r"[a-z_]{1,80}", code) else "bounded_review_invalid"}
            raise
        if any(issue["category"] == "prompt_injection" for issue in result.issues):
            result = replace(result, verdict=EvaluationVerdict.FAIL)
        if result.verdict is EvaluationVerdict.FAIL:
            self.stopped = True
        if not re.search(r"\[K\d+\]", request.report) and result.verdict is not EvaluationVerdict.FAIL:
            result = replace(result, verdict=EvaluationVerdict.NEEDS_REVISION, issues=(*result.issues, dict(
                severity="medium", category="other", quote="[missing inline citation]", evidence="没有知识引用标记。",
                explanation="建议必须由所给知识支持。", suggested_correction="核对实际支持的知识并引用，或删除无依据建议。")))
        self._accepted = (inputs, result)
        return result
    prepare_state = staticmethod(prepare_state)
    build_first = staticmethod(first_request)
    build_correction = staticmethod(correction_request)
    merge_correction = staticmethod(apply_correction)
