"""Offline safety coverage for the controlled live launcher."""

import json
import socket
import sys

import pytest

from scripts.reviewer_profile_live_launcher import (
    MODEL_PROFILE,
    NETWORK_PROFILE,
    LiveLaunchError,
    LivePreflight,
    run_live_once,
    validate_preflight,
)


HEAD = "a" * 40
SECRET = "launcher-secret-must-not-leak"


@pytest.fixture
def preflight(tmp_path):
    ci_proof = tmp_path / "ci-proof.json"
    ci_proof.write_text(
        json.dumps({"head": HEAD, "run": "38500000000", "status": "completed", "conclusion": "success"}),
        encoding="utf-8",
    )
    return LivePreflight(
        group="GPT-pro",
        operator=tmp_path / "new-run",
        primary="primary-principal",
        independent="independent-principal",
        expected_head=HEAD,
        ci_run="38500000000",
        ci_head=HEAD,
        ci_status="success",
        network_profile=NETWORK_PROFILE,
        network_ready=True,
        model_profile=MODEL_PROFILE,
        python_path=sys.executable,
        codex_executable=sys.executable,
        ci_proof=ci_proof,
    )


@pytest.fixture
def business():
    return {"messages": [], "tools": [], "tool_choice": "auto", "response_contract": None}


def test_preflight_is_local_and_does_not_touch_network_or_filesystem(monkeypatch, preflight):
    def forbidden(*args, **kwargs):
        raise AssertionError("network probe must not run")

    monkeypatch.setattr(socket, "socket", forbidden)
    checked = validate_preflight(preflight, current_head=HEAD, git_clean=True)
    assert checked.operator == preflight.operator
    assert not checked.operator.exists()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("group", "auto", "group_invalid"),
        ("primary", "", "primary_required"),
        ("independent", "primary-principal", "review_principals_must_differ"),
        ("expected_head", "b" * 40, "head_mismatch"),
        ("ci_head", "b" * 40, "ci_head_mismatch"),
        ("ci_status", "queued", "ci_not_green"),
        ("network_profile", "proxy", "network_preflight_failed"),
        ("network_ready", False, "network_preflight_failed"),
        ("model_profile", "chat-completions", "model_profile_mismatch"),
    ],
)
def test_preflight_rejects_mismatch(preflight, field, value, code):
    values = {**preflight.__dict__, field: value}
    with pytest.raises(LiveLaunchError, match=code):
        validate_preflight(LivePreflight(**values), current_head=HEAD, git_clean=True)


def test_preflight_rejects_existing_run_claim_or_incomplete_batch(tmp_path, preflight):
    preflight.operator.mkdir()
    (preflight.operator / "claims").mkdir()
    with pytest.raises(LiveLaunchError, match="existing_run_or_incomplete_batch"):
        validate_preflight(preflight, current_head=HEAD, git_clean=True)


def test_live_once_reads_key_and_passes_it_to_sender_without_public_logging(
    capfd, preflight, business
):
    calls = []

    def sender(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": False, "code": "cancelled", "qualified": False}

    result = run_live_once(
        business,
        preflight,
        read_key=lambda prompt: SECRET,
        sender=sender,
        current_head=HEAD,
        git_clean=True,
    )
    result_output = capfd.readouterr().out + capfd.readouterr().err
    assert result["code"] == "cancelled"
    assert result["publication_allowed"] is False
    assert result["batch_bound"] is False
    assert calls[0][1]["api_key"] == SECRET
    assert calls[0][1]["profile"].group == "GPT-pro"
    assert calls[0][1]["directory"] == preflight.operator
    assert SECRET not in result_output
    assert not preflight.operator.exists()


def test_existing_run_is_rejected_before_key_prompt(preflight):
    preflight.operator.mkdir()
    prompted = []
    with pytest.raises(LiveLaunchError, match="existing_run_or_incomplete_batch"):
        run_live_once(
            {},
            preflight,
            read_key=lambda prompt: prompted.append(prompt) or SECRET,
            sender=lambda *args, **kwargs: pytest.fail("sender must not run"),
            current_head=HEAD,
            git_clean=True,
        )
    assert prompted == []


def test_sender_failure_is_fixed_and_secret_free(preflight, business, capfd):
    def sender(*args, **kwargs):
        raise RuntimeError(SECRET)

    with pytest.raises(LiveLaunchError, match="live_call_failed") as error:
        run_live_once(
            business,
            preflight,
            api_key=SECRET,
            sender=sender,
            current_head=HEAD,
            git_clean=True,
        )
    assert SECRET not in str(error.value)
    assert SECRET not in capfd.readouterr().out + capfd.readouterr().err


def test_sender_cannot_enable_qualification(preflight, business):
    def sender(*args, **kwargs):
        return {"ok": True, "code": "ok", "qualified": True, "publication_allowed": False}

    with pytest.raises(LiveLaunchError, match="qualification_boundary_violation"):
        run_live_once(business, preflight, api_key=SECRET, sender=sender, current_head=HEAD, git_clean=True)

