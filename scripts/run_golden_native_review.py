"""One explicitly selected observed-report control, with original receipt gates.

Preview is local/read-only. Labels stay in the scorer, never in model input.
This runner does not register a production Coach or publish a report.
"""
import argparse
from contextlib import nullcontext
from dataclasses import replace
import hashlib
from pathlib import Path
import re

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation
from scripts.run_golden_context_controls import load_inputs
from scripts.run_golden_integrated_review import observe_report
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/datasets/golden_observed_review_controls_v1.json"
ATTRIBUTION_DATASET = ROOT / "data/evaluation/datasets/golden_native_product_attribution_controls_v1.json"
SCOPE_DATASET = ROOT / "data/evaluation/datasets/golden_native_scope_resolution_controls_v1.json"
CLAIM_SCOPE_DATASET = ROOT / "data/evaluation/datasets/golden_native_claim_scope_controls_v1.json"


def score_case(case, result):
    """Location/category match is only a development signal, not entailment."""
    targets = case['targets'] if 'targets' in case else [case['target']]
    flagged = [i for i in result.issues if any(target in i["quote"] for target in targets)]
    unexpected = [number for number, issue in enumerate(result.issues, 1)
                  if not any(target in issue["quote"] for target in targets)]
    accepted = result.verdict.value == "pass" and result.score >= 85 and not result.issues
    matched = accepted if case["expected_report"] == "accept" else result.verdict.value != "pass" and bool(flagged)
    return dict(id=case["id"], valid=True, matched=matched,
        verdict=result.verdict.value, score=result.score, expected_report=case["expected_report"],
        target_location_flagged=bool(flagged),
        unexpected_issue_indices=unexpected,
        manual_adjudication_required=bool(unexpected),
        suggested_category_matched=any(i["category"] in case.get("expected_categories", []) for i in flagged),
        semantic_approval=False)


def prepare(case_index):
    dataset = candidate.strict_json(DATASET.read_text(encoding="utf-8"))
    bindings = dataset["source_bindings"]
    for item in bindings["files"]:
        if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("native_control_source_changed")
    summary, deterministic, knowledge, _ = load_inputs(ROOT / bindings["source_run"], ROOT / bindings["base_report"])
    cases = dataset["cases"]
    if not 1 <= case_index <= len(cases):
        raise ValueError("native_control_case_index_invalid")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("native_control_duplicate_identity")
    for case in cases:
        if digest(case["report"]) != case["report_sha256"] or case["report"].count(case["target"]) != 1:
            raise ValueError("native_control_report_changed")
        if case["expected_report"] not in ("accept", "reject"):
            raise ValueError("native_control_label_invalid")
    case = cases[case_index - 1]
    req = EvaluationRequest(summary, deterministic, knowledge, case["report"], dataset["user_utterance"])
    return case, req


