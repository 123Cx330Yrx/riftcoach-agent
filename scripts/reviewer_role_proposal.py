"""Unregistered role-composition prototype; no credentials or live entry point.

Reuses the product budget algorithm and review state machine. It deliberately
does not satisfy the product's single-model descriptor. Runtime observation,
pricing and qualification must be integrated before any product registration.
"""
import hashlib
from app.evaluation import golden_native_partitioned_tool_review as partitioned
from app.evaluation.golden_explicit_source_projection import VERSION, OLD_ADDRESS, NEW_ADDRESS, project_request
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT

PROPOSAL_ID = 'flash-generation-glm53-review-proposal-v1'


class ProposedRoleBudget(CoachBudgetedProvider):
    """One task ledger, explicit destinations, no model fallback."""
    def __init__(self, generator, reviewer, **kwargs):
        super().__init__(generator, coach_contract=NATIVE_COACH_CONTRACT, **kwargs)
        self.reviewer = reviewer
        self._require_reviewer()
        # Refuse accidental admission through a legacy single-model factory.
        self.model_name = PROPOSAL_ID
        self.last_exchange = None
        self.attempts = []
        self._selected = None

    def _require_reviewer(self):
        p = self.reviewer
        profile = ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
        if (p.provider_name != 'zhipu' or p.model_name != profile.model
                or p.thinking_profile_id != profile.profile_id
                or type(p.sdk_max_retries) is not int or p.sdk_max_retries != 0
                or getattr(p, 'runtime_profile', None) is not None):
            raise ValueError('proposed_reviewer_identity_mismatch')

    def _provider_for_request(self, request):
        phase = request.metadata.get('review_phase')
        iteration = request.metadata.get('agent_loop_iteration')
        if iteration is not None and phase is None:
            if type(iteration) is not int or iteration < 1:
                raise ValueError('proposed_role_phase_invalid')
            self.contract.require_provider(self.provider)
            selected, role = self.provider, 'generation'
        elif iteration is None and phase in (
                'native_business_review', 'native_business_reassessment', 'native_business_revision'):
            if request.metadata.get('source_projection') != VERSION:
                raise ValueError('proposed_source_projection_required')
            if phase == 'native_business_revision':
                self.contract.require_provider(self.provider)
                selected, role = self.provider, 'revision'
            else:
                self._require_reviewer()
                selected, role = self.reviewer, 'review'
        else:
            raise ValueError('proposed_role_phase_invalid')
        self._selected = selected
        self._previous_exchange = getattr(selected, 'last_exchange', None)
        self.attempts.append(dict(ordinal=self.calls + 1, role=role,
            phase=phase or 'generation', model=selected.model_name,
            profile=selected.thinking_profile_id, status='started',
            request_sha256=hashlib.sha256(validate_request(
                request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()))
        return selected

    def chat(self, request):
        self.last_exchange = None
        count = len(self.attempts)
        try:
            response = super().chat(request)
            self.attempts[-1].update(input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens)
            exchange = getattr(self._selected, 'last_exchange', None)
            if (not isinstance(exchange, Exchange) or exchange is self._previous_exchange
                    or exchange.response is not response
                    or exchange.receipt_request_sha256 != self.attempts[-1]['request_sha256']
                    or hashlib.sha256(validate_request(exchange.issued_request,
                        transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
                       != self.attempts[-1]['request_sha256']):
                self._fail('proposed_fresh_receipt_required')
            self.last_exchange = exchange
            self.attempts[-1].update(status='completed')
            return response
        except Exception as error:
            self.stopped = True
            if len(self.attempts) > count:
                self.attempts[-1].update(status='failed', error=getattr(error, 'code', str(error)))
            raise


class ProposedReviewWorkflow(partitioned.NativeBusinessReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        return project_request(partitioned.request(inputs, **kwargs), inputs)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = partitioned.validate(raw, inputs, previous_raw=previous_raw)
        # The validator is unchanged; the sent policy contains the explicit-ID
        # clause. Preserve both identities instead of labeling the old hash live.
        journal = dict(journal, validator_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(partitioned._review_policy(previous_raw).replace(OLD_ADDRESS, NEW_ADDRESS)),
            source_projection=VERSION)
        return payload, wire, journal
