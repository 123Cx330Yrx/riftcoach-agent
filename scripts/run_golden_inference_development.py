"""Opt-in bounded real-model check of known inference controls and report revision."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter, GroundedCoachReviser
from app.evaluation.coach_report import build_fact_pack, EVALUATOR_SYSTEM_PROMPT, REVISER_SYSTEM_PROMPT
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import GoldenProcessStreamProvider
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence, KnowledgeCitation
from app.harness.adapters import _evaluation_payload
from app.providers.config import load_zhipu_settings
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import INFERENCE_COACH_CONTRACT as CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.tools.adapters.llm import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from scripts.check_golden_quality_counterexamples import DATASET, check_evidence

ROOT = Path(__file__).resolve().parents[1]
MAX_CALLS = 25  # Ten evaluations with one format correction each, plus eval/revise/eval (5).


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source: Path):
    dataset = json.loads(DATASET.read_text(encoding="utf-8")); check_evidence(dataset)
    report_path = source / "output/final_report.md"
    if _hash(report_path) != dataset["source_report_sha256"]:
        raise ValueError("source_report_identity_mismatch")
    assets = ROOT / "examples/runtime_profiles/flash_v2_golden_inference"
    RuntimeCompositionRoot.from_directories(skills_root=assets / "skills", prompt_programs_root=assets / "prompt_programs", coach_contract=CONTRACT)
    summary = json.loads((source / "inputs/player_summary.json").read_text(encoding="utf-8"))
    # Bind the development labels to the same metric rows, not an arbitrary report.
    for actual, expected in zip(summary["matches"], dataset["samples"], strict=True):
        if any(actual.get(k) != v for k, v in expected.items() if k != "sample_id"):
            raise ValueError("development_source_cohort_mismatch")
    return dataset, summary, report_path.read_text(encoding="utf-8")


def verify_public_ci(run_id: str):
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("real_observation_requires_clean_checkout")
    result = json.loads(subprocess.check_output(["gh", "run", "view", run_id, "--json", "headSha,status,conclusion,jobs"], cwd=ROOT, text=True))
    jobs = {j["name"]: j["conclusion"] for j in result["jobs"]}
    if result["headSha"] != sha or result["status"] != "completed" or result["conclusion"] != "success" or any(jobs.get(j) != "success" for j in ("pytest", "postgres-migrations", "packaging-smoke")):
        raise ValueError("exact_sha_public_ci_required")
    return sha


def score_case(case, result):
    payload = _evaluation_payload(result)
    expected_kind = {"mixed_role_deficit": "cohort_comparison", "metric_to_ability": "metric_to_ability"}.get(case.get("issue_kind"))
    unsupported = [a for a in payload.get("audits", []) if a["status"] == "unsupported"]
    detected = any(a["kind"] == expected_kind and any(c["quote"] in case["claim"] for c in a["claims"]) for a in unsupported)
    accepted = result.verdict.value == "pass" and result.score >= 85 and not payload["issues"] and not unsupported
    matched = (result.verdict.value != "pass" and detected) if case["expected"] == "reject" else accepted
    return {"id": case["id"], "expected": case["expected"], "verdict": result.verdict.value,
            "matched": matched, "score": result.score, "expected_inference_detected": detected,
            "unsupported_kinds": [a["kind"] for a in unsupported]}


def run(args):
    dataset, summary, original = prepare(args.source_run)
    plan = {"scope": "known_development_not_holdout_or_admission", "contract": CONTRACT.snapshot().model_dump(mode="json"),
            "dataset_sha256": _hash(DATASET), "source_report_sha256": dataset["source_report_sha256"],
            "cases": len(dataset["cases"]), "max_provider_calls": MAX_CALLS,
            "max_input_per_call": 64000, "max_output_per_call": 8192, "max_total_tokens": MAX_CALLS * (64000 + 8192),
            "max_revisions": 1, "sdk_retries": 0, "real_calls_authorized": bool(args.execute)}
    if not args.execute:
        print(json.dumps(plan)); return
    if not re.fullmatch(r"inference-dev-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("invalid_development_run_id")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    from dotenv import dotenv_values
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    state = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cases": [], "report": {}, "stopped": False}

    class Counted:
        def __init__(self, provider):
            self.provider = provider
        def __getattr__(self, key): return getattr(self.provider, key)
        def chat(self, request):
            if state["calls"] >= MAX_CALLS: raise ValueError("development_call_limit")
            state["calls"] += 1
            write_new_json(directory / f"call-{state['calls']:03d}.json", {"ordinal": state["calls"], "state": "reserved_before_io"})
            response = self.provider.chat(request)
            state["input_tokens"] += response.usage.input_tokens
            state["output_tokens"] += response.usage.output_tokens
            return response

    def components(name):
        provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings, directory=directory / name)), coach_contract=CONTRACT)
        registry = ToolRegistry()
        for definition in build_llm_tools(provider, request_policy=CONTRACT.request_policy): registry.register(definition)
        runtime = ToolRuntime(registry)
        options = {"inference_audit": True, "include_generation_facts": True, "include_deterministic_facts": True,
                   "position_policy": CONTRACT.position_policy, "source_use_policy": CONTRACT.source_use_policy, "compact_report_policy": CONTRACT.compact_report_policy}
        return (GroundedChatEvaluationAdapter(runtime=runtime, system_prompt=EVALUATOR_SYSTEM_PROMPT, fact_pack_builder=build_fact_pack, **options),
                GroundedCoachReviser(runtime=runtime, system_prompt=REVISER_SYSTEM_PROMPT, prompt_builder=lambda *x: "unused", validator=lambda *x: None, **options))

    deterministic = (args.source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    knowledge = KnowledgeEvidence(context="[K1] 指标描述单局结果，不能单独证明意识、稳定能力或因果。", source_ids=("development_boundary",), citations=(KnowledgeCitation(citation_id="K1", chunk_id="development-boundary", parent_id=None, source_id="development_boundary", title="Development metric boundary", content="指标描述单局结果，不能单独证明意识、稳定能力或因果。"),))
    try:
        for case in dataset["cases"]:
            evaluator, _ = components(case["id"])
            report = case["claim"] + "\n\n指标与能力、因果需要区分。[K1]"
            result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, report, "检查这条观摩记录是否有事实或推断错误。"))
            write_new_json(directory / f"{case['id']}.json", _evaluation_payload(result))
            state["cases"].append(score_case(case, result))
            print(json.dumps(state["cases"][-1]), flush=True)
        evaluator, reviser = components("full-report")
        # Full report gets its own saved, attributable knowledge projection.
        knowledge_data = json.loads((args.source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
        knowledge = KnowledgeEvidence(context=knowledge_data["context"], source_ids=tuple(knowledge_data["source_ids"]),
            citations=tuple(KnowledgeCitation(**c) for c in knowledge_data["citations"]), abstained=knowledge_data.get("abstained", False))
        result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, original, "复核已归档ShowMaker观摩报告的事实、推断和建议。"))
        write_new_json(directory / "original-evaluation.json", _evaluation_payload(result))
        state["report"]["original_verdict"] = result.verdict.value
        if result.verdict.value == "needs_revision":
            revised = reviser.revise(RevisionRequest(summary, deterministic, knowledge, original, result))
            (directory / "revised-report.md").write_text(revised.report, encoding="utf-8")
            checked = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, revised.report, "复核已归档ShowMaker观摩报告的事实、推断和建议。"))
            write_new_json(directory / "revised-evaluation.json", _evaluation_payload(checked))
            state["report"].update(revised_verdict=checked.verdict.value, revised_score=checked.score)
    except Exception as error:
        state.update(stopped=True, error_type=type(error).__name__)
        raise
    finally:
        state["false_negatives"] = sum(c["expected"] == "reject" and not c["matched"] for c in state["cases"])
        state["false_positives"] = sum(c["expected"] == "accept" and not c["matched"] for c in state["cases"])
        write_new_json(directory / "receipt.json", {**plan, **state})
        print(json.dumps(state), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", required=True, type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--ci-run")
    p.add_argument("--run-id", default="inference-dev-preview")
    p.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    args = p.parse_args()
    if args.execute and (args.env_file is None or not args.ci_run): p.error("execution requires env-file and ci-run")
    try: run(args)
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__": main()
