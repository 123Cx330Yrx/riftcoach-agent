from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.glm53_flash_candidate_profile_probe import (
    CandidateProfileProbeReport,
    run_candidate_profile_probe,
)
from app.evaluation.glm53_flash_transport_generation_split_diagnostic import (
    FrozenContextSnapshot,
)
from app.providers.models import ChatMessage, MessageRole


ROOT = Path(__file__).parents[1]
IMPLEMENTATION_SHA = "a" * 40
DIAGNOSTIC_SHA = "b" * 40


def _context(_root: Path) -> FrozenContextSnapshot:
    return FrozenContextSnapshot(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "只回答一个短句。"),
            ChatMessage(MessageRole.USER, "回答 RQ221。"),
        ),
        input_plan_sha256="1" * 64,
        prompt_context_snapshot_sha256="2" * 64,
    )


def _raw_response(*, content: str | None = "完成", finish_reason: str = "stop"):
    return SimpleNamespace(
        id="candidate-probe-request-id",
        model="glm-5.3-flash",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    reasoning_content="内部推理",
                    tool_calls=[],
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=8),
    )


class _Completions:
    def __init__(self, result: object):
        self.result = result
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class _Client:
    def __init__(self, result: object):
        completions = _Completions(result)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


def _env(_env_file: Path | None):
    return {
        "LLM_PROVIDER": "zhipu",
        "LLM_API_KEY": "secret-never-recorded",
        "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
        "LLM_MODEL": "glm-5.3-flash",
    }


def test_probe_requires_explicit_confirmation_before_loading_environment(tmp_path: Path):
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_candidate_profile_probe(
            repository_root=tmp_path,
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            confirm_real_call=False,
            environment_loader=lambda _path: pytest.fail("environment loaded"),
        )


def test_probe_uses_candidate_payload_and_writes_body_free_receipt(tmp_path: Path):
    clients: list[_Client] = []

    def client_factory(**kwargs):
        assert kwargs["max_retries"] == 0
        assert kwargs["timeout"] == 120.0
        client = _Client(_raw_response())
        clients.append(client)
        return client

    output = tmp_path / "data/evaluation/results/provider_capabilities/probe.json"
    report = run_candidate_profile_probe(
        repository_root=tmp_path,
        implementation_sha=IMPLEMENTATION_SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        output=output,
        confirm_real_call=True,
        environment_loader=_env,
        client_factory=client_factory,
        context_loader=_context,
        now=lambda: datetime(2026, 9, 3, tzinfo=timezone.utc),
    )

    assert isinstance(report, CandidateProfileProbeReport)
    assert report.provider_call_count == 1
    assert report.network_used is True
    assert report.observation.status == "observed"
    assert report.observation.content_state == "non_empty"
    assert report.observation.reasoning_state == "non_empty"
    assert report.candidate_registered is False
    assert report.production_admitted is False
    payload = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert '"content":' not in serialized
    assert '"reasoning":' not in serialized
    assert '"messages":' not in serialized
    request = clients[0].completions.calls[0]
    assert request["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "low",
    }
    assert request["max_tokens"] == 4096
    assert request["timeout"] == 90.0

    with pytest.raises(FileExistsError):
        run_candidate_profile_probe(
            repository_root=tmp_path,
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=True,
            environment_loader=_env,
            client_factory=client_factory,
            context_loader=_context,
        )


def test_probe_sanitizes_provider_failure_and_does_not_claim_network_without_call(tmp_path: Path):
    output = tmp_path / "data/evaluation/results/provider_capabilities/failure.json"
    report = run_candidate_profile_probe(
        repository_root=tmp_path,
        implementation_sha=IMPLEMENTATION_SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        output=output,
        confirm_real_call=True,
        environment_loader=_env,
        client_factory=lambda **_kwargs: _Client(RuntimeError("secret raw error")),
        context_loader=_context,
    )

    assert report.observation.status == "failed"
    assert report.observation.external_calls == 1
    assert report.observation.error_code == "unexpected_sdk_error"
    assert report.network_used is True
    assert "secret raw error" not in output.read_text(encoding="utf-8")
