"""Bounded, label-blind evaluation of the frozen twelve development controls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter
from app.evaluation.coach_report import build_fact_pack, EVALUATOR_SYSTEM_PROMPT
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import GoldenProcessStreamProvider
from app.harness.adapters import _evaluation_payload
from app.harness.steps import EvaluationRequest, KnowledgeCitation, KnowledgeEvidence
from app.providers.config import load_zhipu_settings
from app.providers.errors import ProviderResponseError
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import EVIDENCE_V7_COACH_CONTRACT as CONTRACT
from app.tools.adapters.llm import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from scripts.check_golden_stability_calibration import DATASET, SOURCE, check_evidence
from scripts.run_golden_inference_development import Counted, prepare, verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "a1cef8b4af58b6e241ba9bb683bb814c7a603d3d4ce9e56b61ad9a8af6e07088"
PAIRS = (
    ("selected_pairs", "long_term"),
    ("selected_means", "original_stable"),
    ("stable_negation", "future_without_keyword"),
    ("stable_local_definition", "original_reliable"),
    ("disclaimer_conflict", "reliable_without_keyword"),
    ("causal_leap", "persistent_heading"),
)


def embed(base, claim):
    marker = "## 3. 主要风险点\n"
    if base.count(marker) != 1:
        raise ValueError("control_embedding_marker_invalid")
    return base.replace(marker, marker + "\n" + claim + "\n", 1)


def score(case, result):
    payload = _evaluation_payload(result)
    target = case["claim"]
    claims = [c for a in payload.get("audits", ()) for c in a["claims"]
              if target in c["quote"] or (len(c["quote"]) >= min(12, len(target)) and c["quote"] in target)]
    issues = payload["issues"]
    unsupported = any(c["status"] == "unsupported" and any(i["quote"] == c["quote"] for i in issues) for c in claims)
    clarified = any(c.get("scope") == "ambiguous" and any(i["quote"] == c["quote"] and i["category"] == "other" for i in issues) for c in claims)
    accepted = result.verdict.value == "pass" and result.score >= 85 and not issues
    matched = accepted if case["expected"] == "accept" else result.verdict.value != "pass" and (clarified if case["expected"] == "clarify" else unsupported)
    return dict(id=case["id"], expected=case["expected"], valid=True, verdict=result.verdict.value,
                score=result.score, matched=matched, target_unsupported=unsupported, target_clarified=clarified)


def totals(rows, selected):
    valid = [r for r in rows if r["valid"]]
    groups = {}
    for kind in ("accept", "reject", "clarify"):
        group = [r for r in valid if r["expected"] == kind]
        groups[kind] = dict(planned=sum(c["expected"] == kind for c in selected), valid=len(group),
                            matched=sum(r["matched"] for r in group), mismatched=sum(not r["matched"] for r in group))
    return dict(attempted=len(rows), valid=len(valid), invalid=len(rows)-len(valid),
                all_attempted=len(rows) == len(selected), all_valid=len(valid) == len(selected),
                all_matched=len(valid) == len(selected) and all(r["matched"] for r in valid), groups=groups)


def evaluate_pair(cases, evaluator, summary, deterministic, knowledge, base, directory, state):
    rows = []
    for case in cases:
        report = embed(base, case["claim"])
        first_call = state["calls"] + 1
        write_new_json(directory / f"{case['id']}-input.json", {
            "report": report, "report_sha256": hashlib.sha256(report.encode()).hexdigest(),
            "first_call": first_call,
        })
        request = EvaluationRequest(summary, deterministic, knowledge, report,
            "复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。")
        try:
            result = evaluator.evaluate(request)
        except ProviderResponseError as error:
            if error.code != "invalid_structured_output":
                raise
            row = dict(id=case["id"], expected=case["expected"], valid=False,
                       error_code="invalid_structured_output", matched=False)
        else:
            write_new_json(directory / f"{case['id']}-evaluation.json", _evaluation_payload(result))
            row = score(case, result)
        row.update(first_call=first_call, last_call=state["calls"])
        rows.append(row)
        write_new_json(directory / f"{case['id']}-result.json", row)
        print(json.dumps(row), flush=True)
    return rows


def run(args):
    v8 = getattr(args, "evidence_scope_v8", False)
    from app.runtime.coach_contract import EVIDENCE_V8_COACH_CONTRACT
    contract = EVIDENCE_V8_COACH_CONTRACT if v8 else CONTRACT
    mode = "evidence_v8" if v8 else "evidence_v7"
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    check_evidence(data, SOURCE.read_bytes())
    _, summary, _ = prepare(args.source_run, evidence_scope_v7=True)
    if v8:
        from app.runtime.composition import RuntimeCompositionRoot
        assets = ROOT / "examples/runtime_profiles/flash_v2_golden_evidence_v8"
        RuntimeCompositionRoot.from_directories(skills_root=assets / "skills", prompt_programs_root=assets / "prompt_programs", coach_contract=contract)
    base = args.base_report.read_text(encoding="utf-8")
    if hashlib.sha256(base.encode()).hexdigest() != BASE_SHA:
        raise ValueError("verified_base_report_required")
    lookup = {c["id"]: c for c in data["cases"]}
    pair_numbers = args.pair or list(range(1, 7))
    if len(set(pair_numbers)) != len(pair_numbers):
        raise ValueError("duplicate_pair")
    selected = [lookup[key] for n in pair_numbers for key in PAIRS[n-1]]
    plan = dict(scope="known_development_controls_not_holdout_or_admission", pairs=pair_numbers,
        contract=contract.snapshot().model_dump(mode="json"), base_report_sha256=BASE_SHA,
        dataset_sha256=hashlib.sha256(DATASET.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        selected_case_ids=[c["id"] for c in selected], labels_sent_to_model=False,
        max_calls_per_pair=4, max_calls=4*len(pair_numbers), max_revisions=0,
        max_tokens_per_pair=401920, max_tokens=401920*len(pair_numbers),
        request_timeout_s=300, max_time_per_pair_s=900, max_time_s=900*len(pair_numbers),
        max_output_per_call=32768, reasoning_effort="high", sdk_retries=0,
        invalid_response_policy="record_invalid_then_continue_independent_case",
        transport_failure_policy="stop_remaining_suite", real_calls_authorized=args.execute)
    if not args.execute:
        print(json.dumps(plan)); return
    if not re.fullmatch(r"scope-controls-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("invalid_control_run_id")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    from dotenv import dotenv_values
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    raw = json.loads((args.source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    knowledge = KnowledgeEvidence(context=raw["context"], source_ids=tuple(raw["source_ids"]),
        citations=tuple(KnowledgeCitation(**c) for c in raw["citations"]), abstained=raw.get("abstained", False))
    deterministic = (args.source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    rows, pairs = [], []
    failure = None
    try:
        for n in pair_numbers:
            pair_dir = directory / f"pair-{n:02d}"
            pair_dir.mkdir()
            state = dict(calls=0, input_tokens=0, output_tokens=0)
            pair_receipt = dict(pair=n, state=state)
            pairs.append(pair_receipt)
            provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings,
                directory=pair_dir / "streams", transport_id=contract.descriptor()["stream_transport_id"]),
                state=state, call_limit=4, directory=pair_dir), coach_contract=contract)
            registry = ToolRegistry()
            for definition in build_llm_tools(provider, request_policy=contract.request_policy):
                registry.register(definition)
            evaluator = GroundedChatEvaluationAdapter(runtime=ToolRuntime(registry), system_prompt=EVALUATOR_SYSTEM_PROMPT,
                fact_pack_builder=build_fact_pack, inference_audit=mode)
            try:
                pair_rows = evaluate_pair([lookup[key] for key in PAIRS[n-1]], evaluator, summary,
                                          deterministic, knowledge, base, pair_dir, state)
                rows.extend(pair_rows)
                pair_receipt["completed"] = True
            finally:
                # Recover already saved case results if a later case aborts.
                for p in sorted(pair_dir.glob("*-result.json")):
                    row = json.loads(p.read_text())
                    if row["id"] not in {r["id"] for r in rows}:
                        rows.append(row)
                write_new_json(pair_dir / "receipt.json", pair_receipt)
    except Exception as error:
        failure = type(error).__name__
        raise
    finally:
        receipt = dict(plan, cases=rows, pairs_result=pairs, stopped=failure is not None,
                       error_type=failure, **totals(rows, selected))
        receipt.update(calls=sum(p["state"]["calls"] for p in pairs),
            input_tokens=sum(p["state"]["input_tokens"] for p in pairs),
            output_tokens=sum(p["state"]["output_tokens"] for p in pairs))
        write_new_json(directory / "receipt.json", receipt)
        print(json.dumps({k: receipt[k] for k in ("calls", "input_tokens", "output_tokens", "stopped", "attempted", "valid", "invalid", "all_matched", "groups")}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", type=Path, required=True)
    p.add_argument("--base-report", type=Path, required=True)
    p.add_argument("--pair", action="append", type=int, choices=range(1, 7))
    p.add_argument("--evidence-scope-v8", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--ci-run")
    p.add_argument("--run-id", default="scope-controls-preview")
    p.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    args = p.parse_args()
    if args.execute and (not args.env_file or not args.ci_run):
        p.error("execute requires env-file and ci-run")
    run(args)


if __name__ == "__main__":
    main()
