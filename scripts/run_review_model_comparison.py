"""ADR0108: approved two-call diagnostic, with host review between calls.

The host must type 'accept <response-file-sha256>' only after inspecting ALL
findings; 'reject <sha256>' stops the batch. These decisions never enter the
model input. A new directory is reserved once; no restart, retry or extra call.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from queue import Empty, Queue
import re
import sys
from threading import Thread
import time

from pydantic import TypeAdapter

from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, CapacityBridgeObservation, validate_request, transport_profile
from app.providers.models import ChatResponse
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_review_target_layout import prepare
from scripts.export_partitioned_review import public_response, transport_for
from scripts.prepare_review_model_comparison import build_plan, OUTPUT, ROOT
from scripts.run_golden_inference_development import verify_public_ci

EXPERIMENT = 'review-model-capability-pair-v1'
LIVE_STATUS = 'stopped_source_binding_failure'
RUN_DIRECTORY = ROOT / 'data/runs/model_comparison' / EXPERIMENT


def terminal_adjudication(response_path, remaining):
    response_sha = hashlib.sha256(response_path.read_bytes()).hexdigest()
    print(compact({'host_review_required': response_path.as_posix(), 'response_sha256': response_sha,
                   'remaining_seconds': round(remaining, 3)}), flush=True)
    queue = Queue()
    Thread(target=lambda: queue.put(sys.stdin.readline()), daemon=True).start()
    try:
        decision = queue.get(timeout=max(0, remaining)).strip()
    except Empty:
        raise ValueError('model_comparison_host_deadline') from None
    if decision not in (f'accept {response_sha}', f'reject {response_sha}'):
        raise ValueError('model_comparison_host_decision_invalid')
    return dict(response_sha256=response_sha, accepted=decision.startswith('accept '),
                scope='all issues and advisories in full context; host judgment, not model output')


def observe(provider, directory, variants, plan, *, adjudicate=terminal_adjudication, clock=time.monotonic,
            reviewer_profile=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE,
            transport_id=REVIEW_MODEL_TRANSPORT_ID, inspect_response=None,
            before_case=None, before_send=lambda: None):
    """Two controls with host resume in the same live, deadline-bounded session.

    The default stays the historical GLM diagnostic. An explicit profile must
    match the canonical transport, so selecting Flash cannot silently use GLM
    settings (or vice versa). Restarting never overwrites a previous batch.
    """
    if (reviewer_profile != transport_profile(transport_id)
            or len(variants) != 2 or provider.model_name != reviewer_profile.model
            or provider.thinking_profile_id != reviewer_profile.profile_id
            or provider.transport_id != transport_id or provider.sdk_max_retries != 0
            or provider._calls != 0):
        raise ValueError('model_comparison_identity')
    names = [variant[0] for variant in variants]
    if (len(set(names)) != 2 or len(plan['cells']) != 2
            or any(not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,95}', name) for name in names)
            or names != [cell['id'] for cell in plan['cells']]):
        raise ValueError('model_comparison_input_identity')
    if (directory / 'result.json').exists() or any((directory / name).exists() for name in names):
        raise ValueError('model_comparison_batch_exists')
    for (_, _, request), cell in zip(variants, plan['cells'], strict=True):
        raw = validate_request(request, transport_id=transport_id)
        if 'request_sha256' in cell and hashlib.sha256(raw).hexdigest() != cell['request_sha256']:
            raise ValueError('model_comparison_input_identity')
    limits = plan['proposed_diagnostic_budget']
    started = clock()
    records = []
    result = dict(experiment=plan['experiment'], production_admitted=False, pair_accepted=False)
    try:
        for index, (name, inputs, prepared) in enumerate(variants):
            if before_case is not None:
                remaining = limits['max_seconds_total'] - (clock() - started)
                if remaining <= 0:
                    raise ValueError('model_comparison_shared_budget')
                before_case(directory, dict(plan['cells'][index], key=name), plan, remaining)
                if clock() - started >= limits['max_seconds_total']:
                    raise ValueError('model_comparison_shared_budget')
            case_started = clock()
            record = dict(id=name, completed=False, valid=False, reserved_calls=0,
                          observed_usage=None, usage_source='unavailable')
            records.append(record)
            arm = directory / name
            arm.mkdir(exist_ok=False)
            before = provider._calls
            try:
                before_send()
                remaining = limits['max_seconds_total'] - (clock() - started)
                used = sum(r['observed_usage']['input_tokens'] + r['observed_usage']['output_tokens']
                           for r in records if r['observed_usage'])
                cell = plan['cells'][index]
                if (remaining <= 0 or provider._calls >= limits['max_calls']
                        or used + cell['input_reservation'] + cell['output_cap'] > limits['total_token_reservation']):
                    raise ValueError('model_comparison_shared_budget')
                issued = replace(prepared, timeout_s=min(prepared.timeout_s, remaining))
                issued_raw = validate_request(issued, transport_id=transport_id)
                with (arm / 'request.raw.json').open('xb') as request_file:
                    request_file.write(issued_raw)
                write_new_json(arm / 'request.json', json.loads(issued_raw))
                record['request_sha256'] = hashlib.sha256(issued_raw).hexdigest()
                if clock() - started >= limits['max_seconds_total']:
                    raise ValueError('model_comparison_shared_budget')
                response = provider.chat(issued)
                public = public_response(json.loads(TypeAdapter(ChatResponse).dump_json(response)))
                # Preserve even a completed response rejected by later checks.
                response_path = arm / 'response.json'
                write_new_json(response_path, public)
                record.update(completed=True, observed_usage=public['usage'], usage_source='complete_response')
                if (response.provider != 'zhipu' or response.model != reviewer_profile.model
                        or response.usage.input_tokens > cell['input_reservation']
                        or response.usage.output_tokens > cell['output_cap']):
                    raise ValueError('model_comparison_response_identity_or_budget')
                if clock() - started >= limits['max_seconds_total']:
                    raise ValueError('model_comparison_shared_budget')
                exchange = provider.last_exchange
                if (exchange is None or exchange.response is not response or exchange.issued_request != issued
                        or exchange.receipt_request_sha256 != record['request_sha256']):
                    raise ValueError('model_comparison_exchange_identity')
                if inspect_response is None:
                    raw = review.tool.tool_result(prepared, exchange)
                    _, wire, journal = review.validate(raw, inputs)
                    outcome = dict(score=wire.score, verdict=wire.verdict,
                        issue_blocks=[i.block for i in wire.issues],
                        advisory_blocks=[i.block for i in wire.advisories])
                else:
                    # Task-specific output parsing only. Identity, usage,
                    # deadlines and host adjudication remain this runner's job.
                    outcome, journal = inspect_response(prepared, exchange, inputs)
                journal.update(diagnostic_experiment=plan['experiment'],
                    validator_policy_sha256=journal['policy_sha256'],
                    policy_sha256=digest(prepared.messages[0].content),
                    request_sha256=exchange.receipt_request_sha256,
                    source_projection=prepared.metadata.get('source_projection'))
                write_new_json(arm / 'journal.json', journal)
                record.update(outcome)
                record['valid'] = True
                decision = adjudicate(response_path, limits['max_seconds_total'] - (clock() - started))
                if (type(decision.get('accepted')) is not bool
                        or decision.get('response_sha256') != hashlib.sha256(response_path.read_bytes()).hexdigest()):
                    raise ValueError('model_comparison_host_identity')
                write_new_json(arm / 'host-adjudication.json', decision)
                record['host_accepted'] = decision['accepted']
                if not decision['accepted']:
                    raise ValueError('model_comparison_semantic_failure')
                before_send()  # Bind host acceptance to the same checkout too.
                if clock() - started >= limits['max_seconds_total']:
                    raise ValueError('model_comparison_shared_budget')
            finally:
                record['reserved_calls'] = provider._calls - before
                if record['reserved_calls'] not in (0, 1):
                    raise ValueError('model_comparison_call_accounting')
                if record['reserved_calls'] and not record['completed']:
                    stream = directory / 'transport' / f'stream-{provider._calls:03d}'
                    if (stream / 'progress.json').exists():
                        progress = CapacityBridgeObservation.model_validate(transport_for(stream, provider._calls)['progress'])
                        if progress.input_tokens is not None and progress.output_tokens is not None:
                            record.update(observed_usage=dict(input_tokens=progress.input_tokens, output_tokens=progress.output_tokens),
                                          usage_source='normalized_stream_usage')
                record['unknown_usage_calls'] = record['reserved_calls'] - int(record['observed_usage'] is not None)
                record['elapsed_seconds'] = round(clock() - case_started, 3)
                record['batch_elapsed_seconds'] = round(clock() - started, 3)
                write_new_json(arm / 'accounting.json', record)
        result.update(pair_accepted=True, stop_reason='two_host_accepted_development_controls_not_qualification')
    except BaseException as error:
        result.update(stop_reason='stopped', error_type=type(error).__name__)
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,90}', code):
            result['error_code'] = code
    finally:
        result.update(cases=records, reserved_calls=provider._calls,
            completed_calls=sum(r['completed'] for r in records),
            input_tokens=sum((r['observed_usage'] or {}).get('input_tokens', 0) for r in records),
            output_tokens=sum((r['observed_usage'] or {}).get('output_tokens', 0) for r in records),
            unknown_usage_calls=sum(r.get('unknown_usage_calls', r['reserved_calls']) for r in records),
            elapsed_seconds=round(clock() - started, 3))
        write_new_json(directory / 'result.json', result)
    return result


def run(args):
    if args.execute and LIVE_STATUS != 'approved_bounded_diagnostic_after_exact_ci':
        raise ValueError('model_comparison_closed_no_retry')
    plan = build_plan()
    if plan != json.loads(OUTPUT.read_text(encoding='utf-8')):
        raise ValueError('model_comparison_frozen_plan_changed')
    variants = [v for v in prepare()[0] if v[0].endswith('-baseline')]
    if not args.execute:
        print(compact(plan), flush=True)
        return plan
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY / 'plan.json', dict(preparation_plan=plan, approved_diagnostic=True,
        execution_head_sha=head, ci_run=args.ci_run, transport_id=REVIEW_MODEL_TRANSPORT_ID))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    # Use the authorized account/standard endpoint; never modify its env file.
    settings = replace(load_zhipu_settings(dotenv_values(args.env_file)), model='glm-5.3')
    provider = ReceiptedStreamProvider(settings=settings, directory=RUN_DIRECTORY / 'transport',
                                      transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        result = observe(provider, RUN_DIRECTORY, variants, plan)
    print(compact(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    run(parser.parse_args())
