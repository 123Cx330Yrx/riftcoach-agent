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
from app.runtime.coach_contract import EVIDENCE_V6_COACH_CONTRACT, EVIDENCE_V5_COACH_CONTRACT, EVIDENCE_V4_COACH_CONTRACT, EVIDENCE_V3_COACH_CONTRACT, CAPACITY_COACH_CONTRACT, EVIDENCE_V2_COACH_CONTRACT, EVIDENCE_COACH_CONTRACT, FACT_INFERENCE_COACH_CONTRACT, FEEDBACK_COACH_CONTRACT, EXPANDED_COACH_CONTRACT, COVERAGE_COACH_CONTRACT as CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.tools.adapters.llm import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from scripts.check_golden_quality_counterexamples import DATASET, check_evidence

ROOT = Path(__file__).resolve().parents[1]
MAX_CALLS = 25  # Ten evaluations with one format correction each, plus eval/revise/eval (5).


class Counted:
    def __init__(self, provider, *, state, call_limit, directory):
        self.provider = provider
        self.state = state
        self.call_limit = call_limit
        self.directory = directory
    def __getattr__(self, key): return getattr(self.provider, key)
    def chat(self, request):
        state, call_limit, directory = self.state, self.call_limit, self.directory
        if state["calls"] >= call_limit: raise ValueError("development_call_limit")
        state["calls"] += 1
        write_new_json(directory / f"call-{state['calls']:03d}.json", {"ordinal": state["calls"], "state": "reserved_before_io"})
        response = self.provider.chat(request)
        state["input_tokens"] += response.usage.input_tokens
        state["output_tokens"] += response.usage.output_tokens
        write_new_json(directory / f"response-{state['calls']:03d}.json", {"content": response.content, "finish_reason": response.finish_reason})
        return response


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source: Path, *, scope=False, scope_v2=False, scope_v3=False, scope_v4=False, expanded_output=False, scope_v5=False, fact_inference=False, evidence_scope=False, evidence_scope_v2=False, capacity_output=False, evidence_scope_v3=False, evidence_scope_v4=False, evidence_scope_v5=False, evidence_scope_v6=False):
    from app.runtime.coach_contract import SCOPE_COACH_CONTRACT, SCOPE_V2_COACH_CONTRACT, SCOPE_V3_COACH_CONTRACT, SCOPE_V4_COACH_CONTRACT
    contract = EVIDENCE_V6_COACH_CONTRACT if evidence_scope_v6 else EVIDENCE_V5_COACH_CONTRACT if evidence_scope_v5 else EVIDENCE_V4_COACH_CONTRACT if evidence_scope_v4 else EVIDENCE_V3_COACH_CONTRACT if evidence_scope_v3 else CAPACITY_COACH_CONTRACT if capacity_output else EVIDENCE_V2_COACH_CONTRACT if evidence_scope_v2 else EVIDENCE_COACH_CONTRACT if evidence_scope else FACT_INFERENCE_COACH_CONTRACT if fact_inference else FEEDBACK_COACH_CONTRACT if scope_v5 else EXPANDED_COACH_CONTRACT if expanded_output else SCOPE_V4_COACH_CONTRACT if scope_v4 else SCOPE_V3_COACH_CONTRACT if scope_v3 else SCOPE_V2_COACH_CONTRACT if scope_v2 else SCOPE_COACH_CONTRACT if scope else CONTRACT
    dataset = json.loads(DATASET.read_text(encoding="utf-8")); check_evidence(dataset)
    report_path = source / "output/final_report.md"
    if _hash(report_path) != dataset["source_report_sha256"]:
        raise ValueError("source_report_identity_mismatch")
    assets = ROOT / "examples/runtime_profiles" / ("flash_v2_golden_evidence_v6" if evidence_scope_v6 else "flash_v2_golden_evidence_v5" if evidence_scope_v5 else "flash_v2_golden_evidence_v4" if evidence_scope_v4 else "flash_v2_golden_evidence_v3" if evidence_scope_v3 else "flash_v2_golden_capacity" if capacity_output else "flash_v2_golden_evidence_v2" if evidence_scope_v2 else "flash_v2_golden_evidence" if evidence_scope else "flash_v2_golden_fact" if fact_inference else "flash_v2_golden_feedback" if scope_v5 else "flash_v2_golden_expanded" if expanded_output else "flash_v2_golden_scope_v4" if scope_v4 else "flash_v2_golden_scope_v3" if scope_v3 else "flash_v2_golden_scope_v2" if scope_v2 else "flash_v2_golden_scope" if scope else "flash_v2_golden_coverage")
    RuntimeCompositionRoot.from_directories(skills_root=assets / "skills", prompt_programs_root=assets / "prompt_programs", coach_contract=contract)
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
    if "scope" in case:
        return score_scope_case(case, result)
    payload = _evaluation_payload(result)
    expected_kind = {"mixed_role_deficit": "cohort_comparison", "metric_to_ability": "metric_to_ability"}.get(case.get("issue_kind"))
    unsupported = [a for a in payload.get("audits", []) if a["status"] == "unsupported"]
    detected = any(a["kind"] == expected_kind and any(c.get("status", "unsupported") == "unsupported" and c["quote"] in case["claim"] for c in a["claims"]) for a in unsupported)
    accepted = result.verdict.value == "pass" and result.score >= 85 and not payload["issues"] and not unsupported
    matched = (result.verdict.value != "pass" and detected) if case["expected"] == "reject" else accepted
    return {"id": case["id"], "expected": case["expected"], "verdict": result.verdict.value,
            "matched": matched, "score": result.score, "expected_inference_detected": detected,
            "unsupported_kinds": [a["kind"] for a in unsupported]}


