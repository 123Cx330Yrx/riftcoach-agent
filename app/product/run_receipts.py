"""Body-free immutable receipts for product-facing run lookup."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from app.harness.run_ids import normalize_run_id
from app.runtime.models import (
    RuntimeRunResult,
    RuntimeStatus,
    RuntimeTraceReference,
)
from app.runtime.signals import RuntimePublicationStatus


_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class RunReceiptIntegrityError(RuntimeError):
    """Raised when stored receipt bytes do not satisfy the frozen contract."""


class RunReceiptReference(BaseModel):
    """Body-free identity of the exact immutable receipt bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    relative_path: Literal["api_run_receipt.json"] = "api_run_receipt.json"
    sha256: str

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("sha256 must be a lowercase SHA-256 digest")
        return value


class ApiRunReceipt(BaseModel):
    """Small immutable query index; intentionally contains no content bodies."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "1.0"
    run_id: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus | None = None
    terminal_reason: str
    trace_reference: RuntimeTraceReference | None = None
    created_at_utc: datetime
    report_available: bool

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("unsupported run receipt schema version")
        return value

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        if not _SAFE_CODE_PATTERN.fullmatch(value):
            raise ValueError("terminal_reason must be a safe code")
        return value

    @field_validator("created_at_utc")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("created_at_utc must be timezone-aware UTC")
        return value

    @model_validator(mode="after")
    def validate_terminal_projection(self) -> "ApiRunReceipt":
        if (
            self.trace_reference is not None
            and self.trace_reference.run_id != self.run_id
        ):
            raise ValueError("trace reference run_id must match receipt run_id")
        if self.runtime_status is RuntimeStatus.COMPLETED and (
            self.publication_status is None or self.trace_reference is None
        ):
            raise ValueError(
                "completed receipt requires publication and trace reference"
            )
        if self.report_available:
            if self.trace_reference is None:
                raise ValueError("available report requires a trace reference")
            if self.publication_status not in {
                RuntimePublicationStatus.PUBLISHED,
                RuntimePublicationStatus.DEGRADED,
            }:
                raise ValueError(
                    "available report requires published or degraded status"
                )
        if self.publication_status is RuntimePublicationStatus.REJECTED and (
            self.report_available
        ):
            raise ValueError("rejected receipt cannot expose a report")
        return self

    @classmethod
    def from_runtime_result(
        cls,
        result: RuntimeRunResult[Any],
        *,
        created_at_utc: datetime | None = None,
    ) -> "ApiRunReceipt":
        if not isinstance(result, RuntimeRunResult):
            raise TypeError("result must be a RuntimeRunResult")
        created_at = created_at_utc or datetime.now(timezone.utc)
        return cls(
            run_id=result.run_id,
            runtime_status=result.runtime_status,
            publication_status=result.publication_status,
            terminal_reason=result.terminal_reason,
            trace_reference=result.trace_reference,
            created_at_utc=created_at,
            report_available=(
                result.trace_reference is not None
                and result.publication_status
                in {
                    RuntimePublicationStatus.PUBLISHED,
                    RuntimePublicationStatus.DEGRADED,
                }
            ),
        )


class RunReceiptWriter(Protocol):
    """Narrow Application Service port for persisting one Runtime terminal."""

    def write_result(
        self,
        result: RuntimeRunResult[Any],
        *,
        created_at_utc: datetime | None = None,
    ) -> ApiRunReceipt: ...


class FileRunReceiptStore:
    """Atomic, immutable receipt storage below a shared runs root."""

    filename = "api_run_receipt.json"

    def __init__(self, runs_root: str | Path) -> None:
        self.runs_root = Path(runs_root).resolve()

    def write_result(
        self,
        result: RuntimeRunResult[Any],
        *,
        created_at_utc: datetime | None = None,
    ) -> ApiRunReceipt:
        receipt = ApiRunReceipt.from_runtime_result(
            result,
            created_at_utc=created_at_utc,
        )
        self.write_receipt(receipt)
        return receipt

    def write_receipt(self, receipt: ApiRunReceipt) -> None:
        if not isinstance(receipt, ApiRunReceipt):
            raise TypeError("receipt must be an ApiRunReceipt")
        target = self._receipt_path(receipt.run_id)
        if target.exists():
            raise FileExistsError("run receipt is immutable once written")
        payload = json.dumps(
            receipt.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8") + b"\n"
        self._atomic_write_once(target, payload)

    def read_receipt(self, run_id: str) -> ApiRunReceipt:
        receipt, _ = self.read_receipt_with_reference(run_id)
        return receipt

    def read_receipt_with_reference(
        self,
        run_id: str,
    ) -> tuple[ApiRunReceipt, RunReceiptReference]:
        normalized = normalize_run_id(run_id)
        target = self._receipt_path(normalized)
        payload = target.read_bytes()
        try:
            receipt = ApiRunReceipt.model_validate_json(payload)
        except (ValidationError, TypeError, ValueError) as exc:
            raise RunReceiptIntegrityError(
                "stored run receipt no longer satisfies its schema"
            ) from exc
        if receipt.run_id != normalized:
            raise RunReceiptIntegrityError(
                "stored run receipt belongs to a different run"
            )
        return receipt, RunReceiptReference(
            run_id=normalized,
            sha256=sha256(payload).hexdigest(),
        )

    def _receipt_path(self, run_id: str) -> Path:
        normalized = normalize_run_id(run_id)
        return self.runs_root / normalized / self.filename

    @staticmethod
    def _atomic_write_once(target: Path, payload: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=".api_run_receipt.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            try:
                # The hard-link commit is an atomic create-if-absent operation
                # because source and target live in the same directory.
                os.link(temporary_path, target)
            except FileExistsError:
                raise FileExistsError(
                    "run receipt is immutable once written"
                ) from None
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


__all__ = [
    "ApiRunReceipt",
    "FileRunReceiptStore",
    "RunReceiptReference",
    "RunReceiptIntegrityError",
    "RunReceiptWriter",
]
