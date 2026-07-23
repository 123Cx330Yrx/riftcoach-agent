import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from app.harness.adapters import (
    ChatCoachGenerator,
    ChatCoachReviser,
    ChatEvaluationAdapter,
    LocalRagAdapter,
)
from app.harness.steps import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    GenerationRequest,
    KnowledgeEvidence,
    RetrievalRequest,
    RevisionRequest,
)
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse
from app.rag.retriever import LocalKnowledgeRetriever
from app.tools.adapters import build_knowledge_tools, build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from scripts.run_review_harness import main as run_harness_main


@dataclass
class RecordingProvider:
    responses: list[str]
    provider_name: str = "fake-provider"

    def __post_init__(self):
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        if not self.responses:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="no_fake_response",
            )
        return ChatResponse(
            content=self.responses.pop(0),
            model="glm-test",
            provider=self.provider_name,
        )


def llm_runtime(provider):
    registry = ToolRegistry()
    for definition in build_llm_tools(provider):
        registry.register(definition)
    return ToolRuntime(
        registry,
        sleep=lambda _: None,
        call_id_factory=lambda: "test-call",
    )


class LocalRagAdapterTests(unittest.TestCase):
    def test_retrieval_formats_context_and_preserves_source_ids(self) -> None:
        with TemporaryDirectory() as directory:
            knowledge_dir = Path(directory)
            (knowledge_dir / "review.md").write_text(
                "# 视野复盘\n视野分只能作为录像复盘线索，不能证明因果。\n",
                encoding="utf-8",
            )
            registry = ToolRegistry()
            for definition in build_knowledge_tools(
                LocalKnowledgeRetriever(knowledge_dir)
            ):
                registry.register(definition)
            adapter = LocalRagAdapter(
                runtime=ToolRuntime(registry),
                query_builder=lambda summary: "视野分 因果",
                top_k=3,
            )

            result = adapter.retrieve(
                RetrievalRequest(
                    player_summary={"recent_summary": {}},
                    deterministic_report="# 确定性报告",
                )
            )

        self.assertIn("视野分只能作为录像复盘线索", result.context)
        self.assertEqual(("review.md",), result.source_ids)


class ChatCoachGeneratorTests(unittest.TestCase):
    def test_generator_reuses_injected_prompt_builders(self) -> None:
        provider = RecordingProvider(
            ["# RiftCoach 教练式复盘报告\n\n内容"]
        )
        calls = []
        adapter = ChatCoachGenerator(
            runtime=llm_runtime(provider),
            system_prompt="system",
            summary_compactor=lambda summary: {"compact": summary["value"]},
            prompt_builder=lambda summary, report, evidence: calls.append(
                (summary, report, evidence)
            )
            or "generated prompt",
        )

        result = adapter.generate(
            GenerationRequest(
                player_summary={"value": 7},
                deterministic_report="facts",
                knowledge=KnowledgeEvidence("knowledge", ("source.md",)),
            )
        )

        self.assertEqual(
            "# RiftCoach 教练式复盘报告\n\n内容",
            result.report,
        )
        self.assertEqual(
            [({"compact": 7}, "facts", "knowledge")],
            calls,
        )
        request = provider.requests[0]
        self.assertEqual("generated prompt", request.messages[1].content)

    def test_generator_surfaces_safe_tool_failure(self) -> None:
        adapter = ChatCoachGenerator(
            runtime=llm_runtime(RecordingProvider([])),
            system_prompt="system",
            summary_compactor=lambda summary: summary,
            prompt_builder=lambda summary, report, evidence: "prompt",
        )

        with self.assertRaisesRegex(RuntimeError, "no_fake_response"):
            adapter.generate(
                GenerationRequest(
                    player_summary={},
                    deterministic_report="facts",
                    knowledge=KnowledgeEvidence.empty(),
                )
            )