def prepare_attribution(case_index):
    """Load the unchanged saved-product pair; labels/arithmetic stay host-side."""
    data = candidate.strict_json(ATTRIBUTION_DATASET.read_text(encoding="utf-8"))
    if hashlib.sha256((ROOT / data['origin_artifact']).read_bytes()).hexdigest() != data['origin_artifact_sha256']:
        raise ValueError('native_attribution_origin_changed')
    sources = {}
    for item in data['source_files']:
        path = ROOT / item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('native_attribution_source_changed')
        sources[path.name] = path.read_text(encoding='utf-8')
    if not 1 <= case_index <= len(data['cases']):
        raise ValueError('native_control_case_index_invalid')
    if len({c['id'] for c in data['cases']}) != len(data['cases']):
        raise ValueError('native_control_duplicate_identity')
    for case in data['cases']:
        if digest(case['report']) != case['report_sha256'] or case['report'].count(case['target']) != 1:
            raise ValueError('native_control_report_changed')
        if case['expected_report'] not in ('accept', 'reject'):
            raise ValueError('native_control_label_invalid')
    raw = candidate.strict_json(sources['retrieval_evidence.json'])
    knowledge = KnowledgeEvidence(context=raw['context'], source_ids=tuple(raw['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in raw['citations']), abstained=raw['abstained'])
    case = data['cases'][case_index - 1]
    return case, EvaluationRequest(candidate.strict_json(sources['player_summary.json']),
        sources['deterministic_report.md'], knowledge, case['report'], data['user_utterance'])


def prepare_scope(case_index):
    data = candidate.strict_json(SCOPE_DATASET.read_text(encoding='utf-8'))
    if (ROOT / data['parent_dataset']).resolve() != ATTRIBUTION_DATASET.resolve():
        raise ValueError('native_scope_parent_changed')
    if hashlib.sha256(ATTRIBUTION_DATASET.read_bytes()).hexdigest() != data['parent_sha256']:
        raise ValueError('native_scope_parent_changed')
    _, original = prepare_attribution(2)
    parent = candidate.strict_json(ATTRIBUTION_DATASET.read_text(encoding='utf-8'))
    if data['source_files'] != parent['source_files'] or data['user_utterance'] != original.user_utterance:
        raise ValueError('native_scope_sources_changed')
    if not 1 <= case_index <= len(data['cases']):
        raise ValueError('native_control_case_index_invalid')
    if len({c['id'] for c in data['cases']}) != len(data['cases']):
        raise ValueError('native_control_duplicate_identity')
    for case in data['cases']:
        if digest(case['report']) != case['report_sha256'] or case['report'].count(case['target']) != 1:
            raise ValueError('native_control_report_changed')
        if case['expected_report'] not in ('accept', 'reject'):
            raise ValueError('native_control_label_invalid')
    case = data['cases'][case_index - 1]
    return case, replace(original, report=case['report'])


def prepare_claim_scope(case_index):
    """Reuse committed source checks; analyst labels never enter the request."""
    from scripts.check_native_claim_scope import load_controls
    data, requests, _ = load_controls()
    if not 1 <= case_index <= len(data['cases']):
        raise ValueError('native_control_case_index_invalid')
    return data['cases'][case_index - 1], requests[case_index - 1]


def run(args, *, candidate_module=None):
    active = candidate_module or candidate
    if args.execute:
        active.require_live_qualification()
    suite = getattr(args, 'suite', 'observed')
    loader, dataset = {'observed': (prepare, DATASET), 'attribution': (prepare_attribution, ATTRIBUTION_DATASET),
                       'scope': (prepare_scope, SCOPE_DATASET),
                       'claim-scope': (prepare_claim_scope, CLAIM_SCOPE_DATASET)}[suite]
    case, req = loader(args.case_index)
    inputs = active.NativeBusinessReviewWorkflow.build_inputs(req)
    route = getattr(args, 'provider_route', 'environment')
    if route not in ('environment', 'direct', 'proxy_12000'):
        raise ValueError('native_provider_route_invalid')
    stream_tools = getattr(active, 'STREAM_TOOL_ARGUMENTS', True)
    plan = dict(experiment_id=active.EXPERIMENT_ID, selected_cases=[case["id"]],
        manifest_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        suite=suite, provider_route=route, stream_tool_arguments=stream_tools,
        report_sha256=digest(req.report), input_sha256=digest(inputs.data_json),
        first_input_ceiling=size(active.request(inputs)), labels_sent_to_model=False,
        source_scope="complete_observed_report_analyst_development_control_not_holdout",
        max_calls_per_report=5, max_revisions_per_report=1, max_tokens_per_report=401920,
        max_seconds_per_report=900, max_output_per_call=32768, max_seconds_per_call=300,
        reasoning_effort="high", sdk_retries=0, live_status=active.LIVE_STATUS,
        live_block_reason=active.LIVE_BLOCK_REASON, production_admitted=False,
        manual_between_cases=True, stop_before_unadjudicated_revision=True, semantic_approval=False)
    if not args.execute:
        print(compact(plan))
        return plan
    if not re.fullmatch(r"native-review-[a-z0-9-]{1,55}", args.run_id):
        raise ValueError("native_run_id_invalid")
    plan.update(head_sha=verify_public_ci(args.ci_run), ci_run=args.ci_run)
    directory = args.output_root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / "plan.json", plan)
    case_dir = directory / case["id"]
    case_dir.mkdir()
    write_new_json(case_dir / "input.json", dict(report=req.report, report_sha256=case["report_sha256"]))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    outcome = None
    try:
        settings = load_zhipu_settings(dotenv_values(args.env_file))
        from scripts.diagnose_block_review_route import route_environment
        provider = ReceiptedStreamProvider(settings=settings, directory=case_dir / "streams",
            transport_id=CAPACITY_TRANSPORT_ID, stream_tool_arguments=stream_tools)
        with nullcontext() if route == 'environment' else route_environment(route):
            outcome = observe_report(provider, case_dir, req, case,
                workflow_factory=active.NativeBusinessReviewWorkflow, score_case=score_case)
        print(compact(outcome), flush=True)
        return outcome
    finally:
        saved = case_dir / "result.json"
        accounting = candidate.strict_json(saved.read_text(encoding="utf-8")) if saved.exists() else {}
        receipt = dict(plan, cases=[outcome] if outcome is not None else [],
            reserved_calls=accounting.get("reserved_calls", 0),
            completed_calls=accounting.get("completed_calls", 0),
            input_tokens=accounting.get("input_tokens", 0), output_tokens=accounting.get("output_tokens", 0),
            unknown_usage_calls=accounting.get("unknown_usage_calls", 0), manual_semantic_acceptance=False)
        write_new_json(directory / "receipt.json", receipt)


def main(*, candidate_module=None, policy_variants=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-index", type=int, default=1)
    parser.add_argument("--suite", choices=('observed', 'attribution', 'scope', 'claim-scope'), default='observed')
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--ci-run", default="")
    parser.add_argument('--provider-route', choices=('environment', 'direct', 'proxy_12000'), default='environment')
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/runs/inference_development")
    if policy_variants:
        parser.add_argument('--policy', choices=('legacy', *policy_variants), default='legacy')
    args = parser.parse_args()
    if policy_variants and args.policy != 'legacy':
        candidate_module = policy_variants[args.policy]
    run(args, candidate_module=candidate_module)


if __name__ == "__main__":
    main()
