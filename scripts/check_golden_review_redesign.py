"""Offline decision experiment, NOT an implemented or callable Coach candidate.

Replay saved defects, measure direct reuse of existing review/scope requests,
and demonstrate what explicit handles and source checks can/cannot establish.
No credentials, Provider construction, network requests, or historical rewrites.
"""
import argparse
from dataclasses import replace
from pathlib import Path

from pydantic import Field

from app.evaluation import golden_integrated_review as integrated
from app.evaluation.golden_bound_scope_review import ScopeJudgment, prepare, seal_issued_request, decode
from app.evaluation.golden_context_requests import evaluation_request, revision_request
from app.evaluation.golden_context_review import ContextEvaluation
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest
from app.providers.models import ChatMessage, ChatResponse, MessageRole, TokenUsage
from app.providers.structured import contract_for_model
from scripts.check_golden_integrated_workflow import budgeted
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


class HandledScope(ScopeJudgment):
    target_id: str = Field(pattern=r"^t[0-9]{3}$")


class AddedScope(integrated.Strict):
    source_ref: QuoteRef
    judgment: ScopeJudgment


class BatchScope(integrated.Strict):
    judgments: list[HandledScope] = Field(max_length=64)
    additions: list[AddedScope] = Field(max_length=64)


def handles(source, refs):
    result, seen = {}, set()
    for n, ref in enumerate(refs, 1):
        quote = source.resolve(ref)
        key = (ref["block"], quote)
        if key in seen:
            raise ValueError("duplicate_source_target")
        if n > 64:
            raise ValueError("target_limit")
        seen.add(key)
        result[f"t{n:03}"] = dict(source_ref=ref, quote=quote)
    return result


def join_by_handle(expected, rows):
    """Only identity/correspondence; never approves a judgment's meaning."""
    indexed = {}
    for row in rows:
        key = row.get("target_id")
        if key not in expected:
            raise ValueError("unknown_target_handle")
        if key in indexed:
            raise ValueError("duplicate_target_handle")
        indexed[key] = row
    if set(indexed) != set(expected):
        raise ValueError("missing_target_handle")
    return [(expected[key], indexed[key]) for key in expected]


def batch_shape(single, source, refs):
    """Sizing template only: no response decoder, runtime, or semantic adoption."""
    req = single.request
    schema, content = req.messages[1].content.split("\n[UNTRUSTED DATA]\n", 1)
    data = strict_json(content.removesuffix("\n[END UNTRUSTED DATA]"))
    data.pop("target_ref")
    data["targets"] = [{"target_id": k, "source_ref": v["source_ref"]}
                       for k, v in handles(source, refs).items()]
    contract = contract_for_model(name="scope_batch_sizing_only", version="1.0.0", output_model=BatchScope)
    # The existing single-target instructions are retained for an honest reuse
    # size comparison. This is deliberately NOT a prompt ready for execution.
    return replace(req, response_contract=contract, messages=(req.messages[0],
        ChatMessage(role=MessageRole.USER, content=compact(contract.schema_dict())
            + "\n[UNTRUSTED DATA]\n" + compact(data) + "\n[END UNTRUSTED DATA]")))


