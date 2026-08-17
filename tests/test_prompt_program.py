from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.prompt_context_identity import (
    build_component_fingerprints,
)
from app.evaluation.coach_report import (
    EVALUATOR_SYSTEM_PROMPT,
    REVISER_SYSTEM_PROMPT,
    build_fact_pack,
    build_revision_prompt,
    validate_revised_report,
)
from app.harness.adapters import ChatCoachReviser, SecureChatEvaluationAdapter
from app.providers.capabilities import ProviderCapabilities
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.prompt_program import (
    PromptProgramCatalog,
    PromptProgramCatalogError,
    PromptProgramManifest,
    PromptProgramResolver,
)
from app.runtime.composition import (
    RuntimeCompositionRoot,
    build_secure_product_execution_factory,
)
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.runtime import RuntimeCompositionError
from app.skills.catalog import SkillCatalog


class NoIoProvider:
    provider_name = "no-io-provider"
    model_name = "no-io-model"
    capabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def chat(self, request):
        raise AssertionError("factory construction must not call the Provider")


class NoopObserver:
    def observe(self, signal) -> None:
        return None


def _payload(*, evaluation_version: str = "1.1.0") -> dict:
    skill_catalog = SkillCatalog.from_directory("skills")
    skill = skill_catalog.get("recent-form-review")
    assert skill is not None
    payload = {
        "schema_version": "1.0",
        "program_id": "recent-form-review-coach",
        "program_version": "1.0.0",
        "skill_name": skill.manifest.name,
        "skill_version": skill.manifest.version,
        "context_contract_id": "context-builder-v1",
        "context_contract_version": "1.0.0",
        "evaluation_contract_id": "coach_evaluation",
        "evaluation_contract_version": evaluation_version,
        "component_fingerprints": [
            row.model_dump(mode="json")
            for row in build_component_fingerprints(
                skill,
                evaluation_contract_version=evaluation_version,
            )
        ],
    }
    payload["program_sha256"] = PromptProgramManifest.digest_for(payload)
    return payload


def _write_manifest(root: Path, payload: dict) -> None:
    package = root / payload["program_id"]
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_manifest_is_strict_and_binds_its_own_digest() -> None:
    payload = _payload()
    manifest = PromptProgramManifest.model_validate(payload)

    assert manifest.program_sha256 == PromptProgramManifest.digest_for(payload)

    extra = dict(payload, prompt_text="must not be stored here")
    with pytest.raises(ValidationError, match="extra"):
        PromptProgramManifest.model_validate(extra)

    tampered = dict(payload, program_version="1.0.1")
    with pytest.raises(ValidationError, match="program_sha256"):
        PromptProgramManifest.model_validate(tampered)


def test_catalog_loads_stable_program_snapshot_and_rejects_missing_manifest(
    tmp_path: Path,
) -> None:
    _write_manifest(tmp_path, _payload())
    catalog = PromptProgramCatalog.from_directory(tmp_path)

    assert tuple(row.manifest.program_id for row in catalog.programs) == (
        "recent-form-review-coach",
    )
    assert catalog.get("recent-form-review-coach") is not None

    broken = tmp_path / "broken-program"
    broken.mkdir()
    with pytest.raises(PromptProgramCatalogError, match="manifest.json"):
        PromptProgramCatalog.from_directory(tmp_path)


def test_catalog_rejects_non_secure_evaluation_program(tmp_path: Path) -> None:
    payload = _payload(evaluation_version="1.0.0")
    _write_manifest(tmp_path, payload)

    with pytest.raises(PromptProgramCatalogError, match="1.1.0"):
        PromptProgramCatalog.from_directory(tmp_path)


