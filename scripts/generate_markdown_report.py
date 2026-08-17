import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.lol.data_dragon import DataDragonService
from app.artifacts import deterministic_report_path
from app.lol.report_renderer import build_report
from app.lol.summary_schema import validate_summary_document
from app.lol.terminology import TerminologyStore


def load_summary(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    validate_summary_document(data)
    return data


def main():
    parser = argparse.ArgumentParser(description="Generate Markdown report from player summary JSON.")

    parser.add_argument(
        "--input",
        required=True,
        help="Path to player summary JSON.",
    )

    parser.add_argument(
        "--output",
        help="Optional output path. Derived from the summary player when omitted.",
    )
    parser.add_argument(
        "--terminology",
        default="data/terminology/cn_lol_terms.json",
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    data = load_summary(input_path)
    output_path = Path(args.output) if args.output else deterministic_report_path(data)
    terminology = TerminologyStore(Path(args.terminology))
    ddragon = DataDragonService(language="zh_CN")
    data = terminology.apply_to_summary(data, ddragon)
    report = build_report(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print("Report generated:", output_path)


if __name__ == "__main__":
    main()
