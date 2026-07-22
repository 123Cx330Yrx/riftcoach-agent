import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.coach_report import (
    build_evaluation_prompt,
    build_fact_pack,
    parse_evaluation_response,
)
from app.artifacts import coach_report_path, evaluation_path
from app.lol.data_dragon import DataDragonService
from app.lol.summary_schema import validate_summary_document
from app.lol.terminology import TerminologyStore


def main():
    parser = argparse.ArgumentParser(description="Evaluate a RiftCoach Coach report.")
    parser.add_argument("--summary", required=True)
    parser.add_argument(
        "--report",
        help="Optional Coach report path derived from the summary when omitted.",
    )
    parser.add_argument(
        "--terminology",
        default="data/terminology/cn_lol_terms.json",
    )
    parser.add_argument(
        "--output",
        help="Optional evaluation output path derived from the report when omitted.",
    )
    args = parser.parse_args()

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate_summary_document(summary)
    report_path = Path(args.report) if args.report else coach_report_path(summary)
    output_path = Path(args.output) if args.output else evaluation_path(report_path)
    terminology = TerminologyStore(Path(args.terminology))
    display_summary = terminology.apply_to_summary(
        summary,
        DataDragonService(language="zh_CN"),
    )
    fact_pack = build_fact_pack(display_summary)
    report = report_path.read_text(encoding="utf-8")

    load_dotenv()
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")
    if not all((api_key, base_url, model)):
        raise RuntimeError("LLM_API_KEY, LLM_BASE_URL and LLM_MODEL are required.")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是独立事实审查员，只依据输入证据检查报告。",
            },
            {
                "role": "user",
                "content": build_evaluation_prompt(fact_pack, report),
            },
        ],
        temperature=0.0,
    )
    evaluation = parse_evaluation_response(
        response.choices[0].message.content or ""
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Evaluation score: {evaluation['score']}")
    print(f"Verdict: {evaluation['verdict']}")
    print(f"Issues: {len(evaluation['issues'])}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
