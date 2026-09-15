"""Run frozen complete-report context contrasts; default is a zero-I/O preview."""
import argparse
import json
from pathlib import Path
import re

from app.evaluation.golden_context_requests import evaluation_request
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.harness.adapters import _evaluation_payload
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation
from app.providers.errors import ProviderResponseError
from scripts.run_golden_scope_controls import BASE_SHA, case_progress
from scripts.run_golden_inference_development import prepare, verify_public_ci, Counted

ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = ROOT / "data/evaluation/datasets/golden_context_controls_v1.json"
MANIFEST = ROOT / "data/evaluation/datasets/golden_context_reports_v1.json"
PAIRS = ("explicit_definition", "heading_definition", "quotation_negation", "ineffective_disclaimer", "later_conflict")
UTTERANCE = "复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。"


def assemble(base, fragment):
    if digest(base) != BASE_SHA:
        raise ValueError("verified_base_report_required")
    start = base.index("## 3. 主要风险点\n") + len("## 3. 主要风险点\n")
    end = base.index("## 4. 赢局与输局差异\n")
    section = base[start:end]
    first, remainder = section.lstrip().split("\n", 1)
    if not first.startswith("- **输局经济与输出同位置差距明显"):
        raise ValueError("context_embedding_source_changed")
    # Remove the old local 'stable' definition, which could confound the target.
    # Every other section and the second independent risk bullet stay intact.
    return base[:start] + "\n" + fragment + "\n\n" + remainder.lstrip() + base[end:]


