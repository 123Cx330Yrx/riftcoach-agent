import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.lol.terminology_review import apply_confirmed_reviews, load_json


def main():
    parser = argparse.ArgumentParser(description="Apply confirmed terminology reviews.")
    parser.add_argument(
        "--review",
        required=True,
    )
    parser.add_argument(
        "--terminology",
        default="data/terminology/cn_lol_terms.json",
    )
    args = parser.parse_args()

    review_path = Path(args.review)
    terminology_path = Path(args.terminology)
    updated, applied = apply_confirmed_reviews(
        load_json(review_path),
        load_json(terminology_path),
    )
    if applied == 0:
        print("No confirmed entries found; terminology was not changed.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = terminology_path.with_suffix(f".{timestamp}.bak.json")
    shutil.copy2(terminology_path, backup_path)
    terminology_path.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Applied confirmed entries: {applied}")
    print(f"Backup: {backup_path}")
    print(f"Updated terminology: {terminology_path}")


if __name__ == "__main__":
    main()