def score_scope_case(case, result):
    payload = _evaluation_payload(result)
    claims = [c for a in payload.get("audits", []) for c in a["claims"]
              if c["quote"] and c["quote"] in case["claim"]]
    accepted = result.verdict.value == "pass" and result.score >= 85 and not payload["issues"]
    detected = any(c.get("status") == "unsupported" and any(i["quote"] == c["quote"] for i in payload["issues"]) for c in claims)
    clarified = any(c.get("scope") == "ambiguous" and any(i["quote"] == c["quote"] and i["category"] == "other" for i in payload["issues"]) for c in claims)
    matched = accepted if case["expected"] == "accept" else result.verdict.value != "pass" and (clarified if case["expected"] == "clarify" else detected)
    return {"id": case["id"], "expected": case["expected"], "verdict": result.verdict.value,
            "matched": matched, "score": result.score, "expected_inference_detected": detected,
            "scope_clarification_detected": clarified}


def run(args):
    from app.runtime.coach_contract import SCOPE_COACH_CONTRACT
    evidence_scope_v6 = getattr(args, "evidence_scope_v6", False)
    if evidence_scope_v6 and getattr(args, "evidence_scope_v5", False):
        raise ValueError("exclusive_evidence_version_required")
    evidence_scope_v5 = getattr(args, "evidence_scope_v5", False) or evidence_scope_v6
    if evidence_scope_v5 and getattr(args, "evidence_scope_v4", False):
        raise ValueError("exclusive_evidence_version_required")
    evidence_scope_v4 = getattr(args, "evidence_scope_v4", False) or evidence_scope_v5
    if evidence_scope_v4 and getattr(args, "evidence_scope_v3", False):
        raise ValueError("exclusive_evidence_version_required")
    evidence_scope_v3 = getattr(args, "evidence_scope_v3", False) or evidence_scope_v4
    if evidence_scope_v3 and any(getattr(args, k, False) for k in ("scope", "scope_v2", "scope_v3", "scope_v4", "scope_v5", "fact_inference", "evidence_scope", "evidence_scope_v2")):
        raise ValueError("evidence_scope_v3_requires_exclusive_mode")
    capacity_output = getattr(args, "capacity_output", False) or evidence_scope_v3
    evidence_scope_v2 = getattr(args, "evidence_scope_v2", False) or evidence_scope_v3
    if capacity_output and not evidence_scope_v2:
        raise ValueError("capacity_output_requires_evidence_scope_v2")
    evidence_scope = getattr(args, "evidence_scope", False)
    fact_inference = getattr(args, "fact_inference", False)
    scope_v5 = getattr(args, "scope_v5", False)
    expanded_output = getattr(args, "expanded_output", False)
    if evidence_scope_v2 and (not expanded_output or not args.report_only or args.controls_only or any(getattr(args, k, False) for k in ("scope", "scope_v2", "scope_v3", "scope_v4", "scope_v5", "fact_inference", "evidence_scope"))):
        raise ValueError("evidence_scope_v2_requires_exclusive_expanded_report_only")
    if evidence_scope and (not expanded_output or not args.report_only or args.controls_only or any(getattr(args, k, False) for k in ("scope", "scope_v2", "scope_v3", "scope_v4", "scope_v5", "fact_inference"))):
        raise ValueError("evidence_scope_requires_exclusive_expanded_report_only")
    if fact_inference and (not expanded_output or not args.report_only or args.controls_only or any(getattr(args, k, False) for k in ("scope", "scope_v2", "scope_v3", "scope_v4", "scope_v5"))):
        raise ValueError("fact_inference_requires_exclusive_expanded_report_only")
    if scope_v5 and not expanded_output:
        raise ValueError("scope_v5_requires_expanded_output")
    scope_v4 = getattr(args, "scope_v4", False) or scope_v5 or fact_inference or evidence_scope or evidence_scope_v2
    if expanded_output and (not scope_v4 or not args.report_only or args.controls_only):
        raise ValueError("expanded_output_requires_scope_v4_report_only")
    scope_v3 = getattr(args, "scope_v3", False)
    scope_v2 = getattr(args, "scope_v2", False)
    scope = getattr(args, "scope", False) or scope_v2 or scope_v3 or scope_v4
    from app.runtime.coach_contract import SCOPE_COACH_CONTRACT, SCOPE_V2_COACH_CONTRACT, SCOPE_V3_COACH_CONTRACT, SCOPE_V4_COACH_CONTRACT
    contract = EVIDENCE_V6_COACH_CONTRACT if evidence_scope_v6 else EVIDENCE_V5_COACH_CONTRACT if evidence_scope_v5 else EVIDENCE_V4_COACH_CONTRACT if evidence_scope_v4 else EVIDENCE_V3_COACH_CONTRACT if evidence_scope_v3 else CAPACITY_COACH_CONTRACT if capacity_output else EVIDENCE_V2_COACH_CONTRACT if evidence_scope_v2 else EVIDENCE_COACH_CONTRACT if evidence_scope else FACT_INFERENCE_COACH_CONTRACT if fact_inference else FEEDBACK_COACH_CONTRACT if scope_v5 else EXPANDED_COACH_CONTRACT if expanded_output else SCOPE_V4_COACH_CONTRACT if scope_v4 else SCOPE_V3_COACH_CONTRACT if scope_v3 else SCOPE_V2_COACH_CONTRACT if scope_v2 else SCOPE_COACH_CONTRACT if scope else CONTRACT
    if scope and not (args.report_only or args.controls_only):
        raise ValueError("scope_requires_separate_report_or_controls_run")
    dataset, summary, original = prepare(args.source_run, scope=scope, scope_v2=scope_v2, scope_v3=scope_v3, scope_v4=scope_v4, expanded_output=expanded_output, scope_v5=scope_v5, fact_inference=fact_inference, evidence_scope=evidence_scope, evidence_scope_v2=evidence_scope_v2, capacity_output=capacity_output, evidence_scope_v3=evidence_scope_v3, evidence_scope_v4=evidence_scope_v4, evidence_scope_v5=evidence_scope_v5, evidence_scope_v6=evidence_scope_v6)
    dataset_path = DATASET
    if scope:
        from scripts.check_golden_stability_calibration import DATASET as SCOPE_DATASET, SOURCE, check_evidence as check_scope
        calibration = json.loads(SCOPE_DATASET.read_text(encoding="utf-8"))
        check_scope(calibration, SOURCE.read_bytes())
        dataset = {**dataset, "cases": calibration["cases"]}
        dataset_path = SCOPE_DATASET
        if args.report_only and not args.target_report:
            raise ValueError("scope_report_requires_frozen_96_point_target")
    if args.target_report:
        if _hash(args.target_report) != ("3b4d530279951c54a79eaf330a0b03d841910ab6dc35b8f48402be285a9f8c6e" if scope else "e351b8cb3a09137f895346dd42783a3944805ad48129cb31b2934c20ed91f52d"):
            raise ValueError("reviewed_target_report_identity_mismatch")
        original = args.target_report.read_text(encoding="utf-8")
    selected_cases = [] if args.report_only else [c for c in dataset["cases"] if not args.case_id or c["id"] in args.case_id]
    if args.case_id and not set(args.case_id) <= {c["id"] for c in dataset["cases"]}:
        raise ValueError("unknown_development_case")
    call_limit = min(MAX_CALLS, len(selected_cases) * 2 + (0 if args.controls_only else 5))
    if _hash(args.base_report) != "8485a643fcc2578034e30ac7b74a3c98bebfb2706ef32152ad1402fe59f3d5ef":
        raise ValueError("development_base_report_identity_mismatch")
    base_report = args.base_report.read_text(encoding="utf-8")
    if base_report.count("## 3. 主要风险点\n") != 1:
        raise ValueError("development_embedding_marker_missing_or_duplicate")
    knowledge_data = json.loads((args.source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    saved_knowledge = KnowledgeEvidence(context=knowledge_data["context"], source_ids=tuple(knowledge_data["source_ids"]),
        citations=tuple(KnowledgeCitation(**c) for c in knowledge_data["citations"]), abstained=knowledge_data.get("abstained", False))
    output_cap = contract.descriptor()["max_output_tokens"]
    plan = {"scope": "known_development_not_holdout_or_admission", "contract": contract.snapshot().model_dump(mode="json"),
            "dataset_sha256": _hash(dataset_path), "source_report_sha256": dataset["source_report_sha256"], "base_report_sha256": _hash(args.base_report),
            "case_embedding": "full-manually-reviewed-report-with-single-claim-v2",
            "evaluated_report_sha256": hashlib.sha256(original.encode()).hexdigest(), "controls_only": args.controls_only,
            "cases": len(selected_cases), "selected_case_ids": [c["id"] for c in selected_cases], "max_provider_calls": call_limit,
            "max_input_per_call": 64000, "max_output_per_call": output_cap, "max_total_tokens": (contract.descriptor()["total_tokens"] if capacity_output else call_limit * (64000 + output_cap)),
            "max_revisions": 1, "sdk_retries": 0, "real_calls_authorized": bool(args.execute)}
    if expanded_output:
        plan.update(request_timeout_s=contract.descriptor()["request_timeout_s"], execution_timeout_s=contract.descriptor()["execution_timeout_s"],
                    transport_id=contract.descriptor()["stream_transport_id"], reasoning_effort="high")
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

    def components(name):
        provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings, directory=directory / name, **({"transport_id": contract.descriptor()["stream_transport_id"]} if expanded_output else {})), state=state, call_limit=call_limit, directory=directory), coach_contract=contract)
        registry = ToolRegistry()
        for definition in build_llm_tools(provider, request_policy=contract.request_policy): registry.register(definition)
        runtime = ToolRuntime(registry)
        options = {"inference_audit": "evidence_v6" if evidence_scope_v6 else "evidence_v5" if evidence_scope_v5 else "evidence_v4" if evidence_scope_v4 else "evidence_v3" if evidence_scope_v3 else "capacity_v1" if capacity_output else "evidence_v2" if evidence_scope_v2 else "evidence_v1" if evidence_scope else "fact_v1" if fact_inference else "scope_v5" if scope_v5 else "scope_v4" if scope_v4 else "scope_v3" if scope_v3 else "scope_v2" if scope_v2 else "scope" if scope else "coverage", "include_generation_facts": True, "include_deterministic_facts": True,
                   "position_policy": contract.position_policy, "source_use_policy": contract.source_use_policy, "compact_report_policy": contract.compact_report_policy}
        return (GroundedChatEvaluationAdapter(runtime=runtime, system_prompt=EVALUATOR_SYSTEM_PROMPT, fact_pack_builder=build_fact_pack, **options),
                GroundedCoachReviser(runtime=runtime, system_prompt=REVISER_SYSTEM_PROMPT, prompt_builder=lambda *x: "unused", validator=lambda *x: None, **options))

    deterministic = (args.source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    knowledge = saved_knowledge
    try:
        for case in sorted(selected_cases, key=lambda c: c["id"] != ("selected_pairs" if scope else "vision_fact")):
            evaluator, _ = components(case["id"])
            report = base_report.replace("## 3. 主要风险点\n", "## 3. 主要风险点\n\n" + case["claim"] + "\n", 1)
            write_new_json(directory / f"{case['id']}-input.json", {"report_sha256": hashlib.sha256(report.encode()).hexdigest(), "report": report})
            result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, report, "复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。"))
            write_new_json(directory / f"{case['id']}.json", _evaluation_payload(result))
            state["cases"].append(score_case(case, result))
            print(json.dumps(state["cases"][-1]), flush=True)
            if case["id"] == ("selected_pairs" if scope else "vision_fact") and not state["cases"][-1]["matched"]:
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
        state["clarification_denominator"] = sum(c["expected"] == "clarify" for c in state["cases"])
        state["clarification_misses"] = sum(c["expected"] == "clarify" and not c["matched"] for c in state["cases"])
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
    p.add_argument("--scope", action="store_true")
    p.add_argument("--scope-v2", action="store_true")
    p.add_argument("--scope-v3", action="store_true")
    p.add_argument("--scope-v4", action="store_true")
    p.add_argument("--scope-v5", action="store_true")
    p.add_argument("--fact-inference", action="store_true")
    p.add_argument("--evidence-scope", action="store_true")
    p.add_argument("--evidence-scope-v2", action="store_true")
    p.add_argument("--evidence-scope-v6", action="store_true")
    p.add_argument("--evidence-scope-v5", action="store_true")
    p.add_argument("--evidence-scope-v4", action="store_true")
    p.add_argument("--evidence-scope-v3", action="store_true")
    p.add_argument("--capacity-output", action="store_true")
    p.add_argument("--expanded-output", action="store_true")
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
