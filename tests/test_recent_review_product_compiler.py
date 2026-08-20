from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.harness.run_ids import normalize_run_id
from app.memory.context_models import MemoryContextBinding
from app.players.models import RelationshipRole
from app.runtime.models import RuntimePolicySnapshot, RuntimeRunRequest
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionBoundaryError,
)
from app.skills.recent_form_review import RecentFormReviewInput
from app.skills.router import DeterministicSkillRouter
from app.skills.single_match_review import SingleMatchReviewInput
from app.product.recent_review import (
    ProductRequestCompilationError,
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)


def valid_summary() -> dict:
    return {
        "schema_version": "1.0",
        "metadata": {},
        "player": {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "riot_id": "DemoPlayer#TEST",
        },
        "request": {"count": 10, "queue": 420},
        "recent_summary": {"games_analyzed": 1},
        "matches": [
            {
                "match_id": "KR_PRODUCT_1",
                "game_duration_seconds": 1800,
                "champion_id": 103,
                "champion_name": "Ahri",
                "role": "MIDDLE",
                "win": True,
                "timeline_status": "available",
                "included_in_aggregate": True,
            }
        ],
        "failed_matches": [],
        "excluded_matches": [],
    }


def test_product_request_normalizes_riot_id_and_applies_safe_defaults():
    request = RecentReviewProductRequest(riot_id="  Name#Part # CN1  ")

    assert request.riot_id == "Name#Part#CN1"
    assert request.game_name == "Name#Part"
    assert request.tag_line == "CN1"
    assert request.count == 10
    assert request.queue == 420
    assert request.focus == "overall"
    assert request.model_dump(mode="python") == {
        "riot_id": "Name#Part#CN1",
        "count": 10,
        "queue": 420,
        "focus": "overall",
    }

    with pytest.raises(ValidationError, match="frozen"):
        request.count = 20


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("run_id", "client-run"),
        ("skill", "recent-form-review"),
        ("provider", "deepseek"),
        ("policy", {}),
        ("min_duration_seconds", 0),
        ("prompt_profile", "unsafe"),
        ("path", "data/runs/example"),
        ("sha256", "0" * 64),
    ),
)
def test_product_request_rejects_every_server_owned_field(field: str, value):
    payload = {"riot_id": "DemoPlayer#TEST", field: value}

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RecentReviewProductRequest.model_validate(payload)


@pytest.mark.parametrize("count", (4, 21, "10", True))
def test_product_request_rejects_invalid_or_coerced_count(count):
    with pytest.raises(ValidationError):
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST", count=count)


@pytest.mark.parametrize("queue", (0, 430, "420", True))
def test_product_request_rejects_unsupported_or_coerced_queue(queue):
    with pytest.raises(ValidationError):
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST", queue=queue)


def test_product_request_accepts_no_queue_filter_and_all_supported_focuses():
    assert (
        RecentReviewProductRequest(
            riot_id="DemoPlayer#TEST",
            queue=None,
        ).queue
        is None
    )
    for focus in ("overall", "laning", "survival", "economy", "vision"):
        assert (
            RecentReviewProductRequest(
                riot_id="DemoPlayer#TEST",
                focus=focus,
            ).focus
            == focus
        )

    with pytest.raises(ValidationError):
        RecentReviewProductRequest(
            riot_id="DemoPlayer#TEST",
            focus="teamfighting",
        )


@pytest.mark.parametrize(
    "riot_id",
    (
        "missing-tag",
        "#TEST",
        "DemoPlayer#",
        "Demo\nPlayer#TEST",
        f"{'A' * 65}#TEST",
        f"DemoPlayer#{'T' * 33}",
        f"{'A' * 64}#{'T' * 32}X",
    ),
)
def test_product_request_rejects_malformed_or_unbounded_riot_id(riot_id: str):
    with pytest.raises(ValidationError, match="riot_id"):
        RecentReviewProductRequest(riot_id=riot_id)


def _compile(
    *,
    catalog: SkillCatalog | None = None,
    run_id: str = "review_product_compile",
    request: RecentReviewProductRequest | None = None,
) -> RuntimeRunRequest:
    return RecentReviewRuntimeRequestCompiler(
        catalog or SkillCatalog.from_directory("skills"),
        run_id_factory=lambda: run_id,
    ).compile(
        request
        or RecentReviewProductRequest(
            riot_id="DemoPlayer#TEST",
            focus="survival",
        ),
        player_summary=valid_summary(),
        deterministic_report="  # Deterministic facts  ",
    )


