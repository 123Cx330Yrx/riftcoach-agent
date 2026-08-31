"""Run the fresh, bounded G53-5 GLM-5.3-Flash capability matrix."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from app.evaluation.glm53_flash_capability_matrix import (
    MAX_OBSERVED_TOKENS,
    MAX_REAL_CALLS,
    build_preflight_report,
    run_real_matrix,
)
from app.providers.config import load_zhipu_settings


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_g53_5_capability_matrix_v1.json"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the one-shot GLM-5.3-Flash G53-5 capability matrix."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--max-calls", type=int, default=MAX_REAL_CALLS)
    parser.add_argument(
        "--max-observed-tokens",
        type=int,
        default=MAX_OBSERVED_TOKENS,
    )
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
    if args.max_calls != MAX_REAL_CALLS:
        raise ValueError(f"--max-calls must be exactly {MAX_REAL_CALLS}")
    if args.max_observed_tokens != MAX_OBSERVED_TOKENS:
        raise ValueError(
            f"--max-observed-tokens must be exactly {MAX_OBSERVED_TOKENS}"
        )
    root = Path(__file__).resolve().parents[1]
    output = _resolve_output(root, args.output)

    if args.preflight_only:
        if args.confirm_real_call:
            raise ValueError("preflight-only cannot be combined with real-call confirmation")
        report = build_preflight_report(root)
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(report.model_dump_json(indent=2))
        print("G53-5 preflight passed: no external call; output reserved")
        return 0

    if not args.confirm_real_call:
        raise RuntimeError("real Provider calls require --confirm-real-call")
    load_dotenv(dotenv_path=root / ".env")
    settings = load_zhipu_settings(os.environ)
    report = run_real_matrix(
        repository_root=root,
        output=output,
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
    )
    print(
        "G53-5 completed: "
        f"calls={report.resources.calls_used}/{report.budgets.max_real_calls} "
        f"tokens={report.resources.total_tokens}/"
        f"{report.budgets.max_observed_tokens}"
    )
    print(", ".join(f"{row.case_id}={row.status}" for row in report.cases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
