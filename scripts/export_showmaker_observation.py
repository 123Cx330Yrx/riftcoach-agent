"""Export the verified ShowMaker observation as a local, create-only JSON archive."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.evaluation.observation_archive import export_observation

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=ROOT / "data/runs/golden_slice")
    parser.add_argument("--manual-review", type=Path, required=True, help="已绑定 golden_manual_reviews 的人工复核副本")
    parser.add_argument("--output", type=Path, default=ROOT / "data/observation_exports/showmaker.json")
    args = parser.parse_args()
    archive = export_observation(
        runs_root=args.runs_root,
        manual_review=args.manual_review,
        output=args.output,
    )
    print(json.dumps({
        "schema_version": archive["schema_version"],
        "scope": archive["scope"],
        "source_run_id": archive["source_run_id"],
        "output": str(args.output),
        "create_only": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