def test_compiler_uses_catalog_identity_and_machine_evidence_without_router(
    monkeypatch,
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("typed compiler must not call natural-language Router")

    monkeypatch.setattr(DeterministicSkillRouter, "route", fail_if_called)

    compiled = _compile()
    decision = compiled.execution_request.router_decision

    assert decision.outcome.value == "selected"
    assert decision.reason.value == "matched_skill"
    assert decision.selected_skill == "recent-form-review"
    assert decision.selected_skill_version == "0.2.0"
    assert decision.candidate_skills == ("recent-form-review",)
    assert len(decision.evidence) == 1
    assert decision.evidence[0].skill_name == "recent-form-review"
    assert decision.evidence[0].positive_signals == (
        "entrypoint:reviews.recent",
    )
    assert decision.evidence[0].negative_signals == ()


def test_compiler_fails_closed_when_recent_skill_is_unavailable(tmp_path):
    empty_root = tmp_path / "skills"
    empty_root.mkdir()
    catalog = SkillCatalog.from_directory(empty_root)

    with pytest.raises(ProductRequestCompilationError, match="not available"):
        _compile(catalog=catalog)


def test_compiler_fails_closed_when_recent_skill_input_contract_drifted():
    catalog = SkillCatalog.from_directory("skills")
    recent = catalog.get("recent-form-review")
    assert recent is not None
    incompatible = replace(recent, input_model=SingleMatchReviewInput)
    drifted_catalog = SkillCatalog(root=catalog.root, _skills=(incompatible,))

    with pytest.raises(ProductRequestCompilationError, match="input contract"):
        _compile(catalog=drifted_catalog)


def test_compiler_derives_runtime_policy_from_manifest_and_fixed_v1_policy():
    catalog = SkillCatalog.from_directory("skills")
    recent = catalog.get("recent-form-review")
    assert recent is not None
    changed_manifest = recent.manifest.model_copy(
        update={
            "budgets": recent.manifest.budgets.model_copy(
                update={
                    "max_iterations": 2,
                    "max_tool_calls": 1,
                    "timeout_s": 12.5,
                    "max_context_tokens": 12_000,
                }
            ),
            "quality_gate": recent.manifest.quality_gate.model_copy(
                update={
                    "minimum_score": 91,
                    "allow_deterministic_fallback": False,
                }
            ),
        }
    )
    changed_skill = replace(recent, manifest=changed_manifest)
    changed_catalog = SkillCatalog(
        root=catalog.root,
        _skills=(changed_skill,),
    )

    compiled = _compile(catalog=changed_catalog)

    assert compiled.policy == RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=256,
        max_iterations=2,
        max_tool_calls=1,
        timeout_s=12.5,
        max_context_tokens=12_000,
        publish_score_threshold=91,
        max_revisions=1,
        allow_deterministic_fallback=False,
    )


def test_compiler_preserves_trusted_memory_context_binding_and_rejects_drift():
    context_binding = MemoryContextBinding(
        run_id="review_product_compile",
        owner_id="owner-compiler",
        conversation_id=UUID("41000000-0000-0000-0000-000000000001"),
        relationship_id=UUID("41000000-0000-0000-0000-000000000002"),
        player_subject_id=UUID("41000000-0000-0000-0000-000000000003"),
        relationship_role=RelationshipRole.SELF,
    )
    compiler = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory("skills"),
        run_id_factory=lambda: "review_product_compile",
    )

    compiled = compiler.compile(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
        player_summary=valid_summary(),
        deterministic_report="# facts",
        memory_context_binding=context_binding,
    )
    assert compiled.memory_context_binding == context_binding

    with pytest.raises(ProductRequestCompilationError, match="run_id"):
        compiler.compile(
            RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
            player_summary=valid_summary(),
            deterministic_report="# facts",
            memory_context_binding=context_binding.model_copy(
                update={"run_id": "different_run"}
            ),
        )


