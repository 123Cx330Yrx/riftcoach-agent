"""Measure fully materialized offline candidate requests; never call a provider."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.golden_fact_requests import evaluation_request, revision_request
from app.evaluation.golden_fact_operations import OperationEvaluation
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.harness.steps import KnowledgeEvidence, KnowledgeCitation


def probe(source, report_path):
    summary = json.loads((source / "inputs/player_summary.json").read_text(encoding="utf-8"))
    deterministic = (source / "inputs/deterministic_report.md").read_text(encoding="utf-8")
    data = json.loads((source / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
    knowledge = KnowledgeEvidence(context=data["context"], source_ids=tuple(data["source_ids"]),
                                  citations=tuple(KnowledgeCitation(**v) for v in data["citations"]))
    report = report_path.read_text(encoding="utf-8")
    args = (summary, deterministic, knowledge, report, "Observe report quality.")
    # Deliberately worst-sized bounded feedback rows, not real model diagnoses.
    errors = [{"audit_index": 1, "claim_index": i, "quote_excerpt": "未可信的原句数据" * 10,
               "codes": ["numeric_binding_value_mismatch", "ambiguous_exact_other_issue_missing"]} for i in range(48)]
    requests = [evaluation_request(*args), evaluation_request(*args, diagnostics=errors)]
    # Scripted revision layout only. Claim labels here are not semantic results.
    quotes = [b["text"] for b in report_blocks(report) if "稳定" in b["text"]]
    claims = [dict(quote=q, status="supported", evidence_refs=["scope:limits"], explanation="Scripted size fixture",
                   claim_kind="inference", scope="ambiguous", scope_anchor="稳定", numeric_bindings=[]) for q in quotes]
    issues = [dict(severity="medium", category="other", quote=q, evidence="Scripted size fixture",
                   explanation="Scope clarification fixture", suggested_correction="Clarify sample scope") for q in quotes]
    evaluation = OperationEvaluation.model_validate(dict(score=95, verdict="needs_revision" if quotes else "pass", issues=issues,
        passed_checks=[], summary="Scripted layout only, not semantic approval",
        audits=[dict(kind="metric_to_ability", status="not_applicable", claims=[]),
                dict(kind="cohort_comparison", status="supported" if quotes else "not_applicable", claims=claims)],
        coverage=[dict(block_id=b["block_id"], metric_to_ability="not_applicable",
                       cohort_comparison="supported" if b["text"] in quotes else "not_applicable",
                       scope_ambiguous=b["text"] in quotes) for b in report_blocks(report)]))
    requests.append(revision_request(summary, deterministic, knowledge, report, evaluation))
    return {"input_ceilings": [estimate_runtime_request_input_ceiling(r) for r in requests],
            "output_caps": [r.max_tokens for r in requests], "timeouts": [r.timeout_s for r in requests],
            "new_policy_included": True, "revision_layout": "scripted_not_maximum",
            "external_calls": 0, "runtime_integrated": False, "semantic_approval": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(probe(args.source_run, args.report)))
