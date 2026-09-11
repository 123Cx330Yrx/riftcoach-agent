"""Run one explicitly authorized GLM-5.3 low-thinking candidate probe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.evaluation.glm53_flash_candidate_profile_probe import (
    DEFAULT_OUTPUT,
    run_candidate_profile_probe,
)


ROOT = Path(__file__).resolve().parents[1]


def _path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one body-free GLM-5.3 Flash low-thinking candidate "
            "profile probe."
        )
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--diagnostic-code-sha", required=True)
    parser.add_argument("--output", type=_path, default=ROOT / DEFAULT_OUTPUT)
    parser.add_argument("--env-file", type=_path)
    args = parser.parse_args(argv)
    try:
        report = run_candidate_profile_probe(
            repository_root=ROOT,
            implementation_sha=args.implementation_sha,
            diagnostic_code_sha=args.diagnostic_code_sha,
            output=args.output,
            env_file=args.env_file,
            confirm_real_call=args.confirm_real_call,
        )
    except FileExistsError:
        print("candidate-profile-probe-error=evidence_exists", file=sys.stderr)
        return 2
    except Exception as error:
        # Keep the CLI boundary body-free; detailed provider exceptions never
        # cross into terminal output.
        code = getattr(error, "code", "candidate_profile_probe_failed")
        print(f"candidate-profile-probe-error={code}", file=sys.stderr)
        return 1

    observation = report.observation
    print(
        "candidate-profile-probe "
        f"status={observation.status} "
        f"calls={report.provider_call_count}/{1} "
        f"network={report.network_used} "
        f"finish={observation.finish_reason} "
        f"usage={observation.usage_state}"
    )
    return 0 if observation.status == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

