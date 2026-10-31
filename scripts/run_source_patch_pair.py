"""Bounded source-check/editor capability; no product adoption or live retries.

Uses the complete failed report and the independently audited correct reference.
The operation set and actual assembled report both require host adjudication.
"""
from scripts.closed_comparison_preview import bind_closed_plan

import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation import source_patch_editor as editor
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from scripts.run_flash_knowledge_time_review_pair import prepare as source_controls, ROOT

EXPERIMENT = "source-check-explicit-edit-pair-v1"
RUN_DIRECTORY = ROOT / "data/runs/model_comparison" / EXPERIMENT
CLOSED_EVIDENCE = ROOT / "data/evaluation/results/golden_source_patch_pair_result_v1.json"


def prepare():
    originals, controls = source_controls()
    variants, cells = [], []
    for index, (name, inputs, _) in enumerate(originals):
        request = editor.edit_request(inputs)
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        variants.append((name, inputs, request))
        cells.append(dict(id=name, report_sha256=digest(inputs.source.report), input_sha256=digest(inputs.data_json),
            request_sha256=hashlib.sha256(raw).hexdigest(), input_reservation=size(request), output_cap=request.max_tokens,
            expected_host_only=("Correct both source-time errors; preserve correct content and supported citations."
                if index == 0 else "No edits to the fully audited correct reference.")))
    price = ROLE_COACH_CONTRACT.pricing_profiles["zhipu", "glm-5.3-flash"]
    input_total = sum(c["input_reservation"] for c in cells)
    output_total = sum(c["output_cap"] for c in cells)
    estimate = (Decimal(input_total) * price.input_cost_per_million
        + Decimal(output_total) * price.output_cost_per_million) / 1_000_000
    paths = ("app/evaluation/source_patch_editor.py", "scripts/run_source_patch_pair.py",
        "scripts/check_source_patch_editor.py", "data/evaluation/results/golden_source_patch_feasibility_v1.json",
        "scripts/run_flash_knowledge_time_review_pair.py", "scripts/run_review_model_comparison.py",
        "data/evaluation/datasets/golden_source_time_reference_audit_v2.json",
        "data/evaluation/results/golden_flash_knowledge_time_review_result_v2.json")
    plan = dict(experiment=EXPERIMENT, source_candidate=controls["source_candidate"],
        source_control_plan_sha256=digest(compact(controls)), model="glm-5.3-flash", reasoning_effort="high",
        sdk_retries=0, transport_id=CAPACITY_TRANSPORT_ID, policy_sha256=digest(editor.POLICY), cells=cells,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600, max_seconds_per_call=300,
            total_token_reservation=input_total + output_total, estimated_uncached_cny=str(estimate)),
        prior_reviews_sent_to_model=False, labels_sent_to_model=False, provider_requests=0, production_admitted=False,
        product_state_machine_implemented=False, full_final_review_executed=False,
        decision_if_accepted="Prepare actual edited-report GLM final review, then explicit full-task control flow; no admission.",
        decision_if_rejected="Reject this source-check/editor route for the observed failure; no prompt variants or paid retries.",
        stop_rule="Any protocol, source, semantic, preservation or budget failure stops before the next call.")
    return variants, bind_closed_plan(plan, CLOSED_EVIDENCE, "ba840bc71f762fad04834466dd98d37187321ae5c17a51d8b95b8f90ac7c0945")


def run(args):
    if args.execute and CLOSED_EVIDENCE.exists():
        raise ValueError("source_patch_pair_closed")
    variants, plan = prepare()
    plan_sha = digest(compact(plan))
    if not args.execute:
        print(compact(dict(preparation_plan=plan, preparation_plan_sha256=plan_sha)), flush=True)
        return plan
    if not args.approval_plan_sha or args.approval_plan_sha != plan_sha:
        raise ValueError("source_patch_plan_mismatch")
    if RUN_DIRECTORY.exists():
        raise ValueError("source_patch_pair_exists")
    from scripts.run_golden_inference_development import verify_public_ci
    from app.evaluation.golden_journal import write_new_json
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY / "plan.json", dict(preparation_plan=plan,
        declared_approved_plan_sha256=plan_sha, execution_head_sha=head, ci_run=args.ci_run))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
    from scripts.diagnose_block_review_route import route_environment
    from scripts.run_review_model_comparison import observe, terminal_adjudication
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model="glm-5.3-flash")
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY / "transport",
        transport_id=CAPACITY_TRANSPORT_ID)
    def adjudicate(path, remaining):
        journal_path = path.parent / "journal.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        print(compact(dict(host_edit_review=journal_path.as_posix(),
            assembled_report_sha256=journal["assembled_report_sha256"],
            required_scope="Every original operation/source and the complete assembled report; compare all unchanged content too.")), flush=True)
        decision = terminal_adjudication(path, remaining)
        return dict(decision, scope="All original edits, selected sources, full assembled report and preserved correct content.",
            journal_sha256=hashlib.sha256(journal_path.read_bytes()).hexdigest(),
            assembled_report_sha256=journal["assembled_report_sha256"])
    with route_environment("direct"):
        result = observe(provider, RUN_DIRECTORY, variants, plan,
            reviewer_profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE, transport_id=CAPACITY_TRANSPORT_ID,
            inspect_response=editor.inspect_exchange, adjudicate=adjudicate)
    print(compact(result), flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-plan-sha", default="")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args(argv)
    result = run(args)
    if args.execute and not result.get("pair_accepted", False):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
