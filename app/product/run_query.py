"""Strict, body-free query projection over receipt, Trace and Artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.harness.models import ArtifactKind, RunManifest, RunStatus
from app.harness.run_ids import normalize_run_id
from app.harness.store import FileRunStore
from app.runtime.models import (
    RuntimeArtifactReference,
    RuntimeStatus,
    RuntimeTrace,
    RuntimeUsage,
)
from app.runtime.signals import PublicationDecidedSignal, RuntimePublicationStatus
from app.runtime.store import RuntimeTraceStore

from .run_receipts import ApiRunReceipt, FileRunReceiptStore


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


@dataclass(frozen=True)
class _VerifiedRun:
    receipt: ApiRunReceipt
    trace: RuntimeTrace | None
    report: str | None


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
            return _VerifiedRun(receipt=receipt, trace=trace, report=None)

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
        return _VerifiedRun(receipt=receipt, trace=trace, report=report)

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
    "RunQueryError",
    "RunQueryErrorCode",
    "RunQueryService",
    "RunView",
]
