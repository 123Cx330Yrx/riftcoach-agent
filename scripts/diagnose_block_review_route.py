"""Two bounded route interventions on the exact interrupted review request.

Development diagnosis only. No retries, revision, batch reopening or publication.
The first incomplete response stops the pair. Process-local proxy overrides are
restored even on failure; neither Git nor the user's global environment changes.
"""
import argparse
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re

from pydantic import TypeAdapter

from app.evaluation import golden_native_block_tool_review as review
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REQUEST, validate_request
from app.providers.models import ChatResponse
from scripts.check_native_claim_scope import load_controls
from scripts.export_partitioned_review import public_response
from scripts.run_golden_inference_development import verify_public_ci

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data/evaluation/results/golden_native_block_tool_interruption_a501c33.json'
REQUEST_SHA = '863766f614d73ff4eb5d3c54e1128d14ec6d4d48ca5efd445faf59681f4bc067'
RUN_ID = 'block-review-route-v1'


def prepare():
    archived = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    request = REQUEST.validate_python(archived['request_reconstructed_from_unchanged_code_and_verified_against_reservation'])
    data = json.loads((ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json').read_text(encoding='utf-8'))
    _, _, source = load_controls()
    inputs = review.native.build_inputs(replace(source, report=data['cases'][0]['report'], user_utterance=data['user_utterance']))
    rebuilt = replace(review.request(inputs), metadata=request.metadata)
    raw = validate_request(rebuilt, transport_id=CAPACITY_TRANSPORT_ID)
    # Build with the original code path: validating an archived dataclass via
    # Pydantic normalizes timeout_s=300 to 300.0 and changes its wire hash.
    if (hashlib.sha256(raw).hexdigest() != REQUEST_SHA or
            json.loads(raw) != json.loads(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID))):
        raise ValueError('route_current_request_changed')
    return rebuilt, inputs


@contextmanager
def route_environment(route):
    if route not in ('direct', 'proxy_12000'):
        raise ValueError('route_invalid')
    keys = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
            'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')
    saved = {k: os.environ[k] for k in keys if k in os.environ}
    try:
        for key in keys:
            os.environ.pop(key, None)
        if route == 'direct':
            os.environ['NO_PROXY'] = 'open.bigmodel.cn'
        else:
            os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:12000'
        yield
    finally:
        for key in keys:
            os.environ.pop(key, None)
        os.environ.update(saved)


def observed_usage(directory):
    """Usage may arrive even when assembly rejects the completed wire output."""
    from app.evaluation.golden_stream_bridge import CapacityBridgeObservation
    path = directory / 'stream-001/progress.json'
    if not path.exists():
        return None
    progress = CapacityBridgeObservation.model_validate_json(path.read_bytes())
    if progress.input_tokens is None or progress.output_tokens is None:
        return None
    return dict(input_tokens=progress.input_tokens, output_tokens=progress.output_tokens)


def observe(directory, request, inputs, factory, *, argument_diagnostic=False, experiment=None):
    records = []
    for route in (('direct',) if argument_diagnostic else ('direct', 'proxy_12000')):
        arm = directory / route
        arm.mkdir(exist_ok=False)
        record = dict(route=route, completed=False, valid=False, reserved_calls=0)
        records.append(record)
        provider = factory(arm / 'transport')
        try:
            with route_environment(route):
                response = provider.chat(request)
            record.update(completed=True, response=public_response(json.loads(TypeAdapter(ChatResponse).dump_json(response))))
            # Persist the complete public response even if its schema is invalid.
            write_new_json(arm / 'response.json', record['response'])
            raw = review.previous.tool.tool_result(request, provider.last_exchange)
            _, wire, journal = review.validate(raw, inputs)
            write_new_json(arm / 'journal.json', journal)
            record.update(valid=True, score=wire.score, verdict=wire.verdict,
                issue_blocks=[r.block for r in wire.reviews if r.issues],
                advisory_blocks=[r.block for r in wire.reviews if r.advisories])
        except Exception as error:
            record['error_type'] = type(error).__name__
            code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
            if isinstance(code, str) and re.fullmatch('[a-z_]{1,90}', code):
                record['error_code'] = code
        finally:
            record['reserved_calls'] = provider._calls
            usage = (record['response']['usage'] if record['completed']
                     else observed_usage(arm / 'transport'))
            record['observed_usage'] = usage
            record['usage_source'] = ('complete_response' if record['completed']
                else 'normalized_stream_usage' if usage is not None else 'unavailable')
            record['unknown_usage_calls'] = max(0, provider._calls - int(usage is not None))
            write_new_json(arm / 'result.json', record)
        print(json.dumps({k:v for k,v in record.items() if k != 'response'}), flush=True)
        if not record['valid']:
            break
    result = dict(experiment=experiment or ('block-review-tool-args-v1' if argument_diagnostic else RUN_ID),
        cases=records, production_admitted=False,
        semantic_approval=False, reserved_calls=sum(r['reserved_calls'] for r in records),
        unknown_usage_calls=sum(r['unknown_usage_calls'] for r in records),
        input_tokens=sum((r['observed_usage'] or {}).get('input_tokens', 0) for r in records),
        output_tokens=sum((r['observed_usage'] or {}).get('output_tokens', 0) for r in records))
    write_new_json(directory / 'result.json', result)
    return result


def run(args):
    request, inputs = prepare()
    plan = dict(experiment=RUN_ID, request_sha256=REQUEST_SHA,
        routes=['direct', 'proxy_12000'], model='glm-5.3-flash', reasoning_effort='high',
        max_calls=2, max_seconds_per_call=300, max_output_per_call=32768,
        sdk_retries=0, no_reassessment_or_revision=True, production_admitted=False,
        decisions={
            'direct_incomplete': 'Stop: proxy is not necessary for this new failure; inspect terminal/tool telemetry.',
            'direct_complete_proxy_incomplete': 'Route association supports direct follow-up, not causal proof from one pair.',
            'both_complete': 'Historical stall remains unattributed; inspect full semantics before a new quality batch.',
            'semantic_error': 'Keep the error; route success does not qualify the reviewer.'})
    if args.argument_diagnostic:
        plan.update(experiment='block-review-tool-args-v1', routes=['direct'], max_calls=1,
            intervention='Preserve terminal rejected tool fragments for offline reconstruction; same request bytes.',
            decisions={
                'rejected_arguments': 'Inspect exact fragments and reproduce rejection offline; no retry.',
                'complete_valid': 'Inspect full semantics; prior lost malformed output stays unknown.',
                'incomplete_stream': 'Stop without another request; no inference about absent final arguments.'})
    if not args.execute:
        print(json.dumps(plan))
        return plan
    head = verify_public_ci(args.ci_run)
    directory = ROOT / 'data/runs/route_diagnostic' / plan['experiment']
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory / 'plan.json', dict(plan, head_sha=head, ci_run=args.ci_run))
    write_new_json(directory / 'request.json', json.loads(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(args.env_file))
    return observe(directory, request, inputs, lambda path: ReceiptedStreamProvider(
        settings=settings, directory=path, transport_id=CAPACITY_TRANSPORT_ID),
        argument_diagnostic=args.argument_diagnostic)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--argument-diagnostic', action='store_true')
    run(parser.parse_args())
