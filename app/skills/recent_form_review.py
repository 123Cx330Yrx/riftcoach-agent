"""Typed input and output boundaries for the recent-form review Skill."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.lol.summary_schema import validate_summary_document


class RecentFormReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    player_summary: dict[str, Any]
    deterministic_report: str = Field(min_length=1)
    focus: Literal[
        "overall",
        "laning",
        "survival",
        "economy",
        "vision",
    ] = "overall"

    @model_validator(mode="after")
    def validate_player_summary(self) -> "RecentFormReviewInput":
        validate_summary_document(self.player_summary)
        return self


class RecentFormReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    status: Literal["published", "degraded", "rejected"]
    report: str | None = None
    evaluation_score: int | None = Field(default=None, ge=0, le=100)
    evidence_source_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_terminal_output(self) -> "RecentFormReviewOutput":
        if self.status in {"published", "degraded"} and not self.report:
            raise ValueError("published or degraded output requires a report")
        if self.status == "rejected" and self.report is not None:
            raise ValueError("rejected output must not expose a report")
        return self
