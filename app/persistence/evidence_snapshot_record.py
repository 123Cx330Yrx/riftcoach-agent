from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class EvidenceBundleSnapshotRecord(Base):
    """Append-only typed EvidenceBundle snapshot bound to one owner task/run."""

    __tablename__ = "evidence_bundle_snapshots"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    refresh_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    bundle_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    snapshot_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    stored_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "task_id",
            "revision",
            name="uq_evidence_bundle_snapshots_task_revision",
        ),
        sa.UniqueConstraint(
            "task_id",
            "refresh_id",
            name="uq_evidence_bundle_snapshots_task_refresh",
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "run_id", "owner_id"],
            [
                "review_tasks.task_id",
                "review_tasks.run_id",
                "review_tasks.owner_id",
            ],
            name="fk_evidence_bundle_snapshots_task_identity",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="revision_positive",
        ),
        sa.CheckConstraint(
            "refresh_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'",
            name="refresh_id_format",
        ),
        sa.CheckConstraint(
            "bundle_digest ~ '^[0-9a-f]{64}$'",
            name="bundle_digest_format",
        ),
        sa.CheckConstraint(
            "snapshot_digest ~ '^[0-9a-f]{64}$'",
            name="snapshot_digest_format",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object' AND "
            "octet_length(payload::text) <= 262144",
            name="payload_bound",
        ),
        sa.Index(
            "ix_evidence_bundle_snapshots_owner_run_revision",
            "owner_id",
            "run_id",
            revision.desc(),
        ),
        sa.Index(
            "ix_evidence_bundle_snapshots_task_revision",
            "task_id",
            revision.desc(),
        ),
    )


__all__ = ["EvidenceBundleSnapshotRecord"]
