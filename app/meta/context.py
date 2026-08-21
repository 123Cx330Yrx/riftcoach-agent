"""Projection of dynamic Meta into the existing data-only Context boundary."""

from __future__ import annotations

import json
from datetime import datetime

from app.agent.context import ContextSection, ContextTrust

from .models import MetaEvidence, MetaUseCase


def meta_evidence_context_section(
    evidence: MetaEvidence,
    *,
    now: datetime,
) -> ContextSection:
    if not isinstance(evidence, MetaEvidence):
        raise TypeError("evidence must be MetaEvidence")
    evidence.require_usable(
        MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION,
        now=now,
    )
    return ContextSection(
        section_id=f"meta:{evidence.source}:{evidence.digest[:16]}",
        trust=ContextTrust.EXTERNAL_META_EVIDENCE,
        source=f"{evidence.source}:mcp:{evidence.remote_tool}",
        content=json.dumps(
            evidence.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        ),
        required=False,
        priority=35,
    )


__all__ = ["meta_evidence_context_section"]
