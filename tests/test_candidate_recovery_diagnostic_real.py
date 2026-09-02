"""Offline tests for the isolated v2 real-call composition seam."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.providers.models import ChatMessage, MessageRole
from app.evaluation.candidate_recovery_diagnostic_real import (
    FrozenCandidateContext,
    _load_frozen_context,
    run_candidate_recovery_real_call,
)


GIT_SHA = "0123456789abcdef0123456789abcdef01234567"
PLAN_CONTENT_SHA = "a" * 64
SNAPSHOT_SHA = "b" * 64


def _context() -> FrozenCandidateContext:
    return FrozenCandidateContext(
        messages=(
            # The body exists only in this in-memory test input.  The receipt
            # contract must never copy it to disk.
            ChatMessage(
                MessageRole.SYSTEM,
                "private system instructions",
            ),
            ChatMessage(
                MessageRole.USER,
                "private user request",
            ),
        ),
        input_plan_sha=GIT_SHA,
        input_plan_content_sha256=PLAN_CONTENT_SHA,
        prompt_context_snapshot_sha256=SNAPSHOT_SHA,
    )


def _raw_chunk(
    *,
    model: str | None = None,
    request_id: str | None = None,
    content: str | None = None,
    reasoning: str | None = None,
    finish_reason: str | None = None,
    usage=None,
    empty_choices: bool = False,
):
    if empty_choices:
        choices = []
    else:
        choices = [
            SimpleNamespace(
                delta=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning,
                    tool_calls=None,
                ),
                finish_reason=finish_reason,
            )
        ]
    return SimpleNamespace(
        model=model,
        id=request_id,
        choices=choices,
        usage=usage,
    )


def _usage(input_tokens: int = 20, output_tokens: int = 5):
    return SimpleNamespace(
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )


def _complete_chunks():
    return [
        _raw_chunk(
            model="glm-5.3-flash",
            request_id="request-1",
            content="private answer body",
        ),
        _raw_chunk(finish_reason="stop"),
        _raw_chunk(usage=_usage(), empty_choices=True),
    ]


def _candidate_chunks():
    return [
        _raw_chunk(
            model="glm-5.3-flash",
            request_id="request-2",
            content="",
            reasoning="private reasoning body",
        ),
        _raw_chunk(
            finish_reason="length",
            usage=_usage(input_tokens=20, output_tokens=8192),
        ),
    ]


class _FakeCompletions:
    def __init__(self, chunks):
        self.chunks = tuple(chunks)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.chunks)


class _FakeClient:
    def __init__(self, chunks):
        completions = _FakeCompletions(chunks)
        self.chat = SimpleNamespace(completions=completions)
        self.completions = completions


def _environment():
    return {
        "LLM_PROVIDER": "zhipu",
        "LLM_API_KEY": "private-api-key",
        "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
        "LLM_MODEL": "glm-5.3-flash",
    }


def test_confirmation_gate_reads_nothing_and_makes_no_client(tmp_path: Path):
    called = False

    def factory(**kwargs):
        nonlocal called
        called = True
        return _FakeClient(_complete_chunks())

    with pytest.raises(Exception, match="real_call_confirmation_required"):
        run_candidate_recovery_real_call(
            repository_root=tmp_path,
            implementation_sha=GIT_SHA,
            diagnostic_code_sha=GIT_SHA,
            output=tmp_path / "data/evaluation/results/provider_capabilities/result.json",
            client_factory=factory,
            environment_loader=lambda _: _environment(),
        )
    assert called is False


def test_wrong_case_is_rejected_before_client_creation(tmp_path: Path):
    called = False

    def factory(**kwargs):
        nonlocal called
        called = True
        return _FakeClient(_complete_chunks())

    wrong_case = FrozenCandidateContext(
        messages=_context().messages,
        input_plan_sha=GIT_SHA,
        input_plan_content_sha256=PLAN_CONTENT_SHA,
        prompt_context_snapshot_sha256=SNAPSHOT_SHA,
        case_id="other_case",
    )
    with pytest.raises(Exception, match="case_id_mismatch"):
        run_candidate_recovery_real_call(
            repository_root=tmp_path,
            implementation_sha=GIT_SHA,
            diagnostic_code_sha=GIT_SHA,
            output=tmp_path / "data/evaluation/results/provider_capabilities/result.json",
            confirm_real_call=True,
            client_factory=factory,
            environment_loader=lambda _: _environment(),
            context_loader=lambda _: wrong_case,
        )
    assert called is False


def test_real_seam_makes_one_stream_call_and_writes_body_free_receipt(tmp_path: Path):
    client = _FakeClient(_complete_chunks())

    report = run_candidate_recovery_real_call(
        repository_root=tmp_path,
        implementation_sha=GIT_SHA,
        diagnostic_code_sha=GIT_SHA,
        output=tmp_path / "data/evaluation/results/provider_capabilities/result.json",
        confirm_real_call=True,
        client_factory=lambda **kwargs: client,
        environment_loader=lambda _: _environment(),
        context_loader=lambda _: _context(),
    )

    assert report.external_calls == 1
    assert len(client.completions.calls) == 1
    payload = client.completions.calls[0]
    assert payload["model"] == "glm-5.3-flash"
    assert payload["stream"] is True
    assert payload["max_tokens"] == 8192
    assert payload["timeout"] == 90.0
    assert payload["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "max",
    }
    body = report.written.path.read_text(encoding="utf-8")
    assert "private answer body" not in body
    assert "private system instructions" not in body
    assert "private-api-key" not in body
    assert json.loads(body)["run_state"] == "complete_text"


def test_candidate_shape_is_recorded_without_a_second_request(tmp_path: Path):
    client = _FakeClient(_candidate_chunks())
    report = run_candidate_recovery_real_call(
        repository_root=tmp_path,
        implementation_sha=GIT_SHA,
        diagnostic_code_sha=GIT_SHA,
        output=tmp_path / "data/evaluation/results/provider_capabilities/result.json",
        confirm_real_call=True,
        client_factory=lambda **kwargs: client,
        environment_loader=lambda _: _environment(),
        context_loader=lambda _: _context(),
    )

    assert len(client.completions.calls) == 1
    assert report.receipt.run_state == "candidate_eligible"
    assert report.receipt.recovery_skip_reason == "activation_disabled"
    assert report.receipt.execution_allowed is False
    assert len(report.receipt.attempts) == 1


def test_frozen_context_loader_uses_committed_bytes_for_crlf_checkout():
    context = _load_frozen_context(Path(__file__).parents[1])
    assert context.case_id == "flash_gate_baseline_01"
    assert [message.role.value for message in context.messages] == ["system", "user"]
    assert context.input_plan_content_sha256 == (
        "e5daa6ccd05c8c71a98ec5ce7edeedb6069e9f9a84bca00628c1b08a656bf784"
    )
    assert len(context.input_plan_sha) == 40
