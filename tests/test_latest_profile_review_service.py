from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.product.latest_review import (
    LatestProfileReview,
    LatestProfileReviewRepositoryError,
    LatestProfileReviewResult,
    LatestProfileReviewService,
    LatestProfileReviewServiceError,
)
from app.tasks.models import TaskPublicationStatus, TaskStatus


NOW = datetime(2026, 8, 23, 9, 0, 0, tzinfo=timezone.utc)
PROFILE_ID = UUID("91000000-0000-4000-8000-000000000001")
TASK_ID = UUID("92000000-0000-4000-8000-000000000001")


def review(status: TaskStatus) -> LatestProfileReview:
    succeeded = status is TaskStatus.SUCCEEDED
    return LatestProfileReview(
        task_id=TASK_ID,
        run_id="review_latest_1",
        status=status,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
        publication_status=(
            TaskPublicationStatus.PUBLISHED if succeeded else None
        ),
        report_available=succeeded,
    )


class FakeRepository:
    def __init__(
        self,
        value: LatestProfileReview | None = None,
        *,
        error: LatestProfileReviewRepositoryError | None = None,
    ) -> None:
        self.value = value
        self.error = error
        self.calls: list[tuple[str, UUID]] = []

    def get_latest(
        self,
        *,
        owner_id: str,
        player_profile_id: UUID,
    ) -> LatestProfileReview | None:
        self.calls.append((owner_id, player_profile_id))
        if self.error is not None:
            raise self.error
        return self.value


def test_service_returns_legal_empty_result_for_visible_profile_without_review() -> None:
    repository = FakeRepository()

    result = LatestProfileReviewService(repository).get_latest(
        owner_id="latest-owner",
        player_profile_id=PROFILE_ID,
    )

    assert result == LatestProfileReviewResult(
        player_profile_id=PROFILE_ID,
        latest_review=None,
    )
    assert repository.calls == [("latest-owner", PROFILE_ID)]


@pytest.mark.parametrize(
    "status",
    (
        TaskStatus.QUEUED,
        TaskStatus.RUNNING,
        TaskStatus.RECOVERY_REQUIRED,
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    ),
)
def test_service_keeps_the_actual_latest_task_status(status: TaskStatus) -> None:
    latest = review(status)

    result = LatestProfileReviewService(FakeRepository(latest)).get_latest(
        owner_id="latest-owner",
        player_profile_id=PROFILE_ID,
    )

    assert result.latest_review is latest
    assert result.latest_review.status is status


def test_repository_not_found_is_distinct_from_empty_profile() -> None:
    service = LatestProfileReviewService(
        FakeRepository(
            error=LatestProfileReviewRepositoryError(
                "player_profile_not_found"
            )
        )
    )

    with pytest.raises(LatestProfileReviewServiceError) as caught:
        service.get_latest(
            owner_id="latest-owner",
            player_profile_id=PROFILE_ID,
        )
    assert caught.value.code == "player_profile_not_found"
    assert str(caught.value) == "player_profile_not_found"
    assert caught.value.to_public_dict() == {
        "code": "player_profile_not_found"
    }


@pytest.mark.parametrize(
    "repository_error",
    (
        "latest_review_unavailable",
        "latest_review_integrity_failed",
    ),
)
def test_repository_failures_map_to_one_body_free_service_error(
    repository_error: str,
) -> None:
    service = LatestProfileReviewService(
        FakeRepository(error=LatestProfileReviewRepositoryError(repository_error))
    )

    with pytest.raises(LatestProfileReviewServiceError) as caught:
        service.get_latest(
            owner_id="latest-owner",
            player_profile_id=PROFILE_ID,
        )

    assert caught.value.code == "latest_review_unavailable"
    assert str(caught.value) == "latest_review_unavailable"
    assert caught.value.__context__ is None


@pytest.mark.parametrize(
    ("owner_id", "player_profile_id"),
    (
        ("", PROFILE_ID),
        (" owner", PROFILE_ID),
        ("owner/private", PROFILE_ID),
        ("owner", "not-a-uuid"),
    ),
)
def test_service_rejects_unsafe_identity_before_repository_call(
    owner_id: str,
    player_profile_id: object,
) -> None:
    repository = FakeRepository()

    with pytest.raises((TypeError, ValueError)):
        LatestProfileReviewService(repository).get_latest(
            owner_id=owner_id,
            player_profile_id=player_profile_id,  # type: ignore[arg-type]
        )

    assert repository.calls == []


def test_latest_review_contract_rejects_incoherent_publication_and_time() -> None:
    with pytest.raises(ValidationError):
        LatestProfileReview(
            task_id=TASK_ID,
            run_id="review_latest_1",
            status=TaskStatus.RUNNING,
            created_at=NOW,
            updated_at=NOW - timedelta(seconds=1),
            publication_status=TaskPublicationStatus.PUBLISHED,
            report_available=True,
        )
