"""Isolated full-reassessment workflow; no production Coach registration."""
from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation.golden_bounded_correction_requests import PreparedCorrection
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_contextual_requests import revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE

EXPERIMENT_ID = "golden-comparison-review-v1"


class ComparisonReassessmentWorkflow(ContextualCorrectionWorkflow):
    correction_phase = "comparison_reassessment"
    prepare_state = staticmethod(full.prepare)
    merge_correction = staticmethod(comparison.apply)

    @staticmethod
    def build_correction(state):
        return PreparedCorrection(state, comparison.build_request(state))

    def build_revision(self, request, canonical, inputs):
        return revision_request(inputs, canonical, FULL_CONTEXT_RULE,
            comparison_review=self.last_journal["comparison_bindings"])
