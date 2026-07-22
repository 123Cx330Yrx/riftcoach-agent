import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.coach_report import build_revision_prompt, validate_revised_report
from app.artifacts import evaluation_path, revised_report_path


def main():
    parser = argparse.ArgumentParser(description="Revise a Coach report from evaluation issues.")
    parser.add_argument(
        "--report",
        required=True,
    )
    parser.add_argument(
        "--evaluation",
        help="Optional evaluation path derived from the report when omitted.",
    )
    parser.add_argument(
        "--output",
        help="Optional revised report path derived from the report when omitted.",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    evaluation_file = (
        Path(args.evaluation) if args.evaluation else evaluation_path(report_path)
    )
    output_path = Path(args.output) if args.output else revised_report_path(report_path)
    report = report_path.read_text(encoding="utf-8")
    evaluation = json.loads(evaluation_file.read_text(encoding="utf-8"))
    if not evaluation.get("issues"):
        print("Evaluation has no issues; no revision is needed.")
        return

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
                "content": "你是报告校订员，只修正已明确指出的事实问题。",
            },
            {
                "role": "user",
                "content": build_revision_prompt(report, evaluation),
            },
        ],
        temperature=0.0,
    )
    revised = (response.choices[0].message.content or "").strip()
    validate_revised_report(revised, report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(revised + "\n", encoding="utf-8")
    print(f"Revised report saved to: {output_path}")


if __name__ == "__main__":
    main()