def test_compiler_builds_canonical_skill_input_binding_and_runtime_request():
    calls = 0

    def run_id_factory() -> str:
        nonlocal calls
        calls += 1
        return "review_product_vertical"

    request = RecentReviewProductRequest(
        riot_id="DemoPlayer#TEST",
        count=20,
        queue=None,
        focus="vision",
    )
    catalog = SkillCatalog.from_directory("skills")
    compiled = RecentReviewRuntimeRequestCompiler(
        catalog,
        run_id_factory=run_id_factory,
    ).compile(
        request,
        player_summary=valid_summary(),
        deterministic_report="  # Deterministic facts  ",
    )

    assert calls == 1
    assert compiled.run_id == "review_product_vertical"
    execution = compiled.execution_request
    assert execution.user_utterance == (
        "typed-entrypoint reviews.recent focus=vision"
    )
    assert execution.input_payload == {
        "player_summary": valid_summary(),
        "deterministic_report": "# Deterministic facts",
        "focus": "vision",
    }
    expected_input = RecentFormReviewInput.model_validate(execution.input_payload)
    assert expected_input.focus == "vision"
    assert execution.input_artifacts.run_id == compiled.run_id

    validated = SkillExecutionBoundary(catalog).validate(execution)
    assert validated.run_id == compiled.run_id
    assert validated.typed_input == expected_input
    assert validated.input_artifacts == execution.input_artifacts


def test_existing_boundary_rejects_compiled_content_or_digest_tampering():
    catalog = SkillCatalog.from_directory("skills")
    compiled = _compile(catalog=catalog, run_id="review_product_tamper")
    execution = compiled.execution_request

    tampered_payload = dict(execution.input_payload)
    tampered_payload["deterministic_report"] = "different facts"
    tampered_execution = execution.model_copy(
        update={"input_payload": tampered_payload}
    )
    with pytest.raises(SkillExecutionBoundaryError, match="binding mismatch"):
        SkillExecutionBoundary(catalog).validate(tampered_execution)

    tampered_binding = execution.input_artifacts.model_copy(
        update={
            "deterministic_report": (
                execution.input_artifacts.deterministic_report.model_copy(
                    update={"sha256": "0" * 64}
                )
            )
        }
    )
    tampered_execution = execution.model_copy(
        update={"input_artifacts": tampered_binding}
    )
    with pytest.raises(SkillExecutionBoundaryError, match="binding mismatch"):
        SkillExecutionBoundary(catalog).validate(tampered_execution)


def test_existing_boundary_rejects_post_compile_catalog_version_drift():
    catalog = SkillCatalog.from_directory("skills")
    compiled = _compile(catalog=catalog, run_id="review_product_version")
    recent = catalog.get("recent-form-review")
    single = catalog.get("single-match-review")
    assert recent is not None
    assert single is not None
    drifted_recent = replace(
        recent,
        manifest=recent.manifest.model_copy(update={"version": "9.9.9"}),
    )
    drifted_catalog = SkillCatalog(
        root=catalog.root,
        _skills=(drifted_recent, single),
    )

    with pytest.raises(SkillExecutionBoundaryError, match="version mismatch"):
        SkillExecutionBoundary(drifted_catalog).validate(
            compiled.execution_request
        )


def test_compiler_rejects_an_invalid_server_run_id():
    with pytest.raises(ProductRequestCompilationError, match="server run_id"):
        _compile(run_id="../client-controlled")


def test_compiler_uses_a_trusted_preallocated_run_id_without_calling_factory():
    compiler = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory("skills"),
        run_id_factory=lambda: (_ for _ in ()).throw(
            AssertionError("trusted run_id must bypass generation")
        ),
    )

    compiled = compiler.compile(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
        player_summary=valid_summary(),
        deterministic_report="# Facts",
        run_id="review_sql_preallocated",
    )

    assert compiled.run_id == "review_sql_preallocated"
    assert compiled.execution_request.input_artifacts.run_id == compiled.run_id


def test_compiler_rejects_an_invalid_trusted_run_id_before_generation():
    compiler = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory("skills"),
        run_id_factory=lambda: (_ for _ in ()).throw(
            AssertionError("invalid trusted run_id must not fall back to generation")
        ),
    )

    with pytest.raises(ProductRequestCompilationError, match="trusted run_id"):
        compiler.compile(
            RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
            player_summary=valid_summary(),
            deterministic_report="# Facts",
            run_id="../sql-run",
        )


def test_default_compiler_run_id_is_server_generated_and_portable():
    compiled = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory("skills")
    ).compile(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
        player_summary=valid_summary(),
        deterministic_report="# Facts",
    )

    assert compiled.run_id.startswith("review_")
    assert normalize_run_id(compiled.run_id) == compiled.run_id
