import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.lol.data_dragon import DataDragonService
from app.lol.terminology_review import build_review_queue, load_json


def main():
    parser = argparse.ArgumentParser(description="Prepare a terminology review queue.")
    parser.add_argument(
        "--experiment",
        required=True,
    )
    parser.add_argument(
        "--summary",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    ddragon = DataDragonService(language="zh_CN")
    queue = build_review_queue(
        load_json(Path(args.experiment)),
        load_json(Path(args.summary)),
        ddragon,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Review queue created: {output_path}")
    print(f"Pending entries: {len(queue['entries'])}")


if __name__ == "__main__":
    main()
