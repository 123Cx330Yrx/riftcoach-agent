"""Run the zero-network SDK/httpx transport-gate precheck.

The command uses an in-memory ``httpx.MockTransport`` behind the real OpenAI
SDK and the explicit candidate Zhipu stream adapter.  It never loads dotenv,
reads a key, opens a socket, or writes response bytes to the receipt.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.candidate_transport_gate import (  # noqa: E402
    CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID,
    CandidateTransportGateError,
    run_offline_transport_gate_replay,
    write_candidate_transport_gate_receipt,
)


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/offline/"
    "zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json"
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
        raise CandidateTransportGateError("head_sha_unavailable", "identity") from None
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateTransportGateError("head_sha_invalid", "identity")
    return value


def _resolve_output(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    try:
        output = candidate.resolve()
        allowed = (root / "data/evaluation/results/offline").resolve()
        output.relative_to(allowed)
    except (OSError, ValueError):
        raise CandidateTransportGateError("output_path_invalid", "output") from None
    if output.suffix.lower() != ".json":
        raise CandidateTransportGateError("output_path_invalid", "output")
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the candidate SDK/httpx transport gate offline; no "
            "provider call or network access is permitted."
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
            raise CandidateTransportGateError("head_sha_unavailable", "identity")
        output = _resolve_output(root, args.output)
        receipt = run_offline_transport_gate_replay(
            implementation_sha=implementation_sha,
            observer_code_sha=observer_code_sha,
            input_plan_sha=input_plan_sha,
        )
        written = write_candidate_transport_gate_receipt(
            output,
            receipt,
            offline_root=root / "data/evaluation/results/offline",
        )
    except CandidateTransportGateError as error:
        print(f"candidate-transport-gate-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("candidate-transport-gate-error=evidence_exists", file=sys.stderr)
        return 2

    print(
        "protocol=%s origin=%s provider_calls=%d cases=%d all_passed=%s output=%s"
        % (
            CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID,
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