class ChatEvaluationAdapterTests(unittest.TestCase):
    def test_evaluator_converts_parser_output_to_step_result(self) -> None:
        provider = RecordingProvider(["raw evaluator response"])
        adapter = ChatEvaluationAdapter(
            runtime=llm_runtime(provider),
            system_prompt="review system",
            fact_pack_builder=lambda summary: {"facts": summary["value"]},
            prompt_builder=lambda facts, report: f"{facts['facts']}::{report}",
            response_parser=lambda content: {
                "score": 78,
                "verdict": "needs_revision",
                "issues": [{"category": "causality"}],
                "passed_checks": ["数字忠实"],
                "summary": content,
            },
        )

        result = adapter.evaluate(
            EvaluationRequest(
                player_summary={"value": "fact-pack"},
                deterministic_report="facts",
                knowledge=KnowledgeEvidence.empty(),
                report="draft",
            )
        )

        self.assertEqual(78, result.score)
        self.assertIs(EvaluationVerdict.NEEDS_REVISION, result.verdict)
        self.assertEqual(({"category": "causality"},), result.issues)
        self.assertEqual("raw evaluator response", result.summary)


class ChatCoachReviserTests(unittest.TestCase):
    def test_reviser_passes_structured_issues_to_validator(self) -> None:
        revised = "# RiftCoach 教练式复盘报告\n\n修订内容"
        provider = RecordingProvider([revised])
        prompt_calls = []
        validation_calls = []
        adapter = ChatCoachReviser(
            runtime=llm_runtime(provider),
            system_prompt="revision system",
            prompt_builder=lambda report, evaluation: prompt_calls.append(
                (report, evaluation)
            )
            or "revision prompt",
            validator=lambda candidate, original: validation_calls.append(
                (candidate, original)
            ),
        )
        evaluation = EvaluationResult(
            score=70,
            verdict=EvaluationVerdict.NEEDS_REVISION,
            issues=({"category": "causality"},),
            summary="需要降低因果表述。",
        )

        result = adapter.revise(
            RevisionRequest(
                player_summary={},
                deterministic_report="facts",
                knowledge=KnowledgeEvidence.empty(),
                report="original",
                evaluation=evaluation,
            )
        )

        self.assertEqual(revised, result.report)
        self.assertEqual((revised, "original"), validation_calls[0])
        payload = prompt_calls[0][1]
        self.assertEqual("needs_revision", payload["verdict"])
        self.assertEqual([{"category": "causality"}], payload["issues"])


class ReviewHarnessCliTests(unittest.TestCase):
    def test_dry_run_executes_real_store_retrieval_and_publication(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "summary.json"
            report_path = root / "deterministic.md"
            knowledge_dir = root / "knowledge"
            runs_root = root / "runs"
            knowledge_dir.mkdir()
            knowledge_dir.joinpath("boundaries.md").write_text(
                "# 数据边界\n统计差异只用于提出复盘假设。\n",
                encoding="utf-8",
            )
            summary_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "metadata": {"source": "fixture"},
                        "player": {
                            "game_name": "Example",
                            "tag_line": "TEST",
                            "riot_id": "Example#TEST",
                        },
                        "request": {"count": 1},
                        "recent_summary": {
                            "games_analyzed": 1,
                            "averages": {},
                            "win_loss_comparison": {},
                            "role_summary": [],
                        },
                        "matches": [],
                        "failed_matches": [],
                        "excluded_matches": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report_path.write_text(
                "# RiftCoach 确定性报告\n\n本地测试。\n",
                encoding="utf-8",
            )

            exit_code = run_harness_main(
                [
                    "--summary",
                    str(summary_path),
                    "--deterministic-report",
                    str(report_path),
                    "--knowledge-dir",
                    str(knowledge_dir),
                    "--runs-root",
                    str(runs_root),
                    "--run-id",
                    "dry_run_fixture",
                    "--dry-run",
                ]
            )

            manifest = json.loads(
                runs_root.joinpath(
                    "dry_run_fixture",
                    "manifest.json",
                ).read_text(encoding="utf-8")
            )
            final_report = (
                runs_root
                / "dry_run_fixture"
                / "output"
                / "final_report.md"
            )
            final_report_exists = final_report.exists()

        self.assertEqual(0, exit_code)
        self.assertEqual("published", manifest["status"])
        self.assertEqual("published", manifest["final_decision"])
        self.assertTrue(final_report_exists)


if __name__ == "__main__":
    unittest.main()
