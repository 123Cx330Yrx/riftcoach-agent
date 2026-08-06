"""Load a project-local Skill package without granting execution authority."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ValidationError

from app.tools.registry import ToolRegistry

from .models import SkillManifest


class SkillContractError(ValueError):
    """Raised when a Skill package is malformed or internally inconsistent."""


@dataclass(frozen=True)
class LoadedSkill:
    root: Path
    manifest: SkillManifest
    instructions: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]


def load_skill(skill_root: Path | str) -> LoadedSkill:
    root = Path(skill_root).resolve()
    manifest_path = root / "manifest.yaml"
    if not manifest_path.is_file():
        raise SkillContractError("skill package is missing manifest.yaml")

    raw_manifest = _read_yaml_mapping(manifest_path)
    try:
        manifest = SkillManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise SkillContractError("skill manifest validation failed") from exc

    if root.name != manifest.name:
        raise SkillContractError("skill directory name must match manifest name")

    instructions_path = root / manifest.instructions
    if not instructions_path.is_file():
        raise SkillContractError("skill package is missing SKILL.md")
    instructions = instructions_path.read_text(encoding="utf-8")
    frontmatter = _read_skill_frontmatter(instructions)
    if frontmatter.get("name") != manifest.name:
        raise SkillContractError("SKILL.md name must match manifest name")
    if frontmatter.get("description") != manifest.description:
        raise SkillContractError(
            "SKILL.md description must match manifest description"
        )

    return LoadedSkill(
        root=root,
        manifest=manifest,
        instructions=instructions,
        input_model=_import_pydantic_model(manifest.models.input),
        output_model=_import_pydantic_model(manifest.models.output),
    )


def validate_skill_tools(skill: LoadedSkill, registry: ToolRegistry) -> None:
    registered = {definition.name for definition in registry.list_tools()}
    unknown = set(skill.manifest.permissions.allowed_tools) - registered
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SkillContractError(f"skill references unregistered tools: {names}")


def _read_yaml_mapping(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SkillContractError(f"cannot read YAML file: {path.name}") from exc
    if not isinstance(value, Mapping):
        raise SkillContractError(f"{path.name} must contain a YAML mapping")
    return value


def _read_skill_frontmatter(instructions: str) -> Mapping[str, Any]:
    lines = instructions.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillContractError("SKILL.md must start with YAML frontmatter")
    try:
        closing_index = lines[1:].index("---") + 1
    except ValueError as exc:
        raise SkillContractError("SKILL.md frontmatter is not closed") from exc

    frontmatter_text = "\n".join(lines[1:closing_index])
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise SkillContractError("SKILL.md frontmatter is invalid") from exc
    if not isinstance(frontmatter, Mapping):
        raise SkillContractError("SKILL.md frontmatter must be a mapping")
    if set(frontmatter) != {"name", "description"}:
        raise SkillContractError(
            "SKILL.md frontmatter only allows name and description"
        )
    return frontmatter


def _import_pydantic_model(reference: str) -> type[BaseModel]:
    module_name, class_name = reference.split(":", maxsplit=1)
    try:
        model = getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError) as exc:
        raise SkillContractError(
            f"cannot import Pydantic model: {reference}"
        ) from exc
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise SkillContractError(
            f"referenced type is not a Pydantic model: {reference}"
        )
    return model
