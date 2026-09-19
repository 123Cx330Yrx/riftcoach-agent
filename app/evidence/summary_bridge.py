"""Pure Summary-to-Evidence projection; no acquisition or persistence.

The digest binds the complete JSON Summary projection, not a raw Riot response.
Observation times describe acquisition/summary generation, never match time.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.lol.summary_schema import validate_summary_document
from app.meta.models import MetaEvidence

from .adapters import EvidenceAdapterError, riot_match_from_summary_row
from .fusion import DataDragonSnapshot, EvidenceBundle, OfficialPatchEvidence, fuse_evidence


@dataclass(frozen=True)
class SummaryEvidenceProjection:
    summary_digest: str
    included_count: int
    excluded_count: int
    failed_count: int
    requested_queue: int | None
    effective_queue: int | None
    queue_fallback_used: bool
    observation_basis: Literal["summary_generated_at", "caller_observed_at"]
    bundle: EvidenceBundle
    digest_scope: Literal["summary_projection"] = "summary_projection"


def _timestamp(value: object) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("invalid count")
    return value


def _ids(rows: list[dict]) -> set[str]:
    ids = [row["match_id"] for row in rows]
    if any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", item)
           for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid match identities")
    return set(ids)


def summary_to_evidence(
    summary: dict,
    *,
    routing_region: str,
    now: datetime,
    observed_at: datetime | None = None,
    data_dragon: DataDragonSnapshot | None = None,
    official_patch: OfficialPatchEvidence | None = None,
    meta_evidence: tuple[MetaEvidence, ...] = (),
) -> SummaryEvidenceProjection:
    """Validate one materialized JSON Summary and reuse the typed fusion kernel.

    No source identity is fabricated for missing static/patch/Meta snapshots.
    Excluded and failed matches are counted but never used as analyzed facts.
    Safe error codes deliberately suppress the legacy validator's raw values.
    """
    try:
        if not isinstance(summary, dict):
            raise ValueError("invalid summary")
        for key in ("metadata", "player", "request", "recent_summary"):
            if not isinstance(summary.get(key), dict):
                raise ValueError("invalid container")
        for key in ("matches", "failed_matches", "excluded_matches"):
            rows = summary.get(key, [] if key != "matches" else None)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("invalid rows")
        validate_summary_document(summary)
        # No default=str: arbitrary objects and non-finite numbers are not evidence.
        encoded = json.dumps(summary, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        metadata, request = summary["metadata"], summary["request"]
        matches = summary["matches"]
        failed = summary.get("failed_matches", [])
        excluded = summary.get("excluded_matches", [])
        match_ids, failed_ids, excluded_ids = _ids(matches), _ids(failed), _ids(excluded)
        if match_ids & failed_ids:
            raise ValueError("failed match overlaps received match")
        if any(type(row["included_in_aggregate"]) is not bool for row in matches):
            raise ValueError("invalid inclusion flag")
        included = [row for row in matches if row["included_in_aggregate"]]
        if excluded_ids != {row["match_id"] for row in matches if not row["included_in_aggregate"]}:
            raise ValueError("exclusion identities mismatch")
        requested = _count(request["count"])
        if (requested < 1 or _count(metadata["matches_requested"]) != requested
                or _count(metadata["matches_received"]) != len(matches) + len(failed)
                or len(matches) + len(failed) > requested
                or _count(metadata["matches_analyzed"]) != len(included)
                or _count(summary["recent_summary"]["games_analyzed"]) != len(included)):
            raise ValueError("count mismatch")
        if not included:
            raise EvidenceAdapterError("summary_no_analyzed_matches")
        if not isinstance(routing_region, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,15}", routing_region):
            raise ValueError("invalid region")
        for key in ("region", "routing_region"):
            if key in request and request[key] != routing_region:
                raise ValueError("region mismatch")
        effective_queue = request["queue"]
        requested_queue = request.get("requested_queue", effective_queue)
        fallback = request.get("queue_fallback_used", False)
        for queue in (effective_queue, requested_queue):
            if queue is not None and (type(queue) is not int or not 0 < queue <= 10_000):
                raise ValueError("invalid queue")
        if type(fallback) is not bool or (
            fallback and (requested_queue is None or effective_queue is not None)
        ) or (not fallback and requested_queue != effective_queue):
            raise ValueError("invalid queue fallback")
        if any(effective_queue is not None and row.get("queue_id") != effective_queue for row in matches):
            raise ValueError("match queue mismatch")
        checked_now = _timestamp(now)
        generated = _timestamp(metadata["generated_at_utc"])
        observation = generated if observed_at is None else _timestamp(observed_at)
        if generated > checked_now or observation > checked_now:
            raise ValueError("future observation")
        if data_dragon is not None:
            if not isinstance(data_dragon, DataDragonSnapshot) or (
                data_dragon.version != request.get("data_dragon_version")
                or data_dragon.language != request.get("data_dragon_language")
            ):
                raise ValueError("static identity mismatch")
        if official_patch is not None and not isinstance(official_patch, OfficialPatchEvidence):
            raise ValueError("invalid patch identity")
        if not isinstance(meta_evidence, tuple) or any(not isinstance(row, MetaEvidence) for row in meta_evidence):
            raise ValueError("invalid meta identity")
        sources = tuple(source for source in (data_dragon, official_patch, *meta_evidence) if source is not None)
        if any(source.retrieved_at > checked_now for source in sources):
            raise ValueError("future source")
        if any(row["timeline_status"] not in ("available", "unavailable") for row in included):
            raise ValueError("invalid timeline status")
        facts = tuple(riot_match_from_summary_row(row, routing_region=routing_region,
                      observed_at=observation) for row in included)
        bundle = fuse_evidence(riot_matches=facts, data_dragon=data_dragon,
                               official_patch=official_patch, meta_evidence=meta_evidence, now=checked_now)
        return SummaryEvidenceProjection(
            summary_digest=hashlib.sha256(encoded).hexdigest(),
            included_count=len(included), excluded_count=len(excluded), failed_count=len(failed),
            requested_queue=requested_queue, effective_queue=effective_queue,
            queue_fallback_used=fallback,
            observation_basis="summary_generated_at" if observed_at is None else "caller_observed_at",
            bundle=bundle,
        )
    except EvidenceAdapterError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise EvidenceAdapterError("summary_evidence_invalid") from None