def measure(source_run, base_report, run_dir, historical_evaluation):
    summary, deterministic, knowledge, cases = load_inputs(source_run, base_report)
    case = next(c for c in cases if c["id"] == "stable_unbounded")
    report = case["report"]
    inputs = integrated.ReviewInput.build(EvaluationRequest(summary, deterministic, knowledge, report, UTTERANCE))
    case_dir = run_dir / case["id"]
    original_paths = [case_dir / n for n in ("input.json", "response-001.json", "response-002.json", "diagnostics.json")]
    snapshots = {str(p): p.read_bytes() for p in original_paths}
    saved_input = strict_json(original_paths[0].read_text(encoding="utf-8"))
    if saved_input.get("report") != report:
        raise ValueError("saved_report_mismatch")
    discovery = strict_json(original_paths[1].read_text(encoding="utf-8"))["content"]
    raw = strict_json(original_paths[2].read_text(encoding="utf-8"))["content"]
    targets, _ = integrated.discover(discovery, inputs)
    diagnostics = integrated.assessment_feedback(raw, inputs, targets)
    # Use only explicit synthetic handles to test joining. The saved positional
    # response has no handles and cannot be retroactively joined or accepted.
    mapping = handles(inputs.source, targets)
    rows = [{"target_id": k, "test_marker": v["quote"]} for k, v in mapping.items()]
    reversed_join = join_by_handle(mapping, list(reversed(rows)))
    missing_rejected = False
    try:
        join_by_handle(mapping, rows[1:])
    except ValueError as error:
        missing_rejected = str(error) == "missing_target_handle"

    first_sizes, scope_sizes, batch_sizes = [], [], []
    for c in cases:
        current = integrated.ReviewInput.build(EvaluationRequest(summary, deterministic, knowledge, c["report"], UTTERANCE))
        first_sizes.append(size(budgeted(evaluation_request(summary, deterministic, knowledge, c["report"], UTTERANCE))))
        single = prepare(summary, deterministic, knowledge, c["report"], c["target"])
        scope_sizes.append(size(budgeted(single.request)))
        refs = targets if c["id"] == case["id"] else tuple({"block": i} for i in range(1, len(current.source.blocks)+1))
        batch_sizes.append(size(budgeted(batch_shape(single, current.source, refs))))
    historical = ContextEvaluation.model_validate(strict_json(historical_evaluation.read_text(encoding="utf-8")), strict=True)
    defined = next(c for c in cases if c["id"] == "stable_defined_before")
    revision_size = size(budgeted(revision_request(summary, deterministic, knowledge, defined["report"], historical)))

    # Deliberate semantic counterexample: the overall summary is real source
    # text, but it does not explicitly define this target's word under the frozen
    # rubric. A valid reference and receipt alone cannot decide that relation.
    single = prepare(summary, deterministic, knowledge, report, case["target"])
    context = next(i for i, (_, text) in enumerate(single.source.blocks, 1) if text.startswith("近 5 局"))
    fake = compact(dict(disposition="sample_defined", context_ref={"block": context},
        explanation="整体段落的数字正确，因此已经定义了较稳定的含义。"))
    issued = seal_issued_request(single, budgeted(single.request))
    response = ChatResponse(content=fake, provider="zhipu", model="glm-5.3-flash", finish_reason="stop",
                            usage=TokenUsage(input_tokens=0, output_tokens=0))
    restored = decode(issued, response, receipt_request_sha256=issued.request_sha256)
    for p in original_paths:
        if p.read_bytes() != snapshots[str(p)]:
            raise ValueError("historical_evidence_changed")
    return dict(experiment="golden-review-redesign-offline-v1", provider_calls=0,
        candidate_implemented=False, candidate_adopted=False, semantic_quality="not_evaluated",
        source_report_sha256=digest(report), saved_targets=len(targets), replay_diagnostics=diagnostics,
        historical_bytes_unchanged=True,
        handle_prototype=dict(reordered_rows_keep_source=all(a["quote"] == b["test_marker"] for a,b in reversed_join),
            missing_row_rejected=missing_rejected, historical_rows_assigned_handles=False),
        counterexample=dict(kind="scripted_source_valid_but_relation_unproven",
            source_reference_valid=True, protocol_decoded=restored["disposition"] == "sample_defined",
            whole_report_accepted=restored["whole_report_acceptance"], frozen_rubric_expected="clarify",
            model_generated=False),
        direct_reuse_sizing=dict(full_review_input_range=[min(first_sizes), max(first_sizes)],
            single_scope_input_range=[min(scope_sizes), max(scope_sizes)],
            batch_scope_shape_input_range=[min(batch_sizes), max(batch_sizes)],
            historical_revision_input=revision_size,
            single_scope_five_call_envelope=2*(max(first_sizes)+max(scope_sizes))+revision_size+5*32768,
            batch_scope_five_call_envelope=2*(max(first_sizes)+max(batch_sizes))+revision_size+5*32768,
            limit=401920, first_pass="existing_full_review_not_a_fact_only_implementation",
            target_shapes="saved_48_for_unbounded_case_whole_blocks_for_other_cases",
            limitation="Measured reuse shapes, not future maxima or actual usage. Budget settles actual usage; envelope overrun does not predict every run fails."),
        correction_slots=dict(two_phases_twice_plus_revision=5, available=5,
            one_correction_after_each_evaluation_would_require=7),
        decision="reject_direct_reuse_as_ready_candidate; explicit_handles_only_solve_identity; semantic_obligation_and_correction_path_unresolved")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "run-dir", "historical-evaluation"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = measure(args.source_run, args.base_report, args.run_dir, args.historical_evaluation)
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))


if __name__ == "__main__":
    main()
