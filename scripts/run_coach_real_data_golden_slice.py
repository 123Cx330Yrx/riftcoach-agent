"""Run the bounded real-data Coach golden slice.

Without ``--execute`` this command is a zero-network preflight.  Execution
requires an explicit Riot target and may optionally run the unadmitted Coach
provider seam with ``--with-provider``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from app.evaluation.coach_real_data_golden_slice import (
    ROOT,
    GoldenSliceConfig,
    preflight,
    run_golden_slice,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--riot-id", required=True)
    parser.add_argument("--region", choices=("americas", "asia", "europe", "sea"), required=True)
    parser.add_argument("--count", type=int, choices=tuple(range(1, 6)), default=5)
    parser.add_argument("--position", choices=("top", "mid", "jungle", "adc", "support"), default="mid")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--with-provider", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = GoldenSliceConfig(
        riot_id=args.riot_id,
        routing_region=args.region,
        count=args.count,
        position=args.position,
        run_id=args.run_id,
        with_provider=args.with_provider,
    )
    gate = preflight(config)
    if not args.execute:
        print(gate.model_dump_json(indent=2))
        return 0
    load_dotenv(ROOT.parent / "riftcoach-agent" / ".env")
    receipt = run_golden_slice(config, environ=os.environ)
    output = args.output or (ROOT / "data/evaluation/results/golden_slices" / f"{args.run_id}.json")
    output = output if output.is_absolute() else ROOT / output
    output = output.resolve()
    if not output.is_relative_to((ROOT / "data/evaluation/results/golden_slices").resolve()):
        raise SystemExit("output must remain inside data/evaluation/results/golden_slices")
    if output.exists():
        raise SystemExit("refusing to overwrite an existing golden-slice receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": receipt.result, "bundle_digest": receipt.evidence_bundle_digest, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
