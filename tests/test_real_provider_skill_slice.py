from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.evaluation.provider_domain_skill import DomainSkillSliceReport
from scripts.run_real_provider_skill_slice import (
    RealDomainSliceCliOptions,
    _read_code_sha,
    run_cli,
)


VALID_ENV = {
    "LLM_PROVIDER": "zhipu",
    "LLM_API_KEY": "secret-value",
    "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
    "LLM_MODEL": "glm-5.2",
    "LLM_TIMEOUT_SECONDS": "30",
}


def fake_report() -> DomainSkillSliceReport:
    return DomainSkillSliceReport(
        provider_id="zhipu",
        requested_model="glm-5.2",
        code_sha="b" * 40,
        run_timestamp_utc="2026-08-13T00:00:00Z",
        fixture_sha256="1" * 64,
        prior_result_sha256="2" * 64,
        prior_code_sha="a" * 40,
        domain_calls_used=3,
        cumulative_calls_used=6,
        admitted=True,
        agent_calls=2,
        evaluation_calls=1,
        evaluation_repair_calls=0,
        revision_calls=0,
        budget_block_count=0,
        response_count=3,
        input_tokens=300,
        output_tokens=100,
        latency_ms=1000,
        resolved_models=("glm-5.2", "glm-5.2", "glm-5.2"),
        finish_reasons=("tool_calls", "stop", "stop"),
        request_id_sha256=("3" * 64, "4" * 64, "5" * 64),
        agent_status="completed",
        agent_stop_reason="final_response",
        tool_call_count=1,
        tool_execution_count=1,
        knowledge_source_count=1,
        evaluation_validated=True,
        evaluation_score=94,
        terminal_status="published",
        typed_output_sha256="6" * 64,
    )


class FakeRunner:
    def __init__(self, report: DomainSkillSliceReport) -> None:
        self.report = report

    def run(self) -> DomainSkillSliceReport:
        return self.report


def test_cli_refuses_real_io_without_explicit_confirmation(tmp_path: Path) -> None:
    factories: list[dict] = []

    with pytest.raises(RuntimeError, match="confirmation"):
        run_cli(
            RealDomainSliceCliOptions(
                confirm_real_call=False,
                max_calls=7,
                prior_result=None,
                output=None,
            ),
            environ=VALID_ENV,
            repository_root=tmp_path,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []


def test_cli_rejects_non_exact_cumulative_budget_before_client(
    tmp_path: Path,
) -> None:
    factories: list[dict] = []

    with pytest.raises(ValueError, match="7-call"):
        run_cli(
            RealDomainSliceCliOptions(
                confirm_real_call=True,
                max_calls=4,
                prior_result=None,
                output=None,
            ),
            environ=VALID_ENV,
            repository_root=tmp_path,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []


def test_cli_rejects_paths_outside_public_result_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="provider capability result directory"):
        run_cli(
            RealDomainSliceCliOptions(
                confirm_real_call=True,
                max_calls=7,
                prior_result=tmp_path / "escape.json",
                output=None,
            ),
            environ=VALID_ENV,
            repository_root=tmp_path,
            client_factory=lambda **kwargs: None,
        )


def test_cli_refuses_to_repeat_or_overwrite_an_existing_domain_result(
    tmp_path: Path,
) -> None:
    capability_dir = (
        tmp_path / "data/evaluation/results/provider_capabilities"
    )
    capability_dir.mkdir(parents=True)
    output = capability_dir / "zhipu_recent_form_slice.json"
    output.write_text("existing evidence", encoding="utf-8")
    factories: list[dict] = []

    with pytest.raises(FileExistsError, match="refusing to repeat"):
        run_cli(
            RealDomainSliceCliOptions(
                confirm_real_call=True,
                max_calls=7,
                prior_result=None,
                output=None,
            ),
            environ=VALID_ENV,
            repository_root=tmp_path,
            client_factory=lambda **kwargs: factories.append(kwargs),
        )

    assert factories == []
    assert output.read_text(encoding="utf-8") == "existing evidence"


def test_code_sha_reader_rejects_a_dirty_worktree_before_reporting_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=" M app/provider.py\n",
            stderr="",
        )

    monkeypatch.setattr(
        "scripts.run_real_provider_skill_slice.subprocess.run",
        fake_run,
    )

    with pytest.raises(RuntimeError, match="clean, committed worktree"):
        _read_code_sha(tmp_path)

    assert calls == [
        ["git", "status", "--porcelain", "--untracked-files=normal"]
    ]


def test_cli_builds_zero_retry_client_and_persists_only_sanitized_report(
    tmp_path: Path,
) -> None:
    capability_dir = (
        tmp_path / "data/evaluation/results/provider_capabilities"
    )
    capability_dir.mkdir(parents=True)
    prior = capability_dir / "zhipu_adapter_slice.json"
    prior.write_text("{}", encoding="utf-8")
    fixtures_dir = tmp_path / "examples/fixtures"
    fixtures_dir.mkdir(parents=True)
    (fixtures_dir / "player_summary_demo.json").write_text(
        '{"schema_version":"1.0"}',
        encoding="utf-8",
    )
    (fixtures_dir / "deterministic_report_demo.md").write_text(
        "# deterministic fixture\n",
        encoding="utf-8",
    )
    (tmp_path / "data/rag_docs").mkdir(parents=True)
    (tmp_path / "skills").mkdir()
    client_options: list[dict] = []
    runner_inputs: list[dict] = []

    def runner_factory(**kwargs):
        runner_inputs.append(kwargs)
        return FakeRunner(fake_report())

    report = run_cli(
        RealDomainSliceCliOptions(
            confirm_real_call=True,
            max_calls=7,
            prior_result=None,
            output=None,
        ),
        environ=VALID_ENV,
        repository_root=tmp_path,
        client_factory=lambda **kwargs: client_options.append(kwargs) or object(),
        code_sha_reader=lambda root: "b" * 40,
        prior_loader=lambda path, **kwargs: object(),
        runner_factory=runner_factory,
    )

    output = capability_dir / "zhipu_recent_form_slice.json"
    serialized = output.read_text(encoding="utf-8")
    assert report.admitted is True
    assert output.is_file()
    assert client_options[0]["max_retries"] == 0
    assert runner_inputs[0]["runs_root"] != capability_dir
    assert not Path(runner_inputs[0]["runs_root"]).exists()
    assert json.loads(serialized)["cumulative_calls_used"] == 6
    assert "secret-value" not in serialized
    assert "RAW_" not in serialized
