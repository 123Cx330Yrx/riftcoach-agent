"""Atomic, immutable persistence for one final safe Runtime Trace."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.harness.run_ids import normalize_run_id

from .models import RuntimeTrace, RuntimeTraceReference


class RuntimeTraceIntegrityError(RuntimeError):
    """Raised when stored bytes do not match their immutable reference."""


class RuntimeTraceStore:
    def __init__(self, runs_root: str | Path, run_id: str) -> None:
        self.runs_root = Path(runs_root).resolve()
        self.run_id = normalize_run_id(run_id)
        self.run_directory = self.runs_root / self.run_id
        self.trace_path = self.run_directory / "runtime_trace.json"

    def write_trace(self, trace: RuntimeTrace) -> RuntimeTraceReference:
        if trace.run_id != self.run_id:
            raise ValueError("trace run_id does not match this store")
        if self.trace_path.exists():
            raise FileExistsError("runtime trace is immutable once written")

        payload = json.dumps(
            trace.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8") + b"\n"
        self._atomic_write(payload)
        digest = hashlib.sha256(payload).hexdigest()
        return RuntimeTraceReference(
            run_id=self.run_id,
            trace_schema_version=trace.trace_schema_version,
            sha256=digest,
        )

    def read_trace(self, reference: RuntimeTraceReference) -> RuntimeTrace:
        if reference.run_id != self.run_id:
            raise ValueError("trace reference run_id does not match this store")
        if reference.relative_path != self.trace_path.name:
            raise ValueError("trace reference path does not match this store")

        payload = self.trace_path.read_bytes()
        actual_digest = hashlib.sha256(payload).hexdigest()
        if actual_digest != reference.sha256:
            raise RuntimeTraceIntegrityError(
                "runtime trace digest does not match its reference"
            )
        try:
            trace = RuntimeTrace.model_validate_json(payload)
        except ValidationError as exc:
            raise RuntimeTraceIntegrityError(
                "runtime trace no longer satisfies its schema"
            ) from exc
        if reference.trace_schema_version != trace.trace_schema_version:
            raise RuntimeTraceIntegrityError(
                "runtime trace schema version does not match its reference"
            )
        return trace

    def _atomic_write(self, payload: bytes) -> None:
        self.run_directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.run_directory,
                prefix=".runtime_trace.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if self.trace_path.exists():
                raise FileExistsError("runtime trace is immutable once written")
            os.replace(temporary_path, self.trace_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
