"""Bounded generation requests for the opt-in product, not historical replay."""
from dataclasses import replace
from functools import lru_cache
import json
import math

POLICY_ID = 'sol-product-generation-time300-16384-v1'
MAX_OUTPUT_TOKENS = 16384
REQUEST_TIMEOUT_S = 300


@lru_cache(maxsize=1)
def policy():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    return _issue_candidate_evaluation_request_policy(
        policy_id=POLICY_ID, version='1.0.0', provider_id='riftcoach-mixed',
        model='flash-generation-tianjige-sol-review-v1', agent_timeout_s=330,
        llm_tool_timeout_s=330, transport_timeout_s=360,
        max_output_tokens=MAX_OUTPUT_TOKENS, temperature=1.0, top_p=.95,
    )


def role_for_request(request):
    from app.evaluation import sol_review_contract as historical
    from app.evaluation.natural_duty_contract import VERSION as historical_policy
    if (any(request.metadata.get(k) != v for k, v in policy().metadata().items())
            or 'sol_product_validation' in request.metadata
            or 'sol_product_chat_validation' in request.metadata):
        raise ValueError('product_generation_policy_binding')
    # Reuse all existing role checks. This temporary identity is never issued
    # or serialized: only the product request below crosses the boundary.
    legacy_identity = replace(request, metadata={**request.metadata,
        'evaluation_policy_id': historical_policy})
    if historical.role_for_request(legacy_identity) != 'generation':
        raise ValueError('product_generation_role')
    return 'generation'


def request_bytes(request, *, transport_id=None):
    from app.evaluation.golden_stream_bridge import MAX_BYTES, NATURAL_FLASH_TRANSPORT_ID, _mapping
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    role_for_request(request)
    if transport_id not in (None, NATURAL_FLASH_TRANSPORT_ID):
        raise ValueError('product_generation_transport')
    if (type(request.max_tokens) is not int or not 0 < request.max_tokens <= MAX_OUTPUT_TOKENS
            or not math.isfinite(request.timeout_s) or not 0 < request.timeout_s <= REQUEST_TIMEOUT_S
            or request.temperature != 1.0 or request.top_p != .95
            or estimate_runtime_request_input_ceiling(request) > 64000):
        raise ValueError('product_generation_request_budget')
    raw = json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('product_generation_request_size')
    return raw


def validate_new_request(contract, request):
    """Called before new intent and again for the actual budgeted request."""
    if (type(request.max_tokens) is not int or not 0 < request.max_tokens <= MAX_OUTPUT_TOKENS
            or not math.isfinite(request.timeout_s) or not 0 < request.timeout_s <= REQUEST_TIMEOUT_S):
        raise ValueError('product_request_limits')
    if contract.role_for_request(request) == 'generation':
        request_bytes(request)
    else:
        contract.request_bytes(request)
