import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.lol.terminology_review import apply_review_decisions, load_json


def main():
    parser = argparse.ArgumentParser(description="Apply explicit decisions to a review queue.")
    parser.add_argument(
        "--review",
        required=True,
    )
    parser.add_argument(
        "--decisions",
        default="data/terminology/review_decisions_latest.json",
    )
    args = parser.parse_args()

    review_path = Path(args.review)
    updated, changed = apply_review_decisions(
        load_json(review_path),
        load_json(Path(args.decisions)),
    )
    review_path.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Confirmed review entries: {changed}")
    print(f"Unlisted entries remain pending in: {review_path}")


if __name__ == "__main__":
    main()
