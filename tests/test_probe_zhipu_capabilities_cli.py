from __future__ import annotations

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
