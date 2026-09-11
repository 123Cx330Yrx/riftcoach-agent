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
from app.runtime.coach_contract import COVERAGE_COACH_CONTRACT as CONTRACT
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
    assets = ROOT / "examples/runtime_profiles/flash_v2_golden_coverage"
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
    detected = any(a["kind"] == expected_kind and any(c.get("status", "unsupported") == "unsupported" and c["quote"] in case["claim"] for c in a["claims"]) for a in unsupported)
    accepted = result.verdict.value == "pass" and result.score >= 85 and not payload["issues"] and not unsupported
    matched = (result.verdict.value != "pass" and detected) if case["expected"] == "reject" else accepted
    return {"id": case["id"], "expected": case["expected"], "verdict": result.verdict.value,
            "matched": matched, "score": result.score, "expected_inference_detected": detected,
            "unsupported_kinds": [a["kind"] for a in unsupported]}


def run(args):
    dataset, summary, original = prepare(args.source_run)
    if args.target_report:
        if _hash(args.target_report) != "e351b8cb3a09137f895346dd42783a3944805ad48129cb31b2934c20ed91f52d":
            raise ValueError("reviewed_target_report_identity_mismatch")
        original = args.target_report.read_text(encoding="utf-8")
    selected_cases = [] if args.report_only else [c for c in dataset["cases"] if not args.case_id or c["id"] in args.case_id]
    if args.case_id and not set(args.case_id) <= {c["id"] for c in dataset["cases"]}:
        raise ValueError("unknown_development_case")
    call_limit = min(MAX_CALLS, len(selected_cases) * 2 + (0 if args.controls_only else 5))
    if _hash(args.base_report) != "8485a643fcc2578034e30ac7b74a3c98bebfb2706ef32152ad1402fe59f3d5ef":
        raise ValueError("development_base_report_identity_mismatch")
    base_report = args.base_report.read_text(encoding="utf-8")
    knowledge_data = json.loads((args.source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    saved_knowledge = KnowledgeEvidence(context=knowledge_data["context"], source_ids=tuple(knowledge_data["source_ids"]),
        citations=tuple(KnowledgeCitation(**c) for c in knowledge_data["citations"]), abstained=knowledge_data.get("abstained", False))
    plan = {"scope": "known_development_not_holdout_or_admission", "contract": CONTRACT.snapshot().model_dump(mode="json"),
            "dataset_sha256": _hash(DATASET), "source_report_sha256": dataset["source_report_sha256"], "base_report_sha256": _hash(args.base_report),
            "case_embedding": "full-manually-reviewed-report-with-single-claim-v2",
            "evaluated_report_sha256": hashlib.sha256(original.encode()).hexdigest(), "controls_only": args.controls_only,
            "cases": len(selected_cases), "selected_case_ids": [c["id"] for c in selected_cases], "max_provider_calls": call_limit,
            "max_input_per_call": 64000, "max_output_per_call": 8192, "max_total_tokens": call_limit * (64000 + 8192),
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
            if state["calls"] >= call_limit: raise ValueError("development_call_limit")
            state["calls"] += 1
            write_new_json(directory / f"call-{state['calls']:03d}.json", {"ordinal": state["calls"], "state": "reserved_before_io"})
            response = self.provider.chat(request)
            state["input_tokens"] += response.usage.input_tokens
            state["output_tokens"] += response.usage.output_tokens
            write_new_json(directory / f"response-{state['calls']:03d}.json", {"content": response.content, "finish_reason": response.finish_reason})
            return response

    def components(name):
        provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings, directory=directory / name)), coach_contract=CONTRACT)
        registry = ToolRegistry()
        for definition in build_llm_tools(provider, request_policy=CONTRACT.request_policy): registry.register(definition)
        runtime = ToolRuntime(registry)
        options = {"inference_audit": "coverage", "include_generation_facts": True, "include_deterministic_facts": True,
                   "position_policy": CONTRACT.position_policy, "source_use_policy": CONTRACT.source_use_policy, "compact_report_policy": CONTRACT.compact_report_policy}
        return (GroundedChatEvaluationAdapter(runtime=runtime, system_prompt=EVALUATOR_SYSTEM_PROMPT, fact_pack_builder=build_fact_pack, **options),
                GroundedCoachReviser(runtime=runtime, system_prompt=REVISER_SYSTEM_PROMPT, prompt_builder=lambda *x: "unused", validator=lambda *x: None, **options))

    deterministic = (args.source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    knowledge = saved_knowledge
    try:
        for case in sorted(selected_cases, key=lambda c: c["id"] != "vision_fact"):
            evaluator, _ = components(case["id"])
            report = base_report.replace("## 3. 主要风险点\n", "## 3. 主要风险点\n\n" + case["claim"] + "\n", 1)
            write_new_json(directory / f"{case['id']}-input.json", {"report_sha256": hashlib.sha256(report.encode()).hexdigest(), "report": report})
            result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, report, "复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。"))
            write_new_json(directory / f"{case['id']}.json", _evaluation_payload(result))
            state["cases"].append(score_case(case, result))
            print(json.dumps(state["cases"][-1]), flush=True)
            if case["id"] == "vision_fact" and not state["cases"][-1]["matched"]:
                state["controls_stopped"] = "full_report_positive_control_failed"
                break
        if args.controls_only:
            return
        evaluator, reviser = components("full-report")
        # Full report gets its own saved, attributable knowledge projection.
        knowledge = saved_knowledge
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
        state["evaluated_case_count"] = len(state["cases"])
        state["all_selected_cases_completed"] = len(state["cases"]) == len(selected_cases)
        state["false_negative_denominator"] = sum(c["expected"] == "reject" for c in state["cases"])
        state["false_positive_denominator"] = sum(c["expected"] == "accept" for c in state["cases"])
        state["false_negatives"] = sum(c["expected"] == "reject" and not c["matched"] for c in state["cases"])
        state["false_positives"] = sum(c["expected"] == "accept" and not c["matched"] for c in state["cases"])
        write_new_json(directory / "receipt.json", {**plan, **state})
        print(json.dumps(state), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", required=True, type=Path)
    p.add_argument("--base-report", required=True, type=Path)
    selection = p.add_mutually_exclusive_group()
    selection.add_argument("--report-only", action="store_true")
    selection.add_argument("--case-id", action="append")
    p.add_argument("--controls-only", action="store_true")
    p.add_argument("--target-report", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--ci-run")
    p.add_argument("--run-id", default="inference-dev-preview")
    p.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    args = p.parse_args()
    if args.controls_only and args.report_only: p.error("controls-only conflicts with report-only")
    if args.execute and (args.env_file is None or not args.ci_run): p.error("execution requires env-file and ci-run")
    try: run(args)
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__": main()
