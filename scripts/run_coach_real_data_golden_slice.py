"""Run the bounded real-data Coach golden slice.

Without ``--execute`` this command is a zero-network preflight.  Execution
requires an explicit Riot target and may optionally run the unadmitted Coach
provider seam with ``--with-provider``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from app.evaluation.coach_real_data_golden_slice import (
    ROOT,
    GoldenSliceConfig,
    preflight,
    run_golden_slice,
)
from app.evaluation.golden_journal import write_new_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--riot-id", required=True)
    parser.add_argument("--region", choices=("americas", "asia", "europe", "sea"), required=True)
    parser.add_argument("--count", type=int, choices=tuple(range(1, 6)), default=5)
    parser.add_argument("--position", choices=("auto", "top", "mid", "jungle", "adc", "support"), default="auto",
                        help="Legacy option; data selection always follows actual match positions.")
    parser.add_argument("--training-position", choices=("top", "mid", "jungle", "adc", "support"),
                        action="append", default=[], help="Explicit training goal; repeat for multiple positions.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--with-provider", action="store_true")
    parser.add_argument("--saved-run-id", help="Reuse verified match facts; zero Riot player API calls")
    parser.add_argument("--saved-summary-digest", help="Expected canonical digest of the original Summary")
    parser.add_argument("--ci-run", type=int, help="Successful public CI for this exact committed implementation")
    parser.add_argument("--protocol-report", type=Path, help="Fresh real G53-3-L evidence after the public CI")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = GoldenSliceConfig(
        riot_id=args.riot_id,
        routing_region=args.region,
        count=args.count,
        position=args.position,
        training_positions=tuple(args.training_position),
        run_id=args.run_id,
        with_provider=args.with_provider,
        saved_run_id=args.saved_run_id,
        saved_summary_digest=args.saved_summary_digest,
    )
    gate = preflight(config)
    if not args.execute:
        print(gate.model_dump_json(indent=2))
        return 0
    output = args.output or (ROOT / "data/evaluation/results/golden_slices" / f"{args.run_id}.json")
    output = output if output.is_absolute() else ROOT / output
    output = output.resolve()
    if not output.is_relative_to((ROOT / "data/evaluation/results/golden_slices").resolve()):
        raise SystemExit("output must remain inside data/evaluation/results/golden_slices")
    if output.exists():
        raise SystemExit("refusing to overwrite an existing golden-slice receipt")
    ci = None
    protocol_bytes = None
    if args.with_provider:
        if args.ci_run is None or args.protocol_report is None:
            raise SystemExit("provider execution requires exact-SHA public CI and fresh protocol evidence")
        if args.protocol_report.stat().st_size > 1_000_000:
            raise SystemExit("protocol report exceeds the input bound")
        protocol_bytes = args.protocol_report.read_bytes()
        ci = json.loads(subprocess.run(["gh", "run", "view", str(args.ci_run), "--json",
            "headSha,status,conclusion,jobs,url,updatedAt"], cwd=ROOT,
            check=True, capture_output=True, text=True, timeout=45).stdout)
    load_dotenv(ROOT.parent / "riftcoach-agent" / ".env")
    receipt = run_golden_slice(config, environ=os.environ, ci=ci, protocol_bytes=protocol_bytes)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new_json(output, receipt.model_dump(mode="json"))
    print(json.dumps({"result": receipt.result, "bundle_digest": receipt.evidence_bundle_digest, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
