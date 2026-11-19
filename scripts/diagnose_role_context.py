"""Bounded 2x2 context diagnostic, never qualification or a product workflow."""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time

from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_tool_delivery import RoleToolDeliveryReviewWorkflow as Workflow
from app.evaluation.golden_semantic_review import diagnostics_for, security_terminal
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, RESPONSE, validate_request, CapacityBridgeObservation
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import ROOT, ASSETS, candidate_identity, frozen_cases
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE as PROFILE
from scripts.diagnose_block_review_route import route_environment
from scripts.export_partitioned_review import public_response
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout

EXPERIMENT = 'role-context-factorial-v1'
EVIDENCE = ROOT / 'data/evaluation/results/golden_role_note_qualification_pair_result_v1.json'
PREPARATION = ROOT / 'data/evaluation/results/golden_role_context_preparation_v1.json'
CLOSED_RESULT = ROOT / 'data/evaluation/results/golden_role_context_result_v1.json'
RUN_DIRECTORY = ROOT / 'data/runs/role_context' / EXPERIMENT
ORDER = ('original', 'expanded', 'no_intro', 'expanded_no_intro',
         'expanded_no_intro', 'no_intro', 'expanded', 'original')


def canonical_sha(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def prepare():
    historical = None
    if CLOSED_RESULT.exists():
        raw_closed = CLOSED_RESULT.read_bytes()
        if hashlib.sha256(raw_closed).hexdigest() != '559aa91e8343542f977a87981e5376bc36204fcb7f882ed0d480b7b3fa162c4d':
            raise ValueError('context_historical_evidence_changed')
        historical = json.loads(raw_closed)['public_json_contents']['plan.json']['preparation_plan']
        if historical != json.loads(PREPARATION.read_text(encoding='utf-8')):
            raise ValueError('context_historical_plan_changed')
    else:
        RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
            prompt_programs_root=ROOT/ASSETS/'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    raw = EVIDENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '700eacc1d70d5c8b651c8f1adcfe23ca2ccc906c3906fd8309805a7fe6b0f673':
        raise ValueError('context_original_evidence_changed')
    saved = json.loads(raw)['public_json_contents']
    cases = dict((f['key'], source) for f, source in frozen_cases()[0])
    source = cases['claim-scope:1']
    blocks = Workflow.build_inputs(source).source.blocks
    actual = saved['attribution-1/revision.json']['report']
    actual_blocks = Workflow.build_inputs(replace(source, report=actual)).source.blocks
    intro, old, new, target = blocks[0][1], blocks[13][1], actual_blocks[12][1], blocks[3][1]
    if source.report.count(old) != 1 or not source.report.startswith(intro + '\n\n'):
        raise ValueError('context_report_layout_changed')
    if target != actual_blocks[2][1]:
        raise ValueError('context_target_not_identical')
    cells, variants, common = [], {}, None
    for name, expanded, remove_intro in [('original', False, False), ('expanded', True, False),
            ('no_intro', False, True), ('expanded_no_intro', True, True)]:
        report = source.report.replace(old, new) if expanded else source.report
        if remove_intro:
            report = report[len(intro + '\n\n'):]
        inputs = Workflow.build_inputs(replace(source, report=report))
        request = Workflow.make_request(inputs)
        # Compare actual wire data too: only report blocks and their three
        # existing derived hashes may vary; no target labels or old opinions.
        wire = json.JSONDecoder().raw_decode(request.messages[1].content.split('[UNTRUSTED DATA]\n', 1)[1])[0]
        reduced = deepcopy(wire)
        reduced['source_index'].pop('blocks')
        reduced['source_index'].pop('source_digest')
        reduced['source_roots'].pop('catalog_sha256')
        reduced['computed_evidence'].pop('source_digest')
        invariant = (request.messages[0], request.messages[2:], request.tools, request.metadata, reduced)
        if common is None:
            common = invariant
        if invariant != common or 'previous_review' in wire:
            raise ValueError('context_non_report_input_changed')
        target_indices = [i for i, (_, text) in enumerate(inputs.source.blocks, 1) if text == target]
        if len(target_indices) != 1:
            raise ValueError('context_target_changed')
        if name == 'expanded_no_intro' and [t for _, t in inputs.source.blocks] != [t for _, t in actual_blocks]:
            raise ValueError('context_success_endpoint_changed')
        request_raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        cells.append(dict(id=name, expanded_paragraph=expanded, removed_intro=remove_intro,
            target_block_host_only=target_indices[0], report_sha256=digest(report),
            request_sha256=hashlib.sha256(request_raw).hexdigest(), input_ceiling=size(request),
            block_count=len(inputs.source.blocks), input_sha256=digest(inputs.data_json)))
        variants[name] = (inputs, request)
    if historical is not None:
        if cells != historical['cells'] or digest(target) != historical['original_target_sha256']:
            raise ValueError('context_historical_request_changed')
        return historical, variants
    total_input = 2 * sum(c['input_ceiling'] for c in cells)
    price = ROLE_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = (Decimal(total_input)*price.input_cost_per_million + Decimal(8*32768)*price.output_cost_per_million)/1_000_000
    plan = dict(experiment=EXPERIMENT, candidate=candidate_identity(), model=PROFILE.model,
        reasoning_effort='high', transport_id=REVIEW_MODEL_TRANSPORT_ID, sdk_retries=0,
        evidence_sha256=hashlib.sha256(raw).hexdigest(), script_sha256=digest(Path(__file__).read_text(encoding='utf-8')),
        cells=cells, order=list(ORDER),
        original_target_sha256=digest(target), original_report_sha256=digest(source.report),
        historical_success_report_sha256=digest(actual),
        intervention_scope='Whole explanation-paragraph replacement versus introductory paragraph removal (includes renumbering); not pure detail or pure position.',
        original_15_unchanged=True, labels_sent_to_model=False,
        budget=dict(max_calls=8, max_seconds=2400, request_seconds=300, output_cap=32768,
            input_ceiling=total_input, total_tokens=total_input+8*32768,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        stop_rule='Stop on transport/channel/identity/budget/security failure. Record schema defects without repair; preplanned semantic failures are observations, not accepted reports.',
        decisions=dict(first_round_same_target_outcome='Stop after four: no distinguishable factor pattern; no stability claim.',
            first_round_different_target_outcome='Run the four fixed conditions once more in reverse order, then stop.',
            within_cell_flip='Do not adopt a text/layout intervention from this batch; qualify reliability before further prompt changes.',
            repeat_consistent_factor_pattern='Context sensitivity signal only; test a source-preserving general input intervention with true-error controls before adoption.',
            all_pass='No factor attribution or stability proof; do not credit one factor or inherit original-15 qualification.',
            all_fail='No supported context intervention; stop this line.',
            incomplete='No full factorial conclusion; retain cost and unusable outputs.'),
        production_admitted=False, semantic_fix_verified=False, qualification_evidence=False)
    return plan, variants


def await_round_review(path, remaining):
    decision_path = path.with_name('round-one-host.json')
    print(compact(dict(round_one_review_required=str(path), decision_path=str(decision_path))), flush=True)
    deadline = time.monotonic()+remaining
    while time.monotonic() < deadline:
        if decision_path.exists():
            return json.loads(decision_path.read_text(encoding='utf-8'))
        time.sleep(0.2)
    raise ValueError('context_host_review_timeout')


def check_round_review(path, decision):
    round_data = json.loads(path.read_text(encoding='utf-8'))
    if decision.get('round_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('context_host_review_binding')
    observations = decision.get('observations')
    if not isinstance(observations, list) or len(observations) != 4:
        raise ValueError('context_host_review_inventory')
    for row, observed in zip(round_data, observations, strict=True):
        if (observed.get('condition') != row['condition'] or observed.get('response_sha256') != row['response_sha256']
                or type(observed.get('target_overgeneralization')) is not bool
                or type(observed.get('review_acceptable')) is not bool
                or not isinstance(observed.get('reason'), str) or not observed['reason'].strip()
                or (observed['review_acceptable'] and not row['protocol_valid'])):
            raise ValueError('context_host_review_binding')
    return len({r['target_overgeneralization'] for r in observations}) > 1


def observe(provider, directory, plan, variants, *, before_send=lambda: None,
            review_round=await_round_review, clock=time.monotonic):
    if (provider.model_name != PROFILE.model or provider.thinking_profile_id != PROFILE.profile_id
            or provider.transport_id != REVIEW_MODEL_TRANSPORT_ID or provider.sdk_max_retries != 0
            or provider._calls != 0 or plan['order'] != list(ORDER) or plan['budget']['max_calls'] != 8):
        raise ValueError('context_identity_invalid')
    if (directory/'result.json').exists():
        raise ValueError('context_batch_exists')
    cells = {c['id']: c for c in plan['cells']}
    for name, (_, request) in variants.items():
        if hashlib.sha256(validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest() != cells[name]['request_sha256']:
            raise ValueError('context_prepared_request_changed')
    started, rows = clock(), []
    result = dict(experiment=EXPERIMENT, completed=False, production_admitted=False,
        semantic_fix_verified=False, qualification_evidence=False, cases=rows)
    try:
        for ordinal, name in enumerate(ORDER, 1):
            inputs, request = variants[name]
            cell = cells[name]
            used = sum(sum(r['usage'][k] for k in ('input_tokens', 'output_tokens')) for r in rows if r.get('usage'))
            if (clock()-started+request.timeout_s > plan['budget']['max_seconds']
                    or used+cell['input_ceiling']+request.max_tokens > plan['budget']['total_tokens']):
                raise ValueError('context_batch_budget')
            before_send()
            arm = directory / f'{ordinal:02d}-{name}'
            arm.mkdir(exist_ok=False)
            row = dict(ordinal=ordinal, condition=name, request_sha256=cell['request_sha256'],
                reserved_calls=0, usage=None, protocol_valid=False)
            rows.append(row)
            raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
            (arm/'request.raw.json').write_bytes(raw)
            before = provider._calls
            try:
                if clock()-started+request.timeout_s > plan['budget']['max_seconds']:
                    raise ValueError('context_batch_budget')
                response = provider.chat(request)
                row['usage'] = public_response(json.loads(RESPONSE.dump_json(response)))['usage']
                write_new_json(arm/'response.json', public_response(json.loads(RESPONSE.dump_json(response))))
                row['response_sha256'] = hashlib.sha256((arm/'response.json').read_bytes()).hexdigest()
                exchange = provider.last_exchange
                if (response.provider != 'zhipu' or response.model != PROFILE.model
                        or response.usage.input_tokens > cell['input_ceiling'] or response.usage.output_tokens > request.max_tokens
                        or exchange is None or exchange.response is not response or exchange.issued_request != request
                        or exchange.receipt_request_sha256 != cell['request_sha256']):
                    raise ValueError('context_response_identity_or_budget')
                value = json.loads(tool_result(request, exchange))
                if security_terminal(value):
                    raise ValueError('context_security_terminal')
                row.update(raw_verdict=value.get('verdict'), raw_score=value.get('score'))
                try:
                    _, _, journal = Workflow.validate_review(compact(value), inputs)
                except ValueError as error:
                    if str(error) == 'native_security_terminal':
                        raise
                    # Record invalid output, never complete its fields or turn
                    # it into an accepted EvaluationResult. No recovery call.
                    journal = dict(protocol_valid=False, diagnostics=diagnostics_for(error))
                else:
                    row['protocol_valid'] = True
                write_new_json(arm/'journal.json', journal)
            finally:
                row['reserved_calls'] = provider._calls-before
                if row['reserved_calls'] and row['usage'] is None:
                    path = directory/'transport'/f'stream-{provider._calls:03d}'/'progress.json'
                    if path.exists():
                        p = CapacityBridgeObservation.model_validate_json(path.read_bytes())
                        if p.input_tokens is not None and p.output_tokens is not None:
                            row['usage'] = dict(input_tokens=p.input_tokens, output_tokens=p.output_tokens)
                row['unknown_usage_calls'] = row['reserved_calls']-int(row['usage'] is not None)
                write_new_json(arm/'accounting.json', row)
                print(compact(dict(observed=ordinal, condition=name, protocol_valid=row['protocol_valid'],
                    raw_verdict=row.get('raw_verdict'), artifact=str(arm))), flush=True)
            if clock()-started > plan['budget']['max_seconds']:
                raise ValueError('context_batch_budget')
            if ordinal == 4:
                path = directory/'round-one.json'
                write_new_json(path, rows)
                decision = review_round(path, plan['budget']['max_seconds']-(clock()-started))
                if not check_round_review(path, decision):
                    result.update(completed=True, stop_reason='first_round_no_target_contrast', repeated=False)
                    break
        result['completed'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or str(error)
        result['error_code'] = code if re.fullmatch('[a-z_]{1,100}', code) else 'context_unclassified_failure'
    finally:
        result.update(provider_requests=provider._calls,
            unknown_usage_calls=sum(r.get('unknown_usage_calls', r['reserved_calls']) for r in rows),
            input_tokens=sum((r['usage'] or {}).get('input_tokens', 0) for r in rows),
            output_tokens=sum((r['usage'] or {}).get('output_tokens', 0) for r in rows),
            elapsed_seconds=round(clock()-started, 3))
        write_new_json(directory/'result.json', result)
    return result


def run(args):
    if args.execute and CLOSED_RESULT.exists():
        raise ValueError('context_batch_closed')
    plan, variants = prepare()
    plan_sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            with args.output.open('x', encoding='utf-8', newline='\n') as target:
                json.dump(plan, target, ensure_ascii=False, indent=2)
                target.write('\n')
        return dict(plan_sha256=plan_sha, budget=plan['budget'], provider_requests=0,
            historical_closed=CLOSED_RESULT.exists(), execution_enabled=False)
    if (plan != json.loads(PREPARATION.read_text(encoding='utf-8'))
            or args.plan_sha != plan_sha or args.env_file is None or not args.ci_run):
        raise ValueError('context_preparation_required')
    if RUN_DIRECTORY.exists():
        raise ValueError('context_batch_exists')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json', dict(preparation_plan=plan, plan_sha256=plan_sha, head_sha=head, ci_run=args.ci_run))
    settings = load_role_settings(args.env_file)[1]
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY/'transport', transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        return observe(provider, RUN_DIRECTORY, plan, variants, before_send=lambda: require_unchanged_checkout(head))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    print(compact(run(parser.parse_args())), flush=True)
