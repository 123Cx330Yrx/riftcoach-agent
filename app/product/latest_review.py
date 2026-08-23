"""Owner-scoped locator contracts for the latest Conversation review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Protocol, Self, TypeAlias
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from app.harness.run_ids import normalize_run_id
from app.tasks.models import OwnerId, TaskPublicationStatus, TaskStatus


LatestProfileReviewRepositoryErrorCode: TypeAlias = Literal[
    "player_profile_not_found",
    "latest_review_unavailable",
    "latest_review_integrity_failed",
]
LatestProfileReviewServiceErrorCode: TypeAlias = Literal[
    "player_profile_not_found",
    "latest_review_unavailable",
]
_REPOSITORY_CODES = frozenset(
    {
        "player_profile_not_found",
        "latest_review_unavailable",
        "latest_review_integrity_failed",
    }
)
_SERVICE_CODES = frozenset(
    {"player_profile_not_found", "latest_review_unavailable"}
)
_OWNER_ID = TypeAdapter(OwnerId)


class _LatestReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class LatestProfileReview(_LatestReviewModel):
    """Body-free identity and lifecycle projection of one review task."""

    task_id: UUID
    run_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    publication_status: TaskPublicationStatus | None
    report_available: bool

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.status is TaskStatus.SUCCEEDED:
            if self.publication_status is None:
                raise ValueError("succeeded review requires publication status")
            if self.publication_status is TaskPublicationStatus.REJECTED:
                if self.report_available:
                    raise ValueError("rejected review cannot expose a report")
            elif not self.report_available:
                raise ValueError("published review requires a report")
        elif self.publication_status is not None or self.report_available:
            raise ValueError("non-succeeded review cannot expose publication")
        return self


class LatestProfileReviewResult(_LatestReviewModel):
    schema_version: Literal["1.0"] = "1.0"
    player_profile_id: UUID
    latest_review: LatestProfileReview | None


class LatestProfileReviewRepositoryError(RuntimeError):
    def __init__(self, code: LatestProfileReviewRepositoryErrorCode) -> None:
        if code not in _REPOSITORY_CODES:
            raise ValueError("unsupported latest review repository error code")
        self.code = code
        super().__init__(code)


class LatestProfileReviewServiceError(RuntimeError):
    def __init__(self, code: LatestProfileReviewServiceErrorCode) -> None:
        if code not in _SERVICE_CODES:
            raise ValueError("unsupported latest review service error code")
        self.code = code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        return {"code": self.code}


class LatestProfileReviewRepositoryPort(Protocol):
    def get_latest(
        self,
        *,
        owner_id: str,
        player_profile_id: UUID,
    ) -> LatestProfileReview | None: ...


class LatestProfileReviewService:
    def __init__(self, repository: LatestProfileReviewRepositoryPort) -> None:
        if not callable(getattr(repository, "get_latest", None)):
            raise TypeError("repository must expose get_latest()")
        self._repository = repository

    def get_latest(
        self,
        *,
        owner_id: str,
        player_profile_id: UUID,
    ) -> LatestProfileReviewResult:
        try:
            normalized_owner = _OWNER_ID.validate_python(owner_id, strict=True)
        except (TypeError, ValueError, ValidationError):
            raise TypeError("owner_id must be a safe owner identifier") from None
        if not isinstance(player_profile_id, UUID):
            raise TypeError("player_profile_id must be a UUID")

        latest: LatestProfileReview | None = None
        failure: LatestProfileReviewServiceError | None = None
        try:
            latest = self._repository.get_latest(
                owner_id=normalized_owner,
                player_profile_id=player_profile_id,
            )
        except LatestProfileReviewRepositoryError as error:
            failure = LatestProfileReviewServiceError(
                "player_profile_not_found"
                if error.code == "player_profile_not_found"
                else "latest_review_unavailable"
            )
        except Exception:
            failure = LatestProfileReviewServiceError(
                "latest_review_unavailable"
            )
        if failure is not None:
            raise failure

        if latest is not None and not isinstance(latest, LatestProfileReview):
            raise LatestProfileReviewServiceError(
                "latest_review_unavailable"
            )
        return LatestProfileReviewResult(
            player_profile_id=player_profile_id,
            latest_review=latest,
        )


__all__ = [
    "LatestProfileReview",
    "LatestProfileReviewRepositoryError",
    "LatestProfileReviewRepositoryPort",
    "LatestProfileReviewResult",
    "LatestProfileReviewService",
    "LatestProfileReviewServiceError",
]
