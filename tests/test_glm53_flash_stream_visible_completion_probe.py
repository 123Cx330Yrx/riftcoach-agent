from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.evaluation.glm53_flash_stream_visible_completion_probe as probe
from app.evaluation.glm53_flash_capability_matrix import MatrixSourceIdentity
from app.providers.models import ChatMessage, MessageRole


IMPLEMENTATION_SHA = "e" * 40
DIAGNOSTIC_SHA = "a" * 40


def _context() -> probe.FrozenContextSnapshot:
    return probe.FrozenContextSnapshot(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "private system context"),
            ChatMessage(MessageRole.USER, "private user context"),
        ),
        input_plan_sha256="b" * 64,
        prompt_context_snapshot_sha256="c" * 64,
    )


def _chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    finish_reason: str | None = None,
    choices: object = "default",
    model: str | None = "glm-5.3-flash",
    request_id: str | None = "secret-request-id",
    usage: object | None = None,
):
    if choices != "default":
        return SimpleNamespace(
            id=request_id,
            model=model,
            choices=choices,
            usage=usage,
        )
    return SimpleNamespace(
        id=request_id,
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                delta=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning,
                    tool_calls=None,
                ),
            )
        ],
        usage=usage,
    )


class _Stream:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.next_calls = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        self.next_calls += 1
        if not self._chunks:
            raise StopIteration
        item = self._chunks.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        self.closed = True


class _Completions:
    def __init__(self, stream):
        self.stream = stream
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.stream


class _Client:
    def __init__(self, stream):
        completions = _Completions(stream)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


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
        "LLM_BASE_URL": probe.BASE_URL,
        "LLM_MODEL": probe.MODEL,
        "LLM_PROVIDER": "zhipu",
    }


def _run(tmp_path: Path, stream, *, probe_ordinal=1):
    client = _Client(stream)
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "probe.json"
    )
    report = probe.run_stream_visible_completion_probe(
        repository_root=tmp_path,
        implementation_sha=IMPLEMENTATION_SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        output=output,
        confirm_real_call=True,
        environment_loader=_environment,
        client_factory=lambda **_: client,
        context_loader=lambda _root: _context(),
        source_identity_loader=lambda _root: _identity(),
        now=lambda: datetime(2026, 9, 1, tzinfo=timezone.utc),
        probe_ordinal=probe_ordinal,
    )
    return report, client, output


def test_stops_after_first_visible_content_and_closes_stream(tmp_path):
    stream = _Stream(
        [
            _chunk(reasoning="private reasoning"),
            _chunk(content=" visible answer "),
            _chunk(content="must not be consumed", finish_reason="stop"),
        ]
    )
    report, client, output = _run(tmp_path, stream)

    row = report.observations[0]
    assert len(client.completions.calls) == 1
    assert stream.closed is True
    assert stream.next_calls == 2
    assert row.status == "observed"
    assert row.visible_content_observed is True
    assert row.stopped_after_visible_content is True
    assert row.terminal_observed is False
    assert row.usage_state == "missing"
    assert report.resources.within_token_budget is None
    assert row.first_visible_content_latency_ms is not None
    assert row.reasoning_chunk_count == 1
    assert row.content_chunk_count == 1
    assert client.completions.calls[0]["stream"] is True
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": True},
        "reasoning_effort": "low",
    }

    payload = json.loads(output.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for secret in (
        "private system context",
        "private user context",
        "private reasoning",
        "secret-key",
        "secret-request-id",
        "visible answer",
    ):
        assert secret not in encoded
    assert "messages" not in payload
    assert "content" not in payload
    output.unlink()


def test_terminal_without_visible_content_keeps_usage_if_present(tmp_path):
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=8)
    stream = _Stream(
        [
            _chunk(reasoning="private reasoning"),
            _chunk(finish_reason="length", usage=usage),
        ]
    )
    report, _client, output = _run(tmp_path, stream)
    row = report.observations[0]
    assert row.status == "observed"
    assert row.visible_content_observed is False
    assert row.terminal_observed is True
    assert row.stop_reason == "terminal_without_visible_content"
    assert row.finish_reason == "length"
    assert row.usage_state == "valid"
    assert row.input_tokens == 10
    assert row.output_tokens == 8
    output.unlink()


def test_read_timeout_is_fail_closed_and_closes_stream(tmp_path):
    timeout = type("ReadTimeout", (Exception,), {})()
    stream = _Stream([_chunk(reasoning="private reasoning"), timeout])
    report, _client, output = _run(tmp_path, stream)
    row = report.observations[0]
    assert row.status == "failed"
    assert row.error_code == "timeout"
    assert row.stop_reason == "read_timeout"
    assert row.stream_opened is True

    assert row.first_chunk_observed is True
    assert stream.closed is True
    output.unlink()


@pytest.mark.parametrize(
    "bad_chunk",
    [
        _chunk(choices=[SimpleNamespace(delta=None, finish_reason=None)]),
        _chunk(choices=[SimpleNamespace(delta=SimpleNamespace(content=7), finish_reason=None)]),
    ],
)
def test_malformed_chunk_is_rejected(tmp_path, bad_chunk):
    stream = _Stream([bad_chunk])
    report, _client, output = _run(tmp_path, stream)
    row = report.observations[0]
    assert row.status == "failed"
    assert row.error_code == "malformed_chunk"
    assert stream.closed is True
    output.unlink()


def test_second_clear_thinking_shape_is_selected_without_extra_call(tmp_path):
    stream = _Stream([_chunk(content="visible answer")])
    report, client, output = _run(tmp_path, stream, probe_ordinal=2)
    assert len(client.completions.calls) == 1
    assert [row.status for row in report.observations] == ["skipped", "observed"]
    assert report.observations[0].skip_reason == "probe_selection_excluded"
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "low",
    }
    output.unlink()


def test_confirmation_and_immutable_output_are_required(tmp_path):
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "probe.json"
    )
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        probe.run_stream_visible_completion_probe(
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
        probe.run_stream_visible_completion_probe(
            repository_root=tmp_path,
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=True,
            environment_loader=_environment,
            client_factory=lambda **_: _Client(_Stream([])),
            context_loader=lambda _root: _context(),
            source_identity_loader=lambda _root: _identity(),
        )
    assert output.read_text(encoding="utf-8") == "keep"
    output.unlink()
