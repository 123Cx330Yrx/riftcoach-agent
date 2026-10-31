"""Compile actual product generation/tool inputs; scripted model replies only."""
import hashlib
from pathlib import Path

import pytest

from app.evaluation import golden_native_tool_review as current
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.product.native_coach_composition import build_native_coach_application
from app.product.recent_review import RecentReviewProductRequest
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.rag.hybrid import LocalHybridKnowledgeProvider
from scripts.native_contract_options import body
from tests import test_native_editor_product_budget as product
from tests.test_native_editor_product_budget import offline  # autouse no-network guard
from tests.test_golden_native_business_policy import opinion


class ToolProductProvider(product.ScriptedProductProvider):
    def chat(self, request):
        if 'agent_loop_iteration' in request.metadata:
            return super().chat(request)
        self.requests.append(request)
        data = body(request)
        self.knowledge_count = len(data['knowledge']['citations'])
        tools, content = (), None
        if request.metadata['review_phase'] == 'native_business_revision':
            content = self.edit['report']
        else:
            self.review_calls += 1
            if self.review_calls == 1:
                value = opinion(None, block=6)
                value['issues'][0]['source_ids'] = [product._computed_source(data)]
                if self.recover:
                    value['score'] = '70'
            elif self.recover and self.review_calls == 2:
                value = dict(data['previous_review'], score=70,
                    issue_resolutions=[dict(previous_id=1, disposition='replaced', final_issue=1,
                        source_ids=[product._computed_source(data)], explanation='脚本类型修复，不是模型质量证据。')])
            else:
                value = opinion(None)
            tools = (ToolCall('submission', current.SUBMIT_TOOL, value),)
        response = ChatResponse(content=content, tool_calls=tools, provider=self.provider_name,
            model=self.model_name, finish_reason='tool_calls' if tools else 'stop',
            usage=TokenUsage(size(request) if self.charge_ceiling else 10,
                             request.max_tokens if self.charge_ceiling else 10))
        self.last_exchange = Exchange(request, response,
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


@pytest.mark.parametrize('recover', [False, True])
def test_actual_product_generation_tools_review_edit_publication_share_budget(tmp_path, monkeypatch, recover):
    monkeypatch.setattr(product, 'ScriptedProductProvider', ToolProductProvider)
    factory = product.Factory(recover=recover, charge_ceiling=not recover)
    req = factory.descriptor.req
    app = build_native_coach_application(summary_builder=product.SummaryBuilder(req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows = []

    def review_factory(runtime, provider):
        flow = current.NativeBusinessReviewWorkflow(product.RecordingSharedBudgetSender(provider))
        flows.append(flow)
        return flow

    # Test-instance injection; no production registration or fingerprint change.
    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory', review_factory)
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia',
        count=5, queue=420), run_id='offline_tool_budget')
    delegate, flow = factory.providers['offline_tool_budget'], flows[0]
    assert len(delegate.requests) == flow.send.provider.calls == 5
    assert delegate.knowledge_count == 5
    assert [r.metadata.get('agent_loop_iteration') for r in delegate.requests[:2]] == [1, 2]
    assert any(m.role.value == 'tool' for m in delegate.requests[1].messages)
    assert flow.revisions == 1
    if recover:
        assert result.publication_status.value == 'rejected' and result.output.report is None
        assert flow.stopped and flow.send.failures == [dict(code='external_call_budget_exhausted', phase='native_business_review')]
    else:
        assert result.publication_status.value == 'published', result.terminal_reason
        assert flow.calls == 3
        upper = sum(size(r) + r.max_tokens for r in delegate.requests)
        assert flow.send.provider.tokens == upper <= 401920
        assert flow.last_journal['raw_representation'] == 'tool_arguments_projection'
        print({'evidence': 'offline_scripted_product_not_model_quality', 'total_token_upper': upper,
               'inputs': [size(r) for r in delegate.requests], 'calls': 5})
