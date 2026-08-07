from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from .run_ids import normalize_run_id


class ArtifactIntegrityError(RuntimeError):
    """Raised when an artifact no longer matches its registered digest."""


class FileRunStore:
    """File-backed storage for one immutable Harness run namespace."""

    def __init__(self, runs_root: str | Path, run_id: str) -> None:
        run_id = normalize_run_id(run_id)
        self.runs_root = Path(runs_root).resolve()
        self.run_id = run_id
        self.run_directory = self.runs_root / run_id
        self.manifest_path = self.run_directory / "manifest.json"

    def create_run(self, manifest: RunManifest) -> None:
        if manifest.run_id != self.run_id:
            raise ValueError("manifest run_id does not match this store.")
        if self.manifest_path.exists():
            raise FileExistsError(f"Run already exists: {self.run_id}")

        self.run_directory.mkdir(parents=True, exist_ok=True)
        self.write_manifest(manifest)

    def write_manifest(self, manifest: RunManifest) -> None:
        if manifest.run_id != self.run_id:
            raise ValueError("manifest run_id does not match this store.")

        payload = json.dumps(
            asdict(manifest),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8") + b"\n"
        self._atomic_write(self.manifest_path, payload, prefix=".manifest.")

    def read_manifest(self) -> RunManifest:
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return RunManifest(
            run_id=raw["run_id"],
            status=RunStatus(raw["status"]),
            config=HarnessConfig(**raw["config"]),
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
            revision_count=raw.get("revision_count", 0),
            attempt_id=raw.get("attempt_id", 0),
            artifacts=raw.get("artifacts", []),
            transitions=raw.get("transitions", []),
            final_decision=raw.get("final_decision"),
        )

    def write_artifact(
        self,
        *,
        kind: ArtifactKind,
        relative_path: str | Path,
        content: str | bytes,
        schema_version: str,
        producer: str,
    ) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"Run does not exist: {self.run_id}")

        artifact_path = self._resolve_artifact_path(relative_path)
        if artifact_path.exists():
            raise FileExistsError(
                f"Artifact paths are immutable once written: {relative_path}"
            )

        content_bytes = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(content_bytes).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()
        record: dict[str, Any] = {
            "artifact_id": uuid4().hex,
            "run_id": self.run_id,
            "kind": kind.value,
            "schema_version": schema_version,
            "path": artifact_path.relative_to(self.run_directory).as_posix(),
            "sha256": digest,
            "created_at": created_at,
            "producer": producer,
        }

        self._atomic_write(artifact_path, content_bytes, prefix=f".{artifact_path.name}.")

        manifest = self.read_manifest()
        manifest.artifacts.append(record)
        manifest.updated_at = created_at
        self.write_manifest(manifest)
        return record

    def read_artifact(self, record: dict[str, Any]) -> bytes:
        if record.get("run_id") != self.run_id:
            raise ValueError("artifact belongs to a different run.")

        artifact_path = self._resolve_artifact_path(record["path"])
        content = artifact_path.read_bytes()
        actual_digest = hashlib.sha256(content).hexdigest()
        expected_digest = record.get("sha256")
        if actual_digest != expected_digest:
            raise ArtifactIntegrityError(
                f"Artifact digest mismatch for {record['path']}: "
                f"expected {expected_digest}, got {actual_digest}."
            )
        return content

    def _resolve_artifact_path(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError("artifact path must be relative to the run directory.")

        resolved = (self.run_directory / path).resolve()
        run_directory = self.run_directory.resolve()
        if not resolved.is_relative_to(run_directory) or resolved == run_directory:
            raise ValueError("artifact path must stay inside the run directory.")
        return resolved

    @staticmethod
    def _atomic_write(target: Path, content: bytes, *, prefix: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=prefix,
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, target)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