def load_cases(base):
    fragments = json.loads(FRAGMENTS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (manifest["fragment_sha256"] != digest(FRAGMENTS.read_text(encoding="utf-8"))
        or manifest["base_report_sha256"] != BASE_SHA
        or manifest["input_review"] != "assistant_reviewed_complete_reports_before_model_run"):
        raise ValueError("context_manifest_identity_invalid")
    lookup = {c["id"]: c for c in fragments["cases"]}
    if len(lookup) != 10 or set(lookup) != {c["id"] for c in manifest["cases"]} or len(manifest["cases"]) != 10:
        raise ValueError("context_manifest_cases_invalid")
    cases = []
    for frozen in manifest["cases"]:
        original = lookup[frozen["id"]]
        report = assemble(base, original["report"])
        if digest(report) != frozen["report_sha256"] or report.count(original["target"]) != 1:
            raise ValueError("context_complete_report_changed")
        cases.append(dict(frozen, report=report, target=original["target"], must_flag=original.get("must_flag")))
    return cases


def load_inputs(source_run, base_report):
    _, summary, _ = prepare(source_run, evidence_scope_v7=True)
    raw = json.loads((source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    knowledge = KnowledgeEvidence(context=raw["context"], source_ids=tuple(raw["source_ids"]),
        citations=tuple(KnowledgeCitation(**c) for c in raw["citations"]), abstained=raw.get("abstained", False))
    deterministic = (source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    return summary, deterministic, knowledge, load_cases(base_report.read_text(encoding="utf-8"))


def score(case, result):
    payload = _evaluation_payload(result)
    # Exact target binding prevents an error elsewhere from counting as detection.
    claims = [c for a in payload.get("audits", []) for c in a["claims"] if c["quote"] == case["target"]]
    issues = [i for i in payload["issues"] if i["quote"] == case["target"]]
    clarified = any(c["scope"] == "ambiguous" for c in claims) and any(i["category"] == "other" for i in issues)
    rejected = any(c["status"] == "unsupported" for c in claims) and bool(issues)
    accepted = bool(claims) and all(c["status"] == "supported" and c["scope"] != "ambiguous" for c in claims) and not issues
    target_matched = {"accept": accepted, "reject": rejected, "clarify": clarified}[case["expected_target"]]
    report_pass = result.verdict.value == "pass" and result.score >= 85 and not payload["issues"]
    all_claims = [c for a in payload.get("audits", []) for c in a["claims"]]
    report_rejected = any(c["status"] == "unsupported" and any(i["quote"] == c["quote"] for i in payload["issues"]) for c in all_claims)
    report_clarified = any(c["scope"] == "ambiguous" and any(i["quote"] == c["quote"] and i["category"] == "other" for i in payload["issues"]) for c in all_claims)
    report_matched = report_pass if case["expected_report"] == "accept" else result.verdict.value != "pass" and (
        report_rejected if case["expected_report"] == "reject" else report_clarified)
    if case.get("must_flag"):
        report_matched = report_matched and any(c["quote"] == case["must_flag"] and c["status"] == "unsupported" for c in all_claims)
    return dict(id=case["id"], valid=True, target_matched=target_matched, report_matched=report_matched,
        matched=target_matched and report_matched, verdict=result.verdict.value, score=result.score,
        target_accepted=accepted, target_rejected=rejected, target_clarified=clarified,
        expected_target=case["expected_target"], expected_report=case["expected_report"])


def run(args):
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT as contract
    from app.runtime.composition import RuntimeCompositionRoot
    summary, deterministic, knowledge, cases = load_inputs(args.source_run, args.base_report)
    assets = ROOT / "examples/runtime_profiles/flash_v2_golden_context"
    RuntimeCompositionRoot.from_directories(skills_root=assets/"skills", prompt_programs_root=assets/"prompt_programs", coach_contract=contract)
    numbers = args.pair or [1, 2]
    if len(set(numbers)) != len(numbers):
        raise ValueError("duplicate_pair")
    selected = [c for n in numbers for c in cases if c["pair"] == PAIRS[n-1]]
    sizes = {c["id"]: estimate_runtime_request_input_ceiling(evaluation_request(
        summary, deterministic, knowledge, c["report"], UTTERANCE)) for c in selected}
    plan = dict(scope="complete_context_development_controls_not_holdout", contract=contract.snapshot().model_dump(mode="json"),
        manifest_sha256=digest(MANIFEST.read_text(encoding="utf-8")), selected_case_ids=[c["id"] for c in selected],
        pairs=numbers, input_ceilings=sizes, max_calls=4*len(numbers), max_calls_per_pair=4,
        max_tokens_per_pair=401920, max_time_per_pair_s=900, request_timeout_s=300, max_output_per_call=32768,
        reasoning_effort="high", sdk_retries=0, max_revisions=0, labels_sent_to_model=False,
        failure_policy="record_protocol_or_semantic_failure; stop_suite_on_protocol_or_transport_failure",
        source_inputs_sha256=digest(compact(dict(summary=summary, deterministic=deterministic,
            knowledge=dict(context=knowledge.context, source_ids=knowledge.source_ids, citations=[c.__dict__ for c in knowledge.citations])))))
    if not args.execute:
        print(compact(plan)); return
    if not re.fullmatch(r"context-controls-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("invalid_context_run_id")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory/"plan.json", plan)
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    from app.evaluation.golden_stream_bridge import GoldenProcessStreamProvider
    from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter
    from app.evaluation.coach_report import build_fact_pack, EVALUATOR_SYSTEM_PROMPT
    from app.runtime.coach_budget import CoachBudgetedProvider
    from app.tools.adapters.llm import build_llm_tools
    from app.tools.registry import ToolRegistry
    from app.tools.runtime import ToolRuntime
    rows, started, pairs = [], [], []
    failure = None
    try:
        settings = load_zhipu_settings(dotenv_values(args.env_file))
        for n in numbers:
            pair_dir = directory/f"pair-{n:02d}"
            pair_dir.mkdir()
            state = dict(calls=0, input_tokens=0, output_tokens=0)
            pairs.append(dict(pair=n, state=state))
            provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings,
                directory=pair_dir/"streams", transport_id=contract.descriptor()["stream_transport_id"]),
                state=state, call_limit=4, directory=pair_dir), coach_contract=contract)
            registry = ToolRegistry()
            for definition in build_llm_tools(provider, request_policy=contract.request_policy): registry.register(definition)
            evaluator = GroundedChatEvaluationAdapter(runtime=ToolRuntime(registry), system_prompt=EVALUATOR_SYSTEM_PROMPT,
                fact_pack_builder=build_fact_pack, inference_audit="context_v1")
            for case in [c for c in selected if c["pair"] == PAIRS[n-1]]:
                first_call = state["calls"]+1
                write_new_json(pair_dir/f"{case['id']}-input.json", dict(report=case["report"], report_sha256=case["report_sha256"], first_call=first_call))
                started.append(case["id"])
                try:
                    result = evaluator.evaluate(EvaluationRequest(summary, deterministic, knowledge, case["report"], UTTERANCE))
                except ProviderResponseError as error:
                    if error.code != "invalid_structured_output": raise
                    row = dict(id=case["id"], valid=False, matched=False, failure_kind="protocol", error_code=error.code)
                    failure = "protocol"
                else:
                    write_new_json(pair_dir/f"{case['id']}-evaluation.json", _evaluation_payload(result))
                    row = score(case, result)
                row.update(first_call=first_call, last_call=state["calls"])
                rows.append(row)
                write_new_json(pair_dir/f"{case['id']}-result.json", row)
                print(compact(row), flush=True)
                if failure: break
            if failure: break
    except Exception as error:
        failure = type(error).__name__
        raise
    finally:
        receipt = dict(plan, cases=rows, pairs_result=pairs, stopped=failure is not None, error_type=failure,
            case_counts=case_progress(selected, started, rows), calls=sum(p["state"]["calls"] for p in pairs),
            input_tokens=sum(p["state"]["input_tokens"] for p in pairs), output_tokens=sum(p["state"]["output_tokens"] for p in pairs),
            valid=sum(r["valid"] for r in rows), invalid=sum(not r["valid"] for r in rows),
            all_matched=len(rows)==len(selected) and all(r["matched"] for r in rows))
        write_new_json(directory/"receipt.json", receipt)
        print(compact({k:receipt[k] for k in ("case_counts", "calls", "input_tokens", "output_tokens", "stopped", "valid", "invalid", "all_matched")}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", type=Path, required=True)
    p.add_argument("--base-report", type=Path, required=True)
    p.add_argument("--pair", type=int, action="append", choices=range(1,6))
    p.add_argument("--execute", action="store_true")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--ci-run")
    p.add_argument("--run-id", default="context-controls-preview")
    p.add_argument("--output-root", type=Path, default=ROOT/"data/runs/inference_development")
    args = p.parse_args()
    if args.execute and (not args.env_file or not args.ci_run): p.error("execute requires env-file and ci-run")
    run(args)


if __name__ == "__main__": main()
