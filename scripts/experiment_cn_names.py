import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.lol.data_dragon import DataDragonService
from app.lol.name_naturalizer import (
    build_naturalization_prompt,
    collect_name_candidates,
    parse_naturalization_response,
)
from app.lol.terminology import TerminologyStore


def main():
    parser = argparse.ArgumentParser(
        description="Experiment with GLM-selected natural CN LoL names."
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument(
        "--output",
        required=True,
    )
    parser.add_argument(
        "--terminology",
        default="data/terminology/cn_lol_terms.json",
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Print candidates and prompt without calling GLM.",
    )
    args = parser.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary JSON not found: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ddragon = DataDragonService(language="zh_CN")
    terminology = TerminologyStore(Path(args.terminology))
    candidates = collect_name_candidates(summary, ddragon, terminology)
    prompt = build_naturalization_prompt(candidates)

    print(
        f"Collected {len(candidates['champions'])} champions and "
        f"{len(candidates['items'])} unresolved items; "
        f"reused {len(candidates['confirmed_items'])} confirmed item terms."
    )
    if args.prompt_only:
        print("\n", prompt)
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
                "content": "你负责选择英雄联盟国服玩家最自然的常用称呼，并严格输出 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    result = parse_naturalization_response(
        response.choices[0].message.content or ""
    )
    result["confirmed_champions"] = candidates["confirmed_champions"]
    result["confirmed_items"] = candidates["confirmed_items"]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Name experiment saved to:", output_path)


if __name__ == "__main__":
    main()
