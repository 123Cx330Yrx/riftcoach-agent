"""Same-request Flash reviewer control; existing GLM and edit batches stay closed."""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from scripts.run_knowledge_time_review_pair import prepare as prepare_original, ROOT

EXPERIMENT = "flash-knowledge-time-same-request-review-v1"
RUN_DIRECTORY = ROOT / "data/runs/model_comparison" / EXPERIMENT
CLOSED_EVIDENCE = ROOT / "data/evaluation/results/golden_flash_knowledge_time_review_result_v1.json"
PREDECESSOR = ROOT / "data/evaluation/results/golden_knowledge_time_citation_result_6c3a3db.json"


def prepare():
    variants, original = prepare_original()
    prior = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    actual = prior["public_json_contents"]["original-date-error/request.raw.json"]
    raw_original = validate_request(variants[0][2], transport_id=CAPACITY_TRANSPORT_ID)
    if (json.loads(raw_original) != actual or hashlib.sha256(raw_original).hexdigest()
            != prior["original_file_sha256"]["original-date-error/request.raw.json"]):
        raise ValueError("flash_time_original_request_changed")
    for (_, _, request), cell in zip(variants, original["cells"], strict=True):
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        if hashlib.sha256(raw).hexdigest() != cell["request_sha256"]:
            raise ValueError("flash_time_same_request_required")
    budget = dict(original["proposed_diagnostic_budget"])
    price = ROLE_COACH_CONTRACT.pricing_profiles["zhipu", "glm-5.3-flash"]
    cost = (Decimal(sum(c["input_reservation"] for c in original["cells"])) * price.input_cost_per_million
        + Decimal(sum(c["output_cap"] for c in original["cells"])) * price.output_cost_per_million) / 1_000_000
    budget["estimated_uncached_cny"] = str(cost)
    plan = dict(experiment=EXPERIMENT, model="glm-5.3-flash", reasoning_effort="high", sdk_retries=0,
        transport_id=CAPACITY_TRANSPORT_ID, cells=original["cells"], proposed_diagnostic_budget=budget,
        original_glm_preparation_sha256=digest(compact(original)),
        original_glm_result_sha256=hashlib.sha256(PREDECESSOR.read_bytes()).hexdigest(),
        source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            "scripts/run_flash_knowledge_time_review_pair.py", "scripts/run_knowledge_time_review_pair.py",
            "scripts/run_review_model_comparison.py")},
        source_candidate=original["candidate"], provider_requests=0, production_admitted=False,
        both_requests_byte_identical_to_glm_preparation=True, original_glm_reference_call_sent=False,
        labels_sent_to_model=False, prior_reviews_sent_to_model=False,
        stop_rule="Any protocol/source/semantic/budget failure stops before the next call; no retries.",
        decision_if_accepted="Prepare actual needs_revision/edit/final-review with existing workflow; no model-route adoption or qualification yet.",
        decision_if_rejected="Do not adopt this reviewer substitution; close the pair, no policy variants or automatic paid retries.")
    return variants, plan


def run(args):
    if args.execute and CLOSED_EVIDENCE.exists():
        raise ValueError("flash_time_review_batch_closed")
    variants, plan = prepare()
    plan_sha = digest(compact(plan))
    if not args.execute:
        print(compact(dict(preparation_plan=plan, preparation_plan_sha256=plan_sha)), flush=True)
        return plan
    if not args.approval_plan_sha or args.approval_plan_sha != plan_sha:
        raise ValueError("flash_time_review_plan_mismatch")
    if RUN_DIRECTORY.exists():
        raise ValueError("flash_time_review_batch_exists")
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
    from scripts.run_review_model_comparison import observe
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model="glm-5.3-flash")
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY / "transport",
        transport_id=CAPACITY_TRANSPORT_ID)
    with route_environment("direct"):
        result = observe(provider, RUN_DIRECTORY, variants, plan,
            reviewer_profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE, transport_id=CAPACITY_TRANSPORT_ID)
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
