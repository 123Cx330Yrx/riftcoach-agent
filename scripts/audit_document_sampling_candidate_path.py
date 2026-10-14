"""Offline isolated candidate path for a review-only temperature variant.

This is a local protocol witness, not a production identity. It rebuilds the
existing full-source initial/revision/fresh requests, gives review turns an
explicit candidate marker and temperature, and runs five synthetic calls with
real request validation and receipt binding. No network client, credential,
Provider response, usage receipt, or product registration is created.
"""
from dataclasses import replace
import hashlib
import json
import time
from pathlib import Path

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.glm53_bounded_revision_budget_reachability import (
    estimate_runtime_request_input_ceiling,
)
from app.evaluation.golden_stream_bridge import _mapping, MAX_BYTES, validate_request
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse, TokenUsage, ChatRequest, ChatMessage, MessageRole
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from scripts.report_block_keyed_editor import edit_request
from scripts.report_timed_document_workflow import TimedDocumentWorkflow
from app.evaluation.source_patch_editor import report_inputs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/evaluation/results/document_sampling_candidate_path_audit_20261011.json'
CANDIDATE_MARKER = 'document-review-sampling-temperature-02-v1'
CANDIDATE_TEMPERATURE = 0.2
MAX_CALLS = 5
TOTAL_TOKENS = 401920
ACTIVE_TIMEOUT_S = 900


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def candidate_review_request(request):
    if timing.role_for_request(request) != 'review':
        raise ValueError('candidate_review_role_required')
    return replace(request, temperature=CANDIDATE_TEMPERATURE,
                   metadata={**request.metadata, timing.METADATA: CANDIDATE_MARKER})


def candidate_role(request):
    marker = request.metadata.get(timing.METADATA)
    if marker == CANDIDATE_MARKER:
        projected = replace(request, temperature=1.0,
            metadata={**request.metadata, timing.METADATA: timing.TIMED_MARKER})
        if timing.role_for_request(projected) != 'review':
            raise ValueError('candidate_review_projection')
        if request.temperature != CANDIDATE_TEMPERATURE:
            raise ValueError('candidate_review_temperature')
        return 'review'
    return timing.role_for_request(request)


def candidate_request_bytes(request):
    role = candidate_role(request)
    if role == 'review':
        # The baseline projection validates complete policy/schema/source identity;
        # the candidate marker then permits exactly one isolated model variable.
        projected = replace(request, temperature=1.0,
            metadata={**request.metadata, timing.METADATA: timing.TIMED_MARKER})
        timing.request_bytes(projected)
    else:
        timing.request_bytes(request)
    from app.evaluation.glm53_bounded_revision_budget_reachability import (
        estimate_runtime_request_input_ceiling,
    )
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError('candidate_request_input_budget')
    raw = json.dumps(request, default=_mapping, ensure_ascii=False,
                     allow_nan=False).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('candidate_request_size')
    return raw


class SyntheticCandidateProvider:
    """Local provider-shaped object; chat only creates synthetic responses."""

    provider_name = 'zhipu'
    thinking_profile_id = 'glm53-high-candidate-local-witness'
    sdk_max_retries = 0
    runtime_profile = None
    capabilities = frozenset({'stream', 'tools'})
    request_timing_identity = timing.TIMED_IDENTITY
    last_exchange = None

    def __init__(self):
        self.calls = []

    def chat(self, request):
        role = candidate_role(request)
        model = 'glm-5.3' if role == 'review' else 'glm-5.3-flash'
        raw = candidate_request_bytes(request)
        response = ChatResponse(content='Synthetic local response; no business result',
            provider='zhipu', model=model, finish_reason='stop',
            usage=TokenUsage(input_tokens=10, output_tokens=20))
        self.calls.append(dict(role=role, request=request, raw=raw,
                               model=model, temperature=request.temperature))
        self.last_exchange = Exchange(request, response, sha(raw))
        return response


class SamplingCandidateBudget(CoachBudgetedProvider):
    """Shared five-call budget with candidate review normalization only."""

    def __init__(self, provider, *, clock=None):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name if hasattr(provider, 'model_name') else 'glm-5.3'
        self.capabilities = provider.capabilities
        self.thinking_profile_id = provider.thinking_profile_id
        self.sdk_max_retries = provider.sdk_max_retries
        self.runtime_profile = provider.runtime_profile
        self.clock = clock or time.monotonic
        self.started = self.clock()
        self.calls = self.tokens = self.reserved_tokens = 0
        self.stopped = False
        self.last_exchange = None
        self.observed = []

    def _fail(self, code):
        self.stopped = True
        raise ProviderResponseError(provider='zhipu', code=code)

    def chat(self, request):
        if self.stopped or self.calls >= MAX_CALLS:
            self._fail('external_call_budget_exhausted')
        if self.clock() - self.started >= ACTIVE_TIMEOUT_S:
            self._fail('timeout')
        baseline_role = timing.role_for_request(request)
        effective = candidate_review_request(request) if baseline_role == 'review' else request
        raw = candidate_request_bytes(effective)
        ceiling = estimate_runtime_request_input_ceiling(effective)
        reservation = ceiling + effective.max_tokens
        if self.tokens + self.reserved_tokens + reservation > TOTAL_TOKENS:
            self._fail('token_budget_exhausted')
        self.calls += 1
        self.reserved_tokens += reservation
        try:
            response = self.provider.chat(effective)
            exchange = self.provider.last_exchange
            if (not isinstance(exchange, Exchange) or exchange.response is not response
                    or exchange.issued_request != effective
                    or exchange.receipt_request_sha256 != sha(raw)):
                self._fail('candidate_receipt_binding')
            if (response.provider, response.model) != (
                    'zhipu', 'glm-5.3' if baseline_role == 'review' else 'glm-5.3-flash'):
                self._fail('candidate_response_identity')
            self.tokens += response.usage.input_tokens + response.usage.output_tokens
            self.reserved_tokens -= reservation
            if response.usage.input_tokens > ceiling or response.usage.output_tokens > effective.max_tokens:
                self._fail('candidate_token_envelope')
            self.last_exchange = exchange
            self.observed.append(dict(baseline_role=baseline_role,
                effective_role=candidate_role(effective), temperature=effective.temperature,
                request_sha256=sha(raw), receipt_request_sha256=exchange.receipt_request_sha256,
                provider_model=response.model))
            return response
        except BaseException:
            self.stopped = True
            raise


