"""Typed input and output boundaries for the single-match review Skill."""

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


_TIMELINE_SCALAR_FIELDS = ("deaths_before_10", "deaths_before_15")
_TIMELINE_COLLECTION_FIELDS = (
    "death_times",
    "death_buckets",
    "item_purchases",
    "objective_events",
)


class SingleMatchReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    player_summary: dict[str, Any]
    deterministic_report: str = Field(min_length=1)
    target_match_id: str = Field(min_length=1)
    focus: Literal[
        "overall",
        "laning",
        "survival",
        "economy",
        "vision",
    ] = "overall"

    @field_validator("deterministic_report", "target_match_id")
    @classmethod
    def normalize_input_text(cls, value: str, info) -> str:
        return normalize_required_text(value, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_target_match(self) -> "SingleMatchReviewInput":
        validate_summary_document(self.player_summary)
        target_rows = [
            row
            for row in self.player_summary["matches"]
            if row.get("match_id") == self.target_match_id
        ]
        if len(target_rows) != 1:
            raise ValueError(
                "target_match_id must identify exactly one match row"
            )

        target = target_rows[0]
        timeline_status = target.get("timeline_status")
        if timeline_status not in {"available", "unavailable"}:
            raise ValueError(
                "target match timeline_status must be available or unavailable"
            )
        if timeline_status == "unavailable":
            self._validate_unavailable_timeline(target)
        return self

    @staticmethod
    def _validate_unavailable_timeline(target: dict[str, Any]) -> None:
        timeline_error = target.get("timeline_error")
        if not isinstance(timeline_error, str) or not timeline_error.strip():
            raise ValueError(
                "unavailable Timeline requires a non-blank timeline_error"
            )

        if any(target.get(field) is not None for field in _TIMELINE_SCALAR_FIELDS):
            raise ValueError(
                "Timeline-derived scalar values must remain unknown when "
                "Timeline is unavailable"
            )
        for field in _TIMELINE_COLLECTION_FIELDS:
            value = target.get(field)
            if value is not None and value not in ([], (), {}):
                raise ValueError(
                    "Timeline-derived collections must be empty when "
                    "Timeline is unavailable"
                )


class SingleMatchReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    target_match_id: str = Field(min_length=1)
    status: Literal["published", "degraded", "rejected"]
    report: str | None = None
    evaluation_score: int | None = Field(default=None, ge=0, le=100)
    evidence_source_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @field_validator("run_id")
    @classmethod
    def normalize_output_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("target_match_id")
    @classmethod
    def normalize_output_target_match_id(cls, value: str) -> str:
        return normalize_required_text(value, field_name="target_match_id")

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
    def validate_terminal_output(self) -> "SingleMatchReviewOutput":
        if self.status in {"published", "degraded"} and not self.report:
            raise ValueError("published or degraded output requires a report")
        if self.status == "rejected" and self.report is not None:
            raise ValueError("rejected output must not expose a report")
        return self
