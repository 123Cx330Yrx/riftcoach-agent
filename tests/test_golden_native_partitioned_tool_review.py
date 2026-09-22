from dataclasses import replace
import json

import pytest

from app.evaluation import golden_native_partitioned_tool_review as current
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import RevisionRequest, EvaluationVerdict
from app.providers.errors import ProviderResponseError
from app.providers.models import ToolCall, ToolChoiceMode
from scripts.check_native_contract_options import OfflineResponses
from scripts.run_golden_native_review import prepare_claim_scope
from tests.test_golden_native_business_policy import opinion
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
import hashlib


def valid_review(*, issue=False, advisory=False):
    return dict(score=70 if issue else 96, verdict='needs_revision' if issue else 'pass',
        issues=[] if not issue else [dict(block=4, source_ids=[31], severity='medium', category='fact_error',
            explanation='真实事实错误。', suggested_correction='修正真实错误。')],
        issue_resolutions=[], advisories=[] if not advisory else [dict(block=6, source_ids=[9],
            explanation='完整上下文已确定范围，仅可改善表达。', suggested_correction='可选地明确观察窗口。')])


def exchange_provider(responses):
    class Provider(OfflineResponses):
        def chat(self, request):
            self.requests.append(request)
            value = self.responses[len(self.requests)-1]
            if isinstance(value, str):
                from app.providers.models import ChatResponse, TokenUsage
                response = ChatResponse(content=value, model='glm-5.3-flash', provider='zhipu',
                    usage=TokenUsage(10, 10), finish_reason='stop')
            else:
                response = value
            self.last_exchange = Exchange(request, response,
                hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
            return response
    return Provider(responses)


def tool_response(value, *, name=current.tool.SUBMIT_TOOL if hasattr(current, 'tool') else 'submit_report_review'):
    from app.providers.models import ChatResponse, TokenUsage
    return ChatResponse(content=None, model='glm-5.3-flash', provider='zhipu',
        usage=TokenUsage(10, 10), finish_reason='tool_calls',
        tool_calls=(ToolCall('call', name, value),))


def test_partitioned_schema_preserves_sources_and_makes_advisory_nonblocking():
    _, req = prepare_claim_scope(4)
    inputs = current.native.build_inputs(req)
    prepared = current.request(inputs)
    assert prepared.response_contract is None and prepared.tool_choice is ToolChoiceMode.AUTO
    assert 'advisories' in prepared.tools[0].input_schema['properties']
    assert '五个字段为score、verdict、issues、issue_resolutions、advisories。' in prepared.messages[0].content
    assert '四个字段为score、verdict、issues、issue_resolutions。' not in prepared.messages[0].content
    value = valid_review(advisory=True)
    payload, wire, journal = current.validate(compact(value), inputs)
    assert payload.verdict == 'pass' and payload.issues == []
    assert len(wire.advisories) == len(journal['advisories']) == 1
    assert journal['raw_representation'] == 'tool_arguments_projection'


def test_real_fact_error_stays_blocking_while_advisory_is_preserved():
    _, req = prepare_claim_scope(4)
    inputs = current.native.build_inputs(req)
    payload, wire, journal = current.validate(compact(valid_review(issue=True, advisory=True)), inputs)
    assert payload.verdict == EvaluationVerdict.NEEDS_REVISION.value
    assert len(payload.issues) == 1 and len(journal['advisories']) == 1


def test_advisory_bad_source_or_extra_field_is_rejected():
    _, req = prepare_claim_scope(1)
    inputs = current.native.build_inputs(req)
    value = valid_review(advisory=True)
    value['advisories'][0]['source_ids'] = [999]
    with pytest.raises(ValueError, match='source|unknown'):
        current.validate(compact(value), inputs)
    value = valid_review(advisory=True)
    value['advisories'][0]['severity'] = 'low'
    with pytest.raises(ValueError):
        current.validate(compact(value), inputs)


def test_partitioned_workflow_does_not_revise_for_advisory_only():
    _, req = prepare_claim_scope(1)
    provider = exchange_provider([tool_response(valid_review(advisory=True))])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    result = flow.evaluate(req)
    assert result.verdict is EvaluationVerdict.PASS and flow.calls == 1 and flow.revisions == 0


def test_partitioned_workflow_keeps_one_revision_for_blocking_issue():
    _, req = prepare_claim_scope(4)
    revised = req.report + '\n\n修订见证。[K1]'
    provider = exchange_provider([tool_response(valid_review(issue=True)), revised, tool_response(valid_review(advisory=True))])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    first = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, first))
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict is EvaluationVerdict.PASS and flow.calls == 3 and flow.revisions == 1


def test_partitioned_candidate_reaches_complete_product_five_call_budget_offline(tmp_path, monkeypatch):
    # Reuse the actual product compiler and runtime composition; only the
    # provider reply is scripted. Add the new required advisory array at the
    # provider boundary so this witnesses assembly, generation, revision and
    # recheck together without claiming model quality.
    from dataclasses import replace as dc_replace
    from pathlib import Path
    from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
    from app.product.native_coach_composition import build_native_coach_application
    from app.product.recent_review import RecentReviewProductRequest
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from tests import test_native_editor_product_budget as product
    from tests.test_native_editor_product_budget import offline

    class ProductProvider(product.ScriptedProductProvider):
        def chat(self, request):
            response = super().chat(request)
            if request.metadata.get('review_phase') == 'native_business_revision':
                response = dc_replace(response, content=self.edit['report'], tool_calls=(), finish_reason='stop')
                self.last_exchange = Exchange(request, response,
                    hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
                return response
            if request.metadata.get('review_phase') in ('native_business_review', 'native_business_reassessment'):
                from app.providers.models import ToolCall
                value = json.loads(response.content)
                value.setdefault('advisories', [])
                response = dc_replace(response, content=None,
                    finish_reason='tool_calls', tool_calls=(ToolCall('submission', 'submit_report_review', value),))
            if response.tool_calls and response.tool_calls[0].name == 'submit_report_review':
                call = response.tool_calls[0]
                args = dict(call.arguments)
                args.setdefault('advisories', [])
                response = dc_replace(response, tool_calls=(dc_replace(call, arguments=args),))
                self.last_exchange = Exchange(request, response,
                    hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
            return response

    monkeypatch.setattr(product, 'ScriptedProductProvider', ProductProvider)
    factory = product.Factory(recover=False, charge_ceiling=True)
    req = factory.descriptor.req
    app = build_native_coach_application(summary_builder=product.SummaryBuilder(req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows = []
    def factory_flow(runtime, provider):
        flow = current.NativeBusinessReviewWorkflow(product.RecordingSharedBudgetSender(provider))
        flows.append(flow)
        return flow
    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory', factory_flow)
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia', count=5, queue=420),
        run_id='offline_partitioned_tool_budget')
    provider = factory.providers['offline_partitioned_tool_budget']
    assert result.publication_status.value == 'published'
    assert len(provider.requests) == flows[0].send.provider.calls == 5
    assert flows[0].last_journal['raw_representation'] == 'tool_arguments_projection'
