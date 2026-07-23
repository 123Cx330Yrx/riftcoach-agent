import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.coach_report import (
    build_evaluation_prompt,
    build_fact_pack,
    build_revision_prompt,
    parse_evaluation_response,
    validate_revised_report,
)
from app.harness.adapters import (
    ChatCoachGenerator,
    ChatCoachReviser,
    ChatEvaluationAdapter,
    LocalRagAdapter,
)
from app.harness.models import HarnessConfig
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft,
    EvaluationResult,
    EvaluationVerdict,
)
from app.harness.store import FileRunStore
from app.lol.summary_schema import validate_summary_document
from app.rag.retriever import LocalKnowledgeRetriever
from scripts.generate_llm_coach_report import (
    SYSTEM_PROMPT,
    build_retrieval_query,
    build_user_prompt,
    compact_summary,
)


EVALUATOR_SYSTEM_PROMPT = "你是独立事实审查员，只依据输入证据检查报告。"
REVISER_SYSTEM_PROMPT = "你是报告校订员，只修正已明确指出的事实问题。"


class DryRunGenerator:
    """Deterministic model substitute; all non-model Harness steps remain real."""

    def generate(self, request) -> CoachDraft:
        sources = "、".join(request.knowledge.source_ids) or "未命中知识来源"
        return CoachDraft(
            report=(
                "# RiftCoach 教练式复盘报告\n\n"
                "## 1. 总体结论\n"
                "这是 dry-run 生成的本地验证草稿，不代表真实 Coach 结论。\n\n"
                "## 2. 当前表现亮点\n"
                "dry-run 不解释具体表现。\n\n"
                "## 3. 主要风险点\n"
                "dry-run 不推断具体风险。\n\n"
                "## 4. 赢局与输局差异\n"
                "dry-run 不比较具体指标。\n\n"
                "## 5. 下一步复盘建议\n"
                "正式运行后再根据事实和知识生成建议。\n\n"
                "## 6. 训练计划\n"
                "dry-run 不发布真实训练计划。\n\n"
                "## 7. 数据边界与知识来源\n"
                f"本次仅验证 Harness；检索来源：{sources}。\n"
            )
        )


class DryRunEvaluator:
    def evaluate(self, request) -> EvaluationResult:
        return EvaluationResult(
            score=100,
            verdict=EvaluationVerdict.PASS,
            passed_checks=("dry_run_harness_contract",),
            summary="Dry-run 使用确定性评测结果验证发布路径。",
        )


class DryRunReviser:
    def revise(self, request) -> CoachDraft:
        raise AssertionError("Passing dry-run must not invoke revision.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run RiftCoach's quality-gated review Harness from facts to a "
            "published or deterministic fallback report."
        )
    )
    parser.add_argument("--summary", required=True, help="Player Summary JSON path.")
    parser.add_argument(
        "--deterministic-report",
        required=True,
        help="Deterministic Markdown report path.",
    )
    parser.add_argument(
        "--runs-root",
        default="data/runs",
        help="Directory that stores immutable Harness runs.",
    )
    parser.add_argument(
        "--run-id",
        help="Unique run identifier. A UTC-based identifier is generated when omitted.",
    )
    parser.add_argument(
        "--knowledge-dir",
        default="data/rag_docs",
        help="Directory containing local Markdown knowledge.",
    )
    parser.add_argument("--rag-top-k", type=int, default=5)
    parser.add_argument("--publish-score-threshold", type=int, default=85)
    parser.add_argument("--max-revisions", type=int, default=1)
    parser.add_argument(
        "--no-deterministic-fallback",
        action="store_true",
        help="Reject instead of publishing the deterministic report on failure.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use deterministic fake model steps without consuming model quota.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary_path = Path(args.summary)
    deterministic_path = Path(args.deterministic_report)
    if not summary_path.is_file():
        raise FileNotFoundError(f"Summary JSON not found: {summary_path}")
    if not deterministic_path.is_file():
        raise FileNotFoundError(
            f"Deterministic report not found: {deterministic_path}"
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validate_summary_document(summary)
    deterministic_report = deterministic_path.read_text(encoding="utf-8")
    if not deterministic_report.strip():
        raise ValueError("Deterministic report must not be empty.")

    run_id = args.run_id or generate_run_id()
    store = FileRunStore(args.runs_root, run_id)
    retriever = LocalRagAdapter(
        retriever=LocalKnowledgeRetriever(Path(args.knowledge_dir)),
        query_builder=build_retrieval_query,
        top_k=args.rag_top_k,
    )
    if args.dry_run:
        generator = DryRunGenerator()
        evaluator = DryRunEvaluator()
        reviser = DryRunReviser()
    else:
        client, model = create_llm_client()
        generator = ChatCoachGenerator(
            client=client,
            model=model,
            system_prompt=SYSTEM_PROMPT,
            summary_compactor=compact_summary,
            prompt_builder=build_user_prompt,
        )
        evaluator = ChatEvaluationAdapter(
            client=client,
            model=model,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            fact_pack_builder=build_fact_pack,
            prompt_builder=build_evaluation_prompt,
            response_parser=parse_evaluation_response,
        )
        reviser = ChatCoachReviser(
            client=client,
            model=model,
            system_prompt=REVISER_SYSTEM_PROMPT,
            prompt_builder=build_revision_prompt,
            validator=validate_revised_report,
        )

    harness = ReviewHarness(
        store=store,
        retriever=retriever,
        generator=generator,
        evaluator=evaluator,
        reviser=reviser,
        config=HarnessConfig(
            publish_score_threshold=args.publish_score_threshold,
            max_revisions=args.max_revisions,
            allow_deterministic_fallback=not args.no_deterministic_fallback,
        ),
    )
    manifest = harness.run(
        player_summary=summary,
        deterministic_report=deterministic_report,
    )

    print("Run ID:", manifest.run_id)
    print("Status:", manifest.status.value)
    print("Decision:", manifest.final_decision)
    print("Revisions:", manifest.revision_count)
    print("Manifest:", store.manifest_path)
    final_report = store.run_directory / "output/final_report.md"
    print("Final report:", final_report if final_report.exists() else "not published")
    return 0 if manifest.status.value in {"published", "degraded"} else 1


def create_llm_client() -> tuple[OpenAI, str]:
    """Temporary wiring; Stage 3 will replace this with the Provider Runtime."""

    load_dotenv()
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")
    missing = [
        name
        for name, value in (
            ("LLM_API_KEY", api_key),
            ("LLM_BASE_URL", base_url),
            ("LLM_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing LLM configuration: {', '.join(missing)}")
    return OpenAI(api_key=api_key, base_url=base_url), model


def generate_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"review_{timestamp}_{uuid4().hex[:8]}"


if __name__ == "__main__":
    raise SystemExit(main())
