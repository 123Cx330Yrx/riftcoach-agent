"""Run one separately identified GLM-5.3-Flash tool-stream diagnostic."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from app.evaluation.glm53_flash_tool_stream_followup import (
    FOLLOWUP_MAX_OBSERVED_TOKENS,
    FOLLOWUP_MAX_OUTPUT_TOKENS,
    run_real_tool_stream_followup,
)
from app.providers.config import load_zhipu_settings


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run exactly one larger-cap GLM-5.3-Flash tool-stream diagnostic."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _resolve_output(root: Path, path: Path) -> Path:
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    output = (path if path.is_absolute() else root / path).resolve()
    if not output.is_relative_to(allowed):
        raise ValueError("output must remain inside provider capability results")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.confirm_real_call:
        raise RuntimeError("real Provider calls require --confirm-real-call")
    root = Path(__file__).resolve().parents[1]
    output = _resolve_output(root, args.output)
    load_dotenv(dotenv_path=root / ".env")
    settings = load_zhipu_settings(os.environ)
    report = run_real_tool_stream_followup(
        repository_root=root,
        output=output,
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
    )
    print(
        "G53-5 tool-stream follow-up completed: "
        f"status={report.case.status} calls={report.resources.calls_used}/1 "
        f"tokens={report.resources.total_tokens}/{FOLLOWUP_MAX_OBSERVED_TOKENS} "
        f"max_output={FOLLOWUP_MAX_OUTPUT_TOKENS}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
