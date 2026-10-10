"""Offline boundary contract for the isolated document-review timing candidate.

This module deliberately has no dependency on the legacy stream bridge or
receipt factory. It proves the timing identity and shared task clock before a
future transport implementation is admitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LEGACY_IDENTITY = "document-review-request-identity-v1"
TIMED_IDENTITY = "document-review-request-identity-time600-v1"
TIMED_MARKER = "document-review-time-600-v1"
TASK_TIMEOUT_S = 900
FLASH_TIMEOUT_S = 300
GLM_REVIEW_TIMEOUT_S = 600


@dataclass(frozen=True)
class TimingRequest:
    identity: Literal["document-review-request-identity-v1", "document-review-request-identity-time600-v1"]
    role: Literal["generation", "revision", "review"]
    timeout_s: int
    task_elapsed_s: int
    timing_marker: str | None = None


def allowed_timeout(role: str, *, identity: str = TIMED_IDENTITY) -> int:
    if identity == LEGACY_IDENTITY:
        return FLASH_TIMEOUT_S if role in ("generation", "revision") else FLASH_TIMEOUT_S
    if identity != TIMED_IDENTITY:
        raise ValueError("unknown_document_review_timing_identity")
    return GLM_REVIEW_TIMEOUT_S if role == "review" else FLASH_TIMEOUT_S


def validate(request: TimingRequest) -> int:
    """Return the effective timeout after the shared task clock is applied."""
    if request.identity == LEGACY_IDENTITY:
        if request.timing_marker is not None:
            raise ValueError("legacy_request_has_timing_marker")
    elif request.identity == TIMED_IDENTITY:
        if request.timing_marker != TIMED_MARKER:
            raise ValueError("timed_request_missing_timing_marker")
    else:
        raise ValueError("unknown_document_review_timing_identity")
    if request.task_elapsed_s < 0 or request.task_elapsed_s >= TASK_TIMEOUT_S:
        raise ValueError("document_review_task_timeout")
    cap = allowed_timeout(request.role, identity=request.identity)
    if request.timeout_s <= 0 or request.timeout_s > cap:
        raise ValueError("document_review_request_timeout")
    return min(request.timeout_s, cap, TASK_TIMEOUT_S - request.task_elapsed_s)


def reject_cross_identity(*, identity: str, timing_marker: str | None) -> None:
    """Reject a request that tries to smuggle timed metadata across identities."""
    validate(TimingRequest(identity=identity, role="review", timeout_s=600,
                           task_elapsed_s=0, timing_marker=timing_marker))

