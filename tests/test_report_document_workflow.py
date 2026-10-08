"""Offline endpoint injection, real Agent/Harness/budget/storage; no live quality claim."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.product.native_coach_composition import _build_coach_application, BOUNDARY_EXAMPLES_ASSETS
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT
from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID, role_for_request
from app.runtime.store import RuntimeTraceStore
from scripts import report_document_view as view
from scripts.report_document_workflow import DocumentReviewWorkflow, request_sha
from scripts.native_contract_options import body
from tests.test_coarse_revision_editor import BEFORE, AFTER, cases
from tests.test_native_editor_product_budget import SummaryBuilder, offline
from tests.test_review_bound_coach_application import Responses
from tests.test_role_coach_application import run


def data_for(request):
    if request.metadata.get('report_presentation') == view.VERSION:
        assert len(request.messages) == 4
        return json.loads(request.messages[2].content.split('[UNTRUSTED DATA]\n', 1)[1]
                          .rsplit('\n[END UNTRUSTED DATA]', 1)[0])
    return body(request)


class DocumentResponses(Responses):
    review_data = staticmethod(data_for)

    def chat(self, request):
        response = super().chat(request)
        if request.metadata.get('report_presentation') == view.VERSION:
            if self.mode == 'initial_pass':
                value = dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[])
            elif self.mode == 'fresh_invalid' and self.review_calls > 1:
                value = dict(response.tool_calls[0].arguments, score='95')
            else:
                return response
            response = replace(response, tool_calls=(replace(response.tool_calls[0], arguments=value),))
            self.last_exchange = Exchange(request, response, request_sha(request))
        return response


class ScriptedRoles:
    """Test endpoint only. It does NOT extend the production role router."""
    provider_name = 'zhipu'
    model_name = ROLE_COMPOSITION_ID
    thinking_profile_id = ROLE_PROFILE_ID
    runtime_profile = None
    sdk_max_retries = 0
    source_projection = PROJECTION

    def __init__(self, mode, ceiling):
        self.generator = DocumentResponses(mode=mode, ceiling=ceiling)
        self.reviewer = DocumentResponses(mode=mode, ceiling=ceiling)
        self.reviewer.model_name = 'glm-5.3'
        self.capabilities = self.generator.capabilities
        self.last_exchange = None
        self.attempts = []

    @staticmethod
    def role(request):
        if request.metadata.get('report_presentation') == view.VERSION:
            assert request.metadata['review_phase'] in ('native_business_review', 'native_business_reassessment')
            assert len(request.messages) == 4
            return 'review'
        return role_for_request(request, source_projection=PROJECTION)

    def request_identity(self, request):
        return 'zhipu', 'glm-5.3' if self.role(request) == 'review' else 'glm-5.3-flash'

    def chat(self, request):
        self.last_exchange = None
        role = self.role(request)
        endpoint = self.reviewer if role == 'review' else self.generator
        response = endpoint.chat(request)  # The four-message request itself reaches the stub.
        self.last_exchange = endpoint.last_exchange
        assert self.last_exchange.issued_request is request
        self.attempts.append(dict(role=role, request_sha256=request_sha(request),
            input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))
        return response


class ScriptedBudgetIdentity:
    """Only this test's run instances: keep limits, substitute identity lookup.

    The production contract also rejects four-message reviews, independently of
    its router, in both the budget and observation layer. This adapter is not a
    registered contract. No global contract or budget method is patched.
    """
    def __init__(self, base):
        self.base = base

    def __getattr__(self, name):
        return getattr(self.base, name)

    @staticmethod
    def request_identity(request):
        return 'zhipu', 'glm-5.3' if ScriptedRoles.role(request) == 'review' else 'glm-5.3-flash'


def application(tmp_path, mode, ceiling):
    class Factory:
        def __init__(self):
            self.descriptor = ScriptedRoles(mode, ceiling)
            self.created = {}

        def __call__(self, run_id):
            self.created[run_id] = ScriptedRoles(mode, ceiling)
            return self.created[run_id]

    factory, flows = Factory(), []

    class Capture(DocumentReviewWorkflow):
        def __init__(self, sender):
            self.exchanges, self.journals = [], []
            sender.provider.contract = ScriptedBudgetIdentity(sender.provider.contract)
            sender.provider.provider._request_identity = ScriptedBudgetIdentity.request_identity
            super().__init__(sender, record=lambda phase, exchange: self.exchanges.append((phase, exchange)))
            flows.append(self)

        def evaluate(self, request):
            result = super().evaluate(request)
            self.journals.append(deepcopy(self.last_journal))
            return result

    app = _build_coach_application(contract=BOUNDARY_EXAMPLES_COACH_CONTRACT,
        assets=BOUNDARY_EXAMPLES_ASSETS, workflow_type=Capture,
        summary_builder=SummaryBuilder(deepcopy(factory.descriptor.generator.req.player_summary)),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    return app, factory, flows


@pytest.mark.parametrize('mode,ceiling', [('success', False), ('success', True),
    ('bad_anchor', False), ('bad_fact', False), ('fresh_reject', False), ('recovery', False)])
def test_document_view_actual_application_chain(tmp_path, mode, ceiling):
    app, factory, flows = application(tmp_path, mode, ceiling)
    result = run(app, 'document_chain')
    endpoint, flow = factory.created['document_chain'], flows[0]
    budget = flow.send.provider
    success = mode == 'success'
    assert result.publication_status.value == ('published' if success else 'rejected'), result
    expected = ['generation', 'generation', 'review']
    expected += ['review', 'revision'] if mode == 'recovery' else ['revision'] + ([] if mode == 'bad_anchor' else ['review'])
    assert [a['role'] for a in endpoint.attempts] == expected
    assert budget.calls == len(expected)
    assert budget.tokens == sum(a['input_tokens'] + a['output_tokens'] for a in endpoint.attempts)
    assert len(flow.exchanges) == len(expected) - 2
    assert all(request_sha(e.issued_request) == e.receipt_request_sha256 for _, e in flow.exchanges)
    # Actual knowledge tool results enter both the report review and fresh.
    tools = [json.loads(m.content)['data'] for m in endpoint.generator.requests[1].messages if m.role.value == 'tool']
    assert len(tools) == 5 and all(p['chunks'] for p in tools)
    initial = data_for(endpoint.reviewer.requests[0])
    assert 'blocks' not in initial['source_index']
    assert initial['knowledge']['retrievals'] == [dict(provider=p['provider'], retrieved_at=p['retrieved_at'],
        chunk_ids=[c['chunk_id'] for c in p['chunks']]) for p in tools]
    assert all(len(r.messages) == 4 for r in endpoint.reviewer.requests)
    for journal in flow.journals:
        issued = next(e.issued_request for _, e in flow.exchanges if e.receipt_request_sha256 == journal['receipt_request_sha256'])
        assert journal['policy_sha256'] == digest(issued.messages[0].content)
        assert journal['policy_sha256'] != journal['base_policy_sha256']
        assert journal['issued_request_sha256'] == journal['receipt_request_sha256']
    trace = RuntimeTraceStore(tmp_path, 'document_chain').read_trace(result.trace_reference)
    receipt = FileRunReceiptStore(tmp_path).read_receipt('document_chain')
    assert trace.usage.provider_calls_attempted == trace.usage.provider_responses_observed == len(expected)
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens
    assert receipt.report_available is success
    assert receipt.publication_status == result.publication_status
    assert receipt.trace_reference == result.trace_reference
    final_path = tmp_path/'document_chain/output/final_report.md'
    artifacts = [a for a in trace.artifacts if a.kind == 'final_report']
    if not success:
        assert not final_path.exists() and artifacts == []
        assert result.output is None or result.output.report is None
    if mode == 'bad_anchor':
        assert flow.stopped and flow.last_edit_journal is None
        return
    journal = flow.last_edit_journal
    assert not journal['semantic_approval'] and not journal['production_admitted']
    after = '辅助局视野分为999，故能保证今后获胜。' if mode == 'bad_fact' else AFTER
    exact = endpoint.generator.req.report.replace(BEFORE, after)
    assert journal['assembled_report'] == flow._expected_recheck.source.report == exact
    assert journal['final_review_request_sha256'] == request_sha(view.project(flow._expected_recheck))
    assert journal['baseline_final_review_request_sha256'] == request_sha(editor.Current.make_request(flow._expected_recheck))
    assert journal['baseline_final_review_request_sha256'] != journal['final_review_request_sha256']
    if mode == 'recovery':
        assert flow.stopped and budget.stopped and budget.last_exchange is None
        assert 'final_review_receipt_request_sha256' not in journal
        assert len(endpoint.reviewer.requests) == 2  # Budget forbids a sixth call.
        assert 'previous_review' in data_for(endpoint.reviewer.requests[1])
        return
    final = endpoint.reviewer.requests[-1]
    assert final.messages == view.project(flow._expected_recheck).messages
    assert not {'previous_review', 'previous_issues', 'accepted_review'} & data_for(final).keys()
    assert data_for(final)['knowledge'] == initial['knowledge']
    assert journal['final_review_issued_request_sha256'] == journal['final_review_receipt_request_sha256'] == request_sha(final)
    if success:
        assert result.output.report == exact and final_path.read_bytes() == exact.encode('utf-8')
        assert len(artifacts) == 1 and artifacts[0].sha256 == hashlib.sha256(final_path.read_bytes()).hexdigest()
        requests = endpoint.generator.requests + endpoint.reviewer.requests
        reservation = sum(size(r) + r.max_tokens for r in requests)
        assert reservation <= 401920
        if ceiling:
            assert budget.tokens == reservation
        print(dict(evidence='scripted_document_application_not_model_quality',
            calls=budget.calls, tokens=budget.tokens, reservation=reservation))
    else:
        assert flow.stopped


@pytest.mark.parametrize('fault', ['metadata', 'temperature', 'receipt', 'document', 'model'])
def test_review_exchange_identity_failure_is_terminal_and_recorded(fault):
    req, _, _, raw = cases()['claim-scope:4']
    from app.providers.models import ChatResponse, TokenUsage, ToolCall

    exchanges = []

    def send(request):
        issued = request
        if fault == 'metadata':
            issued = replace(issued, metadata={**issued.metadata, 'report_presentation': 'wrong'})
        elif fault == 'temperature':
            issued = replace(issued, temperature=0.5)
        elif fault == 'document':
            messages = list(issued.messages)
            messages[1] = replace(messages[1], content='old or unrelated report')
            issued = replace(issued, messages=tuple(messages))
        response = ChatResponse(content=None, tool_calls=(ToolCall('test', 'submit_report_review', json.loads(raw)),),
            provider='zhipu', model='glm-5.3-flash' if fault == 'model' else 'glm-5.3',
            finish_reason='tool_calls', usage=TokenUsage(10, 10))
        return Exchange(issued, response, '0' * 64 if fault == 'receipt' else request_sha(issued))

    flow = DocumentReviewWorkflow(send, record=lambda phase, e: exchanges.append(e))
    with pytest.raises(ValueError, match='document_view_exchange_identity|integrated_receipt_mismatch'):
        flow.evaluate(req)
    assert flow.stopped and flow.calls == 1 and len(exchanges) == 1
    with pytest.raises(ValueError, match='native_evaluation_order_invalid'):
        flow.evaluate(req)
    assert flow.calls == 1


def test_production_contract_independently_rejects_document_view():
    _, inputs, _, _ = cases()['claim-scope:4']
    with pytest.raises(ValueError, match='role_source_projection_payload_mismatch'):
        BOUNDARY_EXAMPLES_COACH_CONTRACT.request_identity(view.project(inputs))


@pytest.mark.parametrize('mode', ['initial_pass', 'fresh_invalid'])
def test_no_revision_when_initial_pass_and_no_sixth_call_on_bad_fresh(tmp_path, mode):
    app, factory, flows = application(tmp_path, mode, False)
    result = run(app, 'other_branches')
    flow, endpoint = flows[0], factory.created['other_branches']
    roles = [a['role'] for a in endpoint.attempts]
    if mode == 'initial_pass':
        assert roles == ['generation', 'generation', 'review']
        assert result.publication_status.value == 'published'
        assert result.output.report == endpoint.generator.req.report
        assert flow.last_edit_journal is None
    else:
        assert roles == ['generation', 'generation', 'review', 'revision', 'review']
        assert flow.stopped and flow.send.provider.stopped
        assert flow.send.provider.last_exchange is None
        assert result.publication_status.value == 'rejected'
        assert not (tmp_path/'other_branches/output/final_report.md').exists()
        assert len(flow.exchanges) == 3  # Invalid fresh is kept; recovery never dispatched.


def test_shared_token_reservation_rejects_before_endpoint_dispatch():
    from app.runtime.coach_budget import CoachBudgetedProvider
    from app.providers.errors import ProviderResponseError
    endpoint = ScriptedRoles('success', False)
    budget = CoachBudgetedProvider(endpoint, coach_contract=BOUNDARY_EXAMPLES_COACH_CONTRACT)
    budget.contract = ScriptedBudgetIdentity(budget.contract)
    _, inputs, _, _ = cases()['claim-scope:4']
    request = view.project(inputs)
    # Explicit synthetic prior spend; this is a preflight boundary test, not
    # an application usage measurement or a claim that real five calls overflow.
    budget.tokens = budget.contract.descriptor()['total_tokens'] - request.max_tokens
    with pytest.raises(ProviderResponseError) as error:
        budget.chat(request)
    assert error.value.code == 'token_budget_exhausted'
    assert budget.stopped and budget.calls == budget.reserved_tokens == 0
    assert endpoint.attempts == [] and endpoint.last_exchange is None


@pytest.mark.parametrize('reassessment_passes', [True, False])
def test_standalone_fresh_reassessment_journal_binds_both_attempts(reassessment_passes):
    """Workflow-only four calls; product generation would consume two extra slots.

    This verifies reusable workflow accounting, not permission for a six-call
    application. The application test separately proves its sixth call refusal.
    """
    from app.harness.steps import RevisionRequest
    req, _, _, _ = cases()['claim-scope:4']
    endpoint = ScriptedRoles('fresh_invalid', False)
    retained = []

    def send(request):
        response = endpoint.chat(request)
        if (request.metadata.get('review_phase') == 'native_business_reassessment'
                and reassessment_passes):
            value = dict(response.tool_calls[0].arguments, score=95)
            response = replace(response, tool_calls=(replace(response.tool_calls[0], arguments=value),))
        return Exchange(request, response, request_sha(request))

    flow = DocumentReviewWorkflow(send, record=lambda phase, ex: retained.append(ex))
    initial = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final_req = replace(req, report=draft.report)
    if reassessment_passes:
        assert flow.evaluate(final_req).verdict.value == 'pass'
    else:
        with pytest.raises(ValueError):
            flow.evaluate(final_req)
        assert flow.stopped
    attempts = flow.last_edit_journal['final_review_attempts']
    assert len(attempts) == 2 and flow.calls == 4
    assert [x['receipt_request_sha256'] for x in attempts] == [e.receipt_request_sha256 for e in retained[-2:]]
    if reassessment_passes:
        binding = flow.last_edit_journal['final_review_result_binding']
        assert binding['receipt_request_sha256'] == retained[-1].receipt_request_sha256
        assert binding['receipt_request_sha256'] != flow.last_edit_journal['final_review_receipt_request_sha256']
        assert binding['verdict'] == 'pass'
        assert flow.last_journal['evaluation_requests'] == attempts
    else:
        assert 'final_review_result_binding' not in flow.last_edit_journal
    saved = deepcopy(flow.last_edit_journal)
    with pytest.raises(ValueError, match='native_evaluation_order_invalid'):
        flow.evaluate(final_req)
    assert flow.last_edit_journal == saved
    assert flow._evaluation_bindings == attempts
