"""Strict loading of checked-in Prompt Program manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .models import PromptProgramManifest


class PromptProgramCatalogError(ValueError):
    """Raised when the Prompt Program catalog cannot be trusted."""


@dataclass(frozen=True)
class LoadedPromptProgram:
    manifest: PromptProgramManifest
    path: Path


@dataclass(frozen=True)
class PromptProgramCatalog:
    """An immutable, stable-id ordered snapshot of Program manifests."""

    root: Path
    _programs: tuple[LoadedPromptProgram, ...]

    def __post_init__(self) -> None:
        ids = tuple(row.manifest.program_id for row in self._programs)
        if len(set(ids)) != len(ids):
            raise PromptProgramCatalogError(
                "Prompt Program IDs must be unique"
            )
        if ids != tuple(sorted(ids)):
            raise PromptProgramCatalogError(
                "Prompt Programs must be ordered by program_id"
            )

    @classmethod
    def from_directory(cls, root: str | Path) -> "PromptProgramCatalog":
        catalog_root = Path(root).resolve()
        if not catalog_root.exists():
            raise PromptProgramCatalogError(
                f"Prompt Program catalog root does not exist: {catalog_root}"
            )
        if not catalog_root.is_dir():
            raise PromptProgramCatalogError(
                f"Prompt Program catalog root must be a directory: {catalog_root}"
            )

        package_roots = sorted(
            (
                entry
                for entry in catalog_root.iterdir()
                if entry.is_dir() and not entry.name.startswith(".")
            ),
            key=lambda entry: entry.name,
        )
        loaded: list[LoadedPromptProgram] = []
        for package_root in package_roots:
            manifest_path = package_root / "manifest.json"
            if not manifest_path.is_file():
                raise PromptProgramCatalogError(
                    f"Prompt Program package {package_root.name!r} "
                    "must contain manifest.json"
                )
            try:
                payload = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
                manifest = PromptProgramManifest.model_validate(payload)
            except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
                raise PromptProgramCatalogError(
                    f"cannot load Prompt Program package "
                    f"{package_root.name!r}: {exc}"
                ) from exc
            loaded.append(
                LoadedPromptProgram(manifest=manifest, path=manifest_path)
            )

        return cls(
            root=catalog_root,
            _programs=tuple(
                sorted(loaded, key=lambda row: row.manifest.program_id)
            ),
        )

    @property
    def programs(self) -> tuple[LoadedPromptProgram, ...]:
        return self._programs

    def get(self, program_id: str) -> LoadedPromptProgram | None:
        return next(
            (
                row
                for row in self._programs
                if row.manifest.program_id == program_id
            ),
            None,
        )


__all__ = [
    "LoadedPromptProgram",
    "PromptProgramCatalog",
    "PromptProgramCatalogError",
]
