"""Explicit mixed-provider development contract, never product admission."""
from dataclasses import replace
from decimal import Decimal
from functools import lru_cache
import hashlib
import json

from app.evaluation import natural_duty_contract as legacy
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_review_experiment import SourceIndex, compact
from app.runtime.models import RuntimePricingProfile
from scripts import review_duty_direct_patch as direct, review_duty_composition as duty
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'natural-flash-sol-development-v1'
MODEL = 'flash-generation-tianjige-sol-review-v1'
PROFILE = 'flash-sol-high-development-v1'
PROVIDER = 'riftcoach-mixed'
REVIEW_PROVIDER = 'tianjige'
REVIEW_MODEL = 'gpt-6.1-sol'
REVIEW_TRANSPORT = 'natural-sol-nonstream-v1'
CONTEXT = 'sol_natural_validation'
FRESH_REVIEW_RESERVATION = 80384
ROOT = legacy.ROOT


@lru_cache(maxsize=1)
def policy():
    # Version 2 explicitly binds the mixed router while retaining the same
    # generation request policy id accepted by the existing Flash transport.
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    return _issue_candidate_evaluation_request_policy(policy_id=legacy.VERSION, version='2.0.0',
        provider_id=PROVIDER, model=MODEL, agent_timeout_s=330, llm_tool_timeout_s=330,
        transport_timeout_s=360, max_output_tokens=32768, temperature=1.0, top_p=.95)


def make_request(inputs, name, stage='initial'):
    base = direct.review_request(inputs, name, stage)
    metadata = {k: v for k, v in base.metadata.items() if k != legacy.OLD_TIMING}
    metadata[CONTEXT] = dict(version=VERSION, duty=name, stage=stage,
        report=inputs.source.report, data_json=inputs.data_json, pack_json=inputs.pack_json)
    return replace(base, max_tokens=16384, timeout_s=300, metadata=metadata)


def restore_context(context):
    if set(context) != {'version', 'duty', 'stage', 'report', 'data_json', 'pack_json'} or context['version'] != VERSION:
        raise ValueError('sol_context_shape')
    if context['duty'] not in duty.DUTIES or context['stage'] not in duty.STAGES:
        raise ValueError('sol_context_stage')
    pack = json.loads(context['pack_json'])
    data = json.loads(context['data_json'])
    source = SourceIndex.build(context['report'], pack)
    if data['facts_and_provenance'] != pack or data['source_index'] != source.prompt_sources():
        raise ValueError('sol_context_sources')
    return ReviewInput(source, context['data_json'], context['pack_json'])


def validate_business(business, context):
    inputs = restore_context(context)
    expected = visible(json_value(make_request(inputs, context['duty'], context['stage'])))
    if business != expected:
        raise ValueError('sol_dynamic_request_binding')
    validate = direct.validate if context['stage'] == 'initial' else duty.validate
    return lambda raw: validate(raw, inputs, context['duty'])


def role_for_request(request):
    if CONTEXT not in request.metadata:
        if legacy.role_for_request(request) != 'generation':
            raise ValueError('sol_review_context_required')
        return 'generation'
    if 'agent_loop_iteration' in request.metadata or legacy.MARKER in request.metadata:
        raise ValueError('sol_role_binding')
    context = request.metadata[CONTEXT]
    prepared = make_request(restore_context(context), context['duty'], context['stage'])
    metadata = dict(request.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(request, metadata=metadata, timeout_s=300) != prepared:
        raise ValueError('sol_request_binding')
    return 'review'


def request_identity(request):
    return ('zhipu', 'glm-5.3-flash') if role_for_request(request) == 'generation' else (REVIEW_PROVIDER, REVIEW_MODEL)


def request_bytes(request, *, transport_id=None):
    if role_for_request(request) == 'generation':
        return legacy.request_bytes(request, transport_id=transport_id)
    if transport_id not in (None, REVIEW_TRANSPORT) or not 0 < request.timeout_s <= 300:
        raise ValueError('sol_transport_binding')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('sol_input_limit')
    return json.dumps(request, default=legacy._mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class SolNaturalContract(legacy.NaturalDutyContract):
    @property
    def request_policy(self):
        return policy()

    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, provider_id=PROVIDER, model=MODEL,
            thinking_profile_id=PROFILE, target_runtime_profile_id=PROFILE,
            max_calls=10, total_tokens=739840, execution_timeout_s=2400,
            generation_logical_calls=2, review_logical_calls=4, transport_retries=2,
            generation_policy_reused=legacy.VERSION, stream_transport_id='mixed-explicit',
            component_contract=VERSION)
        value['roles']['review'] = dict(provider=REVIEW_PROVIDER, model=REVIEW_MODEL,
            thinking_profile_id='sol-high-nonstream-v1', transport_id=REVIEW_TRANSPORT,
            sdk_max_retries=0, max_output_tokens=16384, request_timeout_s=300,
            upstream_identity_verified=False, request_extra_body={})
        return value

    request_identity = staticmethod(request_identity)

    def require_provider(self, provider):
        if (provider.provider_name, provider.model_name, provider.thinking_profile_id) != (PROVIDER, MODEL, PROFILE):
            raise ValueError('sol_composite_identity')
        if type(provider.sdk_max_retries) is not int or provider.sdk_max_retries != 0 or provider.runtime_profile is not None:
            raise ValueError('sol_retry_identity')

    @property
    def pricing_profiles(self):
        values = {key: value.model_copy(update={'profile_id': 'mixed-candidate-prices-20261019'})
                  for key, value in super().pricing_profiles.items() if key[1] == 'glm-5.3-flash'}
        values[REVIEW_PROVIDER, REVIEW_MODEL] = RuntimePricingProfile(profile_id='mixed-candidate-prices-20261019',
            version='1.0.0', provider_id=REVIEW_PROVIDER, model=REVIEW_MODEL, currency='CNY',
            input_cost_per_million=Decimal('.4'), output_cost_per_million=Decimal('2'))
        return values


CONTRACT = SolNaturalContract(version='1.6.2')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in legacy.component_fingerprints(skill)}
    for path in ('app/evaluation/sol_natural_contract.py', 'app/runtime/sol_natural_provider.py',
                 'app/evaluation/sol_natural_session.py', 'app/runtime/sol_session_runtime.py',
                 'app/runtime/sol_session_receipts.py',
                 'app/evaluation/sol_session_review.py',
                 'scripts/sol_natural_continuation.py',
                 'scripts/reviewer_responses_process.py', 'scripts/reviewer_responses_nonstream.py',
                 'scripts/reviewer_responses_transport.py', 'scripts/stream_observation.py'):
        key = path.replace('/', '.').replace('.py', '')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