def test_resolver_recomputes_components_and_returns_verified_program(
    tmp_path: Path,
) -> None:
    _write_manifest(tmp_path, _payload())
    resolver = PromptProgramResolver(
        PromptProgramCatalog.from_directory(tmp_path),
        SkillCatalog.from_directory("skills"),
    )

    verified = resolver.resolve("recent-form-review", "0.2.0")

    assert verified.manifest.program_id == "recent-form-review-coach"
    assert verified.manifest.program_version == "1.0.0"
    assert verified.skill_name == "recent-form-review"
    assert verified.context_contract_version == "1.0.0"


def test_checked_in_program_and_composition_root_are_verified() -> None:
    root = RuntimeCompositionRoot.from_directories(
        skills_root="skills",
        prompt_programs_root="prompt_programs",
    )

    verified = root.prompt_program_resolver.resolve(
        "recent-form-review",
        "0.2.0",
    )

    assert verified.program_id == "recent-form-review-coach"
    assert root.skill_catalog.get("recent-form-review") is not None


def test_secure_product_factory_builds_the_v11_evaluator_and_bounded_reviser(
    tmp_path: Path,
) -> None:
    knowledge = LocalHybridKnowledgeProvider.from_directory(
        Path("data/rag_docs")
    )
    factory = build_secure_product_execution_factory(
        knowledge_provider=knowledge
    )
    observer = NoopObserver()
    observed = ObservedLLMProvider(
        delegate=NoIoProvider(),
        observer=observer,
    )

    bundle = factory.build(provider=observed, observer=observer)

    assert type(bundle.evaluator) is SecureChatEvaluationAdapter
    assert bundle.evaluator.system_prompt == EVALUATOR_SYSTEM_PROMPT
    assert bundle.evaluator.fact_pack_builder is build_fact_pack
    assert type(bundle.reviser) is ChatCoachReviser
    assert bundle.reviser.system_prompt == REVISER_SYSTEM_PROMPT
    assert bundle.reviser.prompt_builder is build_revision_prompt
    assert bundle.reviser.validator is validate_revised_report


def test_product_composition_defaults_to_secure_factory_without_io(
    tmp_path: Path,
) -> None:
    root = RuntimeCompositionRoot.from_directories(
        skills_root="skills",
        prompt_programs_root="prompt_programs",
    )
    knowledge = LocalHybridKnowledgeProvider.from_directory(
        Path("data/rag_docs")
    )

    runtime = root.build_runtime(
        runs_root=tmp_path,
        provider=NoIoProvider(),
        knowledge_provider=knowledge,
    )
    observer = NoopObserver()
    bundle = runtime._execution_factory.build(
        provider=ObservedLLMProvider(
            delegate=NoIoProvider(),
            observer=observer,
        ),
        observer=observer,
    )

    assert type(bundle.evaluator) is SecureChatEvaluationAdapter
    assert type(bundle.reviser) is ChatCoachReviser

    with pytest.raises(RuntimeCompositionError, match="knowledge_provider"):
        root.build_runtime(
            runs_root=tmp_path,
            provider=NoIoProvider(),
        )


@pytest.mark.parametrize(
    "mutator, message",
    (
        (
            lambda payload: payload["component_fingerprints"][0].update(
                {"sha256": "0" * 64}
            ),
            "fingerprint",
        ),
        (
            lambda payload: payload.update({"skill_version": "9.9.9"}),
            "Skill",
        ),
        (
            lambda payload: payload.update({"context_contract_version": "9.9.9"}),
            "context",
        ),
    ),
)
def test_resolver_fails_closed_on_program_drift(
    tmp_path: Path,
    mutator,
    message: str,
) -> None:
    payload = _payload()
    mutator(payload)
    payload["program_sha256"] = PromptProgramManifest.digest_for(payload)
    _write_manifest(tmp_path, payload)
    resolver = PromptProgramResolver(
        PromptProgramCatalog.from_directory(tmp_path),
        SkillCatalog.from_directory("skills"),
    )

    with pytest.raises(PromptProgramCatalogError, match=message):
        resolver.resolve("recent-form-review", "0.2.0")
