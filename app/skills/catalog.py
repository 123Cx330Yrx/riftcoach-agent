"""Discover validated project-local Skills as a deterministic snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .loader import LoadedSkill, SkillContractError, load_skill
from .routing_models import SkillRouteCandidate


class SkillCatalogError(SkillContractError):
    """Raised when a Skill catalog cannot be built consistently."""


@dataclass(frozen=True)
class SkillCatalog:
    """An immutable, name-ordered snapshot of validated Skill packages."""

    root: Path
    _skills: tuple[LoadedSkill, ...]

    def __post_init__(self) -> None:
        names = tuple(skill.manifest.name for skill in self._skills)
        if len(set(names)) != len(names):
            raise SkillCatalogError("skill catalog names must be unique")
        if names != tuple(sorted(names)):
            raise SkillCatalogError("skill catalog must be ordered by name")

    @classmethod
    def from_directory(cls, root: Path | str) -> "SkillCatalog":
        catalog_root = Path(root).resolve()
        if not catalog_root.exists():
            raise SkillCatalogError(
                f"skill catalog root does not exist: {catalog_root}"
            )
        if not catalog_root.is_dir():
            raise SkillCatalogError(
                f"skill catalog root must be a directory: {catalog_root}"
            )

        try:
            entries = tuple(catalog_root.iterdir())
        except OSError as exc:
            raise SkillCatalogError(
                f"cannot read skill catalog root: {catalog_root}"
            ) from exc

        package_roots = sorted(
            (
                entry
                for entry in entries
                if entry.is_dir() and not entry.name.startswith(".")
            ),
            key=lambda entry: entry.name,
        )

        loaded_skills: list[LoadedSkill] = []
        for package_root in package_roots:
            try:
                loaded_skills.append(load_skill(package_root))
            except SkillContractError as exc:
                raise SkillCatalogError(
                    f"cannot load skill package {package_root.name!r}: {exc}"
                ) from exc

        skills = tuple(
            sorted(loaded_skills, key=lambda skill: skill.manifest.name)
        )
        return cls(root=catalog_root, _skills=skills)

    @property
    def skills(self) -> tuple[LoadedSkill, ...]:
        return self._skills

    @property
    def route_candidates(self) -> tuple[SkillRouteCandidate, ...]:
        return tuple(
            SkillRouteCandidate.from_manifest(skill.manifest)
            for skill in self._skills
        )

    def get(self, name: str) -> LoadedSkill | None:
        return next(
            (
                skill
                for skill in self._skills
                if skill.manifest.name == name
            ),
            None,
        )
