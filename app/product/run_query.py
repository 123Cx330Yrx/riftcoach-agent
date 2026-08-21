"""Strict, body-free query projection over receipt, Trace and Artifacts."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.harness.models import ArtifactKind, RunManifest, RunStatus
from app.harness.run_ids import normalize_run_id
from app.harness.store import FileRunStore
from app.lol.summary_schema import validate_summary_document
from app.runtime.models import (
    RuntimeArtifactReference,
    RuntimeStatus,
    RuntimeTrace,
    RuntimeUsage,
)
from app.runtime.signals import (
    ExecutionValidatedSignal,
    PublicationDecidedSignal,
    RuntimePublicationStatus,
)
from app.runtime.store import RuntimeTraceStore

from .run_receipts import ApiRunReceipt, FileRunReceiptStore


_MAX_PLAYER_SUMMARY_BYTES = 2 * 1024 * 1024


def _reject_non_finite_json(value: str) -> Any:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


RunQueryErrorCode = Literal[
    "run_not_found",
    "report_not_available",
    "run_integrity_failed",
]


class RunQueryError(RuntimeError):
    """Public body-free query failure."""

    def __init__(self, code: RunQueryErrorCode) -> None:
        self.code = code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        return {"code": self.code}


class RunView(BaseModel):
    """Allowlisted product view; content and local persistence details are absent."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "1.0"
    run_id: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus | None = None
    terminal_reason: str
    skill_name: str | None = None
    skill_version: str | None = None
    prompt_profile_id: str | None = None
    prompt_profile_version: str | None = None
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    elapsed_ms: int | None = None
    usage: RuntimeUsage | None = None
    report_available: bool


class RecentAveragesView(BaseModel):
    """Bounded aggregate metrics; player identity and match rows are absent."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )

    kda: float = Field(ge=0)
    cs_per_min: float = Field(ge=0)
    gold_per_min: float = Field(ge=0)
    damage_per_min: float = Field(ge=0)
    vision_score: float = Field(ge=0)
    kill_participation_percent: float = Field(ge=0, le=100)
    damage_share_percent: float = Field(ge=0, le=100)
    gold_share_percent: float = Field(ge=0, le=100)
    deaths_before_15: float = Field(ge=0)


class RecentComparisonRowView(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )

    cs_per_min: float = Field(ge=0)
    gold_per_min: float = Field(ge=0)
    damage_per_min: float = Field(ge=0)
    vision_score: float = Field(ge=0)
    deaths_before_15: float = Field(ge=0)


class RecentWinLossComparisonView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    wins: RecentComparisonRowView
    losses: RecentComparisonRowView


class RecentSummaryView(BaseModel):
    """Safe business projection of a verified recent-form input Artifact."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    skill_name: Literal["recent-form-review"] = "recent-form-review"
    skill_version: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    report_available: Literal[True] = True
    games_analyzed: int = Field(ge=1, le=100)
    wins: int = Field(ge=0, le=100)
    losses: int = Field(ge=0, le=100)
    win_rate: float = Field(ge=0, le=100)
    main_role: str = Field(min_length=1, max_length=64)
    main_champions: tuple[str, ...] = Field(min_length=1, max_length=5)
    averages: RecentAveragesView
    win_loss_comparison: RecentWinLossComparisonView

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("skill_version", "terminal_reason", "main_role")
    @classmethod
    def validate_bounded_text(cls, value: str, info) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError(f"{info.field_name} must be normalized")
        return value

    @field_validator("main_champions")
    @classmethod
    def validate_main_champions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 64
            for value in values
        ):
            raise ValueError("main_champions must contain bounded normalized text")
        if len(set(values)) != len(values):
            raise ValueError("main_champions must be unique")
        return values

    @model_validator(mode="after")
    def validate_record_math(self) -> "RecentSummaryView":
        if self.wins + self.losses != self.games_analyzed:
            raise ValueError("wins and losses must equal games_analyzed")
        expected = round(self.wins / self.games_analyzed * 100, 1)
        if not math.isclose(self.win_rate, expected, abs_tol=0.05):
            raise ValueError("win_rate does not match wins/games")
        return self