def _generation_request(ordinal):
    request = ChatRequest(messages=(ChatMessage(MessageRole.USER, 'Synthetic local generation'),),
        max_tokens=32768, timeout_s=300, temperature=1.0, top_p=.95,
        metadata={'agent_loop_iteration': ordinal})
    return timing.prepare_request(request)


def audit():
    # Reuse the complete existing workflow fixture only as local source material.
    from tests.test_coarse_revision_editor import cases, BEFORE, AFTER

    original, inputs, accepted, _ = cases()['claim-scope:4']
    initial = TimedDocumentWorkflow.make_request(inputs)
    revision = TimedDocumentWorkflow.edit_request(inputs, accepted)
    edited_report = original.report.replace(BEFORE, AFTER)
    if edited_report == original.report:
        raise ValueError('candidate_edit_fixture_not_changed')
    final_inputs = report_inputs(inputs, edited_report)
    fresh = TimedDocumentWorkflow.make_request(final_inputs)
    sequence = [_generation_request(1), _generation_request(2), initial, revision, fresh]
    provider = SyntheticCandidateProvider()
    budget = SamplingCandidateBudget(provider, clock=lambda: 0.0)
    sender = SharedBudgetReviewSender(budget)
    for request in sequence:
        sender(request)
    if [x['baseline_role'] for x in budget.observed] != [
            'generation', 'generation', 'review', 'revision', 'review']:
        raise ValueError('candidate_role_sequence')
    observed_temps = [x['temperature'] for x in budget.observed]
    if observed_temps != [1.0, 1.0, .2, 1.0, .2]:
        raise ValueError('candidate_temperature_scope')
    if budget.calls != 5 or budget.tokens != 150 or budget.reserved_tokens != 0:
        raise ValueError('candidate_budget_accounting')
    if any(x['request_sha256'] != x['receipt_request_sha256'] for x in budget.observed):
        raise ValueError('candidate_receipt_digest')
    if provider.calls[2]['request'].messages != initial.messages or provider.calls[4]['request'].messages != fresh.messages:
        raise ValueError('candidate_review_messages_changed')
    if provider.calls[0]['request'].temperature != 1.0 or provider.calls[1]['request'].temperature != 1.0:
        raise ValueError('candidate_generation_temperature_changed')
    if provider.calls[3]['request'].temperature != 1.0:
        raise ValueError('candidate_revision_temperature_changed')
    result = dict(kind='document-sampling-candidate-path-offline-audit-v1',
        candidate_marker=CANDIDATE_MARKER, candidate_temperature=CANDIDATE_TEMPERATURE,
        source_case='claim-scope:4', source_report_sha256=sha(original.report.encode()),
        edited_report_sha256=sha(edited_report.encode()),
        sequence=[dict(ordinal=i + 1, **row) for i, row in enumerate(budget.observed)],
        generation_and_revision_temperature=1.0, review_temperatures=[.2, .2],
        calls=budget.calls, synthetic_provider_invocations=len(provider.calls),
        input_tokens=50, output_tokens=100, known_tokens=150,
        reserved_tokens=budget.reserved_tokens, shared_max_calls=MAX_CALLS,
        shared_total_tokens=TOTAL_TOKENS, shared_active_timeout_s=ACTIVE_TIMEOUT_S,
        receipt_bound=True, network_client_constructed=False, credential_reads=0,
        production_admitted=False, execution_ready=False, new_qualification=0,
        business_review=False, fresh_request_rebuilt=True,
        candidate_identity_explicit=True,
        limitation='One local synthetic full lifecycle proves request/ledger/identity/receipt '
                   'coherence only. It does not test Provider acceptance, decoding behavior, '
                   'semantic quality, stability, or paid authorization. The production identity '
                   'and default budget remain unchanged; this candidate is not runnable.')
    return result


if __name__ == '__main__':
    value = audit()
    from app.evaluation.golden_journal import write_new_json
    write_new_json(OUTPUT, value)
    print(json.dumps(dict(calls=value['calls'], observed_temps=[x['temperature'] for x in value['sequence']],
                          provider_calls=0, artifact_sha256=sha(OUTPUT.read_bytes()))))
