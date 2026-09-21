"""One frozen two-call diagnostic: blind edit, then original/new-report review.

No recovery, retries, publication or initial-review qualification. Full outputs
need independent manual review even when the protocol completes.
"""
import argparse
import hashlib
from pathlib import Path
import re
import time

from app.evaluation import golden_native_issues_review as native
from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, ReceiptedStreamProvider, validate_exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from dataclasses import replace
from scripts.blind_edit_settlement import blind_request, settlement_request, validate_settlement, FINAL_POLICY
from scripts.check_native_contract_options import actual_case
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_native_editor_pair import ROOT, read, sha

EXPERIMENT = 'native-blind-edit-settlement-diagnostic-v1'
PLAN = ROOT/'data/evaluation/results/golden_blind_edit_diagnostic_plan_v1.json'
LIVE_STATUS = 'bounded_frozen_diagnostic_after_exact_ci'


def prepare():
    req, saved = actual_case(3)
    raw = saved['responses'][0]['content']
    inputs = native.build_inputs(req)
    first = blind_request(inputs)
    probe = settlement_request(inputs, inputs, raw)
    plan = dict(experiment=EXPERIMENT, report=req.report, original_review_raw=raw,
        source_sha256=digest(inputs.data_json), original_review_sha256=digest(raw),
        blind_request_sha256=hashlib.sha256(validate_request(first, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
        blind_input_ceiling=size(first), settlement_policy_sha256=digest(FINAL_POLICY),
        settlement_schema_sha256=digest(compact(probe.response_contract.schema_dict())),
        model='glm-5.3-flash', reasoning_effort='high', max_calls=2, max_output=32768,
        max_input=63936, request_timeout_s=300, total_tokens=401920, total_timeout_s=900, sdk_retries=0,
        final_request_depends_only_on_actual_draft_and_frozen_inputs=True,
        initial_review_reused_not_reexecuted=True, recovery_allowed=False,
        initial_reviewer_qualified=False, production_admitted=False, semantic_approval=False)
    return req, raw, inputs, first, plan


def frozen():
    prepared = prepare()
    if prepared[-1] != read(PLAN):
        raise ValueError('blind_diagnostic_frozen_plan_changed')
    return prepared


def observe(provider, directory, *, clock=time.time):
    req, original_raw, original, request, _ = frozen()
    output = directory/'outputs'
    output.mkdir(exist_ok=False)
    sender = BudgetedReviewSender(provider, clock=clock)
    attempted, records = 0, []
    result = dict(experiment=EXPERIMENT, protocol_complete=False, semantic_approval=False,
        initial_reviewer_qualified=False, production_admitted=False, recovery_calls=0)
    def preserve(exchange, arm):
        response = exchange.response
        public = dict(content=response.content, content_sha256=digest(response.content or ''),
            provider=response.provider, model=response.model, finish_reason=response.finish_reason,
            request_sha256=exchange.receipt_request_sha256,
            usage=dict(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))
        records.append(public)
        write_new_json(arm/'response.json', public)
        issued = validate_request(exchange.issued_request, transport_id=CAPACITY_TRANSPORT_ID)
        with (arm/'request.wire.json').open('xb') as file: file.write(issued)
        return public

    try:
        for phase in ('edit', 'settlement'):
            arm = output/phase
            arm.mkdir(exist_ok=False)
            attempted += 1
            write_new_json(arm/'attempt.json', dict(ordinal=attempted, state='reserved_before_sender'))
            previous = provider.last_exchange
            try:
                exchange = sender(request)
            except BaseException:
                fresh = provider.last_exchange
                if fresh is not None and fresh is not previous:
                    preserve(fresh, arm)
                raise
            response = exchange.response
            public = preserve(exchange, arm)
            validate_exchange(request, exchange)
            if phase == 'edit':
                draft = response.content
                validate_revised_report(draft, req.report)
                with (arm/'report.md').open('x', encoding='utf-8', newline='') as file: file.write(draft)
                revised = native.build_inputs(replace(req, report=draft))
                # No old expected labels, analyst report, or first output other
                # than its actual draft participates in constructing final input.
                request = settlement_request(revised, original, original_raw)
            else:
                payload, wire, journal = validate_settlement(response.content, revised, original, original_raw)
                write_new_json(arm/'journal.json', journal)
                result.update(protocol_complete=True, final_verdict=payload.verdict,
                    original_decisions=[d.model_dump(mode='json') for d in wire.decisions])
            print(compact(dict(phase=phase, usage=public['usage'])), flush=True)
        result['stop_reason'] = 'complete_pending_independent_manual_review'
    except KeyboardInterrupt:
        result.update(stop_reason='interrupted', error_type='KeyboardInterrupt')
        raise
    except Exception as error:
        result.update(stop_reason='protocol_or_execution_failure', error_type=type(error).__name__)
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,90}', code): result['error_code'] = code
    finally:
        reserved = getattr(provider, '_calls', attempted)
        result.update(attempted_calls=attempted, transport_reserved_calls=reserved, responses_received=len(records),
            unknown_usage_calls=max(0, reserved-len(records)), budget_calls=sender.budget.calls,
            input_tokens=sum(r['usage']['input_tokens'] for r in records),
            output_tokens=sum(r['usage']['output_tokens'] for r in records), budget_tokens=sender.budget.tokens,
            elapsed_seconds=round(clock()-sender.budget.started, 3))
        write_new_json(output/'result.json', result)
    return result


def run(args):
    prepared = frozen()
    plan = prepared[-1]
    if not args.execute:
        print(compact({k:v for k,v in plan.items() if k not in ('report', 'original_review_raw')}))
        return plan
    if LIVE_STATUS != 'bounded_frozen_diagnostic_after_exact_ci':
        raise ValueError('blind_diagnostic_offline')
    head = verify_public_ci(args.ci_run)
    directory = args.output_root/EXPERIMENT
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory/'plan.json', dict(plan, head_sha=head, ci_run=args.ci_run, frozen_plan_sha256=sha(PLAN)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    provider = ReceiptedStreamProvider(settings=settings, directory=directory/'transport', transport_id=CAPACITY_TRANSPORT_ID)
    result = observe(provider, directory)
    print(compact(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--output-root', type=Path, default=ROOT/'data/runs/blind_edit_diagnostic')
    run(parser.parse_args())
