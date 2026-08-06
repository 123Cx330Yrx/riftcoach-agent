from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.skills.catalog import SkillCatalog, SkillCatalogError
from app.skills.loader import SkillContractError
from app.skills.routing_models import RouterRequest


SOURCE_SKILL_ROOT = Path("skills/recent-form-review")


def write_skill_package(root: Path, name: str, description: str) -> Path:
    package_root = root / name
    package_root.mkdir()

    manifest = yaml.safe_load(
        (SOURCE_SKILL_ROOT / "manifest.yaml").read_text(encoding="utf-8")
    )
    manifest["name"] = name
    manifest["description"] = description
    manifest["triggers"]["intent"] = name.replace("-", "_")
    (package_root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (package_root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# Test Skill\n",
        encoding="utf-8",
    )
    return package_root


def test_catalog_loads_real_skill_and_projects_router_metadata():
    catalog = SkillCatalog.from_directory("skills")

    assert catalog.root == Path("skills").resolve()
    assert tuple(skill.manifest.name for skill in catalog.skills) == (
        "recent-form-review",
        "single-match-review",
    )
    skills_by_name = {skill.manifest.name: skill for skill in catalog.skills}
    assert catalog.get("recent-form-review") is skills_by_name[
        "recent-form-review"
    ]
    assert catalog.get("single-match-review") is skills_by_name[
        "single-match-review"
    ]
    assert catalog.get("missing-skill") is None

    candidates = catalog.route_candidates
    assert tuple(candidate.name for candidate in candidates) == (
        "recent-form-review",
        "single-match-review",
    )
    candidates_by_name = {candidate.name: candidate for candidate in candidates}
    assert (
        candidates_by_name["recent-form-review"].triggers.intent
        == "recent_form_review"
    )
    assert (
        candidates_by_name["single-match-review"].triggers.intent
        == "single_match_review"
    )
    assert not hasattr(candidates_by_name["recent-form-review"], "permissions")

    request = RouterRequest(
        utterance="分析我最近十局的状态",
        available_skills=candidates,
    )
    assert request.available_skills == candidates


def test_catalog_orders_packages_by_skill_name(tmp_path):
    write_skill_package(tmp_path, "zeta-review", "Review zeta cases.")
    write_skill_package(tmp_path, "alpha-review", "Review alpha cases.")

    catalog = SkillCatalog.from_directory(tmp_path)

    assert tuple(skill.manifest.name for skill in catalog.skills) == (
        "alpha-review",
        "zeta-review",
    )
    assert tuple(candidate.name for candidate in catalog.route_candidates) == (
        "alpha-review",
        "zeta-review",
    )


def test_catalog_allows_empty_root_and_ignores_files_and_hidden_dirs(tmp_path):
    (tmp_path / "README.md").write_text("Catalog notes", encoding="utf-8")
    (tmp_path / ".internal").mkdir()

    catalog = SkillCatalog.from_directory(tmp_path)

    assert catalog.skills == ()
    assert catalog.route_candidates == ()


def test_catalog_remains_a_snapshot_until_explicitly_rebuilt(tmp_path):
    original = SkillCatalog.from_directory(tmp_path)
    write_skill_package(tmp_path, "later-review", "Review later cases.")

    assert original.skills == ()
    assert tuple(
        skill.manifest.name
        for skill in SkillCatalog.from_directory(tmp_path).skills
    ) == ("later-review",)


def test_catalog_fails_fast_when_a_visible_skill_package_is_invalid(tmp_path):
    (tmp_path / "broken-skill").mkdir()

    with pytest.raises(
        SkillCatalogError,
        match="cannot load skill package 'broken-skill'",
    ) as exc_info:
        SkillCatalog.from_directory(tmp_path)

    assert isinstance(exc_info.value.__cause__, SkillContractError)
    assert "missing manifest.yaml" in str(exc_info.value)


def test_catalog_rejects_missing_or_non_directory_roots(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(SkillCatalogError, match="root does not exist"):
        SkillCatalog.from_directory(missing)

    file_root = tmp_path / "skills.txt"
    file_root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(SkillCatalogError, match="root must be a directory"):
        SkillCatalog.from_directory(file_root)


def test_catalog_constructor_rejects_duplicate_or_unordered_snapshots(tmp_path):
    loaded = SkillCatalog.from_directory("skills").get("recent-form-review")
    assert loaded is not None

    with pytest.raises(SkillCatalogError, match="names must be unique"):
        SkillCatalog(root=Path("skills").resolve(), _skills=(loaded, loaded))

    write_skill_package(tmp_path, "alpha-review", "Review alpha cases.")
    write_skill_package(tmp_path, "zeta-review", "Review zeta cases.")
    ordered = SkillCatalog.from_directory(tmp_path).skills
    with pytest.raises(SkillCatalogError, match="ordered by name"):
        SkillCatalog(
            root=tmp_path.resolve(),
            _skills=tuple(reversed(ordered)),
        )
