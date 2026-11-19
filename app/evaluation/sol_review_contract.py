"""Dynamic dual-policy candidate shared by Runtime and original15 inventory.

The diagnostic continuation remains separate: no inherited exchange or fixed
control material is accepted here. This opt-in candidate grants no admission.
"""
from dataclasses import replace
import hashlib
import json
import sys

from app.evaluation import sol_necessity_contract as parent
from scripts.review_completion_necessity_candidate import COMPLETION_NECESSITY_POLICY
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'natural-flash-sol-dual-necessity-development-v1'
CONTEXT = 'sol_review_validation'
RESPONSE_MODE = 'natural-sol-dual-necessity-v1'
REVIEW_TRANSPORT = 'natural-sol-dual-necessity-nonstream-v1'
ROOT, legacy = parent.ROOT, parent.legacy
ASSETS = ROOT/'examples/runtime_profiles/sol_review_v1'
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL
REVIEW_PROFILE = parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION


def make_request(inputs, name, stage='initial'):
    base = parent.make_request(inputs, name, stage)
    metadata = dict(base.metadata)
    metadata[CONTEXT] = dict(metadata.pop(parent.CONTEXT), version=VERSION)
    messages = base.messages
    if name == 'completion':
        messages = (replace(messages[0], content=messages[0].content+COMPLETION_NECESSITY_POLICY),
                    *messages[1:])
    return replace(base, metadata=metadata, messages=messages)


def restore_context(context):
    if not isinstance(context, dict) or context.get('version') != VERSION:
        raise ValueError('dual_necessity_context')
    return parent.restore_context(dict(context, version=parent.VERSION))


def validate_business(business, context):
    inputs = restore_context(context)
    if business != visible(json_value(make_request(inputs, context['duty'], context['stage']))):
        raise ValueError('dual_necessity_business_binding')
    validate = parent.baseline.direct.validate if context['stage'] == 'initial' else parent.baseline.duty.validate
    return lambda raw: validate(raw, inputs, context['duty'])


def role_for_request(request):
    if CONTEXT not in request.metadata:
        if parent.role_for_request(request) != 'generation':
            raise ValueError('dual_necessity_review_context_required')
        return 'generation'
    context = request.metadata[CONTEXT]
    prepared = make_request(restore_context(context), context['duty'], context['stage'])
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != prepared:
        raise ValueError('dual_necessity_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    if role_for_request(request) == 'generation':
        return parent.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT) or not 0 < request.timeout_s <= 300:
        raise ValueError('dual_necessity_transport_binding')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('dual_necessity_input_limit')
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class DualNecessityContract(parent.NecessityNaturalContract):
    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION,
            completion_policy_sha256=hashlib.sha256(COMPLETION_NECESSITY_POLICY.encode('utf-8')).hexdigest(),
            workflow_scope='dynamic-natural-task-and-original15-candidate')
        value['roles']['review']['transport_id'] = REVIEW_TRANSPORT
        return value

    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    request_identity = staticmethod(request_identity)

    def require_provider(self, provider):
        parent.baseline.SolNaturalContract.require_provider(self, provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('dual_necessity_provider_contract')


CONTRACT = DualNecessityContract(version='1.6.6')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in parent.component_fingerprints(skill)}
    for path in ('app/evaluation/sol_review_contract.py', 'scripts/review_completion_necessity_candidate.py',
                 'scripts/natural_completion_continuation.py'):
        key = path.replace('/', '.').replace('.py', '')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
