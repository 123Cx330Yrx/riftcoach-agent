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


def measure(source, report_path, *, scope=False, scope_v3=False, scope_v4=False, scope_v5=False, fact_inference=False, failed_response=None):
    from app.runtime.coach_contract import FACT_INFERENCE_COACH_CONTRACT, FEEDBACK_COACH_CONTRACT, SCOPE_COACH_CONTRACT, SCOPE_V3_COACH_CONTRACT, SCOPE_V4_COACH_CONTRACT
    contract = FACT_INFERENCE_COACH_CONTRACT if fact_inference else FEEDBACK_COACH_CONTRACT if scope_v5 else SCOPE_V4_COACH_CONTRACT if scope_v4 else SCOPE_V3_COACH_CONTRACT if scope_v3 else SCOPE_COACH_CONTRACT if scope else CONTRACT
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
            if scope or scope_v3 or scope_v4 or scope_v5 or fact_inference:
                for item in evaluation["coverage"]: item["scope_ambiguous"] = False
            if scope_v4 or scope_v5 or fact_inference:
                evaluation["coverage"] = [[r["block_id"], "N", "N", False] for r in evaluation["coverage"]]
            content = json.dumps(evaluation) if request.response_contract else report
            if failed_response is not None and len(requests) == 1:
                content = json.loads(failed_response.read_text(encoding="utf-8"))["content"]
            return ChatResponse(content=content,
                model=self.model_name, provider=self.provider_name, finish_reason="stop", usage=TokenUsage())

    registry = ToolRegistry()
    for definition in build_llm_tools(CoachBudgetedProvider(Offline(), coach_contract=contract), request_policy=contract.request_policy):
        registry.register(definition)
    options = dict(runtime=ToolRuntime(registry), inference_audit="fact_v1" if fact_inference else "scope_v5" if scope_v5 else "scope_v4" if scope_v4 else "scope_v3" if scope_v3 else "scope" if scope else "coverage", include_generation_facts=True, include_deterministic_facts=True,
                   position_policy=contract.position_policy, source_use_policy=contract.source_use_policy, compact_report_policy=contract.compact_report_policy)
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
    parser.add_argument("--scope", action="store_true")
    parser.add_argument("--scope-v3", action="store_true")
    parser.add_argument("--scope-v4", action="store_true")
    parser.add_argument("--scope-v5", action="store_true")
    parser.add_argument("--failed-response", type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.source_run, args.report, scope=args.scope, scope_v3=args.scope_v3, scope_v4=args.scope_v4, scope_v5=args.scope_v5, failed_response=args.failed_response)))
