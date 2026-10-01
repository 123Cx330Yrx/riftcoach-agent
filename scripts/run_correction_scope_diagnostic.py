"""Bounded output-responsibility controls on the existing two-call executor.

No product switch, revision, retry, or migration of historical qualifications.
The prior rejected response remains immutable evidence, not a model input.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.evaluation.coarse_role_qualification import frozen_cases, size
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.runtime.coach_contract import COARSE_ROLE_COACH_CONTRACT as CONTRACT
from scripts.audit_coarse_correction_failure import EXPORT as BASELINE, EXPORT_SHA
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.export_partitioned_review import public_response, transport_for
from scripts.prepare_correction_scope_diagnostic import ROOT, prepare as prepare_inputs, variant
from scripts.run_coarse_source_review_pair import adjudicate_file
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_review_model_comparison import observe
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_task_observation import await_case_ready

EXPERIMENT = 'correction-scope-responsibility-pair-v1'
INPUT_PREPARATION = ROOT/'data/evaluation/results/golden_correction_scope_preparation_v1.json'
PREPARATION = ROOT/'data/evaluation/results/golden_correction_scope_execution_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_correction_scope_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/model_comparison'/EXPERIMENT
KEYS = ('attribution:1', 'claim-scope:1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def prepare():
    if sha(BASELINE) != EXPORT_SHA:
        raise ValueError('correction_scope_baseline_changed')
    inputs_plan, frozen_requests = prepare_inputs()
    if inputs_plan != read(INPUT_PREPARATION):
        raise ValueError('correction_scope_inputs_changed')
    sources = {row['key']: (row, source) for row, source in frozen_cases()[0]}
    variants, cells = [], []
    for key in KEYS:
        row, source = sources[key]
        inputs = Workflow.build_inputs(source)
        _, request = variant(inputs)
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        if raw != frozen_requests[key] or size(request) + request.max_tokens > 96768 or request.timeout_s > 300:
            raise ValueError('correction_scope_request_or_capacity')
        name = key.replace(':', '-')
        variants.append((name, inputs, request))
        cells.append(dict(id=name, key=key, input_sha256=digest(inputs.data_json),
            report_sha256=digest(source.report), expected_initial=row['expected_initial'],
            request_sha256=hashlib.sha256(raw).hexdigest(),
            input_reservation=size(request), output_cap=request.max_tokens))
    prices = CONTRACT.pricing_profiles[('zhipu', 'glm-5.3')]
    estimate = sum((Decimal(c['input_reservation'])*prices.input_cost_per_million
        + Decimal(c['output_cap'])*prices.output_cost_per_million)/1_000_000 for c in cells)
    paths = ('scripts/prepare_correction_scope_diagnostic.py',
        'scripts/run_correction_scope_diagnostic.py', 'scripts/run_review_model_comparison.py',
        'scripts/run_coarse_source_review_pair.py', 'scripts/run_role_task_observation.py',
        'app/evaluation/golden_role_coarse.py', 'app/evaluation/golden_coarse_source_projection.py')
    plan = dict(experiment=EXPERIMENT, prior_failure_export_sha256=EXPORT_SHA,
        input_preparation_sha256=sha(INPUT_PREPARATION), cells=cells,
        source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600,
            max_seconds_per_call=300, total_token_reservation=193536,
            estimated_uncached_cny=str(estimate), hard_billing_cap=False),
        model='glm-5.3', reasoning_effort='high', sdk_retries=0, labels_sent_to_model=False,
        intervention=inputs_plan['change'],
        stop_rule='Stop on any substantive defect in the review output, wrong verdict, protocol, source, identity or budget failure. Legitimate needs_revision is expected for the error control. No retry or synonym variants.',
        success_scope='Two full-context review controls only; no revision, original15 or product qualification.',
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False)
    return plan, variants


def inspect_response(prepared, exchange, inputs):
    if prepared != variant(inputs)[1]:
        raise ValueError('correction_scope_request_binding_mismatch')
    raw = tool_result(prepared, exchange)
    Draft202012Validator(prepared.tools[0].input_schema).validate(json.loads(raw))
    _, wire, journal = Workflow.validate_review(raw, inputs)
    if wire.verdict == 'pass' and wire.score < CONTRACT.descriptor()['minimum_score']:
        raise ValueError('correction_scope_pass_below_threshold')
    return dict(score=wire.score, verdict=wire.verdict,
        issue_blocks=[i.block for i in wire.issues],
        advisory_blocks=[i.block for i in wire.advisories]), journal


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('correction_scope_closed_or_exists')
    plan, variants = prepare()
    plan_sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output, plan)
        return dict(plan_sha256=plan_sha, budget=plan['proposed_diagnostic_budget'],
            provider_requests=0, execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha != plan_sha
            or plan != read(PREPARATION)):
        raise ValueError('correction_scope_preparation_required')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json', dict(preparation_plan=plan,
        plan_sha256=plan_sha, head_sha=head, ci_run=args.ci_run))
    for name, inputs, request in variants:
        write_new_json(RUN_DIRECTORY/(name+'-source.json'),
            dict(input_json=inputs.data_json, report=inputs.source.report))
        (RUN_DIRECTORY/(name+'-prepared-request.json')).write_bytes(
            validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID))
    settings = load_role_settings(args.env_file)[1]
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY/'transport',
        transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        return observe(provider, RUN_DIRECTORY, variants, plan, inspect_response=inspect_response,
            adjudicate=lambda p, t: adjudicate_file(p, t, plan), before_case=await_case_ready,
            before_send=lambda: require_unchanged_checkout(head))


def seal():
    """Hash all original files; publish only public requests, judgments and usage.

    Transport stdout/stderr may include private reasoning and are hash-only.
    The result retains failures and unknown usage rather than reconstructing a
    completion after an interruption.
    """
    saved = read(RUN_DIRECTORY/'plan.json')
    plan, variants = prepare()
    if (saved['preparation_plan'] != plan or plan != read(PREPARATION)
            or saved['plan_sha256'] != canonical_sha(plan)):
        raise ValueError('correction_scope_seal_plan_changed')
    result = read(RUN_DIRECTORY/'result.json')
    if not 0 <= result['reserved_calls'] <= 2 or result['production_admitted']:
        raise ValueError('correction_scope_seal_accounting')
    for (name, inputs, request), cell in zip(variants, plan['cells'], strict=True):
        if sha(RUN_DIRECTORY/(name+'-prepared-request.json')) != cell['request_sha256']:
            raise ValueError('correction_scope_seal_request_changed')
        if read(RUN_DIRECTORY/(name+'-source.json')) != dict(input_json=inputs.data_json, report=inputs.source.report):
            raise ValueError('correction_scope_seal_source_changed')
    for ordinal, record in enumerate(result['cases'], 1):
        arm = RUN_DIRECTORY/record['id']
        name, inputs, prepared = variants[ordinal-1]
        cell = plan['cells'][ordinal-1]
        if record['id'] != name:
            raise ValueError('correction_scope_seal_case_order')
        if record != read(arm/'accounting.json'):
            raise ValueError('correction_scope_seal_accounting_changed')
        if (arm/'request.raw.json').exists():
            actual = (arm/'request.raw.json').read_bytes()
            issued = json.loads(actual)
            if (not 0 < issued['timeout_s'] <= prepared.timeout_s
                    or actual != validate_request(replace(prepared, timeout_s=issued['timeout_s']),
                                                  transport_id=REVIEW_MODEL_TRANSPORT_ID)):
                raise ValueError('correction_scope_seal_issued_request_changed')
        if record['completed']:
            response = read(arm/'response.json')
            transport = transport_for(RUN_DIRECTORY/'transport'/f'stream-{ordinal:03d}', ordinal)
            if (sha(arm/'request.raw.json') != record['request_sha256']
                    or transport['reservation']['request_sha256'] != record['request_sha256']
                    or response['usage'] != record['observed_usage']
                    or any(transport['progress'][k] != response['usage'][k] for k in ('input_tokens', 'output_tokens'))):
                raise ValueError('correction_scope_seal_receipt_changed')
            if (arm/'journal.json').exists():
                journal = read(arm/'journal.json')
                raw = journal['raw']
                if json.loads(raw) != response['tool_calls'][0]['arguments']:
                    raise ValueError('correction_scope_seal_public_arguments_changed')
                _, wire, rebuilt = Workflow.validate_review(raw, inputs)
                rebuilt.update(diagnostic_experiment=plan['experiment'],
                    validator_policy_sha256=rebuilt['policy_sha256'],
                    policy_sha256=digest(prepared.messages[0].content),
                    request_sha256=record['request_sha256'],
                    source_projection=prepared.metadata.get('source_projection'))
                if journal != rebuilt:
                    raise ValueError('correction_scope_seal_journal_changed')
            if 'host_accepted' in record:
                decision = read(arm/'host-adjudication.json')
                other = read(arm/'independent-review.json')
                expected = dict(response_sha256=sha(arm/'response.json'),
                    input_sha256=cell['input_sha256'], report_sha256=cell['report_sha256'],
                    accepted=record['host_accepted'])
                if (decision != read(arm/'host-decision.json')
                        or decision['independent_sha256'] != sha(arm/'independent-review.json')
                        or any(any(row.get(k) != v for k, v in expected.items()) for row in (decision, other))
                        or any(not isinstance(row.get('source_review'), str) or not row['source_review'].strip()
                               for row in (decision, other))
                        or record['host_accepted'] and any(row.get('defects') != [] for row in (decision, other))):
                    raise ValueError('correction_scope_seal_host_changed')
    if (result['reserved_calls'] != sum(r['reserved_calls'] for r in result['cases'])
            or any(result[k] != sum((r['observed_usage'] or {}).get(k, 0) for r in result['cases'])
                   for k in ('input_tokens', 'output_tokens'))
            or result['unknown_usage_calls'] != sum(r['unknown_usage_calls'] for r in result['cases'])):
        raise ValueError('correction_scope_seal_totals_changed')
    if result['pair_accepted'] and (len(result['cases']) != 2 or not all(
            r.get('valid') and r.get('host_accepted') and r['completed'] for r in result['cases'])):
        raise ValueError('correction_scope_seal_incomplete_pair')
    files = sorted(p for p in RUN_DIRECTORY.rglob('*') if p.is_file())
    public = {}
    for path in files:
        relative = path.relative_to(RUN_DIRECTORY).as_posix()
        if path.suffix != '.json':
            continue
        if relative.startswith('transport/') and path.name not in ('reservation.json', 'result.json', 'progress.json'):
            continue
        value = read(path)
        public[relative] = public_response(value) if path.name == 'response.json' else value
    price = CONTRACT.pricing_profiles[('zhipu', 'glm-5.3')]
    cost = (Decimal(result['input_tokens'])*price.input_cost_per_million
        + Decimal(result['output_tokens'])*price.output_cost_per_million)/1_000_000
    output = dict(kind='correction_scope_public_result_v1',
        original_file_sha256={p.relative_to(RUN_DIRECTORY).as_posix(): sha(p) for p in files},
        public_json_contents=public, execution_result=result,
        estimated_uncached_known_cny=str(cost), unknown_usage_calls=result['unknown_usage_calls'],
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False)
    write_new_json(CLOSED_RESULT, output)
    return dict(export_sha256=sha(CLOSED_RESULT), files=len(files),
        provider_requests=result['reserved_calls'], pair_accepted=result['pair_accepted'],
        estimated_uncached_known_cny=str(cost))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--seal', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    result = seal() if args.seal else run(args)
    print(compact(result), flush=True)
    if args.execute and not result['pair_accepted']:
        raise SystemExit(1)
