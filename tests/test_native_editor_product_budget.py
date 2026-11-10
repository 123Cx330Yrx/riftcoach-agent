"""Real product compilation with scripted replies; never model quality evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.product.native_coach_composition import build_native_coach_application
from app.product.recent_review import RecentReviewProductRequest
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from scripts.check_native_contract_options import corrected_case3, OfflineResponses, PASS
from scripts.native_contract_options import OfflineEditorWorkflow, body
from tests.test_coach_application_composition import SummaryBuilder


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('scripted product budget test attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def _computed_source(data):
    # Resolve this actual product request's catalog, never borrow old IDs.
    columns = data['source_roots']['additional_columns']
    rows = [dict(zip(columns, row)) for row in data['source_roots']['additional']]
    return next(row['source_id'] for row in rows if row['key'] == 'derived/computed_evidence')


class ScriptedProductProvider(OfflineResponses):
    def __init__(self, *, recover, charge_ceiling):
        super().__init__([], charge_ceiling=charge_ceiling)
        self.req, self.historical_review, self.edit = corrected_case3()
        self.recover = recover
        self.review_calls = 0
        self.review_raw = None
        self.knowledge_count = None
        self.editor_output = None

    def chat(self, request):
        self.requests.append(request)
        tool_calls = ()
        if request.metadata.get('agent_loop_iteration') == 1:
            assert request.tools
            content = None
            tool_calls = tuple(ToolCall(id=f'offline-product-knowledge-{i}', name='knowledge.search',
                arguments={'query': query, 'top_k': 1}) for i, query in enumerate(
                    ('早期死亡', '补刀与经济', '避免伪精确目标',
                     '可执行性 训练计划 可观察目标 观察周期 复盘方式',
                     '证据分层 比赛统计 时间线 录像 事实 相关性 复盘假设'), 1))
        elif request.metadata.get('agent_loop_iteration') == 2:
            assert any(message.role.value == 'tool' for message in request.messages)
            content = self.req.report
        elif request.metadata.get('review_phase') == 'offline_issue_adjudicating_editor':
            data = body(request)
            assert data['review_sha256'] == digest(self.review_raw)
            edited = deepcopy(self.edit)
            edited['review_sha256'] = data['review_sha256']
            for decision in edited['decisions']:
                decision['source_ids'] = [_computed_source(data)]
            self.editor_output = edited
            content = compact(edited)
        else:
            data = body(request)
            self.knowledge_count = len(data['knowledge']['citations'])
            self.review_calls += 1
            if self.review_calls == 1:
                value = json.loads(self.historical_review)
                for issue in value['issues']:
                    issue['source_ids'] = [_computed_source(data)]
                if self.recover:
                    value['score'] = str(value['score'])
                content = compact(value)
            elif self.recover and self.review_calls == 2:
                assert request.metadata['review_phase'] == 'native_business_reassessment'
                value = deepcopy(data['previous_review'])
                value['score'] = int(value['score'])
                value['issue_resolutions'] = [dict(previous_id=i, disposition='replaced',
                    final_issue=i, source_ids=[_computed_source(data)],
                    explanation='Analyst-authored type recovery, not model evidence.')
                    for i in range(1, len(value['issues']) + 1)]
                content = compact(value)
            else:
                content = PASS
            self.review_raw = content
        response = ChatResponse(content=content, tool_calls=tool_calls,
            provider=self.provider_name, model=self.model_name,
            finish_reason='tool_calls' if tool_calls else 'stop',
            usage=TokenUsage(input_tokens=size(request) if self.charge_ceiling else 10,
                output_tokens=request.max_tokens if self.charge_ceiling else 10))
        self.last_exchange = Exchange(request, response,
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


class Factory:
    def __init__(self, *, recover, charge_ceiling):
        self.descriptor = ScriptedProductProvider(recover=recover, charge_ceiling=charge_ceiling)
        self.providers = {}
        self.recover, self.charge_ceiling = recover, charge_ceiling

    def __call__(self, run_id):
        result = ScriptedProductProvider(recover=self.recover, charge_ceiling=self.charge_ceiling)
        self.providers[run_id] = result
        return result


class RecordingSharedBudgetSender(SharedBudgetReviewSender):
    def __init__(self, provider):
        super().__init__(provider)
        self.failures = []

    def __call__(self, request):
        try:
            return super().__call__(request)
        except ProviderResponseError as error:
            self.failures.append(dict(code=error.code, phase=request.metadata['review_phase']))
            raise


def _run_product(tmp_path, monkeypatch, *, recover, charge_ceiling):
    req, _, _ = corrected_case3()
    factory = Factory(recover=recover, charge_ceiling=charge_ceiling)
    app = build_native_coach_application(summary_builder=SummaryBuilder(req.player_summary),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows = []

    def editor_factory(runtime, provider):
        flow = OfflineEditorWorkflow(RecordingSharedBudgetSender(provider))
        flows.append(flow)
        return flow

    # Patch only this test instance after verified production assembly. Changing
    # the imported native class would change a fingerprinted production module.
    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory', editor_factory)
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1',
        routing_region='asia', count=5, queue=420), run_id='offline_editor_budget')
    provider = factory.providers['offline_editor_budget']
    assert len(flows) == 1
    flow = flows[0]
    budget = flow.send.provider
    assert budget.calls == len(provider.requests)
    assert budget.provider._delegate is provider
    assert provider.knowledge_count == 5
    assert [r.metadata.get('agent_loop_iteration') for r in provider.requests[:2]] == [1, 2]
    assert flow.editor_journal['semantic_approval'] is False
    assert flow.editor_journal['production_admitted'] is False
    rows = [dict(ordinal=i, phase=r.metadata.get('review_phase', 'generation'),
        iteration=r.metadata.get('agent_loop_iteration'), input_ceiling=size(r),
        output_reservation=r.max_tokens) for i, r in enumerate(provider.requests, 1)]
    measured = dict(evidence_kind='scripted_product_contract_not_model_quality',
        recovery=recover, charge_ceiling=charge_ceiling, requests=rows,
        full_output_reservation=sum(row['input_ceiling'] + row['output_reservation'] for row in rows),
        actual_scripted_usage=budget.tokens, shared_budget=401920,
        budget_failures=flow.send.failures,
        publication_status=result.publication_status.value, terminal_reason=result.terminal_reason,
        provider_calls=0, semantic_approval=False)
    print(compact(measured))
    return result, provider, flow, measured


def test_editor_product_uses_actual_generation_and_one_shared_five_call_budget(tmp_path, monkeypatch):
    result, provider, flow, measured = _run_product(tmp_path, monkeypatch,
        recover=False, charge_ceiling=True)
    assert result.publication_status.value == 'published', result.terminal_reason
    assert len(provider.requests) == 5 and flow.calls == 3 and flow.revisions == 1
    assert [row['phase'] for row in measured['requests']] == [
        'generation', 'generation', 'native_business_review',
        'offline_issue_adjudicating_editor', 'native_business_review']
    assert measured['actual_scripted_usage'] == measured['full_output_reservation'] <= 401920
    assert flow._expected_recheck.source.report == provider.editor_output['report']


def test_product_reassessment_cannot_spend_a_sixth_call_after_editor(tmp_path, monkeypatch):
    result, provider, flow, measured = _run_product(tmp_path, monkeypatch,
        recover=True, charge_ceiling=False)
    assert result.publication_status.value == 'rejected'
    assert result.output.report is None
    assert len(provider.requests) == 5 and flow.revisions == 1 and flow.stopped
    assert flow.send.provider.stopped
    assert [row['phase'] for row in measured['requests']] == [
        'generation', 'generation', 'native_business_review',
        'native_business_reassessment', 'offline_issue_adjudicating_editor']
    assert measured['budget_failures'] == [dict(code='external_call_budget_exhausted',
        phase='native_business_review')]
    # Low scripted usage isolates call exhaustion from token exhaustion. The
    # sixth request never reaches the delegate and cannot produce a receipt.
    assert measured['actual_scripted_usage'] == 100
    assert provider.review_calls == 2
