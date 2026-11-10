from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.glm53_flash_response_recovery_diagnostic import (
    BASE_URL,
    MODEL,
    run_response_recovery_diagnostic,
)


IMPLEMENTATION_SHA = "e25c3579e8c37724b76505ad028e066a7e28e654"
DIAGNOSTIC_SHA = "eca01ce1393286dbbe83992c2985f600ea2b30b0"


def _raw(
    *,
    finish_reason: str = "stop",
    content: str | None = "safe answer",
    reasoning: str | None = "safe reasoning",
    request_id: str = "request-secret",
    input_tokens: int = 100,
    output_tokens: int = 50,
):
    return SimpleNamespace(
        id=request_id,
        model=MODEL,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning,
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
        completions = _Completions(responses)
        self.chat = SimpleNamespace(completions=completions)
        self.completions = completions


def _environment(_path):
    return {
        "LLM_API_KEY": "secret-key-not-for-report",
        "LLM_BASE_URL": BASE_URL,
        "LLM_MODEL": MODEL,
        "LLM_PROVIDER": "zhipu",
    }


def _run(tmp_path, responses, *, request_timeout_s=None):
    client = _Client(responses)
    root = Path(__file__).resolve().parents[1]
    output = (
        root
        / "data/evaluation/results/provider_capabilities"
        / f"test-response-recovery-{tmp_path.name}.json"
    )
    output.unlink(missing_ok=True)

    def factory(**kwargs):
        assert kwargs["max_retries"] == 0
        assert kwargs["base_url"] == BASE_URL
        return client

    report = run_response_recovery_diagnostic(
        repository_root=".",
        implementation_sha=IMPLEMENTATION_SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        output=output,
        confirm_real_call=True,
        environment_loader=_environment,
        client_factory=factory,
        request_timeout_s=request_timeout_s,
        now=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    return report, client, output


def test_candidate_length_shape_runs_one_fresh_recovery_and_stays_body_free(tmp_path):
    report, client, output = _run(
        tmp_path,
        [
                _raw(
                    finish_reason="length",
                    content="",
                reasoning="SECRET_REASONING",
                output_tokens=8192,
            ),
            _raw(content="SECRET_RESPONSE", reasoning="SECOND_REASONING"),
        ],
    )

    assert report.provider_calls_attempted == 2
    assert report.candidate_eligible_observed is True
    assert report.recovery_attempted is True
    assert report.recovery_skip_reason is None
    assert report.terminal_state == "complete_text"
    assert [row.attempt_kind for row in report.observations] == [
        "primary",
        "fresh_recovery",
    ]
    assert [call["max_tokens"] for call in client.completions.calls] == [8192, 8192]
    assert all("tools" not in call for call in client.completions.calls)
    payload = json.loads(output.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for secret in ("SECRET_REASONING", "SECRET_RESPONSE", "secret-key-not-for-report", "request-secret"):
        assert secret not in encoded
    assert "messages" not in payload["trace"]
    assert payload["trace"]["calls_attempted"] == 2
    output.unlink()


def test_complete_primary_never_gets_a_hidden_recovery(tmp_path):
    report, client, output = _run(tmp_path, [_raw(content="done")])

    assert report.provider_calls_attempted == 1
    assert report.recovery_attempted is False
    assert report.recovery_skip_reason == "primary_not_candidate_eligible"
    assert report.terminal_state == "complete_text"
    assert len(client.completions.calls) == 1
    output.unlink()


def test_request_timeout_override_controls_primary_and_recovery(tmp_path):
    report, client, output = _run(
        tmp_path,
        [
            _raw(finish_reason="length", content="", output_tokens=8192),
            _raw(content="done"),
        ],
        request_timeout_s=30.0,
    )

    assert [call["timeout"] for call in client.completions.calls] == [30.0, 30.0]
    assert [row.request.timeout_s for row in report.observations] == [30.0, 30.0]
    output.unlink()


@pytest.mark.parametrize(
    "request_timeout_s",
    [True, 0, -1, 29.9, 90.1, float("nan")],
)
def test_request_timeout_override_must_be_finite_and_within_candidate_agent_window(
    tmp_path,
    request_timeout_s,
):
    root = Path(__file__).resolve().parents[1]
    output = (
        root
        / "data/evaluation/results/provider_capabilities"
        / f"test-response-recovery-invalid-timeout-{tmp_path.name}.json"
    )
    output.unlink(missing_ok=True)

    with pytest.raises(ValueError, match="request_timeout_s"):
        run_response_recovery_diagnostic(
            repository_root=".",
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=True,
            environment_loader=_environment,
            client_factory=lambda **_: _Client([_raw(content="unused")]),
            request_timeout_s=request_timeout_s,
        )

    assert not output.exists()


def test_transport_failure_is_recorded_without_a_second_call(tmp_path):
    report, client, output = _run(tmp_path, [RuntimeError("secret transport detail")])

    assert report.provider_calls_attempted == 1
    assert report.recovery_attempted is False
    assert report.terminal_state == "fail_closed"
    observation = report.observations[0]
    assert observation.response_received is False
    assert observation.usage_state == "missing"
    assert observation.sdk_error_class == "sdk_error"
    assert len(client.completions.calls) == 1
    output.unlink()


def test_output_is_immutable(tmp_path):
    report, _client, output = _run(tmp_path, [_raw(content="done")])
    with pytest.raises(FileExistsError):
        run_response_recovery_diagnostic(
            repository_root=".",
            implementation_sha=IMPLEMENTATION_SHA,
            diagnostic_code_sha=DIAGNOSTIC_SHA,
            output=output,
            confirm_real_call=True,
            environment_loader=_environment,
            client_factory=lambda **_: _Client([_raw(content="again")]),
        )
    output.unlink()


