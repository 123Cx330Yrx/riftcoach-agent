from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.probe_zhipu_capabilities import ProbeCliOptions, run_cli


VALID_ENV = {
    "LLM_PROVIDER": "zhipu",
    "LLM_API_KEY": "secret-value",
    "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
    "LLM_MODEL": "glm-test",
    "LLM_TIMEOUT_SECONDS": "30",
}

FLASH_ENV = {**VALID_ENV, "LLM_MODEL": "glm-5.3-flash"}


def test_cli_refuses_real_io_without_explicit_confirmation(tmp_path: Path) -> None:
    factories: list[dict] = []

    with pytest.raises(RuntimeError, match="confirmation"):
        run_cli(
            ProbeCliOptions(
                confirm_real_call=False,
                scope="p1_p5",
                max_calls=5,
                output=tmp_path / "result.json",
            ),
            environ=VALID_ENV,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []


def test_cli_rejects_output_outside_public_result_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="provider capability result directory"):
        run_cli(
            ProbeCliOptions(
                confirm_real_call=True,
                scope="p1_p5",
                max_calls=5,
                output=tmp_path / "escape.json",
            ),
            environ=VALID_ENV,
            repository_root=Path("D:/riftcoach-agent"),
            client_factory=lambda **kwargs: None,
        )


def test_cli_rejects_scope_budget_mismatch_before_client_creation(
    tmp_path: Path,
) -> None:
    factories: list[dict] = []

    with pytest.raises(ValueError, match="p1_diagnostic"):
        run_cli(
            ProbeCliOptions(
                confirm_real_call=True,
                scope="p1_diagnostic",
                max_calls=5,
                output=tmp_path / "result.json",
            ),
            environ=VALID_ENV,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []


def test_cli_p1_diagnostic_uses_one_call_and_separate_default_output(
    tmp_path: Path,
) -> None:
    calls: list[dict] = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id="raw-request-secret",
            model="glm-test-resolved",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="RIFTCOACH_PROVIDER_OK",
                        tool_calls=[],
                    ),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    report = run_cli(
        ProbeCliOptions(
            confirm_real_call=True,
            scope="p1_diagnostic",
            max_calls=1,
            output=None,
        ),
        environ=VALID_ENV,
        repository_root=tmp_path,
        client_factory=lambda **kwargs: client,
        code_sha_reader=lambda root: "a" * 40,
    )

    output = (
        tmp_path
        / "data/evaluation/results/provider_capabilities"
        / "zhipu_glm52_p1_diagnostic.json"
    )
    assert report.probe_scope == "p1_diagnostic"
    assert report.calls_used == 1
    assert len(calls) == 1
    assert output.is_file()
    assert "raw-request-secret" not in output.read_text(encoding="utf-8")


def test_cli_isolates_flash_default_output_by_model(
    tmp_path: Path,
) -> None:
    client_options: list[dict] = []

    def create(**kwargs):
        return SimpleNamespace(
            id="raw-flash-request-secret",
            model="glm-5.3-flash",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="RIFTCOACH_PROVIDER_OK",
                        reasoning_content="raw-flash-reasoning",
                        tool_calls=[],
                    ),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    report = run_cli(
        ProbeCliOptions(
            confirm_real_call=True,
            scope="p1_diagnostic",
            max_calls=1,
            output=None,
        ),
        environ=FLASH_ENV,
        repository_root=tmp_path,
        client_factory=lambda **kwargs: (client_options.append(kwargs) or client),
        code_sha_reader=lambda root: "a" * 40,
    )

    output = (
        tmp_path
        / "data/evaluation/results/provider_capabilities"
        / "zhipu_glm53_flash_p1_diagnostic.json"
    )
    assert report.requested_model == "glm-5.3-flash"
    assert output.is_file()
    assert "raw-flash-reasoning" not in output.read_text(encoding="utf-8")
    assert client_options[0]["timeout"] == 120.0


def test_cli_adapter_protocol_uses_production_adapter_and_exact_budget(
    tmp_path: Path,
) -> None:
    calls: list[dict] = []
    structured_json = json.dumps(
        {
            "score": 100,
            "verdict": "pass",
            "issues": [],
            "passed_checks": ["protocol contract"],
            "summary": "Structured protocol is valid.",
        }
    )
    responses = [
        SimpleNamespace(
            id="RAW_STRUCTURED_REQUEST",
            model="glm-test-resolved",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=structured_json, tool_calls=[]),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        ),
        SimpleNamespace(
            id="RAW_TOOL_REQUEST",
            model="glm-test-resolved",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                id="RAW_TOOL_CALL",
                                type="function",
                                function=SimpleNamespace(
                                    name="knowledge_search",
                                    arguments=json.dumps(
                                        {
                                            "query": "reduce deaths before 15 minutes",
                                            "top_k": 1,
                                        }
                                    ),
                                ),
                            )
                        ],
                    ),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=4),
        ),
        SimpleNamespace(
            id="RAW_FINAL_REQUEST",
            model="glm-test-resolved",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="RIFTCOACH_TOOL_ROUNDTRIP_OK",
                        tool_calls=[],
                    ),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=30, completion_tokens=3),
        ),
    ]

    def create(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    client_options: list[dict] = []

    def client_factory(**kwargs):
        client_options.append(kwargs)
        return client

    report = run_cli(
        ProbeCliOptions(
            confirm_real_call=True,
            scope="adapter_protocol",
            max_calls=3,
            output=None,
        ),
        environ=VALID_ENV,
        repository_root=tmp_path,
        client_factory=client_factory,
        code_sha_reader=lambda root: "a" * 40,
    )

    assert report.admitted is True
    assert report.calls_used == 3
    assert len(calls) == 3
    assert client_options[0]["max_retries"] == 0
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[1]["tools"][0]["function"]["name"] == "knowledge_search"
    assert calls[2]["messages"][-1]["role"] == "tool"
    assert calls[2]["messages"][-1]["tool_call_id"] == "RAW_TOOL_CALL"

    output = (
        tmp_path
        / "data/evaluation/results/provider_capabilities"
        / "zhipu_adapter_slice.json"
    )
    serialized = output.read_text(encoding="utf-8")
    assert output.is_file()
    assert "RAW_" not in serialized
    assert "reduce deaths before 15 minutes" not in serialized
    assert "RIFTCOACH_TOOL_ROUNDTRIP_OK" not in serialized


def test_cli_adapter_protocol_rejects_non_exact_budget_before_client() -> None:
    factories: list[dict] = []

    with pytest.raises(ValueError, match="adapter_protocol"):
        run_cli(
            ProbeCliOptions(
                confirm_real_call=True,
                scope="adapter_protocol",
                max_calls=4,
                output=None,
            ),
            environ=VALID_ENV,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []
