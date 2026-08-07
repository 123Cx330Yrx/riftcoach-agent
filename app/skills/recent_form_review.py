"""Typed input and output boundaries for the recent-form review Skill."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.lol.summary_schema import validate_summary_document
from app.harness.run_ids import normalize_run_id

from .text_contracts import (
    normalize_optional_text,
    normalize_required_text,
    normalize_unique_texts,
)


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

    @field_validator("deterministic_report")
    @classmethod
    def normalize_deterministic_report(cls, value: str) -> str:
        return normalize_required_text(
            value,
            field_name="deterministic_report",
        )

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

    @field_validator("run_id")
    @classmethod
    def normalize_output_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("report")
    @classmethod
    def normalize_report(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, field_name="report")

    @field_validator("evidence_source_ids", "warnings")
    @classmethod
    def normalize_output_texts(
        cls,
        values: tuple[str, ...],
        info,
    ) -> tuple[str, ...]:
        return normalize_unique_texts(values, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_terminal_output(self) -> "RecentFormReviewOutput":
        if self.status in {"published", "degraded"} and not self.report:
            raise ValueError("published or degraded output requires a report")
        if self.status == "rejected" and self.report is not None:
            raise ValueError("rejected output must not expose a report")
        return self
