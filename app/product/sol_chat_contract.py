"""Explicit product Chat route, sharing the existing business and budget policy.

It has a separate durable identity. No default switch or old-task migration.
"""
from dataclasses import replace
import hashlib
import json
import sys

from app.product import sol_contract as parent

VERSION = 'natural-flash-sol-product-chat-v1'
WORKER_PROFILE = 'sol-dual-product-chat-v1'
CONTEXT = 'sol_product_chat_validation'
RESPONSE_MODE = REVIEW_TRANSPORT = 'natural-sol-product-chat-v1'
REVIEW_THINKING_PROFILE = 'sol-high-chat-stream-v1'
ROOT, legacy = parent.ROOT, parent.legacy
ASSETS = ROOT / 'examples/runtime_profiles/sol_product_chat_v1'
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL, REVIEW_PROFILE = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL, parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION


def make_request(inputs, name, stage='initial'):
    request = parent.make_request(inputs, name, stage)
    metadata = dict(request.metadata)
    metadata[CONTEXT] = dict(metadata.pop(parent.CONTEXT), version=VERSION)
    return replace(request, metadata=metadata)


def restore_context(context):
    if not isinstance(context, dict) or context.get('version') != VERSION:
        raise ValueError('product_chat_context')
    return parent.restore_context(dict(context, version=parent.VERSION))


def validate_business(business, context):
    restore_context(context)
    return parent.validate_business(business, dict(context, version=parent.VERSION))


def role_for_request(request):
    if CONTEXT not in request.metadata:
        if parent.role_for_request(request) != 'generation':
            raise ValueError('product_chat_context_required')
        return 'generation'
    context = request.metadata[CONTEXT]
    prepared = make_request(restore_context(context), context['duty'], context['stage'])
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != prepared:
        raise ValueError('product_chat_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    if role_for_request(request) == 'generation':
        return parent.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT):
        raise ValueError('product_chat_transport_binding')
    # Reuse the exact parent budget checks without serializing a different request.
    context = dict(request.metadata[CONTEXT], version=parent.VERSION)
    metadata = {k: v for k, v in request.metadata.items() if k != CONTEXT}
    parent.request_bytes(replace(request, metadata={**metadata, parent.CONTEXT: context}))
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class ChatProductContract(parent.ProductContract):
    request_identity = staticmethod(request_identity)

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION, reused_business_contract=parent.VERSION)
        value['roles']['review'].update(transport_id=REVIEW_TRANSPORT, thinking_profile_id=REVIEW_THINKING_PROFILE)
        return value

    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def require_provider(self, provider):
        from app.evaluation.sol_natural_contract import SolNaturalContract
        SolNaturalContract.require_provider(self, provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('sol_chat_product_provider_contract')


CONTRACT = ChatProductContract(version='1.7.10')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in parent.component_fingerprints(skill)}
    for path in ('app/product/sol_chat_contract.py', 'scripts/reviewer_chat_contract.py',
                 'scripts/reviewer_chat_stream.py', 'app/tasks/continuation.py'):
        key = path.replace('/', '.').removesuffix('.py')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
