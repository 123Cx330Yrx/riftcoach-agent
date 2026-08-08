import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.artifacts import coach_report_path, evaluation_path
from app.evaluation.coach_report import (
    build_evaluation_prompt,
    build_fact_pack,
)
from app.harness.adapters import ChatEvaluationAdapter
from app.harness.steps import EvaluationRequest, KnowledgeEvidence
from app.lol.data_dragon import DataDragonService
from app.lol.summary_schema import validate_summary_document
from app.lol.terminology import TerminologyStore
from app.providers.config import create_zhipu_provider, load_zhipu_settings
from app.tools.adapters import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


EVALUATOR_SYSTEM_PROMPT = "你是独立事实审查员，只依据输入证据检查报告。"


def create_evaluation_runtime() -> ToolRuntime:
    load_dotenv()
    provider = create_zhipu_provider(load_zhipu_settings())
    registry = ToolRegistry()
    for definition in build_llm_tools(provider):
        registry.register(definition)
    return ToolRuntime(registry)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a RiftCoach Coach report."
    )
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
    report_path = (
        Path(args.report) if args.report else coach_report_path(summary)
    )
    output_path = (
        Path(args.output) if args.output else evaluation_path(report_path)
    )
    terminology = TerminologyStore(Path(args.terminology))
    display_summary = terminology.apply_to_summary(
        summary,
        DataDragonService(language="zh_CN"),
    )
    report = report_path.read_text(encoding="utf-8")

    adapter = ChatEvaluationAdapter(
        runtime=create_evaluation_runtime(),
        system_prompt=EVALUATOR_SYSTEM_PROMPT,
        fact_pack_builder=build_fact_pack,
        prompt_builder=build_evaluation_prompt,
    )
    result = adapter.evaluate(
        EvaluationRequest(
            player_summary=display_summary,
            deterministic_report="",
            knowledge=KnowledgeEvidence.empty(),
            report=report,
        )
    )
    evaluation = {
        "score": result.score,
        "verdict": result.verdict.value,
        "issues": [dict(issue) for issue in result.issues],
        "passed_checks": list(result.passed_checks),
        "summary": result.summary,
    }

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
