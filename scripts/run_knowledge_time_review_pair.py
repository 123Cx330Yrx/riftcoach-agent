"""Preview two complete reports with actual local retrieval times.

The v2 batch stopped after a complete semantic failure; execution is closed.
Offline preview preserves the approved request for audit. A new method requires
its own preparation and authorization, not reopening this completed batch.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.golden_stream_bridge import REQUEST, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import candidate_identity
from app.harness.knowledge import knowledge_evidence_from_search_payloads, knowledge_projection
from app.harness.steps import EvaluationRequest
from app.product.native_coach_composition import ROLE_ASSETS
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from scripts.native_contract_options import body
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'data/evaluation/results/golden_role_application_result_346213c.json'
RETRIEVALS = ROOT / 'data/evaluation/datasets/golden_knowledge_time_retrievals_v1.json'
PREDECESSOR = ROOT / 'data/evaluation/results/golden_knowledge_time_result_883c23e.json'
EXPERIMENT = 'knowledge-time-citation-review-pair-v2'
LIVE_STATUS = 'stopped_semantic_failure'
RUN_DIRECTORY = ROOT / 'data/runs/model_comparison' / EXPERIMENT


def prepare():
    RuntimeCompositionRoot.from_directories(skills_root=ROLE_ASSETS / 'skills',
        prompt_programs_root=ROLE_ASSETS / 'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    original = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    retrievals = json.loads(RETRIEVALS.read_text(encoding='utf-8'))
    if retrievals['original_sha256'] != hashlib.sha256(EVIDENCE.read_bytes()).hexdigest():
        raise ValueError('knowledge_time_original_evidence_changed')
    public = original['public_json_contents']
    old = REQUEST.validate_json(compact(public['transport/review/request-003.json']))
    old_body = body(old)
    messages = public['transport/generation/request-002.json']['messages']
    old_payloads = [json.loads(m['content'])['data'] for m in messages if m['role'] == 'tool']
    old_calls = [call for m in messages for call in m.get('tool_calls', [])]
    searches = retrievals['searches']
    if len(searches) != len(old_calls) or any(
        row['original_call_id'] != call['id'] or row['arguments'] != call['arguments']
        or row['cached'] or row['tool_version'] != '2.1.0'
        for row, call in zip(searches, old_calls, strict=True)
    ):
        raise ValueError('knowledge_time_local_search_identity')
    knowledge = knowledge_evidence_from_search_payloads(row['data'] for row in searches)
    current = knowledge_projection(knowledge)
    times = current.pop('retrievals')
    for citation in current['citations']:
        citation.pop('retrievals')
    if current != knowledge_projection(knowledge_evidence_from_search_payloads(old_payloads)):
        raise ValueError('knowledge_time_citation_contents_changed')
    source = old.messages[2].content.split('[UNTRUSTED deterministic_source_facts]\n', 1)[1].rsplit(
        '\n[END UNTRUSTED deterministic_source_facts]', 1)[0]
    report = original['original_markdown_contents']['reports/output/final_report.md']
    reference = original['host_reference']
    if (digest(report) != reference['original_sha256']
        or digest(reference['report']) != reference['reference_sha256']
        or report.count(reference['edit']['before']) != 1
        or report.replace(reference['edit']['before'], reference['edit']['after']) != reference['report']):
        raise ValueError('knowledge_time_reference_changed')
    request = EvaluationRequest(player_summary=public['reports/inputs/player_summary.json'],
        deterministic_report=source, knowledge=knowledge, report=report,
        user_utterance=old_body['user_utterance'])
    baseline = RoleReviewWorkflow.make_request(build_inputs(replace(request,
        knowledge=knowledge_evidence_from_search_payloads(old_payloads))))
    if baseline.messages != old.messages or baseline.tools != old.tools:
        raise ValueError('knowledge_time_baseline_reconstruction_changed')
    variants, cells = [], []
    for name, text, expected in (
        ('original-date-error', report, 'needs_revision: unsupported knowledge retrieval date'),
        ('date-removed-reference', reference['report'], 'pass: optional wording stays advisory'),
    ):
        inputs = build_inputs(replace(request, report=text))
        prepared = RoleReviewWorkflow.make_request(inputs)
        raw = validate_request(prepared, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        variants.append((name, inputs, prepared))
        cells.append(dict(id=name, report_sha256=digest(text), input_sha256=digest(inputs.data_json),
            request_sha256=hashlib.sha256(raw).hexdigest(), input_reservation=size(prepared),
            output_cap=prepared.max_tokens, expected_host_only=expected))
    total_input = sum(c['input_reservation'] for c in cells)
    total_output = sum(c['output_cap'] for c in cells)
    price = ROLE_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = (Decimal(total_input) * price.input_cost_per_million
        + Decimal(total_output) * price.output_cost_per_million) / 1_000_000
    plan = dict(experiment=EXPERIMENT, candidate=candidate_identity(),
        source_evidence_sha256=retrievals['original_sha256'],
        predecessor_result_sha256=hashlib.sha256(PREDECESSOR.read_bytes()).hexdigest(),
        local_retrievals_sha256=hashlib.sha256(RETRIEVALS.read_bytes()).hexdigest(),
        model='glm-5.3', reasoning_effort='high', sdk_retries=0,
        transport_id=REVIEW_MODEL_TRANSPORT_ID, retrievals=times, cells=cells,
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600, max_seconds_per_call=300,
            total_token_reservation=total_input + total_output, estimated_uncached_cny=str(cost)),
        provider_requests=0, production_admitted=False, labels_sent_to_model=False,
        evidence_scope='Fresh local retrievals, original full report and host reference; not model revision or original-15 qualification.',
        stop_rule='Stop after any rejected protocol, source or full-context host review. No retries.')
    return variants, plan


def run(args):
    if args.execute and LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError('knowledge_time_citation_semantic_failure_requires_method_review')
    variants, plan = prepare()
    plan_sha = digest(compact(plan))
    if not args.execute:
        print(compact(dict(plan, preparation_plan_sha256=plan_sha)), flush=True)
        return plan
    if not args.approval_plan_sha or args.approval_plan_sha != plan_sha:
        raise ValueError('knowledge_time_specific_preparation_approval_required')
    if RUN_DIRECTORY.exists():
        raise ValueError('knowledge_time_batch_exists')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY / 'plan.json', dict(preparation_plan=plan,
        declared_approved_plan_sha256=plan_sha, execution_head_sha=head, ci_run=args.ci_run))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
    from scripts.diagnose_block_review_route import route_environment
    from scripts.run_review_model_comparison import observe
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model='glm-5.3')
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY / 'transport',
        transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        result = observe(provider, RUN_DIRECTORY, variants, plan)
    print(compact(result), flush=True)
    return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--execute', action='store_true')
    result.add_argument('--approval-plan-sha', default='')
    result.add_argument('--ci-run', default='')
    result.add_argument('--env-file', type=Path)
    return result


if __name__ == '__main__':
    args = parser().parse_args()
    result = run(args)
    if args.execute and not result['pair_accepted']:
        raise SystemExit(1)
