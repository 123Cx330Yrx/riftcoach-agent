"""Explicit six-call, time300 natural-duty candidate; no production admission."""
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from app.model_runtime import _issue_candidate_evaluation_request_policy
from app.runtime.coach_contract import RoleCoachExecutionContract, CoachContractSnapshot
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.evaluation.golden_stream_bridge import _mapping, MAX_BYTES
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from scripts import review_duty_direct_patch as direct, review_duty_composition as duty
from app.evaluation.document_review_timing_adapter import METADATA as OLD_TIMING

VERSION = 'natural-duty-direct-patch-time300-v1'
MODEL = 'flash-generation-glm53-dual-duty-patch-v1'
PROFILE = 'natural-duty-high-v1'
MARKER = 'natural_duty_candidate'
ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def policy():
    return _issue_candidate_evaluation_request_policy(policy_id=VERSION, version='1.0.0',
        provider_id='zhipu', model=MODEL, agent_timeout_s=330, llm_tool_timeout_s=330,
        transport_timeout_s=360, max_output_tokens=32768, temperature=1.0, top_p=.95)


def make_request(inputs, name, stage='initial'):
    base = direct.review_request(inputs, name, stage)
    metadata = dict(base.metadata)
    del metadata[OLD_TIMING]
    metadata[MARKER] = VERSION
    return replace(base, timeout_s=300, metadata=metadata)


def role_for_request(request):
    if OLD_TIMING in request.metadata:
        raise ValueError('natural_duty_old_timing')
    if 'agent_loop_iteration' in request.metadata:
        iteration = request.metadata['agent_loop_iteration']
        if (type(iteration) is not int or iteration < 1
                or request.metadata.get('harness_step') is not None
                or request.metadata.get('evaluation_policy_id') != VERSION
                or any(k in request.metadata for k in (duty.MARKER, direct.MARKER, 'review_phase', MARKER))):
            raise ValueError('natural_duty_generation_identity')
        return 'generation'
    marker = request.metadata.get(duty.MARKER, {})
    if not isinstance(marker, dict):
        raise ValueError('natural_duty_review_identity')
    if (request.metadata.get(MARKER) != VERSION or request.metadata.get(direct.MARKER) != direct.VERSION
            or dict(marker) != dict(version=duty.VERSION, duty=marker.get('duty'), stage=marker.get('stage'))
            or marker.get('duty') not in duty.DUTIES or marker.get('stage') not in duty.STAGES
            or request.metadata.get('harness_step') != 'evaluate'
            or len(request.tools) != 1 or request.tools[0].name != 'submit_report_review'):
        raise ValueError('natural_duty_review_identity')
    return 'review'


def request_identity(request):
    return 'zhipu', 'glm-5.3-flash' if role_for_request(request) == 'generation' else 'glm-5.3'


def request_bytes(request, *, transport_id=None):
    role = role_for_request(request)
    if transport_id not in (None, VERSION + ':' + role):
        raise ValueError('natural_duty_transport_identity')
    if (not math.isfinite(request.timeout_s) or not 0 < request.timeout_s <= 300
            or request.max_tokens != 32768 or request.temperature != 1.0 or request.top_p != .95
            or estimate_runtime_request_input_ceiling(request) > 64000):
        raise ValueError('natural_duty_request_budget')
    raw = json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('natural_duty_request_size')
    return raw


def request_sha(request):
    return hashlib.sha256(request_bytes(request)).hexdigest()


