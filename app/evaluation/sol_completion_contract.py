"""Opt-in completion diagnostic contract; no qualification or paid launcher."""
from dataclasses import replace
import hashlib
import json
import sys

from app.evaluation import sol_necessity_contract as parent
from scripts.review_completion_necessity_candidate import COMPLETION_NECESSITY_POLICY, materials
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'natural-sol-completion-necessity-development-v1'
CONTEXT = parent.CONTEXT
RESPONSE_MODE = 'natural-sol-completion-necessity-v1'
REVIEW_TRANSPORT = 'natural-sol-completion-necessity-nonstream-v1'
ROOT, legacy = parent.ROOT, parent.legacy
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL
REVIEW_PROFILE = parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION


def restore_context(context):
    value = dict(context)
    case = value.pop('control_case', None)
    if value.get('version') != VERSION or case not in (None, 'b', 'c', 'd'):
        raise ValueError('completion_context_identity')
    inputs = parent.restore_context(dict(value, version=parent.VERSION))
    if case is not None and (value['duty'] != 'completion' or value['stage'] != 'initial'
                            or inputs != materials()[case]):
        raise ValueError('completion_control_material')
    return inputs


def make_request(inputs, name, stage='initial', *, control_case=None):
    base = parent.make_request(inputs, name, stage)
    # The inherited accepted facts exchange keeps its original request/contract.
    # It is replay-only; the new receiver explicitly refuses to send it.
    if name == 'facts' and stage == 'initial' and control_case is None:
        return base
    context = dict(base.metadata[CONTEXT], version=VERSION)
    if control_case is not None:
        context['control_case'] = control_case
        restore_context(context)
    messages = base.messages
    if name == 'completion':
        messages = (replace(messages[0], content=messages[0].content+COMPLETION_NECESSITY_POLICY),
                    *messages[1:])
    return replace(base, messages=messages, metadata={**base.metadata, CONTEXT:context})


def validate_business(business, context):
    inputs = restore_context(context)
    prepared = make_request(inputs, context['duty'], context['stage'], control_case=context.get('control_case'))
    if business != visible(json_value(prepared)):
        raise ValueError('completion_business_binding')
    validate = parent.baseline.direct.validate if context['stage'] == 'initial' else parent.baseline.duty.validate
    return lambda raw: validate(raw, inputs, context['duty'])


def role_for_request(request):
    context = request.metadata.get(CONTEXT)
    if context is None:
        return parent.role_for_request(request)
    if context.get('version') == parent.VERSION:
        if (context.get('duty'), context.get('stage')) != ('facts', 'initial'):
            raise ValueError('completion_inherited_stage')
        return parent.role_for_request(request)
    inputs = restore_context(context)
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != make_request(
            inputs, context['duty'], context['stage'], control_case=context.get('control_case')):
        raise ValueError('completion_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    role = role_for_request(request)
    if role == 'generation' or request.metadata[CONTEXT].get('version') == parent.VERSION:
        return parent.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT) or not 0 < request.timeout_s <= 300:
        raise ValueError('completion_transport_binding')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('completion_input_ceiling')
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class CompletionContract(parent.NecessityNaturalContract):
    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION,
            max_calls=14, total_tokens=870431, execution_timeout_s=3600,
            control_logical_calls=3, natural_review_logical_calls=4,
            completion_policy_sha256=hashlib.sha256(COMPLETION_NECESSITY_POLICY.encode('utf-8')).hexdigest(),
            inherited_facts='original-contract-replay-only',
            workflow_scope='completion-diagnostic-continuation-not-product-runtime')
        value['roles']['review']['transport_id'] = REVIEW_TRANSPORT
        return value

    request_identity = staticmethod(request_identity)

    def require_provider(self, provider):
        parent.baseline.SolNaturalContract.require_provider(self, provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('completion_provider_contract')


CONTRACT = CompletionContract(version='1.6.5')
