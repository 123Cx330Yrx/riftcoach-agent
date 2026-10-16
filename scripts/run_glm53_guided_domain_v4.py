"""Run the fresh four-case guided GLM-5.3 Flash domain gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.glm53_guided_domain_assets import admit_guided_domain_assets
from app.evaluation.glm53_guided_domain_gate import (
    DEFAULT_OUTPUT,
    DEFAULT_RUNS_ROOT,
    build_guided_domain_preflight,
    canonical_result_bytes,
    run_guided_domain,
)
from app.evaluation.glm53_low_profile_domain_gate import create_low_profile_provider
from app.providers.config import load_zhipu_settings
from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fresh guided V4 domain gate.")
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--output", type=Path, default=ROOT / DEFAULT_OUTPUT)
    parser.add_argument("--runs-root", type=Path, default=ROOT / DEFAULT_RUNS_ROOT)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        bundle = build_guided_domain_preflight(
            project_root=ROOT,
            implementation_sha=args.implementation_sha,
            public_ci_sha=args.public_ci_sha,
            confirm_public_ci_success=args.confirm_public_ci_success,
        )
        if args.preflight_only:
            print("guided-v4-preflight=ready")
            return 0
        if not args.confirm_real_call:
            raise RuntimeError("real guided V4 calls require --confirm-real-call")
        if args.output.exists():
            raise FileExistsError("guided V4 result is immutable")
        load_dotenv(args.env_file, override=False)
        provider = create_low_profile_provider(load_zhipu_settings())
        result = run_guided_domain(
            bundle=bundle,
            implementation_sha=args.implementation_sha,
            provider=provider,
            project_root=ROOT,
            runs_root=args.runs_root,
            confirm_real_call=True,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_result_bytes(result))
        print(f"guided-v4 status={'admitted' if result['admitted'] else 'rejected'} calls={result['resources']['calls_used']}")
        return 0 if result["admitted"] else 1
    except Exception as error:
        print(f"guided-v4-error={getattr(error, 'code', 'preflight_failed')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
