"""Run the bounded GLM-5.3-Flash transport/generation split diagnostic."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.glm53_flash_transport_generation_split_diagnostic import (  # noqa: E402
    DEFAULT_OUTPUT,
    run_transport_generation_split_diagnostic,
)


def _head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one bounded, body-free GLM-5.3-Flash transport/generation split."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--implementation-sha")
    parser.add_argument("--diagnostic-code-sha")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    report = run_transport_generation_split_diagnostic(
        repository_root=root,
        implementation_sha=args.implementation_sha or _head_sha(root),
        diagnostic_code_sha=args.diagnostic_code_sha,
        output=args.output,
        env_file=args.env_file,
        confirm_real_call=args.confirm_real_call,
    )
    statuses = ",".join(
        f"{row.variant}:{row.status}" for row in report.observations
    )
    print(
        "provider=%s model=%s calls=%d statuses=%s interpretation=%s output=%s"
        % (
            report.provider_id,
            report.requested_model,
            report.calls_attempted,
            statuses,
            report.verdicts.interpretation_code,
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


