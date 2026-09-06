"""Preflight by default; explicit high-profile product development observation."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.coach_grounded_development import prepare_observation, execute_once, verify_development_ci, prepare_suite, execute_suite_once
from app.runtime.coach_contract import GROUNDED_COACH_CONTRACT


def command(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True, timeout=45).stdout.strip()


@contextmanager
def high_provider(env_file):
    # This is entered by provider_factory only after the create-only reservation.
    from dotenv import dotenv_values
    from openai import OpenAI
    from app.providers.config import load_zhipu_settings
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    settings = load_zhipu_settings(dotenv_values(env_file))
    if settings.model != "glm-5.3-flash" or settings.base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
        raise ValueError("development_requires_standard_flash_api")
    with OpenAI(api_key=settings.api_key, base_url=settings.base_url, max_retries=0,
                timeout=GROUNDED_COACH_CONTRACT.descriptor()["request_timeout_s"]) as client:
        yield ZhipuProvider.from_candidate_profile(client=client, model=settings.model,
                                                   profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("overall", "survival", "economy", "memory"), default="economy")
    parser.add_argument("--suite", action="store_true", help="Run all four known development cases, not an admission exam")
    parser.add_argument("--tool-batch-v2", action="store_true", help="Explicit versioned eight-local-tool budget; model-call budget unchanged")
    parser.add_argument("--run-id")
    parser.add_argument("--plan-sha256")
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--ci-run", type=int)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args(argv)
    phase = "local_preflight"
    try:
        plan = (prepare_suite(ROOT, suite_id=args.run_id or "coach-grounded-suite-preview", tool_batch=args.tool_batch_v2) if args.suite else
                prepare_observation(ROOT, scenario=args.scenario, run_id=args.run_id or "coach-grounded-dev-preview", tool_batch=args.tool_batch_v2))
        if not args.confirm_real_call:
            print(json.dumps({"status": "ready", "scope": "development_not_admission", "network": 0,
                **({"run_id": plan.suite_id, "scenarios": [p.scenario for p in plan.plans]} if args.suite else
                   {"run_id": plan.run_id, "scenario": plan.scenario}), "plan_sha256": plan.sha256,
                "reasoning_effort": "high", "max_output_tokens": 8192, "max_calls": 36 if args.suite else 9,
                "max_total_tokens": 2598912 if args.suite else 649728, "request_timeout_s": 60}))
            return 0
        phase = "real_preflight"
        if not args.run_id or args.ci_run is None or args.plan_sha256 != plan.sha256:
            raise ValueError("development_requires_explicit_matching_identity")
        if command("git", "status", "--porcelain"):
            raise ValueError("development_requires_clean_worktree")
        sha = command("git", "rev-parse", "HEAD")
        ci = json.loads(command("gh", "run", "view", str(args.ci_run), "--json", "headSha,status,conclusion,jobs,url"))
        if args.suite:
            phase = "reserved_suite_execution"
            with ExitStack() as stack:
                result = execute_suite_once(ROOT, suite=plan, implementation_sha=sha, ci=ci,
                    provider_factory=lambda: stack.enter_context(high_provider(args.env_file)),
                    on_progress=lambda row: print(json.dumps(row, ensure_ascii=True), flush=True))
            print(json.dumps(result, ensure_ascii=True), flush=True)
            return 0 if result["passed"] else 1
        evidence = verify_development_ci(plan, implementation_sha=sha, ci=ci)
        phase = "reserved_execution"
        with ExitStack() as stack:
            receipt = execute_once(ROOT, plan=plan, real_evidence=evidence,
                provider_factory=lambda: stack.enter_context(high_provider(args.env_file)))
        print(json.dumps({"status": "passed" if receipt.passed else "failed", "scope": receipt.scope,
            "provider_calls": receipt.provider_calls, "sources": len(receipt.observation.evidence_source_ids),
            "score": receipt.observation.evaluation_score, "failure_codes": receipt.failure_codes}))
        return 0 if receipt.passed else 1
    except Exception:
        print(f"grounded-development-error={phase}; inspect reserved safe records if present", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
