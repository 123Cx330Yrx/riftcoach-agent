"""Actual product-compiled inputs + scripted role responses, never live quality."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from app.harness.steps import RevisionRequest
from app.evaluation.golden_review_experiment import digest
from app.product.native_coach_composition import build_native_coach_application
from app.product.recent_review import RecentReviewProductRequest
from app.providers.errors import ProviderResponseError
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT
from app.runtime.review_sender import SharedBudgetReviewSender
from scripts.reviewer_role_proposal import ProposedRoleBudget, ProposedReviewWorkflow
from scripts.native_contract_options import body
from tests import test_native_editor_product_budget as product
from tests.test_native_editor_product_budget import offline
from tests.test_native_tool_product_budget import ToolProductProvider


class RoleResponses(ToolProductProvider):
    def chat(self, request):
        response = super().chat(request)
        if response.tool_calls and 'review_phase' in request.metadata:
            call = response.tool_calls[0]
            response = replace(response, tool_calls=(replace(call,
                arguments={**call.arguments, 'advisories': []}),))
            self.last_exchange = replace(self.last_exchange, response=response)
        return response


@pytest.fixture
def compiled(tmp_path, monkeypatch):
    """Capture real generation/tool inputs and review evidence from product."""
    monkeypatch.setattr(product, 'ScriptedProductProvider', RoleResponses)
    factory = product.Factory(recover=False, charge_ceiling=False)
    app = build_native_coach_application(summary_builder=product.SummaryBuilder(factory.descriptor.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    inputs = []

    class Capture(ProposedReviewWorkflow):
        def evaluate(self, req):
            inputs.append(req)
            return super().evaluate(req)

    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory',
        lambda runtime, provider: Capture(SharedBudgetReviewSender(provider)))
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia',
        count=5, queue=420), run_id='compile_role_inputs')
    assert result.publication_status.value == 'published', result.terminal_reason
    delegate = factory.providers['compile_role_inputs']
    assert delegate.knowledge_count == 5
    requests = delegate.requests[:2]
    assert any(m.role.value == 'tool' for m in requests[1].messages)
    return requests, inputs[0]


def providers(*, recover=False, charge_ceiling=False):
    generator = RoleResponses(recover=False, charge_ceiling=charge_ceiling)
    reviewer = RoleResponses(recover=recover, charge_ceiling=charge_ceiling)
    reviewer.model_name = 'glm-5.3'
    reviewer.thinking_profile_id = ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id
    return generator, reviewer


@pytest.mark.parametrize('recover', [False, True])
def test_roles_share_real_product_inputs_budget_and_review_state(compiled, recover):
    requests, req = compiled
    generator, reviewer = providers(recover=recover, charge_ceiling=not recover)
    budget = ProposedRoleBudget(generator, reviewer)
    for request in requests:
        budget.chat(request)
    flow = ProposedReviewWorkflow(SharedBudgetReviewSender(budget))
    first = flow.evaluate(req)
    assert flow.last_journal['policy_sha256'] == digest(reviewer.requests[-1].messages[0].content)
    assert flow.last_journal['policy_sha256'] != flow.last_journal['validator_policy_sha256']
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
        req.knowledge, req.report, first))
    if recover:
        with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
            flow.evaluate(replace(req, report=draft.report))
        assert flow.stopped and budget.stopped and budget.last_exchange is None
        assert [a['role'] for a in budget.attempts] == ['generation', 'generation', 'review', 'review', 'revision']
        recovery = body(reviewer.requests[1])
        assert recovery['previous_review']['score'] == '70'
    else:
        assert flow.evaluate(replace(req, report=draft.report)).verdict.value == 'pass'
        assert [a['role'] for a in budget.attempts] == ['generation', 'generation', 'review', 'revision', 'review']
        assert flow._expected_recheck.source.report == draft.report
        assert body(reviewer.requests[-1]) != body(reviewer.requests[0])
    assert budget.calls == len(budget.attempts) == 5
    assert len(generator.requests) + len(reviewer.requests) == 5
    assert all(a['status'] == 'completed' for a in budget.attempts)
    assert [a['ordinal'] for a in budget.attempts] == list(range(1, 6))
    assert all(a['model'] == ('glm-5.3' if a['role'] == 'review' else 'glm-5.3-flash') for a in budget.attempts)
    assert budget.tokens == sum(a['input_tokens'] + a['output_tokens'] for a in budget.attempts) <= 401920
    assert all('evidence_by_id' in body(r)['source_index'] for r in reviewer.requests)
    with pytest.raises(ValueError):
        NATIVE_COACH_CONTRACT.require_provider(budget)
    print(json.dumps(dict(evidence='offline_scripted_not_product_admission', recovery=recover,
        calls=budget.calls, tokens=budget.tokens, attempts=budget.attempts)))


@pytest.mark.parametrize('failure', ['wrong_model', 'missing_receipt', 'wrong_receipt',
    'exception', 'time', 'late', 'tokens', 'phase', 'profile', 'missing_projection'])
def test_failure_stops_without_fallback_or_new_ledger(compiled, monkeypatch, failure):
    _, req = compiled
    generator, reviewer = providers()
    now = [0.0]
    budget = ProposedRoleBudget(generator, reviewer, clock=lambda: now[0])
    flow = ProposedReviewWorkflow(SharedBudgetReviewSender(budget))
    request = flow.make_request(flow.build_inputs(req))
    original = reviewer.chat

    def broken(request):
        if failure == 'exception':
            raise RuntimeError('scripted_transport_failure')
        response = original(request)
        if failure == 'wrong_model':
            return replace(response, model='glm-5.3-flash')
        if failure == 'missing_receipt':
            reviewer.last_exchange = None
        if failure == 'wrong_receipt':
            reviewer.last_exchange = replace(reviewer.last_exchange, receipt_request_sha256='0' * 64)
        if failure == 'late':
            now[0] = 901
        return response

    monkeypatch.setattr(reviewer, 'chat', broken)
    if failure == 'time':
        now[0] = 900
    if failure == 'tokens':
        budget.tokens = 401920
    if failure == 'phase':
        request = replace(request, metadata={**request.metadata, 'agent_loop_iteration': 1})
    if failure == 'profile':
        reviewer.thinking_profile_id = 'low'
    if failure == 'missing_projection':
        request = replace(request, metadata={k: v for k, v in request.metadata.items() if k != 'source_projection'})
    with pytest.raises((ValueError, ProviderResponseError, RuntimeError)):
        budget.chat(request)
    calls = budget.calls
    assert budget.stopped and budget.last_exchange is None and not generator.requests
    with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
        budget.chat(request)
    assert budget.calls == calls
    assert calls == (1 if failure in ('wrong_model', 'missing_receipt', 'wrong_receipt', 'exception', 'late') else 0)
    if failure in ('missing_receipt', 'wrong_receipt'):
        assert budget.attempts[0]['input_tokens'] == 10 and budget.tokens == 20
