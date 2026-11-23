from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.evaluation.glm53_flash_transport_generation_split_diagnostic as split
from app.agent.context import ContextBundle
from app.evaluation.glm53_flash_capability_matrix import MatrixSourceIdentity
from app.providers.models import ChatMessage, MessageRole


IMPLEMENTATION_SHA = "e25c3579e8c37724b76505ad028e066a7e28e654"
DIAGNOSTIC_SHA = "a" * 40


def _context() -> split.FrozenContextSnapshot:
    return split.FrozenContextSnapshot(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "private system context"),
            ChatMessage(MessageRole.USER, "private user context"),
        ),
        input_plan_sha256="b" * 64,
        prompt_context_snapshot_sha256="c" * 64,
    )


def _raw_response(
    *,
    content: str | None = "RIFTCOACH_TRANSPORT_OK",
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


def _stream_chunk(*, content: str | None = "first", choices: bool = True):
    return SimpleNamespace(
        id="secret-stream-id",
        model="glm-5.3-flash",
        choices=(
            [
                SimpleNamespace(
                    finish_reason=None,
                    delta=SimpleNamespace(
                        content=content,
                        reasoning_content="private stream reasoning",
                        tool_calls=None,
                    ),
                )
            ]
            if choices
            else []
        ),
        usage=None,
    )


class _Stream:
    def __init__(self, first=None, error: Exception | None = None):
        self.first = first
        self.error = error
        self.closed = False
        self.used = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.error is not None:
            raise self.error
        if self.used:
            raise StopIteration
        self.used = True
        return self.first

    def close(self):
        self.closed = True


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
        origin_main_sha="e" * 40,
        worktree_dirty=True,
        worktree_patch_sha256="f" * 64,
    )


def _environment(_path):
    return {
        "LLM_API_KEY": "secret-key",
        "LLM_BASE_URL": split.BASE_URL,
        "LLM_MODEL": split.MODEL,
        "LLM_PROVIDER": "zhipu",
    }


def _run(tmp_path, responses):
    client = _Client(responses)
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "split.json"
    )
    identity = _identity()
    report = split.run_transport_generation_split_diagnostic(
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
    )
    return report, client, output


def test_split_records_three_body_free_variants_and_closes_stream(tmp_path):
    stream = _Stream(_stream_chunk())
    report, client, output = _run(
        tmp_path,
        [_raw_response(), _raw_response(content="short answer"), stream],
    )

    assert report.calls_attempted == 3
    assert [row.variant for row in report.observations] == [
        "minimal_transport_control",
        "frozen_short_nonstream",
        "frozen_stream_first_chunk",
    ]
    assert report.observations[0].status == "observed"
    assert report.observations[0].marker_match is True
    assert report.observations[1].generation_observed is True
    assert report.observations[2].first_chunk_observed is True
    assert report.verdicts.transport_reachable is True
    assert report.verdicts.minimal_control_observed is True
    assert report.verdicts.stream_first_chunk_observed is True
    assert report.verdicts.production_admitted is False
    assert stream.closed is True

    calls = client.completions.calls
    assert [call["stream"] for call in calls] == [False, False, True]
    assert calls[0]["max_tokens"] == split.MINIMAL_MAX_TOKENS
    assert calls[1]["max_tokens"] == split.SHORT_MAX_TOKENS
    assert calls[2]["max_tokens"] == split.STREAM_MAX_TOKENS
    assert calls[0]["extra_body"] == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    }
    assert calls[2]["extra_body"]["thinking"]["type"] == "enabled"

    payload = json.loads(output.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for secret in (
        "private system context",
        "private user context",
        "private reasoning",
        "private stream reasoning",
        "secret-key",
        "secret-request-id",
        "secret-stream-id",
    ):
        assert secret not in encoded
    assert "messages" not in payload
    assert "content" not in payload
    output.unlink()


def test_stream_first_chunk_timeout_is_distinguished_from_open_failure(tmp_path):
    stream = _Stream(error=type("ReadTimeout", (Exception,), {})())
    report, _client, output = _run(
        tmp_path,
        [_raw_response(), _raw_response(content="short answer"), stream],
    )

    observation = report.observations[2]
    assert observation.stream_opened is True
    assert observation.first_chunk_observed is False
    assert observation.error_stage == "first_chunk"
    assert observation.sdk_error_class == "timeout"
    assert observation.error_code == "timeout"
    assert report.verdicts.stream_first_chunk_observed is False
    output.unlink()


def test_authentication_failure_stops_remaining_variants_without_retry(tmp_path):
    error = type("AuthenticationError", (Exception,), {})()
    report, client, output = _run(tmp_path, [error])

    assert len(client.completions.calls) == 1
    assert report.calls_attempted == 1
    assert report.observations[0].error_code == "authentication_failed"
    assert [row.status for row in report.observations] == [
        "failed",
        "skipped",
        "skipped",
    ]
    assert report.observations[1].skip_reason == "authentication_failed"
    output.unlink()


def test_confirmation_and_immutable_output_are_required(tmp_path):
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "split.json"
    )
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        split.run_transport_generation_split_diagnostic(
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
        split.run_transport_generation_split_diagnostic(
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


