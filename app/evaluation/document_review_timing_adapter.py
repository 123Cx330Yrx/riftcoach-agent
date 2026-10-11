"""Full-request timing candidate reusing the existing task budget.

Classification projects onto the legacy protocol only. Actual timed issued
bytes and receipt digests retain the new identity. SDK/process admission is
available only by explicit candidate opt-in; default product admission is closed.
"""
from dataclasses import dataclass, replace
import hashlib
import json
import math
import time

from app.providers.models import ChatRequest
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT

LEGACY_IDENTITY = "document-review-request-identity-v1"
TIMED_IDENTITY = "document-review-request-identity-time600-v1"
TIMED_MARKER = "document-review-time-600-v1"
METADATA = "document_review_timing"
TASK_TIMEOUT_S = 900
FLASH_TIMEOUT_S = 300
GLM_REVIEW_TIMEOUT_S = 600


def _number(value, code):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(code)
    return value


def allowed_timeout(role, *, identity=TIMED_IDENTITY):
    if role not in ("generation", "revision", "review"):
        raise ValueError("document_review_role")
    if identity not in (LEGACY_IDENTITY, TIMED_IDENTITY):
        raise ValueError("unknown_document_review_timing_identity")
    return GLM_REVIEW_TIMEOUT_S if identity == TIMED_IDENTITY and role == "review" else FLASH_TIMEOUT_S


@dataclass(frozen=True)
class TimingRequest:
    """Pure arithmetic only; not an owned clock or a full request identity."""
    identity: str
    role: str
    timeout_s: float
    task_elapsed_s: float
    timing_marker: str | None = None


def validate(request):
    cap = allowed_timeout(request.role, identity=request.identity)
    if request.identity == LEGACY_IDENTITY and request.timing_marker is not None:
        raise ValueError("legacy_request_has_timing_marker")
    if request.identity == TIMED_IDENTITY and request.timing_marker != TIMED_MARKER:
        raise ValueError("timed_request_missing_timing_marker")
    elapsed = _number(request.task_elapsed_s, "document_review_task_timeout")
    timeout = _number(request.timeout_s, "document_review_request_timeout")
    if not 0 <= elapsed < TASK_TIMEOUT_S:
        raise ValueError("document_review_task_timeout")
    if not 0 < timeout <= cap:
        raise ValueError("document_review_request_timeout")
    return min(timeout, TASK_TIMEOUT_S - elapsed)


def reject_cross_identity(*, identity, timing_marker):
    """Compatibility helper; validates metadata rather than a fabricated request."""
    if identity == LEGACY_IDENTITY:
        if timing_marker is not None:
            raise ValueError("legacy_request_has_timing_marker")
    elif identity == TIMED_IDENTITY:
        if timing_marker != TIMED_MARKER:
            raise ValueError("timed_request_missing_timing_marker")
    else:
        raise ValueError("unknown_document_review_timing_identity")


def _classify(request):
    from scripts.report_contrast_review import request_identity as classify
    from app.evaluation.document_review_identity import role_for_request as legacy_role
    from scripts.report_contrast_review import baseline_request, METADATA as TEACHING
    classify(request)
    return legacy_role(baseline_request(request) if TEACHING in request.metadata else request)


def role_for_request(request):
    """Validate complete policy/schema/role; projection is classification only.

    Never use the projected request for transport, SHA or old delivery proof.
    """
    if not isinstance(request, ChatRequest) or request.metadata.get(METADATA) != TIMED_MARKER:
        raise ValueError("timed_request_missing_timing_marker")
    timeout = _number(request.timeout_s, "document_review_request_timeout")
    metadata = dict(request.metadata)
    del metadata[METADATA]
    projected = replace(request, metadata=metadata, timeout_s=min(timeout, 300))
    role = _classify(projected)
    if not 0 < timeout <= allowed_timeout(role):
        raise ValueError("document_review_request_timeout")
    if (request.max_tokens != 32768 or request.temperature != 1.0 or request.top_p != .95
            or "task_elapsed_s" in request.metadata):
        raise ValueError("timed_request_contract")
    return role


