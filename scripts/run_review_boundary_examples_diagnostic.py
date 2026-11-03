"""Fixed out-of-domain boundary examples on the existing two-control runner.

No product registration, source rewriting, retries or historical qualification.
Preview is offline; execute requires frozen preparation and exact-commit CI.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator

from app.evaluation.correction_scope_qualification import candidate_identity, frozen_cases, size
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as Workflow
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE as PROFILE
from app.runtime.coach_contract import CORRECTION_SCOPE_COACH_CONTRACT as CONTRACT
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.export_partitioned_review import public_response, read, sha, transport_for
from scripts.prepare_review_model_comparison import mock_wire
from scripts.run_coarse_source_review_pair import adjudicate_file
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_review_model_comparison import observe
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_task_observation import await_case_ready
from scripts.review_boundary_examples import EXAMPLES, request_for

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = 'review-boundary-examples-pair-v1'
KEYS = ('claim-scope:1', 'scope:3')
PREPARATION = ROOT/'data/evaluation/results/golden_review_boundary_examples_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_review_boundary_examples_result_v1.json'
CLOSED_SHA = '1a4df090a2d5d1f575b307f90b54e6c25bfc823d9c34db920fca4f8a96635ddc'
RUN_DIRECTORY = ROOT/'data/runs/model_comparison'/EXPERIMENT


def sdk_wire(request):
    captured = []
    def create(**kwargs):
        captured.append(deepcopy(kwargs))
        return iter(())
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider = ZhipuProvider.from_candidate_profile(client=client, model=PROFILE.model, profile=PROFILE)
    provider._open_stream_for_adapter(request, tool_stream=True, include_usage_tail=True)
    arguments, = captured
    return mock_wire(arguments)


def prepare():
    variants, cells, all_inputs = [], [], []
    for row, source in frozen_cases()[0]:
        inputs = Workflow.build_inputs(source)
        baseline, request = Workflow.make_request(inputs), request_for(inputs)
        if (replace(request, messages=baseline.messages) != baseline
                or request.messages[1:] != baseline.messages[1:]
                or request.messages[0].content != baseline.messages[0].content + '\n' + EXAMPLES):
            raise ValueError('boundary_examples_intervention_not_isolated')
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        if size(request) > 64000:
            raise ValueError('boundary_examples_input_capacity')
        all_inputs.append(dict(key=row['key'], input_sha256=digest(inputs.data_json),
            baseline_input_ceiling=size(baseline), diagnostic_input_ceiling=size(request),
            baseline_request_sha256=hashlib.sha256(validate_request(baseline,
                transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest(),
            diagnostic_request_sha256=hashlib.sha256(raw).hexdigest()))
        if row['key'] not in KEYS:
            continue
        before, after = sdk_wire(baseline), sdk_wire(request)
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        if (changed != ['messages'] or after['reasoning_effort'] != 'high'
                or after['temperature'] != 1 or after['top_p'] != .95
                or after['model'] != 'glm-5.3' or after['max_tokens'] != 32768):
            raise ValueError('boundary_examples_sdk_intervention_changed')
        name = row['key'].replace(':', '-')
        variants.append((name, inputs, request))
        cells.append(dict(id=name, key=row['key'], input_sha256=digest(inputs.data_json),
            report_sha256=digest(source.report), expected_initial=row['expected_initial'],
            request_sha256=hashlib.sha256(raw).hexdigest(), input_reservation=size(request),
            output_cap=request.max_tokens, changed_sdk_fields=changed,
            baseline_sdk_sha256=digest(compact(before)), diagnostic_sdk_sha256=digest(compact(after))))
    cells.sort(key=lambda c: KEYS.index(c['key']))
    variants.sort(key=lambda v: [k.replace(':', '-') for k in KEYS].index(v[0]))
    if len(cells) != 2 or len(all_inputs) != 15:
        raise ValueError('boundary_examples_control_inventory')
    prices = CONTRACT.pricing_profiles[('zhipu', 'glm-5.3')]
    cost = sum((Decimal(c['input_reservation'])*prices.input_cost_per_million
        + Decimal(c['output_cap'])*prices.output_cost_per_million)/1_000_000 for c in cells)
    paths = (__file__, 'scripts/review_boundary_examples.py', 'scripts/run_review_model_comparison.py', 'scripts/run_coarse_source_review_pair.py',
        'scripts/run_role_task_observation.py', 'app/evaluation/golden_role_correction_scope.py',
        'app/evaluation/golden_stream_bridge.py', 'app/providers/zhipu.py',
        'app/providers/zhipu_stream_adapter.py', 'scripts/prepare_review_model_comparison.py')
    paths = [Path(p).resolve().relative_to(ROOT).as_posix() if Path(p).is_absolute() else p for p in paths]
    plan = dict(experiment=EXPERIMENT, baseline_candidate=candidate_identity(), cells=cells,
        all15_input_audit=all_inputs, source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        proposed_diagnostic_budget=dict(max_calls=2, max_seconds_total=600, max_seconds_per_call=300,
            total_token_reservation=sum(c['input_reservation']+c['output_cap'] for c in cells),
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        model=PROFILE.model, reasoning_effort='high', temperature=1, top_p=.95,
        sdk_retries=0, labels_sent_to_model=False,
        intervention='Append one fixed out-of-domain demonstration block to the existing review policy; preserve full sources, reports, schema, model and sampling. Initial/fresh/reassessment share this block; editor unchanged.',
        examples=EXAMPLES, examples_sha256=digest(EXAMPLES), development_controls_not_holdout=True, execution_authorized=False,
        stop_rule='First semantic, source, correction, protocol, identity or budget failure stops; no retry, example rewrite or alternate industry search.',
        success_scope='Two feasibility controls only; no causal improvement, stability, edit/fresh, original15 or product qualification.',
        product_budget_unchanged=dict(calls=5, tokens=401920, seconds=900),
        offline_application_check=dict(test='tests/test_review_boundary_examples.py',
            normal_five_call_reservation=359066, recovery_five_call_reservation=360434,
            recovery_exhausts_calls_before_fresh=True,
            scope='Scripted real application; request reservations are fixture-specific, not a live latency or semantic guarantee.'),
        review_controls_qualified=False, actual_product_task_qualified=False, production_admitted=False)
    if CLOSED_RESULT.exists():
        if sha(CLOSED_RESULT) != CLOSED_SHA:
            raise ValueError('boundary_examples_closed_evidence_changed')
        saved = read(CLOSED_RESULT)['public_json_contents']['plan.json']
        frozen = saved['preparation_plan']
        # A closed diagnostic keeps its historical code/manifest identity.
        # Rebuild all actual inputs, policies, requests and budgets unchanged;
        # current product wiring must never retroactively rebind its evidence.
        plan.update(baseline_candidate=frozen['baseline_candidate'],
                    source_sha256=frozen['source_sha256'])
        if plan != frozen or plan != read(PREPARATION) or canonical_sha(plan) != saved['plan_sha256']:
            raise ValueError('boundary_examples_closed_preparation_changed')
    return plan, variants


def inspect_response(prepared, exchange, inputs):
    if prepared != request_for(inputs):
        raise ValueError('boundary_examples_request_binding')
    raw = tool_result(prepared, exchange)
    Draft202012Validator(prepared.tools[0].input_schema).validate(json.loads(raw))
    _, wire, journal = Workflow.validate_review(raw, inputs)
    if wire.verdict == 'pass' and wire.score < CONTRACT.descriptor()['minimum_score']:
        raise ValueError('boundary_examples_pass_below_threshold')
    return dict(score=wire.score, verdict=wire.verdict, issue_blocks=[i.block for i in wire.issues],
        advisory_blocks=[i.block for i in wire.advisories]), journal


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('boundary_examples_batch_closed_or_exists')
    plan, variants = prepare()
    plan_sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output, plan)
        return dict(plan_sha256=plan_sha, budget=plan['proposed_diagnostic_budget'], provider_requests=0)
    if (not args.env_file or not args.ci_run or args.plan_sha != plan_sha or plan != read(PREPARATION)):
        raise ValueError('boundary_examples_frozen_preparation_required')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json', dict(preparation_plan=plan, plan_sha256=plan_sha,
        head_sha=head, ci_run=args.ci_run))
    for name, inputs, request in variants:
        write_new_json(RUN_DIRECTORY/(name+'-source.json'), dict(input_json=inputs.data_json, report=inputs.source.report))
        (RUN_DIRECTORY/(name+'-prepared-request.json')).write_bytes(validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID))
    provider = ReceiptedStreamProvider(settings=load_role_settings(args.env_file)[1],
        directory=RUN_DIRECTORY/'transport', transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        return observe(provider, RUN_DIRECTORY, variants, plan, inspect_response=inspect_response,
            adjudicate=lambda p, t: adjudicate_file(p, t, plan), before_case=await_case_ready,
            before_send=lambda: require_unchanged_checkout(head))


def seal():
    """Bind public evidence to frozen inputs, original calls and both judgments."""
    plan, variants = prepare()
    saved, result = read(RUN_DIRECTORY/'plan.json'), read(RUN_DIRECTORY/'result.json')
    if saved['preparation_plan'] != plan or plan != read(PREPARATION) or saved['plan_sha256'] != canonical_sha(plan):
        raise ValueError('boundary_examples_seal_plan')
    if result['reserved_calls'] > 2 or result['production_admitted'] or len(result['cases']) > 2:
        raise ValueError('boundary_examples_seal_budget')
    stream_root = RUN_DIRECTORY/'transport'
    stream_names = {p.name for p in stream_root.iterdir()} if stream_root.exists() else set()
    if stream_names != {f'stream-{i:03d}' for i in range(1, result['reserved_calls']+1)}:
        raise ValueError('boundary_examples_seal_transport_inventory')
    for name, inputs, request in variants:
        if ((RUN_DIRECTORY/(name+'-prepared-request.json')).read_bytes() != validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
                or read(RUN_DIRECTORY/(name+'-source.json')) != dict(input_json=inputs.data_json, report=inputs.source.report)):
            raise ValueError('boundary_examples_seal_input')
    for ordinal, (record, (name, inputs, prepared), cell) in enumerate(zip(result['cases'], variants, plan['cells']), 1):
        arm = RUN_DIRECTORY/name
        if record['id'] != name or record != read(arm/'accounting.json'):
            raise ValueError('boundary_examples_seal_order_or_accounting')
        if (arm/'request.raw.json').exists():
            actual = (arm/'request.raw.json').read_bytes()
            timeout = json.loads(actual)['timeout_s']
            if not 0 < timeout <= prepared.timeout_s or actual != validate_request(replace(prepared, timeout_s=timeout), transport_id=REVIEW_MODEL_TRANSPORT_ID):
                raise ValueError('boundary_examples_seal_request')
        if record['completed']:
            response = read(arm/'response.json')
            transport = transport_for(RUN_DIRECTORY/'transport'/f'stream-{ordinal:03d}', ordinal)
            if (sha(arm/'request.raw.json') != record['request_sha256']
                    or transport['reservation']['request_sha256'] != record['request_sha256']
                    or transport['reservation']['transport_id'] != REVIEW_MODEL_TRANSPORT_ID
                    or transport['result']['state'] != 'complete'
                    or (response['provider'], response['model']) != ('zhipu', PROFILE.model)
                    or response['usage'] != record['observed_usage']
                    or any(transport['progress'][k] != response['usage'][k] for k in ('input_tokens', 'output_tokens'))):
                raise ValueError('boundary_examples_seal_receipt')
            if record['valid'] and not (arm/'journal.json').is_file():
                raise ValueError('boundary_examples_seal_missing_journal')
            if (arm/'journal.json').exists():
                journal = read(arm/'journal.json')
                if json.loads(journal['raw']) != response['tool_calls'][0]['arguments']:
                    raise ValueError('boundary_examples_seal_journal')
                Draft202012Validator(prepared.tools[0].input_schema).validate(json.loads(journal['raw']))
                _, wire, rebuilt = Workflow.validate_review(journal['raw'], inputs)
                outcome = dict(score=wire.score, verdict=wire.verdict,
                    issue_blocks=[i.block for i in wire.issues], advisory_blocks=[i.block for i in wire.advisories])
                if (any(record.get(k) != v for k, v in outcome.items())
                        or wire.verdict == 'pass' and wire.score < CONTRACT.descriptor()['minimum_score']
                        or record.get('host_accepted') and wire.verdict != ('pass' if cell['expected_initial'] == 'accept' else 'needs_revision')):
                    raise ValueError('boundary_examples_seal_verdict')
                rebuilt.update(diagnostic_experiment=EXPERIMENT, validator_policy_sha256=rebuilt['policy_sha256'],
                    policy_sha256=digest(prepared.messages[0].content), request_sha256=record['request_sha256'],
                    source_projection=prepared.metadata.get('source_projection'))
                if journal != rebuilt:
                    raise ValueError('boundary_examples_seal_journal')
            if 'host_accepted' in record:
                decision, other = read(arm/'host-decision.json'), read(arm/'independent-review.json')
                expected = dict(response_sha256=sha(arm/'response.json'), input_sha256=cell['input_sha256'],
                    report_sha256=cell['report_sha256'], accepted=record['host_accepted'])
                if (decision != read(arm/'host-adjudication.json') or decision['independent_sha256'] != sha(arm/'independent-review.json')
                        or any(row.get(k) != v for row in (decision, other) for k, v in expected.items())
                        or any(not isinstance(row.get('source_review'), str) or not row['source_review'].strip() for row in (decision, other))
                        or record['host_accepted'] and any(row.get('defects') != [] for row in (decision, other))):
                    raise ValueError('boundary_examples_seal_host')
    for field, total in dict(reserved_calls=sum(r['reserved_calls'] for r in result['cases']),
            unknown_usage_calls=sum(r['unknown_usage_calls'] for r in result['cases']),
            input_tokens=sum((r['observed_usage'] or {}).get('input_tokens', 0) for r in result['cases']),
            output_tokens=sum((r['observed_usage'] or {}).get('output_tokens', 0) for r in result['cases'])).items():
        if result[field] != total:
            raise ValueError('boundary_examples_seal_totals')
    if result['pair_accepted'] and (len(result['cases']) != 2 or not all(r['completed'] and r['valid'] and r.get('host_accepted') for r in result['cases'])):
        raise ValueError('boundary_examples_seal_incomplete')
    if (result['completed_calls'] != sum(r['completed'] for r in result['cases'])
            or result['pair_accepted'] and (result['elapsed_seconds'] > plan['proposed_diagnostic_budget']['max_seconds_total']
                or result['unknown_usage_calls'] != 0)):
        raise ValueError('boundary_examples_seal_completion')
    files = sorted(p for p in RUN_DIRECTORY.rglob('*') if p.is_file())
    public = {}
    for path in files:
        relative = path.relative_to(RUN_DIRECTORY).as_posix()
        if path.suffix != '.json' or relative.startswith('transport/') and path.name not in ('reservation.json', 'result.json', 'progress.json'):
            continue
        value = read(path)
        public[relative] = public_response(value) if path.name == 'response.json' else value
    write_new_json(CLOSED_RESULT, dict(kind='review_boundary_examples_public_result_v1',
        original_file_sha256={p.relative_to(RUN_DIRECTORY).as_posix(): sha(p) for p in files},
        public_json_contents=public, execution_result=result, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False))
    return dict(export_sha256=sha(CLOSED_RESULT), provider_requests=result['reserved_calls'], pair_accepted=result['pair_accepted'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--seal', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    result = seal() if args.seal else run(args)
    print(compact(result), flush=True)
    if args.execute and not result['pair_accepted']:
        raise SystemExit(1)
