"""Read completed original transport evidence after a lost session result."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE, CapacityBridgeObservation
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.runtime.sol_natural_provider import SolReviewProvider
from scripts.reviewer_responses_process import read_json


def request_from_raw(raw):
    original = json.loads(raw)
    value = REQUEST.validate_json(raw)
    return replace(value, **{k: original[k] for k in ('timeout_s', 'temperature', 'top_p')})


def recover_success(root, intent, attempt):
    request = request_from_raw(attempt['issued_raw'])
    role = contract.role_for_request(request)
    ordinal = attempt['ordinal']
    before = attempt['budget_before']
    if ordinal != before['calls']+1 or ordinal != before['router_calls']+1 or not 1 <= ordinal <= 7:
        raise ValueError('session_attempt_ordinal_binding')
    prepared = REQUEST.validate_json(json.dumps(intent['request']))
    expected = replace(prepared, timeout_s=request.timeout_s,
        max_tokens=min(prepared.max_tokens or 32768, 32768), temperature=1.0, top_p=.95,
        metadata={**prepared.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
    if expected != request:
        raise ValueError('session_attempt_request_binding')
    if role == 'review':
        provider = SolReviewProvider(api_key='', directory=root/'review', task_directory=root,
                                    sender=lambda *a, **k: (_ for _ in ()).throw(AssertionError('recovery IO')))
        response = provider.read_completed_at_ordinal(request, ordinal=ordinal, role=role)
        elapsed = read_json(root/'review'/f'call-{ordinal:03d}'/'receipt.json')['elapsed_s']
        allowed = {f'review/call-{ordinal:03d}/{name}' for name in (
            'request.json', 'validation-context.json', 'profile.json', 'usage.json',
            'receipt.json', 'worker-result.json', 'observation/observation.json')}
        profile, transport = provider.thinking_profile_id, provider.transport_id
    else:
        from app.evaluation.golden_stream_bridge import NATURAL_FLASH_TRANSPORT_ID
        from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
        transport, profile = NATURAL_FLASH_TRANSPORT_ID, ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
        folder = root/'generation'
        raw = (folder/f'request-{ordinal:03d}.json').read_bytes()
        if raw != contract.request_bytes(request):
            raise ValueError('session_flash_request_binding')
        response_raw = (folder/f'response-{ordinal:03d}.json').read_bytes()
        response = RESPONSE.validate_json(response_raw)
        stream = folder/f'stream-{ordinal:03d}'
        reservation, terminal = read_json(stream/'reservation.json'), read_json(stream/'result.json')
        progress = CapacityBridgeObservation.model_validate(read_json(stream/'progress.json'), strict=True)
        pin = hashlib.sha256(raw).hexdigest()
        binding = dict(ordinal=ordinal, role=role, provider='zhipu', model='glm-5.3-flash',
            thinking_profile_id=profile, transport_id=transport, request_sha256=pin,
            raw_directory='generation', state='reserved_before_io')
        result = dict(binding, state='complete', response_sha256=hashlib.sha256(response_raw).hexdigest(),
                      input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        result_path = root/f'call-result-{ordinal:03d}.json'
        if (read_json(root/f'call-{ordinal:03d}.json') != binding
                or result_path.exists() and read_json(result_path) != result
                or not reservation or reservation.get('request_sha256') != pin
                or reservation.get('ordinal') != ordinal or reservation.get('model') != response.model
                or reservation.get('thinking_profile_id') != profile
                or reservation.get('transport_id') != transport
                or reservation.get('stream_tool_arguments') != bool(request.tools)
                or not terminal or terminal.get('state') != 'complete' or terminal.get('transport_id') != transport
                or progress.state != 'complete' or progress.close_state != 'closed'
                or any(v is None for v in (progress.eof_ms, progress.close_ms, progress.terminal_ms))
                or progress.http_requests != 1 or progress.input_tokens != response.usage.input_tokens
                or progress.output_tokens != response.usage.output_tokens):
            raise ValueError('session_flash_complete_evidence_required')
        elapsed = terminal['elapsed_ms']/1000
        allowed = {f'generation/{name}-{ordinal:03d}.json' for name in ('request', 'response')}
        allowed.update(f'generation/stream-{ordinal:03d}/{name}.json' for name in ('reservation', 'result', 'progress'))
    allowed.update((f'call-{ordinal:03d}.json', f'call-result-{ordinal:03d}.json'))
    ceiling = estimate_runtime_request_input_ceiling(request)
    if ((response.provider, response.model) != contract.request_identity(request)
            or response.finish_reason not in ('stop', 'tool_calls')
            or response.usage.input_tokens > ceiling or response.usage.output_tokens > request.max_tokens
            or type(elapsed) not in (int, float) or not math.isfinite(elapsed)
            or not 0 <= elapsed <= request.timeout_s):
        raise ValueError('session_saved_response_or_time_invalid')
    budget = deepcopy(before)
    budget.update(calls=ordinal, router_calls=ordinal, tokens=before['tokens']+
                  response.usage.input_tokens+response.usage.output_tokens, stopped=False, failed=False)
    # Previous unknown reservations remain; this completed attempt releases
    # only its own reservation, which was not yet added to budget_before.
    if not attempt['retry_pending']:
        budget['logical'][role] += 1
    budget['attempts'].append(dict(ordinal=ordinal, role=role,
        phase=request.metadata.get('review_phase', 'generation'), model=response.model,
        profile=profile, transport_id=transport, request_sha256=contract.request_sha(request),
        status='completed', input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))
    return dict(ok=True, response_raw=RESPONSE.dump_json(response).decode('utf-8'),
        issued_raw=attempt['issued_raw'], receipt_request_sha256=contract.request_sha(request),
        budget=budget, recovery='validated_original_response_no_send'), elapsed, allowed
