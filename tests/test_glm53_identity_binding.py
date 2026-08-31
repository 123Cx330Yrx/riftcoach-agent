from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.evaluation.glm53_domain_gate as gate
from app.evaluation.glm53_domain_gate import (
    G53_3_CURRENT_PROTOCOL_RESULT_PATH,
    GLM53DomainGateOptions,
    GLM53ABIdentityBinding,
    build_glm53_ab_identity_binding,
    build_glm53_preflight,
    run_cli,
)


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_SHA = "f0d5ee270f9dac8137368239b85471eca3edf570"
EVIDENCE_SHA = "407ee7559c46a84e82f81d5f43f435ad89013949"
EVIDENCE_PATH = G53_3_CURRENT_PROTOCOL_RESULT_PATH.as_posix()


@pytest.fixture
def historical_evidence_checkout(monkeypatch):
    """Run historical A→B fixtures without weakening the production guard.

    The real gate must require the running checkout to be B.  These tests
    intentionally inspect the already-published f0d5→407 pair while the
    test suite itself is checked out at a newer implementation commit, so
    only the private Git-head reader is replaced in this fixture.
    """

    monkeypatch.setattr(gate, "_read_head_sha", lambda _root: EVIDENCE_SHA)


def _binding(**overrides):
    values = {
        "project_root": ROOT,
        "protocol_result_path": G53_3_CURRENT_PROTOCOL_RESULT_PATH,
        "implementation_sha": IMPLEMENTATION_SHA,
        "implementation_public_ci_run_id": 33372880364,
        "evidence_commit_sha": EVIDENCE_SHA,
        "evidence_public_ci_run_id": 33373561017,
        "confirm_implementation_ci_success": True,
        "confirm_evidence_ci_success": True,
        "current_head_sha": EVIDENCE_SHA,
    }
    values.update(overrides)
    return build_glm53_ab_identity_binding(**values)


def test_ab_binding_separates_implementation_and_evidence_commits(
    historical_evidence_checkout,
):
    binding = _binding()

    assert binding.implementation_sha == IMPLEMENTATION_SHA
    assert binding.protocol_code_sha == IMPLEMENTATION_SHA
    assert binding.evidence_commit_sha == EVIDENCE_SHA
    assert binding.evidence_public_ci_sha == EVIDENCE_SHA
    # This is the canonical LF digest from the committed B blob.  A CRLF
    # checkout is normalized by the gate before hashing.
    assert binding.protocol_result_sha256 == (
        "1fda5b03d74514fe59c835e5783ff66bb4f16355f32c2adcf82a069bcf70984c"
    )


def test_ab_binding_checks_real_git_parent_and_committed_blob(
    historical_evidence_checkout,
):
    binding = _binding()

    assert binding.evidence_paths == (EVIDENCE_PATH,)


def test_ab_binding_rejects_same_commit_for_a_and_b():
    with pytest.raises(ValueError, match="distinct"):
        GLM53ABIdentityBinding(
            implementation_sha=IMPLEMENTATION_SHA,
            implementation_public_ci_sha=IMPLEMENTATION_SHA,
            implementation_public_ci_run_id=1,
            implementation_public_ci_success_confirmed=True,
            protocol_code_sha=IMPLEMENTATION_SHA,
            evidence_commit_sha=IMPLEMENTATION_SHA,
            evidence_public_ci_sha=IMPLEMENTATION_SHA,
            evidence_public_ci_run_id=2,
            evidence_public_ci_success_confirmed=True,
            protocol_result_path=EVIDENCE_PATH,
            protocol_result_sha256="a" * 64,
            evidence_paths=(EVIDENCE_PATH,),
        )


def test_ab_binding_rejects_a_code_change_in_evidence_commit(
    monkeypatch, historical_evidence_checkout
):
    monkeypatch.setattr(
        gate,
        "_read_commit_diff_paths",
        lambda _root, _implementation, _evidence: (
            EVIDENCE_PATH,
            "app/evaluation/glm53_domain_gate.py",
        ),
    )
    with pytest.raises(ValueError, match="outside the declared evidence set"):
        _binding()


def test_ab_binding_rejects_protocol_result_not_present_in_evidence_commit(
    historical_evidence_checkout,
):
    with pytest.raises(ValueError, match="does not contain"):
        _binding(
            protocol_result_path=(
                ROOT
                / "data/evaluation/results/provider_capabilities/"
                "evidence-file-that-was-not-added.json"
            ),
        )


def test_ab_preflight_emits_schema_1_1_and_rechecks_the_binding(
    historical_evidence_checkout,
):
    binding = _binding()
    prepared = build_glm53_preflight(
        project_root=ROOT,
        dataset_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json",
        input_plan_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json",
        snapshot_path=ROOT / "data/evaluation/contracts/glm53_flash_recent_form_prompt_context_v1.json",
        protocol_result_path=ROOT / EVIDENCE_PATH,
        code_sha=IMPLEMENTATION_SHA,
        public_ci_sha=IMPLEMENTATION_SHA,
        confirm_public_ci_success=True,
        confirm_evidence_ci_success=True,
        identity_binding=binding,
        current_head_sha=EVIDENCE_SHA,
    )

    assert prepared.admission.schema_version == "1.1"
    assert prepared.admission.identity_binding == binding
    assert prepared.admission.code_sha == IMPLEMENTATION_SHA


