from __future__ import annotations

from datetime import datetime, timezone

from .models import RunManifest, RunStatus


class IllegalTransitionError(RuntimeError):
    """Raised when a run attempts a transition outside the explicit graph."""


class StaleAttemptError(RuntimeError):
    """Raised when a result belongs to an older revision attempt."""


ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset(
        {
            RunStatus.FACTS_READY,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.FACTS_READY: frozenset(
        {
            RunStatus.KNOWLEDGE_READY,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.KNOWLEDGE_READY: frozenset(
        {
            RunStatus.DRAFT_READY,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.DRAFT_READY: frozenset(
        {
            RunStatus.EVALUATING,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.EVALUATING: frozenset(
        {
            RunStatus.PASSED,
            RunStatus.NEEDS_REVISION,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.NEEDS_REVISION: frozenset(
        {
            RunStatus.REVISING,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.REVISING: frozenset(
        {
            RunStatus.RE_EVALUATING,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.RE_EVALUATING: frozenset(
        {
            RunStatus.PASSED,
            RunStatus.NEEDS_REVISION,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.PASSED: frozenset(
        {
            RunStatus.PUBLISHED,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }
    ),
    RunStatus.PUBLISHED: frozenset(),
    RunStatus.DEGRADED: frozenset(),
    RunStatus.REJECTED: frozenset(),
}


def advance(
    manifest: RunManifest,
    target: RunStatus,
    *,
    attempt_id: int | None = None,
    reason: str | None = None,
) -> RunManifest:
    """Advance a manifest by one legal transition and append an audit record."""

    if attempt_id is not None and attempt_id != manifest.attempt_id:
        raise StaleAttemptError(
            f"Attempt {attempt_id} is stale; current attempt is {manifest.attempt_id}."
        )

    source = manifest.status
    if target not in ALLOWED_TRANSITIONS[source]:
        raise IllegalTransitionError(
            f"Illegal Harness transition: {source.value} -> {target.value}."
        )

    if target is RunStatus.REVISING:
        manifest.revision_count += 1
        manifest.attempt_id += 1

    transitioned_at = datetime.now(timezone.utc).isoformat()
    transition = {
        "from": source.value,
        "to": target.value,
        "at": transitioned_at,
        "attempt_id": manifest.attempt_id,
    }
    if reason:
        transition["reason"] = reason

    manifest.status = target
    manifest.updated_at = transitioned_at
    manifest.transitions.append(transition)
    return manifest
