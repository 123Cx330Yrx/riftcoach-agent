"""Run the explicitly authorized, bounded Zhipu P1-P5 capability probe."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from app.evaluation.provider_capability_gate import CapabilityProbeReport
from app.providers.config import load_zhipu_settings
from app.providers.zhipu_probe import ZhipuCapabilityProbe


_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/zhipu_glm52_p1_p5.json"
)


@dataclass(frozen=True)
class ProbeCliOptions:
    confirm_real_call: bool
    max_calls: int
    output: Path


def run_cli(
    options: ProbeCliOptions,
    *,
    environ: Mapping[str, str] | None = None,
    repository_root: Path | None = None,
    client_factory: Callable[..., Any] = OpenAI,
) -> CapabilityProbeReport:
    """Validate all safety gates, perform at most five calls, and persist evidence."""

    if not options.confirm_real_call:
        raise RuntimeError("Real provider calls require explicit confirmation.")
    if options.max_calls != 5:
        raise ValueError("The P1-P5 experiment requires an exact five-call budget.")

    root = (
        repository_root
        if repository_root is not None
        else Path(__file__).resolve().parents[1]
    ).resolve()
    allowed_root = (
        root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    output = options.output
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError(
            "Output must remain inside the provider capability result directory."
        )

    settings = load_zhipu_settings(environ)
    code_sha = _read_code_sha(root)
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.default_timeout_s,
        max_retries=0,
    )
    report = ZhipuCapabilityProbe(
        client=client,
        model=settings.model,
        code_sha=code_sha,
        max_calls=options.max_calls,
    ).run()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def _read_code_sha(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str] | None = None) -> ProbeCliOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded Zhipu GLM capability experiment.",
    )
    parser.add_argument(
        "--confirm-real-call",
        action="store_true",
        help="Acknowledge that this command performs billable external calls.",
    )
    parser.add_argument("--max-calls", type=int, default=5)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    return ProbeCliOptions(
        confirm_real_call=args.confirm_real_call,
        max_calls=args.max_calls,
        output=args.output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    report = run_cli(_parse_args(argv), environ=os.environ)
    statuses = ", ".join(
        f"{case.case_id}={case.status}" for case in report.cases
    )
    print(
        f"provider={report.provider_id} model={report.requested_model} "
        f"calls={report.calls_used}/{report.max_calls} admitted={report.admitted}"
    )
    print(statuses)
    return 0 if report.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
