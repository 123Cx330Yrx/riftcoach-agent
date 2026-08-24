"""Public HTTP models for the live workbench identity and Summary seams."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.product.latest_review import (
    LatestProfileReview,
    LatestProfileReviewResult,
)
from app.product.run_query import (
    RecentAveragesView,
    RecentSummaryView,
    RecentWinLossComparisonView,
    RunTimelineMatchView,
    RunTimelineView,
)
from app.runtime.models import RuntimeStatus
from app.runtime.signals import RuntimePublicationStatus
from app.tasks.models import TaskPublicationStatus, TaskStatus


class LiveWorkbenchApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class LatestProfileReviewLinks(LiveWorkbenchApiModel):
    task: str
    events: str
    stream: str
    run: str
    summary: str
    timeline: str
    report: str
    product_state: str
    evidence: str


class LatestProfileReviewItemResponse(LiveWorkbenchApiModel):
    task_id: UUID
    run_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    publication_status: TaskPublicationStatus | None
    report_available: bool
    links: LatestProfileReviewLinks

    @classmethod
    def from_review(
        cls,
        review: LatestProfileReview,
    ) -> "LatestProfileReviewItemResponse":
        if not isinstance(review, LatestProfileReview):
            raise TypeError("review must be a LatestProfileReview")
        task_path = f"/tasks/{review.task_id}"
        run_path = f"/runs/{review.run_id}"
        return cls(
            **review.model_dump(mode="python"),
            links=LatestProfileReviewLinks(
                task=task_path,
                events=f"{task_path}/events",
                stream=f"{task_path}/events/stream",
                run=run_path,
                summary=f"{run_path}/recent-summary",
                timeline=f"{run_path}/timeline",
                report=f"{run_path}/report",
                product_state=f"{run_path}/product-state",
                evidence=f"{run_path}/evidence",
            ),
        )


class LatestProfileReviewResponse(LiveWorkbenchApiModel):
    schema_version: Literal["1.0"] = "1.0"
    player_profile_id: UUID
    latest_review: LatestProfileReviewItemResponse | None

    @classmethod
    def from_result(
        cls,
        result: LatestProfileReviewResult,
    ) -> "LatestProfileReviewResponse":
        if not isinstance(result, LatestProfileReviewResult):
            raise TypeError("result must be a LatestProfileReviewResult")
        return cls(
            player_profile_id=result.player_profile_id,
            latest_review=(
                LatestProfileReviewItemResponse.from_review(result.latest_review)
                if result.latest_review is not None
                else None
            ),
        )


class RecentSummaryResponse(LiveWorkbenchApiModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    skill_name: Literal["recent-form-review"] = "recent-form-review"
    skill_version: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    report_available: Literal[True] = True
    games_analyzed: int
    wins: int
    losses: int
    win_rate: float
    main_role: str
    main_champions: tuple[str, ...]
    averages: RecentAveragesView
    win_loss_comparison: RecentWinLossComparisonView

    @classmethod
    def from_view(cls, view: RecentSummaryView) -> "RecentSummaryResponse":
        if not isinstance(view, RecentSummaryView):
            raise TypeError("view must be a RecentSummaryView")
        return cls(**view.model_dump(mode="python"))


class RunTimelineResponse(LiveWorkbenchApiModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    skill_name: Literal["recent-form-review"] = "recent-form-review"
    skill_version: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    source: Literal["riot_match_v5_timeline"] = "riot_match_v5_timeline"
    timeline_status: Literal["available", "partial", "unavailable"]
    total_matches: int
    projected_matches: int
    matches_truncated: bool
    matches: tuple[RunTimelineMatchView, ...]

    @classmethod
    def from_view(cls, view: RunTimelineView) -> "RunTimelineResponse":
        if not isinstance(view, RunTimelineView):
            raise TypeError("view must be a RunTimelineView")
        return cls(**view.model_dump(mode="python"))


__all__ = [
    "LatestProfileReviewItemResponse",
    "LatestProfileReviewLinks",
    "LatestProfileReviewResponse",
    "RecentSummaryResponse",
    "RunTimelineResponse",
]