def test_ab_preflight_requires_current_evidence_head(
    historical_evidence_checkout,
):
    binding = _binding()
    with pytest.raises(ValueError, match="current evidence commit B"):
        build_glm53_preflight(
            project_root=ROOT,
            dataset_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json",
            input_plan_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json",
            snapshot_path=ROOT / "data/evaluation/contracts/glm53_flash_recent_form_prompt_context_v1.json",
            protocol_result_path=ROOT / EVIDENCE_PATH,
            code_sha=IMPLEMENTATION_SHA,
            public_ci_sha=IMPLEMENTATION_SHA,
            confirm_public_ci_success=True,
            confirm_evidence_ci_success=True,
            identity_binding=binding,
        )


def test_schema_1_1_admission_cannot_downgrade_runtime_profile(
    historical_evidence_checkout,
):
    binding = _binding()
    prepared = build_glm53_preflight(
        project_root=ROOT,
        dataset_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json",
        input_plan_path=ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json",
        snapshot_path=ROOT / "data/evaluation/contracts/glm53_flash_recent_form_prompt_context_v1.json",
        protocol_result_path=ROOT / EVIDENCE_PATH,
        code_sha=IMPLEMENTATION_SHA,
        public_ci_sha=IMPLEMENTATION_SHA,
        confirm_public_ci_success=True,
        confirm_evidence_ci_success=True,
        identity_binding=binding,
        current_head_sha=EVIDENCE_SHA,
    )
    payload = prepared.admission.model_dump()
    payload.update(
        {
            "runtime_profile_id": "legacy-manifest-budget",
            "runtime_profile_version": "legacy",
            "max_output_tokens_per_request": 1024,
        }
    )
    with pytest.raises(ValueError, match="specialised Flash runtime profile"):
        gate.GLM53FreshDomainAdmission(**payload)


def test_ab_binding_rejects_a_tampered_protocol_digest(
    historical_evidence_checkout,
):
    with pytest.raises(ValueError, match="expected identity"):
        _binding(expected_protocol_result_sha256="a" * 64)


def test_ab_binding_rejects_unsafe_declared_evidence_path(
    historical_evidence_checkout,
):
    with pytest.raises(ValueError, match="capability results tree"):
        _binding(
            evidence_paths=(
                EVIDENCE_PATH,
                "data/evaluation/results/provider_capabilities/../x.json",
            )
        )


def test_ab_binding_requires_the_supplied_head_to_match_git_head():
    with pytest.raises(ValueError, match="supplied checkout identity"):
        _binding(current_head_sha=IMPLEMENTATION_SHA)


def test_direct_parent_rejects_a_merge_evidence_commit(monkeypatch):
    merge_parent = "c" * 40

    def fake_run(command, **_kwargs):
        if command[1] == "merge-base":
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        if command[1] == "rev-list":
            return SimpleNamespace(
                returncode=0,
                stdout=f"{EVIDENCE_SHA} {IMPLEMENTATION_SHA} {merge_parent}\n",
                stderr="",
            )
        raise AssertionError(f"unexpected git command: {command}")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="direct child"):
        gate._require_direct_evidence_parent(
            ROOT, IMPLEMENTATION_SHA, EVIDENCE_SHA
        )


def test_commit_diff_rejects_modifying_existing_evidence(monkeypatch):
    monkeypatch.setattr(gate, "_require_direct_evidence_parent", lambda *_args: None)

    def fake_run(command, **_kwargs):
        assert command[1] == "diff"
        return SimpleNamespace(
            returncode=0,
            stdout=f"M\t{EVIDENCE_PATH}\n",
            stderr="",
        )

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="only add"):
        gate._read_commit_diff_paths(ROOT, IMPLEMENTATION_SHA, EVIDENCE_SHA)


def test_ab_binding_rejects_working_protocol_tamper(
    monkeypatch, historical_evidence_checkout
):
    monkeypatch.setattr(gate, "_file_sha256", lambda _path: "a" * 64)
    with pytest.raises(ValueError, match="working protocol bytes"):
        _binding()


def test_ab_binding_requires_both_ci_confirmations(
    historical_evidence_checkout,
):
    with pytest.raises(ValueError, match="CI confirmations"):
        _binding(confirm_evidence_ci_success=False)
    with pytest.raises(ValueError, match="CI confirmations"):
        _binding(confirm_evidence_ci_success=1)


def test_direct_parent_rejects_a_non_ancestor(monkeypatch):
    def fake_run(command, **_kwargs):
        assert command[1] == "merge-base"
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="descend"):
        gate._require_direct_evidence_parent(
            ROOT, IMPLEMENTATION_SHA, EVIDENCE_SHA
        )


def test_g53_7_cli_refuses_to_run_without_explicit_a_b_identities():
    with pytest.raises(ValueError, match="requires explicit implementation commit A"):
        run_cli(
            GLM53DomainGateOptions(confirm_real_call=False, preflight_only=True),
            repository_root=ROOT,
            code_sha_reader=lambda _root: EVIDENCE_SHA,
            environment_loader=lambda _root: pytest.fail("environment must not load"),
        )


def test_g53_7_cli_builds_ab_preflight_before_environment(
    historical_evidence_checkout,
):
    admission = run_cli(
        GLM53DomainGateOptions(
            confirm_real_call=False,
            preflight_only=True,
            public_ci_sha=IMPLEMENTATION_SHA,
            confirm_public_ci_success=True,
            implementation_sha=IMPLEMENTATION_SHA,
            implementation_public_ci_run_id=33372880364,
            evidence_commit_sha=EVIDENCE_SHA,
            evidence_public_ci_run_id=33373561017,
            confirm_evidence_ci_success=True,
        ),
        repository_root=ROOT,
        code_sha_reader=lambda _root: EVIDENCE_SHA,
        environment_loader=lambda _root: pytest.fail("environment must not load"),
    )

    assert admission.schema_version == "1.1"
    assert admission.identity_binding is not None
    assert admission.external_provider_calls == 0
