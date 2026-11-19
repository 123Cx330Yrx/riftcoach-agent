"""Offline expressibility, preservation and capacity witnesses, not live quality."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import source_patch_editor as editor
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import frozen_cases
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from scripts.check_source_bound_report import original_request, ROOT


def audit():
    req, saved, failure = original_request()
    inputs = build_inputs(req)
    reference = json.loads((ROOT / "data/evaluation/datasets/golden_source_time_reference_audit_v2.json").read_text(encoding="utf-8"))
    edits = []
    for change in reference["edits_from_original"]:
        block = next(n for n, (_, text) in enumerate(inputs.source.blocks, 1) if change["before"] in text)
        edits.append(dict(block=block, before=change["before"], after=change["after"],
            source_ids=[25] if block == 27 else [31], reason="Analyst-created representation witness, never model output."))
    assembly = editor.apply_edits(compact(dict(edits=edits)), inputs)
    assert assembly.report == reference["reference_report"]
    actual_final_input = build_inputs(replace(req, report=assembly.report))
    final = RoleReviewWorkflow.make_request(actual_final_input)
    keep = editor.apply_edits('{"edits":[]}', inputs)
    old_raw = failure["public_json_contents"]["original-date-error/journal.json"]["raw"]
    payload, _, _ = RoleReviewWorkflow.validate_review(old_raw, build_inputs(replace(req, report=keep.report)))
    coverage = []
    for case, frozen in frozen_cases()[0]:
        check = build_inputs(frozen)
        unchanged = editor.apply_edits('{"edits":[]}', check)
        assert unchanged.report == frozen.report
        coverage.append(dict(key=case["key"], input_sha256=case["input_sha256"],
            report_sha256=digest(frozen.report), keep_identical=True,
            edit_input_reservation=size(editor.edit_request(check)), model_observed=False))
    # Historical generation requests are capacity samples only. They do NOT
    # make a new end-to-end run: the current retrieval projection is different.
    generation = [REQUEST.validate_json(compact(saved["public_json_contents"][name])) for name in (
        "transport/generation/request-001.json", "transport/generation/request-002.json")]
    requests = [*generation, RoleReviewWorkflow.make_request(inputs), editor.edit_request(inputs), final]
    sizes = [size(r) for r in requests]
    limits = ROLE_COACH_CONTRACT.descriptor()
    full_reservation = sum(sizes) + sum(r.max_tokens for r in requests)
    paths = ("app/evaluation/source_patch_editor.py", "scripts/check_source_patch_editor.py")
    return dict(evidence_kind="offline_explicit_source_edit_feasibility", provider_requests=0,
        production_admitted=False, product_state_machine_implemented=False,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        analyst_authored_patch=assembly.journal, final_review_report_sha256=digest(actual_final_input.source.report),
        keep_negative_control=dict(report_unchanged=keep.report == req.report, old_reviewer_verdict=payload.verdict,
            host_accepted=False, semantic_approval=False), frozen_fifteen=coverage,
        five_call_capacity_sample=dict(input_reservations=sizes, full_output_reservation=full_reservation,
            call_limit=limits["max_calls"], token_limit=limits["total_tokens"],
            within_input_caps=all(n <= limits["max_input_tokens"] for n in sizes),
            fits_conservative_token_sum=full_reservation <= limits["total_tokens"],
            execution_timeout_s=limits["execution_timeout_s"], per_call_timeout_s=limits["request_timeout_s"],
            latency_not_proven=True, generation_is_historical_size_sample=True),
        remaining=["live source edit/keep correctness and completion", "actual edited-report full final review",
            "explicit Harness pass-after-check states and shared budget integration",
            "same-version original fifteen and real product consumption"])


if __name__ == "__main__":
    print(compact(audit()))
