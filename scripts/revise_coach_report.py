import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.artifacts import evaluation_path, revised_report_path
from app.evaluation.coach_report import (
    build_revision_prompt,
    validate_revised_report,
)
from app.harness.adapters import ChatCoachReviser
from app.harness.steps import (
    EvaluationResult,
    EvaluationVerdict,
    KnowledgeEvidence,
    RevisionRequest,
)
from app.providers.config import create_zhipu_provider, load_zhipu_settings
from app.tools.adapters import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


REVISER_SYSTEM_PROMPT = "你是报告校订员，只修正已经明确指出的事实问题。"


def create_revision_runtime() -> ToolRuntime:
    load_dotenv()
    provider = create_zhipu_provider(load_zhipu_settings())
    registry = ToolRegistry()
    for definition in build_llm_tools(provider):
        registry.register(definition)
    return ToolRuntime(registry)


def main():
    parser = argparse.ArgumentParser(
        description="Revise a Coach report from evaluation issues."
    )
    parser.add_argument("--report", required=True)
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
        Path(args.evaluation)
        if args.evaluation
        else evaluation_path(report_path)
    )
    output_path = (
        Path(args.output)
        if args.output
        else revised_report_path(report_path)
    )
    report = report_path.read_text(encoding="utf-8")
    evaluation = json.loads(evaluation_file.read_text(encoding="utf-8"))
    if not evaluation.get("issues"):
        print("Evaluation has no issues; no revision is needed.")
        return

    result = EvaluationResult(
        score=evaluation["score"],
        verdict=EvaluationVerdict(evaluation["verdict"]),
        issues=tuple(evaluation.get("issues", [])),
        passed_checks=tuple(evaluation.get("passed_checks", [])),
        summary=evaluation.get("summary", ""),
    )
    adapter = ChatCoachReviser(
        runtime=create_revision_runtime(),
        system_prompt=REVISER_SYSTEM_PROMPT,
        prompt_builder=build_revision_prompt,
        validator=validate_revised_report,
    )
    revised = adapter.revise(
        RevisionRequest(
            player_summary={},
            deterministic_report="",
            knowledge=KnowledgeEvidence.empty(),
            report=report,
            evaluation=result,
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(revised.report + "\n", encoding="utf-8")
    print(f"Revised report saved to: {output_path}")


if __name__ == "__main__":
    main()
