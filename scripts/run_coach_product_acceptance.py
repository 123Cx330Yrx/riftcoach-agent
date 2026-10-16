"""RQ-246 defaults to offline asset verification; real execution is explicit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.coach_product_acceptance import admit_assets
from app.evaluation.coach_product_acceptance_runner import execute_once, verify_real_evidence


def command(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True, timeout=45).stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--ci-run", type=int)
    parser.add_argument("--protocol-report", type=Path)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args(argv)
    try:
        assets = admit_assets(ROOT)
        if not args.confirm_real_call:
            print(f"coach-product-preflight=ready cases=4 assets={assets.sha256} network=0")
            return 0
        if args.ci_run is None or args.protocol_report is None:
            raise ValueError("real_acceptance_requires_ci_and_protocol")
        if command("git", "status", "--porcelain"):
            raise ValueError("real_acceptance_requires_clean_worktree")
        sha = command("git", "rev-parse", "HEAD")
        ci = json.loads(command("gh", "run", "view", str(args.ci_run), "--json",
                                "headSha,status,conclusion,jobs,url,updatedAt"))
        evidence = verify_real_evidence(assets, implementation_sha=sha, ci=ci,
                                        protocol_bytes=args.protocol_report.read_bytes())
        def provider_factory():
            from dotenv import load_dotenv
            from app.evaluation.glm53_low_profile_domain_gate import create_low_profile_provider
            from app.providers.config import load_zhipu_settings
            load_dotenv(args.env_file, override=False)
            return create_low_profile_provider(load_zhipu_settings())
        receipt = execute_once(ROOT, real_evidence=evidence, provider_factory=provider_factory)
        print(f"coach-product-acceptance={'passed' if receipt.passed else 'stopped'} calls={receipt.provider_calls}")
        return 0 if receipt.passed else 1
    except Exception:
        print("coach-product-error=preflight_or_execution_failed; inspect safe local receipt if reserved", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
