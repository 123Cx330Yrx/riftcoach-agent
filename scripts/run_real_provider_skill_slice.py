"""Run the explicitly authorized cumulative-budget recent-form admission slice."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from app.evaluation.provider_domain_skill import (
    DomainSkillSliceReport,
    DomainSkillSliceRunner,
    PriorAdapterEvidence,
    load_prior_adapter_evidence,
)
from app.providers.config import load_zhipu_settings
from app.providers.zhipu import ZhipuProvider


_CUMULATIVE_MAX_CALLS = 7
_DEFAULT_PRIOR_RESULT = Path(
    "data/evaluation/results/provider_capabilities/zhipu_adapter_slice.json"
)
_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/zhipu_recent_form_slice.json"
)


@dataclass(frozen=True)
class RealDomainSliceCliOptions:
    confirm_real_call: bool
    max_calls: int
    prior_result: Path | None
    output: Path | None


def run_cli(
    options: RealDomainSliceCliOptions,
    *,
    environ: Mapping[str, str] | None = None,
    repository_root: Path | None = None,
    client_factory: Callable[..., Any] = OpenAI,
    code_sha_reader: Callable[[Path], str] | None = None,
    prior_loader: Callable[..., PriorAdapterEvidence] = load_prior_adapter_evidence,
    runner_factory: Callable[..., DomainSkillSliceRunner] = DomainSkillSliceRunner,
) -> DomainSkillSliceReport:
    """Validate all local safety gates before creating a billable client."""

    if not options.confirm_real_call:
        raise RuntimeError("Real Provider calls require explicit confirmation.")
    if options.max_calls != _CUMULATIVE_MAX_CALLS:
        raise ValueError("recent-form domain slice requires the cumulative 7-call budget.")

    root = (
        repository_root
        if repository_root is not None
        else Path(__file__).resolve().parents[1]
    ).resolve()
    capability_dir = (
        root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    prior_path = _resolve_public_path(
        root=root,
        allowed_root=capability_dir,
        value=options.prior_result or _DEFAULT_PRIOR_RESULT,
    )
    output_path = _resolve_public_path(
        root=root,
        allowed_root=capability_dir,
        value=options.output or _DEFAULT_OUTPUT,
    )
    if prior_path == output_path:
        raise ValueError("domain result must not overwrite prior adapter evidence.")
    if output_path.exists():
        raise FileExistsError(
            "domain result already exists; refusing to repeat or overwrite the experiment."
        )

    settings = load_zhipu_settings(environ)
    prior_evidence = prior_loader(
        prior_path,
        expected_provider_id="zhipu",
        expected_model=settings.model,
    )
    summary_path = (root / "examples/fixtures/player_summary_demo.json").resolve()
    report_path = (root / "examples/fixtures/deterministic_report_demo.md").resolve()
    knowledge_dir = (root / "data/rag_docs").resolve()
    skills_dir = (root / "skills").resolve()
    if not summary_path.is_file() or not report_path.is_file():
        raise ValueError("anonymous domain fixtures are missing.")
    if not knowledge_dir.is_dir() or not skills_dir.is_dir():
        raise ValueError("domain knowledge or Skill directory is missing.")
    player_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    deterministic_report = report_path.read_text(encoding="utf-8")
    code_sha = (code_sha_reader or _read_code_sha)(root)

    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.default_timeout_s,
        max_retries=0,
    )
    provider = ZhipuProvider(client=client, model=settings.model)
    with tempfile.TemporaryDirectory(prefix="riftcoach-domain-slice-") as directory:
        runner = runner_factory(
            provider=provider,
            code_sha=code_sha,
            prior_evidence=prior_evidence,
            player_summary=player_summary,
            deterministic_report=deterministic_report,
            runs_root=Path(directory) / "runs",
            knowledge_dir=knowledge_dir,
            skills_dir=skills_dir,
        )
        result = runner.run()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def _resolve_public_path(
    *,
    root: Path,
    allowed_root: Path,
    value: Path,
) -> Path:
    resolved = value if value.is_absolute() else root / value
    resolved = resolved.resolve()
    if not resolved.is_relative_to(allowed_root):
        raise ValueError(
            "Path must remain inside the provider capability result directory."
        )
    return resolved


def _read_code_sha(repository_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if status.stdout.strip():
        raise RuntimeError(
            "real domain admission requires a clean, committed worktree."
        )
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str] | None = None) -> RealDomainSliceCliOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded Zhipu recent-form domain admission slice."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--max-calls", type=int, default=_CUMULATIVE_MAX_CALLS)
    parser.add_argument("--prior-result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    return RealDomainSliceCliOptions(
        confirm_real_call=args.confirm_real_call,
        max_calls=args.max_calls,
        prior_result=args.prior_result,
        output=args.output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    result = run_cli(_parse_args(argv), environ=os.environ)
    print(
        f"provider={result.provider_id} model={result.requested_model} "
        f"domain_calls={result.domain_calls_used}/{result.domain_max_calls} "
        f"cumulative_calls={result.cumulative_calls_used}/"
        f"{result.cumulative_max_calls} admitted={result.admitted}"
    )
    print(
        f"terminal={result.terminal_status} "
        f"evaluation_score={result.evaluation_score} "
        f"error_code={result.error_code}"
    )
    return 0 if result.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