class SingleMatchReviewView(BaseModel):
    """Body-free identity of one verified published single-match review."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    skill_name: Literal["single-match-review"] = "single-match-review"
    skill_version: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    review_available: Literal[True] = True
    review_sha256: str

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("review_sha256")
    @classmethod
    def validate_review_digest(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("review_sha256 must be a lowercase SHA-256 digest")
        return value


@dataclass(frozen=True)
class _VerifiedRun:
    receipt: ApiRunReceipt
    trace: RuntimeTrace | None
    report: str | None
    report_sha256: str | None


class RunQueryService:
    """Rebuild safe query truth instead of trusting any one local file."""

    def __init__(
        self,
        runs_root: str | Path,
        *,
        receipt_store: FileRunReceiptStore | None = None,
    ) -> None:
        self._runs_root = Path(runs_root).resolve()
        self._receipts = receipt_store or FileRunReceiptStore(self._runs_root)

    def get_run(self, run_id: str) -> RunView:
        verified = self._load_safely(run_id)
        trace = verified.trace
        return RunView(
            run_id=verified.receipt.run_id,
            runtime_status=verified.receipt.runtime_status,
            publication_status=verified.receipt.publication_status,
            terminal_reason=verified.receipt.terminal_reason,
            skill_name=trace.identity.skill_name if trace is not None else None,
            skill_version=(
                trace.identity.skill_version if trace is not None else None
            ),
            prompt_profile_id=(
                trace.identity.prompt_profile_id if trace is not None else None
            ),
            prompt_profile_version=(
                trace.identity.prompt_profile_version
                if trace is not None
                else None
            ),
            started_at_utc=(trace.started_at_utc if trace is not None else None),
            completed_at_utc=(
                trace.completed_at_utc if trace is not None else None
            ),
            elapsed_ms=trace.elapsed_ms if trace is not None else None,
            usage=trace.usage if trace is not None else None,
            report_available=verified.receipt.report_available,
        )

    def get_report(self, run_id: str) -> str:
        verified = self._load_safely(run_id)
        if not verified.receipt.report_available or verified.report is None:
            raise RunQueryError("report_not_available")
        return verified.report

    def get_recent_summary(self, run_id: str) -> RecentSummaryView:
        verified = self._load_safely(run_id)
        self._require_published_skill(verified, "recent-form-review")
        try:
            summary = self._read_verified_player_summary(verified)
            recent = summary.get("recent_summary")
            if not isinstance(recent, Mapping):
                raise ValueError("recent_summary is not a mapping")
            assert verified.trace is not None
            return RecentSummaryView(
                run_id=verified.receipt.run_id,
                skill_version=verified.trace.identity.skill_version,
                runtime_status=verified.receipt.runtime_status,
                publication_status=verified.receipt.publication_status,
                terminal_reason=verified.receipt.terminal_reason,
                games_analyzed=recent.get("games_analyzed"),
                wins=recent.get("wins"),
                losses=recent.get("losses"),
                win_rate=recent.get("win_rate"),
                main_role=recent.get("main_role"),
                main_champions=tuple(recent.get("main_champions", ())),
                averages=recent.get("averages"),
                win_loss_comparison=recent.get("win_loss_comparison"),
            )
        except RunQueryError:
            raise
        except Exception:
            raise RunQueryError("run_integrity_failed") from None

    def get_single_match_review(self, run_id: str) -> SingleMatchReviewView:
        verified = self._load_safely(run_id)
        self._require_published_skill(verified, "single-match-review")
        if verified.report_sha256 is None or verified.trace is None:
            raise RunQueryError("run_integrity_failed")
        try:
            return SingleMatchReviewView(
                run_id=verified.receipt.run_id,
                skill_version=verified.trace.identity.skill_version,
                runtime_status=verified.receipt.runtime_status,
                publication_status=verified.receipt.publication_status,
                terminal_reason=verified.receipt.terminal_reason,
                review_sha256=verified.report_sha256,
            )
        except Exception:
            raise RunQueryError("run_integrity_failed") from None

    @staticmethod
    def _require_published_skill(
        verified: _VerifiedRun,
        expected_skill: str,
    ) -> None:
        if (
            verified.receipt.publication_status
            not in {
                RuntimePublicationStatus.PUBLISHED,
                RuntimePublicationStatus.DEGRADED,
            }
            or not verified.receipt.report_available
        ):
            raise RunQueryError("report_not_available")
        if (
            verified.trace is None
            or verified.trace.identity.skill_name != expected_skill
        ):
            raise RunQueryError("run_integrity_failed")

    def _read_verified_player_summary(
        self,
        verified: _VerifiedRun,
    ) -> Mapping[str, Any]:
        trace = verified.trace
        if trace is None:
            raise ValueError("player summary requires Trace")
        store = FileRunStore(self._runs_root, verified.receipt.run_id)
        manifest = store.read_manifest()
        records = self._artifact_records(manifest, ArtifactKind.PLAYER_SUMMARY)
        references = self._artifact_references(trace, ArtifactKind.PLAYER_SUMMARY)
        if len(records) != 1 or len(references) != 1:
            raise ValueError("player summary must be unique in manifest and Trace")
        record = records[0]
        reference = references[0]
        if record.get("run_id") != verified.receipt.run_id:
            raise ValueError("player summary belongs to a different run")
        if self._artifact_identity(record) != self._reference_identity(reference):
            raise ValueError("Trace and manifest player summary mismatch")
        if (
            record.get("schema_version") != "1.0"
            or record.get("path") != "inputs/player_summary.json"
            or record.get("producer") != "review_harness.input"
        ):
            raise ValueError("unsupported player summary identity")
        executions = tuple(
            event.signal
            for event in trace.events
            if isinstance(event.signal, ExecutionValidatedSignal)
        )
        if (
            len(executions) != 1
            or len(executions[0].input_artifact_sha256s) < 1
            or executions[0].input_artifact_sha256s[0] != reference.sha256
        ):
            raise ValueError("player summary is not the validated input Artifact")
        content = store.read_artifact(record)
        if len(content) > _MAX_PLAYER_SUMMARY_BYTES:
            raise ValueError("player summary exceeds the query projection budget")
        payload = json.loads(
            content.decode("utf-8"),
            parse_constant=_reject_non_finite_json,
        )
        if not isinstance(payload, dict):
            raise ValueError("player summary root must be an object")
        validate_summary_document(payload)
        return payload

    def _load_safely(self, run_id: str) -> _VerifiedRun:
        normalized: str | None = None
        not_found: RunQueryError | None = None
        try:
            normalized = normalize_run_id(run_id)
        except (TypeError, ValueError):
            not_found = RunQueryError("run_not_found")
        if not_found is not None:
            raise not_found
        assert normalized is not None

        receipt: ApiRunReceipt | None = None
        receipt_failure: RunQueryError | None = None
        try:
            receipt = self._receipts.read_receipt(normalized)
        except FileNotFoundError:
            receipt_failure = RunQueryError("run_not_found")
        except Exception:
            receipt_failure = RunQueryError("run_integrity_failed")
        if receipt_failure is not None:
            raise receipt_failure
        assert receipt is not None

        verified: _VerifiedRun | None = None
        integrity_failure: RunQueryError | None = None
        try:
            verified = self._verify(receipt)
        except Exception:
            integrity_failure = RunQueryError("run_integrity_failed")
        if integrity_failure is not None:
            raise integrity_failure
        assert verified is not None
        return verified

    def _verify(self, receipt: ApiRunReceipt) -> _VerifiedRun:
        trace = self._read_trace(receipt)
        self._cross_check_trace(receipt, trace)

        store = FileRunStore(self._runs_root, receipt.run_id)
        manifest = store.read_manifest() if store.manifest_path.is_file() else None
        if manifest is None:
            self._validate_missing_manifest(receipt, trace)
            return _VerifiedRun(
                receipt=receipt,
                trace=trace,
                report=None,
                report_sha256=None,
            )

        publication_reason = self._validate_manifest(
            receipt,
            trace,
            manifest,
        )
        final_records = self._final_records(manifest)
        final_references = self._final_references(trace)
        report = self._verify_report(
            receipt=receipt,
            store=store,
            records=final_records,
            references=final_references,
        )
        self._cross_check_publication_signal(
            receipt=receipt,
            trace=trace,
            manifest_reason=publication_reason,
        )
        return _VerifiedRun(
            receipt=receipt,
            trace=trace,
            report=report,
            report_sha256=(
                final_references[0].sha256 if report is not None else None
            ),
        )

    def _read_trace(self, receipt: ApiRunReceipt) -> RuntimeTrace | None:
        if receipt.trace_reference is None:
            return None
        return RuntimeTraceStore(
            self._runs_root,
            receipt.run_id,
        ).read_trace(receipt.trace_reference)

    @staticmethod
    def _cross_check_trace(
        receipt: ApiRunReceipt,
        trace: RuntimeTrace | None,
    ) -> None:
        if trace is None:
            if receipt.runtime_status is RuntimeStatus.COMPLETED:
                raise ValueError("completed receipt is missing Trace")
            if receipt.report_available:
                raise ValueError("report cannot be verified without Trace")
            return
        if (
            trace.run_id != receipt.run_id
            or trace.runtime_status is not receipt.runtime_status
            or trace.publication_status is not receipt.publication_status
            or trace.terminal_reason != receipt.terminal_reason
        ):
            raise ValueError("receipt and Trace terminal state mismatch")

    @staticmethod
    def _validate_missing_manifest(
        receipt: ApiRunReceipt,
        trace: RuntimeTrace | None,
    ) -> None:
        if (
            receipt.runtime_status is not RuntimeStatus.FAILED
            or receipt.publication_status is not None
            or receipt.report_available
            or (trace is not None and RunQueryService._final_references(trace))
        ):
            raise ValueError("manifest missing outside an early failed run")

    @staticmethod
    def _validate_manifest(
        receipt: ApiRunReceipt,
        trace: RuntimeTrace | None,
        manifest: RunManifest,
    ) -> str | None:
        if manifest.run_id != receipt.run_id:
            raise ValueError("manifest run_id mismatch")
        terminal = manifest.status.is_terminal
        if receipt.publication_status is None:
            if terminal or manifest.final_decision is not None:
                raise ValueError("manifest claims an unobserved publication")
            return None

        if not terminal or manifest.status.value != receipt.publication_status.value:
            raise ValueError("manifest publication status mismatch")
        expected_decision = {
            RunStatus.PUBLISHED: "published",
            RunStatus.DEGRADED: "deterministic_fallback",
            RunStatus.REJECTED: "rejected",
        }[manifest.status]
        if manifest.final_decision != expected_decision:
            raise ValueError("manifest final decision mismatch")
        if not manifest.transitions or not isinstance(manifest.transitions[-1], dict):
            raise ValueError("terminal manifest requires a final transition")
        final_transition = manifest.transitions[-1]
        if final_transition.get("to") != manifest.status.value:
            raise ValueError("manifest terminal transition mismatch")
        reason = final_transition.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("manifest terminal transition requires a reason")
        if trace is None and receipt.runtime_status is RuntimeStatus.COMPLETED:
            raise ValueError("completed publication requires Trace")
        return reason

    @staticmethod
    def _final_records(manifest: RunManifest) -> tuple[dict, ...]:
        records = tuple(
            record
            for record in manifest.artifacts
            if isinstance(record, dict)
            and record.get("kind") == ArtifactKind.FINAL_REPORT.value
        )
        if any(not isinstance(record, dict) for record in manifest.artifacts):
            raise ValueError("manifest artifact record is not a mapping")
        return records

    @staticmethod
    def _artifact_records(
        manifest: RunManifest,
        kind: ArtifactKind,
    ) -> tuple[dict, ...]:
        if any(not isinstance(record, dict) for record in manifest.artifacts):
            raise ValueError("manifest artifact record is not a mapping")
        return tuple(
            record
            for record in manifest.artifacts
            if record.get("kind") == kind.value
        )

    @staticmethod
    def _artifact_references(
        trace: RuntimeTrace,
        kind: ArtifactKind,
    ) -> tuple[RuntimeArtifactReference, ...]:
        return tuple(
            reference
            for reference in trace.artifacts
            if reference.kind == kind.value
        )

    @staticmethod
    def _artifact_identity(record: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            record.get("kind"),
            record.get("schema_version"),
            record.get("path"),
            record.get("sha256"),
            record.get("producer"),
        )

    @staticmethod
    def _reference_identity(
        reference: RuntimeArtifactReference,
    ) -> tuple[Any, ...]:
        return (
            reference.kind,
            reference.schema_version,
            reference.relative_path,
            reference.sha256,
            reference.producer,
        )

    @staticmethod
    def _final_references(
        trace: RuntimeTrace | None,
    ) -> tuple[RuntimeArtifactReference, ...]:
        if trace is None:
            return ()
        return tuple(
            reference
            for reference in trace.artifacts
            if reference.kind == ArtifactKind.FINAL_REPORT.value
        )

    @staticmethod
    def _verify_report(
        *,
        receipt: ApiRunReceipt,
        store: FileRunStore,
        records: tuple[dict, ...],
        references: tuple[RuntimeArtifactReference, ...],
    ) -> str | None:
        if not receipt.report_available:
            if receipt.trace_reference is not None and (records or references):
                raise ValueError("receipt hides a Trace-backed final report")
            if receipt.publication_status in {
                None,
                RuntimePublicationStatus.REJECTED,
            } and records:
                raise ValueError("non-report run contains a final report")
            return None

        if len(records) != 1 or len(references) != 1:
            raise ValueError("available report must be unique in all stores")
        record = records[0]
        reference = references[0]
        if record.get("run_id") != receipt.run_id:
            raise ValueError("final report belongs to a different run")
        record_identity = (
            record.get("kind"),
            record.get("schema_version"),
            record.get("path"),
            record.get("sha256"),
            record.get("producer"),
        )
        reference_identity = (
            reference.kind,
            reference.schema_version,
            reference.relative_path,
            reference.sha256,
            reference.producer,
        )
        if record_identity != reference_identity:
            raise ValueError("Trace and manifest final report mismatch")
        if record.get("schema_version") != "1.0":
            raise ValueError("unsupported final report schema")
        content = store.read_artifact(record)
        report = content.decode("utf-8")
        if not report.strip():
            raise ValueError("final report must not be blank")
        return report

    @staticmethod
    def _cross_check_publication_signal(
        *,
        receipt: ApiRunReceipt,
        trace: RuntimeTrace | None,
        manifest_reason: str | None,
    ) -> None:
        if trace is None:
            return
        signals = tuple(
            event.signal
            for event in trace.events
            if isinstance(event.signal, PublicationDecidedSignal)
        )
        if receipt.publication_status is None:
            if signals:
                raise ValueError("Trace contains an unclaimed publication")
            return
        if len(signals) != 1:
            raise ValueError("published Trace requires one publication decision")
        signal = signals[0]
        if (
            signal.publication_status is not receipt.publication_status
            or signal.terminal_reason != manifest_reason
        ):
            raise ValueError("Trace and manifest publication terminal mismatch")


__all__ = [
    "RecentAveragesView",
    "RecentComparisonRowView",
    "RecentSummaryView",
    "RecentWinLossComparisonView",
    "RunQueryError",
    "RunQueryErrorCode",
    "RunQueryService",
    "RunView",
    "SingleMatchReviewView",
]
