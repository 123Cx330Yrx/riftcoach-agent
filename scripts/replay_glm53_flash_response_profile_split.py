"""Run the GLM-5.3-Flash response-profile split entirely offline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.glm53_flash_response_profile_split import (  # noqa: E402
    DEFAULT_OUTPUT,
    PROTOCOL_ID,
    ResponseProfileSplitError,
    run_response_profile_terminal_recovery_split,
    write_response_profile_terminal_recovery_receipt,
)


def _head_sha(root: Path) -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        raise ResponseProfileSplitError("head_sha_unavailable", "identity") from None
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ResponseProfileSplitError("head_sha_invalid", "identity")
    return value


def _resolve_output(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    try:
        output = candidate.resolve()
        allowed = (root / "data/evaluation/results/offline").resolve()
    except OSError:
        raise ResponseProfileSplitError("output_path_invalid", "output") from None
    if output.suffix.lower() != ".json" or not output.is_relative_to(allowed):
        raise ResponseProfileSplitError("offline_path_required", "output")
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the Flash response profile/terminal/recovery split with fixed "
            "in-memory fixtures; no provider call is permitted."
        )
    )
    parser.add_argument("--repository-root", type=Path, default=_ROOT)
    parser.add_argument("--implementation-sha")
    parser.add_argument("--diagnostic-code-sha")
    parser.add_argument("--input-plan-sha")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repository_root.resolve()
    try:
        needs_head = any(
            value is None
            for value in (
                args.implementation_sha,
                args.diagnostic_code_sha,
                args.input_plan_sha,
            )
        )
        head = _head_sha(root) if needs_head else None
        implementation_sha = args.implementation_sha or head
        diagnostic_code_sha = args.diagnostic_code_sha or head
        input_plan_sha = args.input_plan_sha or head
        if implementation_sha is None or diagnostic_code_sha is None or input_plan_sha is None:
            raise ResponseProfileSplitError("head_sha_unavailable", "identity")
        output = _resolve_output(root, args.output)
        receipt = run_response_profile_terminal_recovery_split(
            implementation_sha=implementation_sha,
            diagnostic_code_sha=diagnostic_code_sha,
            input_plan_sha=input_plan_sha,
        )
        written = write_response_profile_terminal_recovery_receipt(
            output,
            receipt,
            offline_root=root / "data/evaluation/results/offline",
        )
    except ResponseProfileSplitError as error:
        print(f"response-profile-split-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("response-profile-split-error=evidence_exists", file=sys.stderr)
        return 2

    print(
        "protocol=%s origin=%s provider_calls=%d cases=%d all_passed=%s output=%s"
        % (
            PROTOCOL_ID,
            receipt.evidence_origin,
            receipt.provider_call_count,
            receipt.case_count,
            receipt.all_cases_passed,
            written,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
