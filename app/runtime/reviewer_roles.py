"""Explicit opt-in model roles; one router below the existing task budget.

This module owns identity and routing, not admission or another budget. Actual
responses retain the selected model; the composite ID only names the run plan.
"""
import hashlib

from app.evaluation.golden_explicit_source_projection import VERSION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse
from app.providers.zhipu_profiles import (ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE,
    ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE)

ROLE_COMPOSITION_ID = "flash-generation-glm53-review-v1"
ROLE_PROFILE_ID = "flash-generation-glm53-review-high-v1"


def role_for_request(request):
    phase = request.metadata.get("review_phase")
    iteration = request.metadata.get("agent_loop_iteration")
    step = request.metadata.get("harness_step")
    if phase is None and type(iteration) is int and iteration >= 1 and step is None:
        return "generation"
    if iteration is None and phase in ("native_business_review", "native_business_reassessment", "native_business_revision"):
        if request.metadata.get("source_projection") != VERSION:
            raise ValueError("role_source_projection_required")
        steps = {
            "native_business_review": ("evaluate",),
            "native_business_reassessment": ("evaluate", "evaluate_repair"),
            "native_business_revision": ("revise",),
        }
        if step not in steps[phase]:
            raise ValueError("role_phase_invalid")
        return "revision" if phase == "native_business_revision" else "review"
    raise ValueError("role_phase_invalid")


def profile_for_role(role):
    if role not in ("generation", "revision", "review"):
        raise ValueError("role_phase_invalid")
    return ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE if role == "review" else ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE


def transport_for_role(role):
    profile_for_role(role)
    return REVIEW_MODEL_TRANSPORT_ID if role == "review" else CAPACITY_TRANSPORT_ID


def request_identity(request):
    return "zhipu", profile_for_role(role_for_request(request)).model


def role_descriptor():
    return {role: {"provider": "zhipu", "model": profile_for_role(role).model,
        "thinking_profile_id": profile_for_role(role).profile_id,
        "request_extra_body": profile_for_role(role).extra_body(),
        "transport_id": transport_for_role(role), "sdk_max_retries": 0}
        for role in ("generation", "revision", "review")}


def require_role_provider(provider, role):
    profile = profile_for_role(role)
    if (provider.provider_name != "zhipu" or provider.model_name != profile.model
            or getattr(provider, "thinking_profile_id", None) != profile.profile_id
            or type(getattr(provider, "sdk_max_retries", None)) is not int
            or provider.sdk_max_retries != 0 or getattr(provider, "runtime_profile", None) is not None
            or getattr(provider, "transport_id", transport_for_role(role)) != transport_for_role(role)):
        raise ValueError("role_provider_identity_mismatch")


class RoleRoutedProvider:
    provider_name = "zhipu"
    model_name = ROLE_COMPOSITION_ID
    thinking_profile_id = ROLE_PROFILE_ID
    sdk_max_retries = 0
    runtime_profile = None

    def __init__(self, generator, reviewer):
        require_role_provider(generator, "generation")
        require_role_provider(reviewer, "review")
        if generator is reviewer or generator.capabilities != reviewer.capabilities:
            raise ValueError("role_provider_composition_mismatch")
        self.generator, self.reviewer = generator, reviewer
        self.capabilities = generator.capabilities
        self.last_exchange = None
        self.attempts = []
        self._calls = 0
        self._failed = False

    @staticmethod
    def request_identity(request):
        return request_identity(request)

    def chat(self, request):
        self.last_exchange = None
        if self._failed:
            raise ProviderResponseError(provider=self.provider_name, code="role_run_stopped")
        response = None
        attempt = None
        try:
            role = role_for_request(request)
            selected = self.reviewer if role == "review" else self.generator
            require_role_provider(selected, role)
            transport = transport_for_role(role)
            expected_identity = request_identity(request)
            raw = validate_request(request, transport_id=transport)
            previous = getattr(selected, "last_exchange", None)
            self._calls += 1
            attempt = dict(ordinal=self._calls, role=role,
                phase=request.metadata.get("review_phase", "generation"),
                model=expected_identity[1], profile=selected.thinking_profile_id,
                transport_id=transport, request_sha256=hashlib.sha256(raw).hexdigest(), status="started")
            self.attempts.append(attempt)
            send = getattr(selected, "chat_at_ordinal", None)
            response = (send(request, ordinal=self._calls, role=role) if callable(send) else selected.chat(request))
            if not isinstance(response, ChatResponse) or (response.provider, response.model) != expected_identity:
                raise ProviderResponseError(provider=self.provider_name, code="role_response_identity_mismatch")
            attempt.update(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
            exchange = getattr(selected, "last_exchange", None)
            if (not isinstance(exchange, Exchange) or exchange is previous or exchange.response is not response
                    or exchange.receipt_request_sha256 != attempt["request_sha256"]
                    or hashlib.sha256(validate_request(exchange.issued_request, transport_id=transport)).hexdigest() != attempt["request_sha256"]):
                raise ProviderResponseError(provider=self.provider_name, code="role_fresh_receipt_required")
            self.last_exchange = exchange
            attempt["status"] = "completed"
            return response
        except BaseException as error:
            self._failed = True
            if attempt is not None:
                attempt.update(status="failed", error=getattr(error, "code", type(error).__name__))
            if isinstance(response, ChatResponse) and isinstance(error, ProviderResponseError):
                error.observed_response = response
                error.observed_usage = response.usage
            raise
