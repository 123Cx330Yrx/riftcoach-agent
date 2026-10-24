"""Frozen two-call coverage diagnostic, never an autonomous-review qualification.

Keep full reports/sources and submit-tool schema. Only narrow the judgment task
to a host-selected paragraph. One original error and its existing corrected
control discriminate focused judgment from whole-report coverage. No retries,
revision, publication, or expected labels are sent to the model.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from pydantic import TypeAdapter

from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.providers.models import ChatResponse
from scripts.check_native_claim_scope import load_controls
from scripts.export_partitioned_review import public_response
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'data/evaluation/results/golden_partitioned_focus_plan_v1.json'
EXPERIMENT = 'partitioned-focus-diagnostic-v1'


def prepare():
    dataset = ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json'
    data = json.loads(dataset.read_text(encoding='utf-8'))
    _, _, source = load_controls()  # Existing committed real input, not ignored run data.
    variants = []
    conditions = []
    for case in data['cases']:
        req = replace(source, report=case['report'], user_utterance=data['user_utterance'])
        if digest(req.report) != case['report_sha256']:
            raise ValueError('focus_report_changed')
        inputs = review.native.build_inputs(req)
        # Freeze the locator, not the target wording or expected verdict.
        block = 14
        if case['target'] not in inputs.source.blocks[block - 1][1]:
            raise ValueError('focus_locator_changed')
        base = review.request(inputs)
        prefix = '你是RiftCoach报告审查员。检查完整报告和全部来源，判断报告是否有需要修复的真实问题。'
        if not base.messages[0].content.startswith(prefix):
            raise ValueError('focus_base_policy_changed')
        policy = (
            f'你是RiftCoach报告审查员。本次是定点诊断：根据完整报告及全部来源，只判断第{block}段是否存在需要修复的真实问题。'
            '其余段落仍是解释范围、否定、条件及引用所需的完整上下文。'
            '只提交指定段的issues或advisories；指定位置不意味着该段有错，也不代表其他段已通过。'
            + base.messages[0].content[len(prefix):])
        request = review.native.budget_check(replace(base,
            messages=(replace(base.messages[0], content=policy), *base.messages[1:])))
        variants.append((case['id'], inputs, request))
        conditions.append(dict(id=case['id'], block=block,
            report_sha256=digest(req.report), input_sha256=digest(inputs.data_json),
            request_sha256=hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
            base_request_sha256=hashlib.sha256(validate_request(base, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
            policy_sha256=digest(policy), input_ceiling=size(request),
            expected_host_only=case['expected_report']))
    plan = dict(experiment=EXPERIMENT, conditions=conditions, model='glm-5.3-flash',
        reasoning_effort='high', max_calls=2, max_output_per_call=32768,
        max_seconds_per_call=300, max_tokens=401920, max_seconds=900, sdk_retries=0,
        no_revision_or_reassessment=True, production_admitted=False,
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        full_reservation=sum(c['input_ceiling'] + 32768 for c in conditions),
        limitations='Host-selected focus; one call per condition; not autonomous coverage, causal proof, or qualification.')
    if plan['full_reservation'] > plan['max_tokens']:
        raise ValueError('focus_pair_budget_exceeded')
    return variants, plan


def observe(provider, directory, variants):
    sender = BudgetedReviewSender(provider)
    records = []
    attempts = 0
    result = dict(experiment=EXPERIMENT, protocol_complete=False, production_admitted=False,
                  manual_semantic_acceptance=False)
    try:
        if len(variants) != 2:
            raise ValueError('focus_pair_count_invalid')
        for case_id, inputs, request in variants:
            attempts += 1
            arm = directory / case_id
            arm.mkdir(exist_ok=False)
            write_new_json(arm / 'attempt.json', dict(ordinal=attempts))
            exchange = sender(request)
            response = public_response(json.loads(TypeAdapter(ChatResponse).dump_json(exchange.response)))
            records.append(dict(id=case_id, response=response))
            write_new_json(arm / 'response.json', response)
            write_new_json(arm / 'request.json', json.loads(validate_request(exchange.issued_request,
                transport_id=CAPACITY_TRANSPORT_ID)))
            raw = review.tool.tool_result(request, exchange)
            payload, wire, journal = review.validate(raw, inputs)
            journal.update(experiment=EXPERIMENT, policy_sha256=digest(request.messages[0].content),
                           full_report_review=False, host_selected_focus_block=14)
            write_new_json(arm / 'journal.json', journal)
            records[-1].update(verdict=wire.verdict, score=wire.score,
                issue_blocks=[i.block for i in wire.issues], advisory_blocks=[a.block for a in wire.advisories])
            if any(b != 14 for b in records[-1]['issue_blocks'] + records[-1]['advisory_blocks']):
                raise ValueError('focus_result_outside_scope')
            print(compact({k:v for k,v in records[-1].items() if k != 'response'}), flush=True)
        result.update(protocol_complete=True, stop_reason='pair_requires_manual_adjudication')
    except Exception as error:
        result.update(stop_reason='protocol_or_execution_failure', error_type=type(error).__name__)
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,90}', code):
            result['error_code'] = code
    finally:
        reserved = getattr(provider, '_calls', attempts)
        result.update(cases=records, attempted_calls=attempts, reserved_calls=reserved,
            completed_calls=len(records), unknown_usage_calls=max(0, reserved-len(records)),
            input_tokens=sum(c['response']['usage']['input_tokens'] for c in records),
            output_tokens=sum(c['response']['usage']['output_tokens'] for c in records))
        write_new_json(directory / 'result.json', result)
    return result


def run(args):
    variants, plan = prepare()
    if plan != json.loads(PLAN.read_text(encoding='utf-8')):
        raise ValueError('focus_plan_changed')
    if not args.execute:
        print(compact(plan))
        return plan
    head = verify_public_ci(args.ci_run)
    directory = args.output_root / EXPERIMENT
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / 'plan.json', dict(plan, head_sha=head, ci_run=args.ci_run))
    # Save both independent requests before any credentials or paid execution.
    for case_id, _, request in variants:
        write_new_json(directory / f'prepared-{case_id}.json', json.loads(validate_request(request,
            transport_id=CAPACITY_TRANSPORT_ID)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    provider = ReceiptedStreamProvider(settings=settings, directory=directory / 'transport',
                                      transport_id=CAPACITY_TRANSPORT_ID)
    result = observe(provider, directory, variants)
    print(compact({k:v for k,v in result.items() if k != 'cases'}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--output-root', type=Path, default=ROOT / 'data/runs/focus_diagnostic')
    run(parser.parse_args())
