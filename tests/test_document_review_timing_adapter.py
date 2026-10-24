import pytest

from app.evaluation.document_review_timing_adapter import (
    FLASH_TIMEOUT_S,
    GLM_REVIEW_TIMEOUT_S,
    LEGACY_IDENTITY,
    TASK_TIMEOUT_S,
    TIMED_IDENTITY,
    TIMED_MARKER,
    TimingRequest,
    reject_cross_identity,
    validate,
)


def test_timed_review_uses_600_but_flash_roles_stay_300():
    assert validate(TimingRequest(TIMED_IDENTITY, "review", 600, 0, TIMED_MARKER)) == GLM_REVIEW_TIMEOUT_S
    assert validate(TimingRequest(TIMED_IDENTITY, "generation", 300, 0, TIMED_MARKER)) == FLASH_TIMEOUT_S
    assert validate(TimingRequest(TIMED_IDENTITY, "revision", 300, 0, TIMED_MARKER)) == FLASH_TIMEOUT_S


def test_shared_task_clock_truncates_timed_review():
    assert validate(TimingRequest(TIMED_IDENTITY, "review", 600, 500, TIMED_MARKER)) == 400
    with pytest.raises(ValueError, match="task_timeout"):
        validate(TimingRequest(TIMED_IDENTITY, "review", 600, TASK_TIMEOUT_S, TIMED_MARKER))


def test_legacy_identity_cannot_carry_timed_marker_or_600_seconds():
    with pytest.raises(ValueError, match="timing_marker"):
        reject_cross_identity(identity=LEGACY_IDENTITY, timing_marker=TIMED_MARKER)
    with pytest.raises(ValueError, match="request_timeout"):
        validate(TimingRequest(LEGACY_IDENTITY, "review", 600, 0))


def test_timed_identity_requires_marker():
    with pytest.raises(ValueError, match="timing_marker"):
        validate(TimingRequest(TIMED_IDENTITY, "review", 600, 0))
