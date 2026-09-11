"""Offline control-flow probe: real-shaped facts, full RAG, scripted responses.

No reconstructed historical model text or quality claim. Temporary private run
artifacts are removed on exit; output contains only digests, counts and enums.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.context import DeterministicContextSizer
from app.agent.loop import AgentLoop
from app.evaluation.coach_real_data_golden_slice import render_golden_context_report
from app.evaluation.glm53_bounded_revision_budget_reachability import (
    _WorstPathProvider, estimate_runtime_request_input_ceiling,
)
from app.harness.store import FileRunStore
from app.product.coach_composition import build_coach_application
from app.product.coach_positions import position_context
from app.product.recent_review import RecentReviewProductRequest
from app.providers.models import TokenUsage, ToolCall
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT


class _ReplayProvider(_WorstPathProvider):
    thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
    sdk_max_retries = 0

    def __init__(self, *, reasoning_characters=0):
        super().__init__()
        self.reasoning_characters = reasoning_characters

    def chat(self, request):
        response = super().chat(request)
        ordinal = len(self.requests)
        if ordinal <= 3:
            queries = (("早期死亡", "补刀经济", "视野控制", "团战决策"),
                       ("早期死亡", "补刀经济"), ("早期死亡", "补刀经济"))[ordinal - 1]
            response = replace(response, tool_calls=tuple(
                ToolCall(id=f"offline-{ordinal}-{i}", name="knowledge.search",
                         arguments={"query": query, "top_k": ordinal + 2})
                for i, query in enumerate(queries)),
                reasoning_content="x" * self.reasoning_characters or None)
        # Conservative resource settlement, not invented observed API usage.
        if request.response_contract is not None and request.response_contract.version in ("1.3.0", "1.4.0") and ordinal in (6, 9):
            payload = json.loads(response.content)
            payload["audits"] = [{"kind": kind, "status": "not_applicable", "claims": []}
                                 for kind in ("metric_to_ability", "cohort_comparison")]
            response = replace(response, content=json.dumps(payload, ensure_ascii=False))
        return replace(response, usage=TokenUsage(
            input_tokens=estimate_runtime_request_input_ceiling(request), output_tokens=8192))


def probe(summary, *, contract=LATENCY_COACH_CONTRACT, reasoning_characters=0, bundle=None,
          training_positions=("mid", "support")):
    if all(contract is not c for c in (BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT)):
        raise ValueError("unsupported replay contract")
    if type(reasoning_characters) is not int or not 0 <= reasoning_characters <= 100000:
        raise ValueError("invalid replay reasoning size")
    summary_bytes = json.dumps(summary, sort_keys=True, ensure_ascii=True,
                              separators=(",", ":")).encode()
    digest = hashlib.sha256(summary_bytes).hexdigest()
    roles = position_context(summary, training_positions=training_positions)
    class FrozenSummary:
        def build(self, **kwargs):
            return copy.deepcopy(summary)
        def build_by_puuid(self, **kwargs):
            return copy.deepcopy(summary)

    provider = _ReplayProvider(reasoning_characters=reasoning_characters)
    loop_rows = []
    original_run = AgentLoop.run
    def observe_loop(self, request, **kwargs):
        result = original_run(self, request, **kwargs)
        sizer = DeterministicContextSizer()
        loop_rows.append({
            "context_limit": request.max_context_tokens,
            "initial_units": sizer.estimate_messages(request.messages),
            "final_units": sizer.estimate_messages(result.messages),
            "agent_stop_reason": result.stop_reason.value,
            "tool_calls": len(result.tool_executions),
            "successful_tool_calls": sum(row.result.success for row in result.tool_executions),
        })
        return result
    def no_network(*args, **kwargs):
        raise AssertionError("offline replay forbids network")

    # Instrumentation exists only in this single-process offline checker.
    with tempfile.TemporaryDirectory(prefix="riftcoach-offline-golden-") as directory, \
         patch.object(socket.socket, "connect", no_network), \
         patch.object(socket.socket, "connect_ex", no_network), \
         patch.object(socket, "create_connection", no_network), \
         patch.object(AgentLoop, "run", observe_loop):
        app = build_coach_application(
            summary_builder=FrozenSummary(), provider=provider,
            knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs"),
            runs_root=directory, compact_context_json=True, coach_contract=contract,
            report_renderer=lambda value: render_golden_context_report(
                value, summary_digest=digest, bundle_digest=bundle.digest if bundle is not None else "0" * 64,
                roles=roles, bundle=bundle),
        )
        result = app.review(RecentReviewProductRequest(
            riot_id="OfflineReplay#TEST", routing_region="asia", count=5, queue=420, focus="overall",
        ), run_id="offline_golden_budget")
        manifest = FileRunStore(directory, result.run_id).read_manifest()
        return {
            "scope": "scripted_offline_control_flow_not_quality_or_admission",
            "summary_digest": digest, "coach_contract": contract.snapshot().model_dump(mode="json"),
            "network_used": False, "external_provider_calls": 0,
            "scripted_provider_calls": len(provider.requests),
            "terminal_reason": result.terminal_reason, "failure_code": manifest.failure_code,
            "revision_count": manifest.revision_count,
            "agent": loop_rows,
            "request_input_ceilings": [estimate_runtime_request_input_ceiling(r) for r in provider.requests],
            "source_bundle_present_by_call": [bundle is not None and any(
                bundle.digest in (message.content or "") for message in request.messages
            ) for request in provider.requests],
            "position_policy_present_by_call": [bool(contract.position_policy) and any(
                contract.position_policy in (message.content or "")
                or json.dumps(contract.position_policy, ensure_ascii=False)[1:-1] in (message.content or "")
                for message in request.messages
            ) for request in provider.requests],
            "reserved_output_tokens": 8192 * len(provider.requests),
            "report_available": result.output.report is not None if result.output else False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--compare-legacy", action="store_true")
    args = parser.parse_args()
    if args.summary.stat().st_size > 2_000_000:
        raise ValueError("saved summary too large")
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    contracts = (BATCH_COACH_CONTRACT, LATENCY_COACH_CONTRACT) if args.compare_legacy else (LATENCY_COACH_CONTRACT,)
    print(json.dumps([probe(summary, contract=contract) for contract in contracts], indent=2))


if __name__ == "__main__":
    main()
