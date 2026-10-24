"""One archived-input timing diagnostic. Default preflight makes zero requests."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from app.evaluation.golden_stream_diagnostic import prepare_request, observe, supervise
from app.evaluation.golden_journal import write_new_json
from app.evaluation.coach_product_acceptance_runner import verify_real_evidence
from app.runtime.coach_contract import ADVICE_COACH_CONTRACT

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True, timeout=15).stdout.strip()


def prepare(config):
    return prepare_request(ROOT / "data/runs/golden_slice", **config["inputs"])


def child(directory, started, deadline):
    # The parent owns the deadline, output namespace and verified public evidence.
    config = json.loads((directory / "reservation.json").read_bytes())
    request, identity = prepare(config)
    if identity != config["identity"] or git("rev-parse", "HEAD") != config["implementation_sha"]:
        raise ValueError("diagnostic_identity_changed")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("diagnostic_dirty_tree")
    verify_real_evidence(ADVICE_COACH_CONTRACT.snapshot(), implementation_sha=config["implementation_sha"],
                         ci=config["ci"], protocol_bytes=(directory / "protocol.json").read_bytes())
    from dotenv import load_dotenv
    from openai import OpenAI, DefaultHttpxClient
    from app.providers.config import load_zhipu_settings
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    load_dotenv(ROOT.parent / "riftcoach-agent" / ".env")
    settings = load_zhipu_settings(os.environ)
    if settings.model != "glm-5.3-flash" or settings.base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
        raise ValueError("diagnostic_provider_identity")
    client = None

    class OwnedSession:
        def __init__(self, session):
            self.session = session
        def __iter__(self):
            return iter(self.session)
        @property
        def close_failed(self):
            return self.session.close_failed
        def close(self):
            try:
                self.session.close()
            finally:
                client.close()

    def opener(hook, remaining):
        nonlocal client
        write_new_json(directory / "provider-001.json", {
            "source": "provider", "ordinal": 1, "state": "attempt_reserved_before_io"})
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url, max_retries=0,
            timeout=remaining, http_client=DefaultHttpxClient(event_hooks={"request": [hook]}))
        provider = ZhipuProvider.from_candidate_profile(client=client, model=settings.model,
            profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
        try:
            session = provider.stream_adapter().stream_session(
                replace(request, timeout_s=max(.001, deadline - time.monotonic())), include_usage_tail=True)
            return OwnedSession(session)
        except BaseException:
            client.close()
            raise

    observe(opener, directory=directory, started=started, deadline=deadline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--ci-run", type=int)
    parser.add_argument("--protocol-report", type=Path)
    parser.add_argument("--child", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--started", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child is not None:
        child(args.child, args.started, args.deadline)
        return 0
    if args.config is None or args.config.stat().st_size > 16384:
        raise ValueError("diagnostic_config_required")
    config = json.loads(args.config.read_bytes())
    _, identity = prepare(config)
    if not args.execute:
        print(json.dumps({"identity": identity, "provider_attempts": 0, "network_used": False}))
        return 0
    if not args.run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,95}", args.run_id):
        raise ValueError("diagnostic_run_id_invalid")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("diagnostic_dirty_tree")
    sha = git("rev-parse", "HEAD")
    if args.ci_run is None or args.protocol_report is None or args.protocol_report.stat().st_size > 1_000_000:
        raise ValueError("diagnostic_public_evidence_required")
    ci = json.loads(subprocess.run(["gh", "run", "view", str(args.ci_run), "--json",
        "headSha,status,conclusion,jobs,url,updatedAt"], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=45).stdout)
    protocol = args.protocol_report.read_bytes()
    evidence = verify_real_evidence(ADVICE_COACH_CONTRACT.snapshot(), implementation_sha=sha,
                                  ci=ci, protocol_bytes=protocol)
    directory = ROOT / "data/runs/golden_stream_diagnostics" / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "reservation.json", {"inputs": config["inputs"], "identity": identity,
        "implementation_sha": sha, "ci": ci, "real_evidence": evidence.model_dump(mode="json")})
    with (directory / "protocol.json").open("xb") as handle:
        handle.write(protocol)
        handle.flush()
        os.fsync(handle.fileno())
    result = supervise([sys.executable, "-B", "-m", "scripts.diagnose_coach_golden_stream",
                        "--child", str(directory)], directory=directory)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # No raw provider exception, prompt, credentials or player inputs on console.
        print('{"error":"diagnostic_failed"}')
        raise SystemExit(1) from None
