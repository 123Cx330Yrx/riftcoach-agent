"""Measure real-shaped evaluation/revision requests without external calls."""
import argparse
import json
from pathlib import Path

from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter, GroundedCoachReviser
from app.evaluation.coach_report import build_fact_pack, EVALUATOR_SYSTEM_PROMPT, REVISER_SYSTEM_PROMPT
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence, KnowledgeCitation
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.coach_contract import COVERAGE_COACH_CONTRACT as CONTRACT
from app.runtime.coach_budget import CoachBudgetedProvider
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from app.tools.adapters.llm import build_llm_tools
from scripts.check_coach_golden_replay import _ReplayProvider


def measure(source, report_path):
    summary = json.loads((source / "inputs/player_summary.json").read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    deterministic = (source / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    data = json.loads((source / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    knowledge = KnowledgeEvidence(context=data["context"], source_ids=tuple(data["source_ids"]), citations=tuple(KnowledgeCitation(**v) for v in data["citations"]))
    requests = []

    class Offline(_ReplayProvider):
        def chat(self, request):
            requests.append(request)
            evaluation = {"score": 95, "verdict": "pass", "issues": [], "passed_checks": [], "summary": "Scripted size probe only",
                "audits": [{"kind": kind, "status": "not_applicable", "claims": []} for kind in ("metric_to_ability", "cohort_comparison")],
                "coverage": [{"block_id": b["block_id"], "metric_to_ability": "not_applicable", "cohort_comparison": "not_applicable"} for b in report_blocks(report)]}
            return ChatResponse(content=json.dumps(evaluation) if request.response_contract else report,
                model=self.model_name, provider=self.provider_name, finish_reason="stop", usage=TokenUsage())

    registry = ToolRegistry()
    for definition in build_llm_tools(CoachBudgetedProvider(Offline(), coach_contract=CONTRACT), request_policy=CONTRACT.request_policy):
        registry.register(definition)
    options = dict(runtime=ToolRuntime(registry), inference_audit="coverage", include_generation_facts=True, include_deterministic_facts=True,
                   position_policy=CONTRACT.position_policy, source_use_policy=CONTRACT.source_use_policy, compact_report_policy=CONTRACT.compact_report_policy)
    evaluator = GroundedChatEvaluationAdapter(system_prompt=EVALUATOR_SYSTEM_PROMPT, fact_pack_builder=build_fact_pack, **options)
    result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, report, "Observe report quality."))
    reviser = GroundedCoachReviser(system_prompt=REVISER_SYSTEM_PROMPT, prompt_builder=lambda *x: "unused", validator=lambda *x: None, **options)
    reviser.revise(RevisionRequest(summary, deterministic, knowledge, report, result))
    return {"scope": "offline_request_size_not_semantic_quality", "external_calls": 0, "blocks": len(result.coverage),
            "input_ceilings": [estimate_runtime_request_input_ceiling(r) for r in requests], "output_caps": [r.max_tokens for r in requests]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.source_run, args.report)))
