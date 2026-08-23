"""PostgreSQL owner-scoped latest Conversation review locator."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerLinkTaskRecord,
)
from app.persistence.task_record import ReviewTaskRecord
from app.product.latest_review import (
    LatestProfileReview,
    LatestProfileReviewRepositoryError,
)
from app.tasks.models import OwnerId, TaskPublicationStatus, TaskStatus


SessionFactory = Callable[[], Session]
_OWNER_ID = TypeAdapter(OwnerId)


class PostgresLatestProfileReviewRepository:
    """Locate one visible profile's latest schema-2 recent review."""

    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def get_latest(
        self,
        *,
        owner_id: str,
        player_profile_id: UUID,
    ) -> LatestProfileReview | None:
        try:
            normalized_owner = _OWNER_ID.validate_python(owner_id, strict=True)
        except (TypeError, ValueError, ValidationError):
            raise TypeError("owner_id must be a safe owner identifier") from None
        if not isinstance(player_profile_id, UUID):
            raise TypeError("player_profile_id must be a UUID")

        try:
            with self._session_factory() as session:
                with session.begin():
                    visible = session.scalar(
                        sa.select(
                            OwnerPlayerRelationshipRecord.relationship_id
                        ).where(
                            OwnerPlayerRelationshipRecord.owner_id
                            == normalized_owner,
                            OwnerPlayerRelationshipRecord.relationship_id
                            == player_profile_id,
                            OwnerPlayerRelationshipRecord.status == "active",
                            sa.exists().where(
                                PlayerLinkTaskRecord.owner_id
                                == OwnerPlayerRelationshipRecord.owner_id,
                                PlayerLinkTaskRecord.relationship_id
                                == OwnerPlayerRelationshipRecord.relationship_id,
                                PlayerLinkTaskRecord.status == "succeeded",
                            ),
                        )
                    )
                    if visible is None:
                        raise LatestProfileReviewRepositoryError(
                            "player_profile_not_found"
                        )

                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(
                            ReviewTaskRecord.owner_id == normalized_owner,
                            ReviewTaskRecord.relationship_id == player_profile_id,
                            ReviewTaskRecord.schema_version == "2.0",
                            ReviewTaskRecord.task_kind == "recent_review",
                        )
                        .order_by(
                            ReviewTaskRecord.created_at.desc(),
                            ReviewTaskRecord.task_id.desc(),
                        )
                        .limit(1)
                    )
                    if record is None:
                        return None
                    latest = LatestProfileReview(
                        task_id=record.task_id,
                        run_id=record.run_id,
                        status=TaskStatus(record.status),
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                        publication_status=(
                            TaskPublicationStatus(record.publication_status)
                            if record.publication_status is not None
                            else None
                        ),
                        report_available=record.report_available,
                    )
                return latest
        except LatestProfileReviewRepositoryError:
            raise
        except SQLAlchemyError:
            raise LatestProfileReviewRepositoryError(
                "latest_review_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise LatestProfileReviewRepositoryError(
                "latest_review_integrity_failed"
            ) from None


__all__ = ["PostgresLatestProfileReviewRepository"]
