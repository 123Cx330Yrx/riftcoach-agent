"""Offline counterexamples for source ownership; no credentials or live switch.

Historical labels and reports stay immutable. New assemblies are explicitly
analyst-created witnesses, never a model edit or a new semantic observation.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import frozen_cases
from app.evaluation.source_bound_report import SLOT, VERSION, assemble_report
from app.harness.knowledge import knowledge_evidence_from_search_payloads
from app.harness.steps import EvaluationRequest
from scripts.native_contract_options import body
from app.evaluation.golden_stream_bridge import REQUEST

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = Path("data/evaluation/results/golden_role_application_result_346213c.json")
FAILURE = Path("data/evaluation/results/golden_knowledge_time_citation_result_6c3a3db.json")
RETRIEVALS = Path("data/evaluation/datasets/golden_knowledge_time_retrievals_v1.json")


def original_request():
    saved = json.loads((ROOT / APPLICATION).read_text(encoding="utf-8"))
    failure = json.loads((ROOT / FAILURE).read_text(encoding="utf-8"))
    retrievals = json.loads((ROOT / RETRIEVALS).read_text(encoding="utf-8"))
    if hashlib.sha256((ROOT / APPLICATION).read_bytes()).hexdigest() != retrievals["original_sha256"]:
        raise ValueError("source_ownership_original_changed")
    public = saved["public_json_contents"]
    old_request = REQUEST.validate_json(compact(public["transport/review/request-003.json"]))
    source = old_request.messages[2].content.split("[UNTRUSTED deterministic_source_facts]\n", 1)[1].rsplit(
        "\n[END UNTRUSTED deterministic_source_facts]", 1)[0]
    original = saved["original_markdown_contents"]["reports/output/final_report.md"]
    knowledge = knowledge_evidence_from_search_payloads(row["data"] for row in retrievals["searches"])
    req = EvaluationRequest(public["reports/inputs/player_summary.json"], source, knowledge,
        original, body(old_request)["user_utterance"])
    return req, saved, failure


def audit():
    req, saved, failure = original_request()
    original, knowledge = req.report, req.knowledge
    records = []
    try:
        assemble_report(original, knowledge, phase="draft", record=records.append)
    except ValueError as error:
        legacy_rejection = str(error)
    else:
        raise AssertionError("legacy prose must never be silently migrated")

    # Preserve the complete bad report. Adding correct metadata cannot repair it.
    witness = assemble_report(original + "\n\n" + SLOT, knowledge, phase="draft", record=records.append)
    assert witness.startswith(original)
    bad_quote = failure["host_review"]["report_quote"]
    assert bad_quote in witness
    raw = failure["public_json_contents"]["original-date-error/journal.json"]["raw"]
    assert digest(raw) == failure["public_json_contents"]["original-date-error/journal.json"]["raw_sha256"]
    original_payload, _, _ = RoleReviewWorkflow.validate_review(raw, build_inputs(req))
    payload, _, journal = RoleReviewWorkflow.validate_review(raw, build_inputs(replace(req, report=witness)))
    assert original_payload.verdict == payload.verdict == "pass"

    # These are capacity/preservation checks, not relabelled qualification cases.
    cases, _ = frozen_cases()
    coverage = []
    for case, frozen in cases:
        text = assemble_report(frozen.report + "\n\n" + SLOT, frozen.knowledge,
            phase="draft", record=lambda _: None)
        inputs = build_inputs(replace(frozen, report=text))
        prepared = RoleReviewWorkflow.make_request(inputs)
        assert text.startswith(frozen.report)
        coverage.append(dict(key=case["key"], original_report_sha256=digest(frozen.report),
            frozen_input_sha256=case["input_sha256"], witness_report_sha256=digest(text),
            full_original_preserved=True, block_count=len(inputs.source.blocks),
            review_input_reservation=size(prepared), model_observed=False))
    paths = (APPLICATION, FAILURE, RETRIEVALS,
        Path("app/evaluation/source_bound_report.py"), Path("scripts/check_source_bound_report.py"))
    return dict(evidence_kind="offline_responsibility_counterexamples", version=VERSION,
        input_file_sha256={p.as_posix(): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        records=[row.to_dict() for row in records],
        legacy_report=dict(rejection=legacy_rejection, meaning="missing new syntax, NOT detection of the date error"),
        negative_control=dict(original_bad_quote=bad_quote, retained=True,
            replayed_raw_sha256=digest(raw), validator_verdict=payload.verdict,
            semantic_approval=journal["semantic_approval"], host_accepted=False,
            scope="Old public response replayed on an analyst-assembled report; no new model observation."),
        frozen_15_preservation=coverage, provider_requests=0, production_admitted=False,
        decision="Retain offline assembly boundary; reject source rendering as a sufficient semantic fix.",
        remaining="Full-context reviewer recall and source entailment, actual generation/edit/final review, original-15 qualification and product consumption.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        write_new_json(args.output, result)
    print(compact({key: result[key] for key in ("evidence_kind", "decision", "provider_requests", "production_admitted")}))


if __name__ == "__main__":
    main()
