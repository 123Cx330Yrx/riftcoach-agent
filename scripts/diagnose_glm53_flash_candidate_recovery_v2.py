"""Run one explicitly authorized GLM-5.3 candidate v2 real-call diagnostic."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.candidate_recovery_diagnostic_real import (  # noqa: E402
    DEFAULT_OUTPUT,
    CandidateRealCallError,
    run_candidate_recovery_real_call,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded, body-free GLM-5.3 Flash candidate recovery "
            "diagnostic (primary only; recovery remains disabled)."
        )
    )
    parser.add_argument(
        "--confirm-real-call",
        action="store_true",
        help="Acknowledge one billable external request.",
    )
    parser.add_argument("--repository-root", type=Path, default=_ROOT)
    parser.add_argument("--implementation-sha")
    parser.add_argument("--diagnostic-code-sha")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    head = _head_sha(root)
    try:
        report = run_candidate_recovery_real_call(
            repository_root=root,
            implementation_sha=args.implementation_sha or head,
            diagnostic_code_sha=args.diagnostic_code_sha or head,
            output=args.output,
            env_file=args.env_file,
            confirm_real_call=args.confirm_real_call,
        )
    except CandidateRealCallError as error:
        print(f"candidate-real-call-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("candidate-real-call-error=evidence_exists", file=sys.stderr)
        return 2
    attempt = report.receipt.attempts[0] if report.receipt.attempts else None
    usage = attempt.usage_state if attempt is not None else "unknown"
    elapsed = (
        attempt.latency.total_elapsed_ms
        if attempt is not None
        else None
    )
    print(
        "provider=zhipu model=glm-5.3-flash calls=%d run_state=%s "
        "terminal=%s usage=%s elapsed_ms=%s recovery=disabled output=%s"
        % (
            report.external_calls,
            report.receipt.run_state,
            report.receipt.terminal_reason,
            usage,
            elapsed,
            report.written.path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
