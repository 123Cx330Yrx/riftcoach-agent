from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class OwnerDataDeletionRecord(Base):
    __tablename__ = "owner_data_deletions"

    marker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    scope: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    affected_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    safe_reason: Mapped[str | None] = mapped_column(sa.String(128))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_owner_data_deletions_owner_idempotency",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name="schema_version_allowed"),
        sa.CheckConstraint(
            "scope IN ('conversation_only', 'conversation_and_derived_memory', "
            "'relationship_private_data')",
            name="scope_allowed",
        ),
        sa.CheckConstraint(
            "((scope IN ('conversation_only', 'conversation_and_derived_memory') "
            "AND conversation_id IS NOT NULL AND relationship_id IS NULL) OR "
            "(scope = 'relationship_private_data' AND conversation_id IS NULL "
            "AND relationship_id IS NOT NULL))",
            name="target_shape",
        ),
        sa.CheckConstraint(
            "status IN ('cleanup_pending', 'complete')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "octet_length(affected_counts::text) <= 2048",
            name="affected_counts_bound",
        ),
        sa.CheckConstraint(
            "((status = 'cleanup_pending' AND completed_at IS NULL) OR "
            "(status = 'complete' AND safe_reason IS NULL AND completed_at IS NOT NULL))",
            name="status_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(completed_at IS NULL OR completed_at >= created_at)",
            name="timestamp_order",
        ),
        sa.Index(
            "ix_owner_data_deletions_pending",
            "owner_id",
            "status",
            "updated_at",
        ),
    )


__all__ = ["OwnerDataDeletionRecord"]
