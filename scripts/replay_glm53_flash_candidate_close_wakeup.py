"""Run the body-free, offline GLM-5.3 close/wakeup replay matrix.

Unlike the real-provider probe, this command never loads dotenv or credentials,
never constructs or calls an SDK client, and never opens a network connection.
The existing package import may load dependency modules, but the command only
exercises the in-memory observer seam and writes a separately typed
``offline_fake`` receipt.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.candidate_close_wakeup_replay import (  # noqa: E402
    CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID,
    CandidateCloseWakeReplayError,
    run_candidate_close_wakeup_replay,
    write_candidate_close_wakeup_replay_receipt,
)


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/offline/"
    "zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json"
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
        raise CandidateCloseWakeReplayError("head_sha_unavailable", "identity") from None
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateCloseWakeReplayError("head_sha_invalid", "identity")
    return value


def _resolve_output(root: Path, value: Path) -> Path:
    """Keep CLI evidence inside the dedicated offline results tree."""

    candidate = value if value.is_absolute() else root / value
    try:
        output = candidate.resolve()
        allowed = (root / "data/evaluation/results/offline").resolve()
    except OSError:
        raise CandidateCloseWakeReplayError("output_path_invalid", "output") from None
    if (
        output.suffix.lower() != ".json"
        or not output.is_relative_to(allowed)
        or output.name in {"", ".", ".."}
    ):
        raise CandidateCloseWakeReplayError("output_path_invalid", "output")
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the candidate close/wakeup observer offline; no provider "
            "call or network access is permitted."
        )
    )
    parser.add_argument("--repository-root", type=Path, default=_ROOT)
    parser.add_argument("--implementation-sha")
    parser.add_argument("--observer-code-sha")
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
                args.observer_code_sha,
                args.input_plan_sha,
            )
        )
        head = _head_sha(root) if needs_head else None
        implementation_sha = args.implementation_sha or head
        observer_code_sha = args.observer_code_sha or head
        input_plan_sha = args.input_plan_sha or head
        if (
            implementation_sha is None
            or observer_code_sha is None
            or input_plan_sha is None
        ):
            raise CandidateCloseWakeReplayError("head_sha_unavailable", "identity")
        output = _resolve_output(root, args.output)
        receipt = run_candidate_close_wakeup_replay(
            implementation_sha=implementation_sha,
            observer_code_sha=observer_code_sha,
            input_plan_sha=input_plan_sha,
        )
        written = write_candidate_close_wakeup_replay_receipt(
            output,
            receipt,
            offline_root=root / "data/evaluation/results/offline",
        )
    except CandidateCloseWakeReplayError as error:
        print(f"candidate-close-wakeup-replay-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("candidate-close-wakeup-replay-error=evidence_exists", file=sys.stderr)
        return 2

    print(
        "protocol=%s origin=%s provider_calls=%d scenarios=%d all_passed=%s output=%s"
        % (
            CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID,
            receipt.evidence_origin,
            receipt.provider_call_count,
            len(receipt.cases),
            receipt.all_cases_passed,
            written,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
