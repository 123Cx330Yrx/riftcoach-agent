from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.evaluation.glm53_flash_output_budget_calibration as calibration
from app.evaluation.glm53_flash_capability_matrix import MatrixSourceIdentity
from app.providers.models import ChatMessage, MessageRole


IMPLEMENTATION_SHA = "e" * 40
DIAGNOSTIC_SHA = "a" * 40


def _context() -> calibration.FrozenContextSnapshot:
    return calibration.FrozenContextSnapshot(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "private system context"),
            ChatMessage(MessageRole.USER, "private user context"),
        ),
        input_plan_sha256="b" * 64,
        prompt_context_snapshot_sha256="c" * 64,
    )


def _raw_response(
    *,
    content: str | None = "visible answer",
    finish_reason: str = "stop",
    input_tokens: int = 10,
    output_tokens: int = 4,
):
    return SimpleNamespace(
        id="secret-request-id",
        model="glm-5.3-flash",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    reasoning_content="private reasoning",
                    tool_calls=None,
                ),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        ),
    )


class _Completions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _Client:
    def __init__(self, responses):
        self.completions = _Completions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _identity() -> MatrixSourceIdentity:
    return MatrixSourceIdentity(
        head_sha="d" * 40,
        origin_main_sha="f" * 40,
        worktree_dirty=True,
        worktree_patch_sha256="1" * 64,
    )


def _environment(_path):
    return {
        "LLM_API_KEY": "secret-key",
        "LLM_BASE_URL": calibration.BASE_URL,
        "LLM_MODEL": calibration.MODEL,
        "LLM_PROVIDER": "zhipu",
    }


def _run(tmp_path: Path, responses, *, probe_limit=3, probe_ordinal=None):
    client = _Client(responses)
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "calibration.json"
    )
    identity = _identity()
    report = calibration.run_output_budget_calibration(
        repository_root=tmp_path,
        implementation_sha=IMPLEMENTATION_SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        output=output,
        confirm_real_call=True,
        environment_loader=_environment,
        client_factory=lambda **_: client,
        context_loader=lambda _root: _context(),
        source_identity_loader=lambda _root: identity,
        now=lambda: datetime(2026, 9, 1, tzinfo=timezone.utc),
        probe_limit=probe_limit,
        probe_ordinal=probe_ordinal,
    )
    return report, client, output


def test_calibration_compares_caps_without_retaining_bodies(tmp_path):
    report, client, output = _run(
        tmp_path,
        [
            _raw_response(content="visible answer"),
            _raw_response(content=None, finish_reason="length", output_tokens=8),
            _raw_response(content=None, finish_reason="length", output_tokens=12),
        ],
    )

    assert report.calls_attempted == 3
    assert [row.variant for row in report.observations] == [
        "frozen_low_2048_nonstream",
        "frozen_low_8192_nonstream",
        "frozen_max_8192_nonstream",
    ]
    assert report.observations[0].visible_content_observed is True
    assert report.observations[1].visible_content_observed is False
    assert report.observations[2].visible_content_observed is False
    assert report.verdicts.visible_content_observed is True
    calls = client.completions.calls
    assert [call["max_tokens"] for call in calls] == [2048, 8192, 8192]
    assert [call["stream"] for call in calls] == [False, False, False]
    assert [call["extra_body"]["reasoning_effort"] for call in calls] == [
        "low",
        "low",
        "max",
    ]

    payload = json.loads(output.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for secret in (
        "private system context",
        "private user context",
        "private reasoning",
        "secret-key",
        "secret-request-id",
    ):
        assert secret not in encoded
    assert "messages" not in payload
    assert "content" not in payload
    output.unlink()


def test_timeout_does_not_retry_and_next_cap_is_still_observed(tmp_path):
    timeout = type("ReadTimeout", (Exception,), {})()
    report, client, output = _run(
        tmp_path, [timeout, _raw_response(), _raw_response(content=None, finish_reason="length")]
    )

    assert len(client.completions.calls) == 3
    assert report.observations[0].status == "failed"
    assert report.observations[0].error_code == "timeout"
    assert report.observations[1].status == "observed"
    assert report.observations[2].status == "observed"
    assert report.verdicts.transport_reachable is True
    output.unlink()


def test_authentication_failure_stops_remaining_cap(tmp_path):
    error = type("AuthenticationError", (Exception,), {})()
    report, client, output = _run(tmp_path, [error])

    assert len(client.completions.calls) == 1
    assert [row.status for row in report.observations] == ["failed", "skipped", "skipped"]
    assert report.observations[1].skip_reason == "authentication_failed"
    assert report.observations[2].skip_reason == "authentication_failed"
    output.unlink()


def test_probe_limit_preserves_fixed_shape_and_skips_unrun_suffix(tmp_path):
    report, client, output = _run(
        tmp_path,
        [_raw_response(content="visible answer")],
        probe_limit=1,
    )

    assert len(client.completions.calls) == 1
    assert report.calls_attempted == 1
    assert [row.status for row in report.observations] == [
        "observed",
        "skipped",
        "skipped",
    ]
    assert [row.skip_reason for row in report.observations] == [
        None,
        "probe_limit_exhausted",
        "probe_limit_exhausted",
    ]
    output.unlink()


def test_probe_selection_runs_only_requested_variant(tmp_path):
    report, client, output = _run(
        tmp_path,
        [_raw_response(content="selected answer")],
        probe_ordinal=2,
    )

    assert len(client.completions.calls) == 1
    assert report.calls_attempted == 1
    assert [row.status for row in report.observations] == [
        "skipped",
        "observed",
        "skipped",
    ]
    assert [row.skip_reason for row in report.observations] == [
        "probe_selection_excluded",
        None,
        "probe_selection_excluded",
    ]
    assert client.completions.calls[0]["max_tokens"] == 8192
    assert client.completions.calls[0]["extra_body"]["reasoning_effort"] == "low"
    output.unlink()


def test_confirmation_and_immutable_output_are_required(tmp_path):
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "calibration.json"
    )
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        calibration.run_output_budget_calibration(
            repository_root=tmp_path,
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=False,
            context_loader=lambda _root: _context(),
            source_identity_loader=lambda _root: _identity(),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        calibration.run_output_budget_calibration(
            repository_root=tmp_path,
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=True,
            environment_loader=_environment,
            client_factory=lambda **_: _Client([]),
            context_loader=lambda _root: _context(),
            source_identity_loader=lambda _root: _identity(),
        )
    assert output.read_text(encoding="utf-8") == "keep"
    output.unlink()


