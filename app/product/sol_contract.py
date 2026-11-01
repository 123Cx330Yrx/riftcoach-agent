"""Opt-in product contract with trusted purpose and bounded streaming.

Source projection, duty schemas and repair validation reuse the admitted
development work. Historical qualification requests retain their own contract.
"""
from dataclasses import replace
import hashlib
import json
import sys

from app.evaluation import sol_review_contract as parent

VERSION = 'natural-flash-sol-product-v1'
WORKER_PROFILE = 'sol-dual-product-v1'
ROOT, legacy = parent.ROOT, parent.legacy
ASSETS = ROOT / 'examples/runtime_profiles/sol_product_v1'
CONTEXT = 'sol_product_validation'
RESPONSE_MODE = 'natural-sol-product-stream-v1'
REVIEW_TRANSPORT = 'natural-sol-product-stream-v1'
REVIEW_THINKING_PROFILE = 'sol-high-stream-v1'
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL, REVIEW_PROFILE = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL, parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION
def make_request(inputs, name, stage='initial'):
    from .review_purpose import input_purpose, purpose_policy
    base = parent.make_request(inputs, name, stage)
    metadata = dict(base.metadata)
    metadata[CONTEXT] = dict(metadata.pop(parent.CONTEXT), version=VERSION)
    return replace(base, metadata=metadata, messages=(replace(base.messages[0],
        content=base.messages[0].content+'\n\n'+purpose_policy(input_purpose(inputs))), *base.messages[1:]))


def restore_context(context):
    from .review_purpose import input_purpose
    if not isinstance(context, dict) or context.get('version') != VERSION:
        raise ValueError('product_review_context')
    inputs = parent.restore_context(dict(context, version=parent.VERSION))
    input_purpose(inputs)
    return inputs


def validate_business(business, context):
    from scripts.prepare_reviewer_profile_screen import visible, json_value
    from scripts import review_duty_direct_patch as direct, review_duty_composition as duty
    inputs = restore_context(context)
    if business != visible(json_value(make_request(inputs, context['duty'], context['stage']))):
        raise ValueError('product_review_business_binding')
    validate = direct.validate if context['stage'] == 'initial' else duty.validate
    return lambda raw: validate(raw, inputs, context['duty'])


def role_for_request(request):
    if CONTEXT not in request.metadata:
        if parent.role_for_request(request) != 'generation':
            raise ValueError('product_review_context_required')
        return 'generation'
    context = request.metadata[CONTEXT]
    prepared = make_request(restore_context(context), context['duty'], context['stage'])
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != prepared:
        raise ValueError('product_review_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    if role_for_request(request) == 'generation':
        return parent.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT):
        raise ValueError('product_stream_transport_binding')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if not 0 < request.timeout_s <= 300 or estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('product_review_request_budget')
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class ProductContract(parent.DualNecessityContract):
    @property
    def context_policy(self):
        from app.evaluation.golden_position_policy import POSITION_POLICY as historical
        from .review_purpose import POSITION_POLICY
        base = super().context_policy
        if base.count(historical) != 1:
            raise ValueError('product_position_policy_binding')
        return base.replace(historical, POSITION_POLICY)

    request_identity = staticmethod(request_identity)

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION,
            max_calls=8, total_tokens=401920, execution_timeout_s=900,
            transport_retries=2, generation_logical_calls=4,
            time_basis='cumulative-active-seconds', workflow_scope='opt-in-product',
            qualification_only=False, publication_policy='dual-review-exact-application-v1',
            reused_business_contract=parent.VERSION,
            task_purpose_policy='product-review-purpose-v1',
            context_policy_sha256=hashlib.sha256(self.context_policy.encode()).hexdigest())
        value['roles']['review'].update(transport_id=REVIEW_TRANSPORT,
            thinking_profile_id=REVIEW_THINKING_PROFILE)
        return value

    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def require_provider(self, provider):
        parent.parent.baseline.SolNaturalContract.require_provider(self, provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('sol_product_provider_contract')


CONTRACT = ProductContract(version='1.7.2')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in parent.component_fingerprints(skill)}
    rows['generation_policy'] = ComponentFingerprint(component_id='generation_policy',
        source='generation_policy', sha256=hashlib.sha256(CONTRACT.context_policy.encode()).hexdigest())
    for path in ('app/product/sol_contract.py', 'app/product/sol_workflow.py',
                 'app/product/manual_retry_grant.py', 'app/product/review_purpose.py', 'scripts/reviewer_responses_stream.py',
                 'app/product/stream_migration.py', 'app/product/budget_supplement.py', 'app/workers/sol_continuation.py',
                 'app/product/zero_send_recovery.py',
                 'app/product/protocol_failure_recovery.py',
                 'app/tasks/reconciliation.py', 'app/tasks/models.py', 'app/persistence/task_repository.py',
                 'app/persistence/task_continuations.py'):
        key = path.replace('/', '.').removesuffix('.py')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT / path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
