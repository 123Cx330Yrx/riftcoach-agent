"""Explicit dynamic development contract for the reviewed necessity policy.

No credentials, paid launcher, product registration or quality admission.
Legacy requests and frozen receipts retain their original contract.
"""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import sys

from app.evaluation import sol_natural_contract as baseline
from scripts.review_necessity_candidate import NECESSITY_POLICY
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_transport import Profile

VERSION = 'natural-flash-sol-necessity-development-v1'
CONTEXT = 'sol_necessity_validation'
RESPONSE_MODE = 'natural-sol-necessity-v2'
REVIEW_TRANSPORT = 'natural-sol-necessity-nonstream-v2'
REVIEW_PROFILE = Profile(group='GPT-企业专线', route='proxy-12000')
FRESH_REVIEW_RESERVATION = 80384
ROOT, legacy = baseline.ROOT, baseline.legacy
PROVIDER, MODEL, PROFILE = baseline.PROVIDER, baseline.MODEL, baseline.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL = baseline.REVIEW_PROVIDER, baseline.REVIEW_MODEL


def make_request(inputs, name, stage='initial'):
    base = baseline.make_request(inputs, name, stage)
    metadata = dict(base.metadata)
    context = dict(metadata.pop(baseline.CONTEXT), version=VERSION)
    metadata[CONTEXT] = context
    messages = base.messages
    if name == 'facts':
        messages = (replace(messages[0], content=messages[0].content + NECESSITY_POLICY), *messages[1:])
    return replace(base, messages=messages, metadata=metadata)


def restore_context(context):
    if not isinstance(context, dict) or context.get('version') != VERSION:
        raise ValueError('necessity_natural_context')
    return baseline.restore_context(dict(context, version=baseline.VERSION))


def validate_business(business, context):
    inputs = restore_context(context)
    if business != visible(json_value(make_request(inputs, context['duty'], context['stage']))):
        raise ValueError('necessity_natural_request_binding')
    validate = baseline.direct.validate if context['stage'] == 'initial' else baseline.duty.validate
    return lambda raw: validate(raw, inputs, context['duty'])


def role_for_request(request):
    if CONTEXT not in request.metadata:
        if baseline.role_for_request(request) != 'generation':
            raise ValueError('necessity_natural_review_context_required')
        return 'generation'
    context = request.metadata[CONTEXT]
    prepared = make_request(restore_context(context), context['duty'], context['stage'])
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != prepared:
        raise ValueError('necessity_natural_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    if role_for_request(request) == 'generation':
        return baseline.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT) or not 0 < request.timeout_s <= 300:
        raise ValueError('necessity_natural_transport_binding')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('necessity_natural_input_limit')
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class NecessityNaturalContract(baseline.SolNaturalContract):
    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION,
            transport_retries=4, execution_timeout_s=3600,
            transport_retry_mode='manual-reaped-timeout-v1',
            output_policy='single-tool-with-message-v2',
            output_recovery_mode='manual-reaped-format-v1',
            necessity_policy_sha256=hashlib.sha256(NECESSITY_POLICY.encode('utf-8')).hexdigest(),
            review_profile=dict(group=REVIEW_PROFILE.group, route=REVIEW_PROFILE.route),
            review_prices_cny_per_million=dict(input='0.5', output='2.5'))
        value['roles']['review']['transport_id'] = REVIEW_TRANSPORT
        return value

    request_identity = staticmethod(request_identity)

    def require_provider(self, provider):
        super().require_provider(provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('necessity_natural_provider_contract')

    @property
    def pricing_profiles(self):
        values = {key: value.model_copy(update={'profile_id':'necessity-enterprise-prices-20261024'})
                  for key, value in super().pricing_profiles.items()}
        values[REVIEW_PROVIDER, REVIEW_MODEL] = values[REVIEW_PROVIDER, REVIEW_MODEL].model_copy(update=dict(
            profile_id='necessity-enterprise-prices-20261024',
            input_cost_per_million=Decimal('.5'), output_cost_per_million=Decimal('2.5')))
        return values


CONTRACT = NecessityNaturalContract(version='1.6.4')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in baseline.component_fingerprints(skill)}
    for path in ('app/evaluation/sol_necessity_contract.py', 'scripts/review_necessity_candidate.py'):
        key = path.replace('/', '.').replace('.py', '')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
