from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .run_ids import normalize_run_id


class RunStatus(str, Enum):
    CREATED = "created"
    FACTS_READY = "facts_ready"
    KNOWLEDGE_READY = "knowledge_ready"
    DRAFT_READY = "draft_ready"
    EVALUATING = "evaluating"
    NEEDS_REVISION = "needs_revision"
    REVISING = "revising"
    RE_EVALUATING = "re_evaluating"
    PASSED = "passed"
    PUBLISHED = "published"
    DEGRADED = "degraded"
    REJECTED = "rejected"

    @property
    def is_terminal(self) -> bool:
        return self in {
            RunStatus.PUBLISHED,
            RunStatus.DEGRADED,
            RunStatus.REJECTED,
        }


class ArtifactKind(str, Enum):
    PLAYER_SUMMARY = "player_summary"
    DETERMINISTIC_REPORT = "deterministic_report"
    RETRIEVAL_EVIDENCE = "retrieval_evidence"
    COACH_DRAFT = "coach_draft"
    EVALUATION_RESULT = "evaluation_result"
    REVISED_REPORT = "revised_report"
    FINAL_REPORT = "final_report"
    RUN_MANIFEST = "run_manifest"


@dataclass(frozen=True)
class HarnessConfig:
    publish_score_threshold: int = 85
    max_revisions: int = 1
    allow_deterministic_fallback: bool = True
    # Optional stricter evidence floor used by explicitly bounded candidate
    # runs.  The default keeps the historical product behavior unchanged.
    minimum_evidence_sources: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.publish_score_threshold <= 100:
            raise ValueError("publish_score_threshold must be between 0 and 100.")
        if not 0 <= self.max_revisions <= 3:
            raise ValueError("max_revisions must be between 0 and 3.")
        if (
            isinstance(self.minimum_evidence_sources, bool)
            or not isinstance(self.minimum_evidence_sources, int)
            or self.minimum_evidence_sources < 0
        ):
            raise ValueError("minimum_evidence_sources must be a non-negative integer.")


@dataclass
class RunManifest:
    run_id: str
    status: RunStatus
    config: HarnessConfig
    created_at: str
    updated_at: str
    revision_count: int = 0
    attempt_id: int = 0
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    transitions: list[dict[str, Any]] = field(default_factory=list)
    final_decision: str | None = None

    @classmethod
    def new(cls, run_id: str, config: HarnessConfig) -> "RunManifest":
        run_id = normalize_run_id(run_id)
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            run_id=run_id,
            status=RunStatus.CREATED,
            config=config,
            created_at=now,
            updated_at=now,
        )
