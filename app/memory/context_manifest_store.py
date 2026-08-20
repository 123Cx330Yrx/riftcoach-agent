from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from app.harness.run_ids import normalize_run_id
from app.memory.context_models import (
    MemoryContextManifest,
    canonical_memory_context_manifest_bytes,
)


_MANIFEST_NAME = "memory_context_manifest.json"
_MAX_MANIFEST_BYTES = 128 * 1024


class MemoryContextManifestStoreError(RuntimeError):
    """Safe local persistence failure for a private Context manifest."""


class FileMemoryContextManifestStore:
    def __init__(self, runs_root: str | Path) -> None:
        self._runs_root = Path(runs_root).expanduser().resolve()

    def write(self, manifest: MemoryContextManifest) -> str:
        if not isinstance(manifest, MemoryContextManifest):
            raise TypeError("manifest must be a MemoryContextManifest")
        run_id = normalize_run_id(manifest.binding.run_id)
        payload = canonical_memory_context_manifest_bytes(manifest)
        if len(payload) > _MAX_MANIFEST_BYTES:
            raise MemoryContextManifestStoreError("manifest_size_invalid")

        try:
            self._runs_root.mkdir(parents=True, exist_ok=True)
            run_path = self._runs_root / run_id
            if run_path.is_symlink():
                raise MemoryContextManifestStoreError("manifest_path_unsafe")
            run_path.mkdir(parents=False, exist_ok=True)
            if run_path.resolve() != run_path:
                raise MemoryContextManifestStoreError("manifest_path_unsafe")
            target = run_path / _MANIFEST_NAME
            if target.is_symlink():
                raise MemoryContextManifestStoreError("manifest_path_unsafe")
            if target.exists():
                existing = target.read_bytes()
                if existing != payload:
                    raise MemoryContextManifestStoreError(
                        "manifest_integrity_conflict"
                    )
                return hashlib.sha256(existing).hexdigest()

            descriptor, temporary_name = tempfile.mkstemp(
                dir=run_path,
                prefix=f".{_MANIFEST_NAME}.",
                suffix=".tmp",
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
        except MemoryContextManifestStoreError:
            raise
        except (OSError, ValueError):
            raise MemoryContextManifestStoreError(
                "manifest_persistence_failed"
            ) from None
        return hashlib.sha256(payload).hexdigest()


__all__ = [
    "FileMemoryContextManifestStore",
    "MemoryContextManifestStoreError",
]