def prepare_request(request):
    """Upgrade a valid original/contrast request without changing its content."""
    if METADATA in request.metadata:
        raise ValueError("timed_request_already_marked")
    role = _classify(request)
    candidate = replace(request, timeout_s=allowed_timeout(role),
                        metadata={**request.metadata, METADATA: TIMED_MARKER})
    role_for_request(candidate)
    return candidate


def request_identity(request):
    from app.runtime.reviewer_roles import profile_for_role
    return "zhipu", profile_for_role(role_for_request(request)).model


def request_bytes(request):
    """Exact candidate bytes; not a legacy transport validation receipt."""
    from app.evaluation.golden_stream_bridge import _mapping, MAX_BYTES
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    role_for_request(request)
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError("timed_request_input_budget")
    raw = json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("timed_request_size")
    return raw


class _TimedLimits:
    """Private candidate limits; not registered as a production Coach contract."""
    grounded = True
    request_identity = staticmethod(request_identity)

    def descriptor(self):
        from app.evaluation.golden_stream_bridge import (
            TIMED_REVIEW_TRANSPORT_ID, TIMED_FLASH_TRANSPORT_ID, transport_request_policy)
        base = DOCUMENT_REVIEW_COACH_CONTRACT.descriptor()
        roles = {role: dict(value, transport_id=(TIMED_REVIEW_TRANSPORT_ID if role == "review" else TIMED_FLASH_TRANSPORT_ID),
                            request_timeout_s=allowed_timeout(role)) for role, value in base["roles"].items()}
        policies = {role: transport_request_policy(value["transport_id"]).metadata()
                    for role, value in roles.items()}
        # Do not serialize the old uniform330 policy as the candidate's SDK
        # policy. The existing Agent prefix policy remains a separate limit.
        return dict(base, request_timeout_s=600, roles=roles, request_policy=policies,
                    request_policy_id="document-review-time600-per-role-v1",
                    request_timing_identity=TIMED_IDENTITY, base_contract_version=base["version"],
                    execution_ready=False)


class TimedDocumentBudget(CoachBudgetedProvider):
    """One budget shared by generation, review, edit and fresh.

    Constructor validates the provider contract and explicit candidate marker.
    Limits are installed here, never patched onto a legacy budget by a caller.
    """
    def __init__(self, provider, *, clock=time.monotonic):
        if getattr(provider, "request_timing_identity", None) != TIMED_IDENTITY:
            raise ValueError("timed_provider_identity")
        super().__init__(provider, clock=clock, coach_contract=DOCUMENT_REVIEW_COACH_CONTRACT)
        _number(self.started, "timed_clock_invalid")
        self._last_clock = self.started
        self._source_clock = clock
        self.clock = self._checked_clock
        self.contract = _TimedLimits()
        self._exchange = None

    def _checked_clock(self):
        current = _number(self._source_clock(), "timed_clock_invalid")
        if current < self._last_clock:
            self._fail("timed_clock_regressed")
        self._last_clock = current
        return current

    @property
    def last_exchange(self):
        return None if self.stopped else self._exchange

    def _provider_for_request(self, request):
        # Capture the exact post-budget bytes before delegation. Receipt checks
        # may not trust a provider-selected timeout or input projection.
        self._issued = request
        return super()._provider_for_request(request)

    def chat(self, request):
        from app.evaluation.golden_integrated_runtime import Exchange
        self._exchange = None
        if self.stopped:
            self._fail("external_call_budget_exhausted")
        try:
            role_for_request(request)
            request_bytes(request)
            previous = getattr(self.provider, "last_exchange", None)
            response = super().chat(request)
            exchange = getattr(self.provider, "last_exchange", None)
            if not isinstance(exchange, Exchange) or exchange is previous or exchange.response is not response:
                self._fail("integrated_fresh_transport_receipt_required")
            if (exchange.issued_request != self._issued
                    or exchange.receipt_request_sha256 != hashlib.sha256(request_bytes(self._issued)).hexdigest()):
                self._fail("timed_receipt_binding")
            self._exchange = exchange
            return response
        except BaseException:
            self.stopped = True
            raise

