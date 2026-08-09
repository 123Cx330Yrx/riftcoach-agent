from __future__ import annotations

from pathlib import Path

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
                max_calls=5,
                output=tmp_path / "escape.json",
            ),
            environ=VALID_ENV,
            repository_root=Path("D:/riftcoach-agent"),
            client_factory=lambda **kwargs: None,
        )
