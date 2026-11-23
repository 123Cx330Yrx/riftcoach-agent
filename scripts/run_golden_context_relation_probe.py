"""Four frozen targets, one full-context diagnostic call each; preview by default."""
import argparse
import json
from pathlib import Path
import re

from app.evaluation.golden_context_relation_probe import EXPERIMENT_ID, validate_response
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from scripts.run_golden_context_controls import load_inputs, MANIFEST, ROOT
from scripts.run_golden_scope_controls import case_progress
from scripts.run_golden_inference_development import Counted, verify_public_ci


def observe(provider, directory, cases, requests, pack, state, *, validator=validate_response, experiment_id=EXPERIMENT_ID):
    """Persist every started case and stop the batch on invalid/transport output."""
    rows, started = [], []
    failure = None
    try:
        for case, request in zip(cases, requests, strict=True):
            write_new_json(directory / (case["id"] + "-input.json"),
                dict(report=case["report"], target=case["target"], report_sha256=case["report_sha256"]))
            started.append(case["id"])
            response = provider.chat(request)
            row = dict(id=case["id"], valid=False, target_matched=False)
            try:
                if response.finish_reason != "stop" or response.tool_calls:
                    raise ValueError("incomplete_relation_response")
                result = validator(response.content, case["report"], pack, case["target"])
            except (ValueError, TypeError):
                failure = "protocol"
                row["failure_kind"] = failure
            else:
                expected = {"accept": "sample_defined", "clarify": "needs_clarification"}[case["expected_target"]]
                row.update(valid=True, disposition=result.disposition, expected=expected,
                    target_matched=result.disposition == expected)
                write_new_json(directory / (case["id"] + "-judgment.json"), result.model_dump(mode="json"))
            rows.append(row)
            write_new_json(directory / (case["id"] + "-result.json"), row)
            print(compact(row), flush=True)
            if failure:
                break
    except BaseException as error:
        failure = type(error).__name__
        raise
    finally:
        receipt = dict(experiment_id=experiment_id, cases=rows, case_counts=case_progress(cases, started, rows),
            **state, stopped=failure is not None, failure=failure,
            whole_report_acceptance=False, automatic_target_matches=sum(r["target_matched"] for r in rows),
            manual_semantic_review_required=True)
        write_new_json(directory / "receipt.json", receipt)
        print(compact({k: v for k, v in receipt.items() if k != "cases"}), flush=True)


def run(args):
    from app.evaluation import golden_context_relation_probe as experiment
    if getattr(args, "v2", False):
        from app.evaluation import golden_context_relation_probe_v2 as experiment
    summary, deterministic, knowledge, cases = load_inputs(args.source_run, args.base_report)
    cases = cases[:4]  # Frozen critical definition and heading pairs only.
    requests = [experiment.build_request(summary, deterministic, knowledge, c["report"], c["target"]) for c in cases]
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT as budget_contract
    plan = dict(experiment_id=experiment.EXPERIMENT_ID, response_contract_version=experiment.response_contract().version,
        scope="target_scope_diagnostic_not_report_evaluation",
        selected_case_ids=[c["id"] for c in cases], labels_sent_to_model=False,
        manifest_sha256=digest(MANIFEST.read_text(encoding="utf-8")),
        input_ceilings=[estimate_runtime_request_input_ceiling(r) for r in requests],
        input_identities=[digest(compact([m.content for m in r.messages])) for r in requests],
        budget_contract=budget_contract.snapshot().model_dump(mode="json"),
        max_calls=4, max_revisions=0, max_corrections=0, sdk_retries=0, reasoning_effort="high",
        max_input_tokens=64000, max_output_tokens=32768, request_timeout_s=300,
        total_tokens=401920, execution_timeout_s=900, whole_report_acceptance=False)
    if not args.execute:
        print(compact(plan))
        return plan
    if not re.fullmatch(r"context-relation-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("invalid_relation_run_id")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    from app.evaluation.golden_stream_bridge import GoldenProcessStreamProvider
    from app.runtime.coach_budget import CoachBudgetedProvider
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    state = dict(calls=0, input_tokens=0, output_tokens=0)
    provider = CoachBudgetedProvider(Counted(GoldenProcessStreamProvider(settings=settings,
        directory=directory / "streams", transport_id=budget_contract.descriptor()["stream_transport_id"]),
        state=state, call_limit=4, directory=directory), coach_contract=budget_contract)
    observe(provider, directory, cases, requests, fact_pack(summary), state,
        validator=experiment.validate_response, experiment_id=experiment.EXPERIMENT_ID)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-run", required=True, type=Path)
    p.add_argument("--base-report", required=True, type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--v2", action="store_true", help="Use the separately versioned reference-only diagnostic schema")
    p.add_argument("--env-file", type=Path)
    p.add_argument("--ci-run")
    p.add_argument("--run-id", default="context-relation-preview")
    p.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    args = p.parse_args()
    if args.execute and (not args.env_file or not args.ci_run):
        p.error("execute requires env-file and ci-run")
    run(args)


if __name__ == "__main__":
    main()