class NaturalDutyContract(RoleCoachExecutionContract):
    @property
    def request_policy(self):
        return policy()

    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, version=self.version, model=MODEL, thinking_profile_id=PROFILE,
            max_calls=6, total_tokens=401920, execution_timeout_s=900, request_timeout_s=300,
            skill_version='0.7.0', program_version='4.0.0', evaluation_contract_version='4.0.0',
            inference_policy_id=VERSION, evaluation_repair_policy='none',
            revision_policy='reviewer-authored-exact-patches', qualification_only=True,
            publication_policy='always-reject-unqualified-candidate',
            stream_transport_id=VERSION, target_runtime_profile_id=PROFILE)
        value['roles'] = {k:dict(v, transport_id=VERSION+':'+k, request_timeout_s=300)
                          for k,v in value['roles'].items() if k != 'revision'}
        return value

    def snapshot(self):
        return CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    request_identity = staticmethod(request_identity)

    def require_provider(self, provider):
        if (provider.provider_name != 'zhipu' or provider.model_name != MODEL
                or getattr(provider, 'thinking_profile_id', None) != PROFILE
                or type(getattr(provider, 'sdk_max_retries', None)) is not int or provider.sdk_max_retries != 0
                or getattr(provider, 'runtime_profile', None) is not None):
            raise ValueError('natural_duty_provider_identity')


CONTRACT = NaturalDutyContract(version='1.6.0')


class NaturalDutyProvider(RoleRoutedProvider):
    model_name, thinking_profile_id = MODEL, PROFILE
    role_for_request = staticmethod(role_for_request)
    validate_request = staticmethod(request_bytes)

    def __init__(self, generator, reviewer, *, source_projection=None):
        from app.evaluation.golden_coarse_source_projection import VERSION as coarse
        from app.evaluation.golden_explicit_source_projection import VERSION as explicit
        if source_projection not in (None, coarse, explicit):
            raise ValueError('natural_duty_source_projection')
        self.source_projection = explicit if source_projection is None else source_projection
        self.require_selected_provider(generator, 'generation')
        self.require_selected_provider(reviewer, 'review')
        if generator is reviewer or generator.capabilities != reviewer.capabilities:
            raise ValueError('natural_duty_provider_composition')
        self.generator, self.reviewer = generator, reviewer
        self.capabilities = generator.capabilities
        self.last_exchange, self.attempts = None, []
        self._calls, self._failed = 0, False

    def require_selected_provider(self, provider, role):
        from app.runtime.reviewer_roles import profile_for_role
        if role not in ('generation', 'review'):
            raise ValueError('natural_duty_provider_role')
        profile = profile_for_role(role)
        if (provider.provider_name != 'zhipu' or provider.model_name != profile.model
                or getattr(provider, 'thinking_profile_id', None) != profile.profile_id
                or type(getattr(provider, 'sdk_max_retries', None)) is not int
                or provider.sdk_max_retries != 0 or getattr(provider, 'runtime_profile', None) is not None
                or getattr(provider, 'transport_id', self.transport_for_role(role)) != self.transport_for_role(role)):
            raise ValueError('natural_duty_child_identity')

    def transport_for_role(self, role):
        return VERSION+':'+role

    def chat(self, request):
        budget = getattr(self, 'candidate_budget', None)
        if budget is not None:
            # The observer's pre-send guard may perform disk/CI checks after
            # CoachBudgetedProvider calculated its original remaining time.
            remaining = budget.contract.descriptor()['execution_timeout_s'] - (budget.clock()-budget.started)
            if remaining <= 0:
                from app.providers.errors import ProviderResponseError
                self._failed = True
                raise ProviderResponseError(provider='zhipu', code='timeout')
            request = replace(request, timeout_s=min(request.timeout_s, remaining))
        return super().chat(request)


def component_fingerprints(skill):
    from app.runtime.role_coach_contract import component_fingerprints as base
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    paths = ('app/evaluation/natural_duty_contract.py', 'app/evaluation/natural_duty_workflow.py',
        'app/product/natural_duty_candidate.py', 'scripts/review_duty_direct_patch.py',
        'scripts/review_duty_composition.py', 'scripts/prepare_review_duty_probe.py',
        'scripts/report_timed_document_workflow.py', 'scripts/report_contrast_review.py',
        'scripts/report_document_view.py', 'scripts/report_document_workflow.py',
        'app/evaluation/source_patch_editor.py', 'app/runtime/dispatch_runtime.py',
        'app/runtime/dispatch_control.py', 'app/runtime/natural_duty_provider_factory.py')
    rows = {r.component_id:r for r in base(skill)}
    for path in paths:
        key = path.replace('/', '.').replace('.py', '')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
