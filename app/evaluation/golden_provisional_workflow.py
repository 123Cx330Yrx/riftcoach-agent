"""Failed provisional development entry; all retired candidates remain blocked.

See ADR-0102's live result and format-only witness. Executable correction did
not correct semantic sample selection; no local field-fix rerun is qualified.
"""
from app.evaluation.golden_provisional_reassessment import ProvisionalReassessmentWorkflow

EXPERIMENT_ID = "golden-provisional-review-v1"
LIVE_STATUS = "offline_only"
LIVE_BLOCK_REASON = "provisional_final_comparison_and_scope_failed"


def require_live_qualification():
    raise ValueError(LIVE_BLOCK_REASON)

__all__ = ["ProvisionalReassessmentWorkflow", "EXPERIMENT_ID", "LIVE_STATUS", "LIVE_BLOCK_REASON"]
