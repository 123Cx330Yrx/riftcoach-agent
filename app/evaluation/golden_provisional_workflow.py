"""Separately qualified development entry; retired candidates remain blocked.

Qualification allows a bounded observation, not production or semantic approval.
See ADR-0102's provisional contract qualification for evidence and stop rules.
"""
from app.evaluation.golden_provisional_reassessment import ProvisionalReassessmentWorkflow

EXPERIMENT_ID = "golden-provisional-review-v1"
LIVE_STATUS = "bounded_development_observation"
LIVE_BLOCK_REASON = None

__all__ = ["ProvisionalReassessmentWorkflow", "EXPERIMENT_ID", "LIVE_STATUS", "LIVE_BLOCK_REASON"]
