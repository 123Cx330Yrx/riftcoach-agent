from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import golden_native_json_block_review as current
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from tests.test_golden_native_buffered_block_review import independent, committed_inputs_only
from tests.test_golden_native_block_tool_review import control, grouped
from tests.test_golden_native_partitioned_tool_review import exchange_provider, valid_review
from tests.test_native_editor_product_budget import offline


def test_only_submission_channel_changes_full_sources_and_business_contract_remain():
    _, inputs, count = control()
    old, new = current.previous.request(inputs), current.request(inputs)
    assert not new.tools and new.response_contract.schema_dict() == old.tools[0].input_schema
    assert new.messages[2:] == old.messages[2:]
    header = current.native.schema_notation(new.response_contract.schema_dict()) + '\n'
    assert new.messages[1].content == header + old.messages[1].content
    assert new.messages[0].content == old.messages[0].content.replace(current.tool.TOOL_DELIVERY, current.tool.TEXT_DELIVERY)
    assert new.max_tokens == old.max_tokens == 32768 and new.timeout_s == old.timeout_s == 300
    raw = compact(independent(valid_review(advisory=True), count))
    _, _, journal = current.validate(raw, inputs)
    assert journal['raw_representation'] == 'response_content' and journal['raw'] == raw
    assert journal['policy_sha256'] == digest(new.messages[0].content)


@pytest.mark.parametrize('kind', ['prose_tail', 'duplicate_member'])
def test_historical_framing_failures_stop_without_hidden_reassessment(kind):
    req, _, count = control()
    raw = compact(independent(valid_review(), count))
    raw = raw + '\nYet the report is wrong.' if kind == 'prose_tail' else raw[:-1] + ',"score":85}'
    provider = exchange_provider([raw])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider))
    with pytest.raises((ValueError, ProviderResponseError)): flow.evaluate(req)
    assert flow.stopped and flow.calls == len(provider.requests) == 1


def test_explicit_reassessment_edit_and_independent_final_review():
    req, _, count = control()
    before = independent(valid_review(issue=True), count)
    before['score'] = 'invalid'
    corrected = grouped(valid_review(issue=True), count)
    corrected['issue_resolutions'] = [dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[31], explanation='Scripted explicit correction mapping.')]
    provider = exchange_provider([compact(before), compact(corrected), req.report,
        compact(independent(valid_review(advisory=True), count))])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    edited = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = flow.evaluate(replace(req, report=edited.report))
    assert final.verdict.value == 'pass' and flow.calls == 4 and flow.revisions == 1
    assert 'issue_resolutions' in provider.requests[1].response_contract.schema_dict()['required']
    assert 'issue_resolutions' not in provider.requests[3].response_contract.schema_dict()['properties']


def test_json_mode_reaches_real_sdk_builder_with_same_high_budget(tmp_path):
    from app.evaluation.golden_stream_bridge import collect
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
    from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage
    _, inputs, count = control()
    raw = compact(independent(valid_review(), count))
    stream = ClosableStream([chunk(content=raw, finish_reason='stop'), chunk(raw_usage=usage())])
    client = FakeClient(stream)
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3-flash',
        profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    response = collect(current.request(inputs), lambda req, _: provider.stream_adapter(
        evaluation_request_policy=CONTEXT_COACH_CONTRACT.request_policy).stream_session(req, include_usage_tail=True),
        directory=tmp_path, started=0, deadline=300, clock=lambda:1, transport_id=CAPACITY_TRANSPORT_ID)
    payload = client.completions.calls[0]
    assert response.content == raw
    assert payload['response_format'] == {'type':'json_object'}
    assert payload['stream'] is True and payload['stream_options'] == {'include_usage':True}
    assert 'tools' not in payload and 'tool_stream' not in payload['extra_body']
    assert payload['extra_body']['reasoning_effort'] == 'high' and payload['max_tokens'] == 32768


def test_actual_product_generation_review_edit_recheck_stays_in_five_calls(tmp_path, monkeypatch):
    from app.product.native_coach_composition import build_native_coach_application
    from app.product.recent_review import RecentReviewProductRequest
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from tests import test_native_editor_product_budget as product

    class Provider(product.ScriptedProductProvider):
        def chat(self, request):
            response = super().chat(request)
            phase = request.metadata.get('review_phase')
            if phase == 'native_business_revision':
                response = replace(response, content=self.edit['report'], tool_calls=(), finish_reason='stop')
            elif phase in ('native_business_review', 'native_business_reassessment'):
                data = json.loads(request.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
                flat = dict(json.loads(response.content), advisories=[])
                value = independent(flat, len(data['source_index']['blocks']))
                response = replace(response, content=compact(value))
            self.last_exchange = Exchange(request, response,
                hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
            return response

    monkeypatch.setattr(product, 'ScriptedProductProvider', Provider)
    factory = product.Factory(recover=False, charge_ceiling=True)
    req = factory.descriptor.req
    app = build_native_coach_application(summary_builder=product.SummaryBuilder(req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows=[]
    def review_factory(runtime, provider):
        flow = current.NativeBusinessReviewWorkflow(product.RecordingSharedBudgetSender(provider))
        flows.append(flow)
        return flow
    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory', review_factory)
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia', count=5, queue=420),
        run_id='offline_json_block_budget')
    assert result.publication_status.value == 'published', result.terminal_reason
    assert len(factory.providers['offline_json_block_budget'].requests) == flows[0].send.provider.calls == 5
    assert flows[0].send.provider.tokens <= 401920
    assert flows[0].last_journal['raw_representation'] == 'response_content'


@pytest.mark.parametrize('usage_observed', [True, False])
def test_real_runner_does_not_confuse_assembly_rejection_with_unknown_usage(tmp_path, usage_observed):
    from scripts.run_golden_integrated_review import observe_report
    from app.evaluation.golden_stream_bridge import CapacityBridgeObservation
    from scripts.run_golden_native_review import score_case
    req, _, _ = control()
    from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
    class Failed(ReceiptedStreamProvider):
        _calls = 0
        last_exchange = None
        def __init__(self): pass
        def chat(self, request):
            self._calls += 1
            d=tmp_path/'streams/stream-001'
            d.mkdir(parents=True)
            observation=CapacityBridgeObservation(**(dict(input_tokens=11640, output_tokens=5845) if usage_observed else {}))
            (d/'progress.json').write_text(observation.model_dump_json(), encoding='utf-8')
            raise ProviderResponseError(provider='zhipu',code='stream_child_failed')
    result = observe_report(Failed(),tmp_path,req,{'id':'scripted_failure'},
        workflow_factory=current.NativeBusinessReviewWorkflow,score_case=score_case)
    assert not result['valid'] and result['completed_calls'] == 0 and result['reserved_calls'] == 1
    assert result['unknown_usage_calls'] == (0 if usage_observed else 1)
    assert result['input_tokens']+result['output_tokens'] == (17485 if usage_observed else 0)
