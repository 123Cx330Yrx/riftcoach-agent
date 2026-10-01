"""Submission protocol, full input preservation and shared Agent budget witnesses."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import golden_native_business_policy as business
from app.evaluation import golden_native_tool_review as current
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, Exchange
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage, ToolCall, ToolChoiceMode
from scripts.check_native_contract_options import OfflineResponses
from scripts.run_golden_native_review import prepare_claim_scope
from tests.test_golden_native_business_policy import opinion


def response(value=None, **overrides):
    fields = dict(content=None, model='glm-5.3-flash', provider='zhipu', usage=TokenUsage(10, 10),
        finish_reason='tool_calls', tool_calls=(ToolCall('submission', current.SUBMIT_TOOL,
            value if value is not None else opinion(None)),))
    return ChatResponse(**dict(fields, **overrides))


class Responses(OfflineResponses):
    def chat(self, req):
        self.requests.append(req)
        reply = self.responses[len(self.requests)-1]
        if isinstance(reply, str):
            reply = response(content=reply, tool_calls=(), finish_reason='stop')
        self.last_exchange = Exchange(req, reply,
            hashlib.sha256(validate_request(req, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return reply


@pytest.mark.parametrize('phase', ['initial', 'reassessment', 'revision'])
def test_all_sources_business_policy_schema_and_settings_preserved(phase):
    _, req = prepare_claim_scope(3)
    inputs = current.native.build_inputs(req)
    old = compact(opinion(inputs, block=6))
    _, wire, _ = business.validate(old, inputs)
    kwargs = {'previous_raw': old, 'diagnostics': {'errors': ['synthetic']}} if phase == 'reassessment' else (
        {'accepted': wire} if phase == 'revision' else {})
    before, after = business.request(inputs, **kwargs), current.request(inputs, **kwargs)
    if phase == 'revision':
        assert before == after
    else:
        assert after.tools[0].input_schema == before.response_contract.schema_dict()
        assert after.response_contract is None and after.tool_choice is ToolChoiceMode.AUTO
        header = current.native.schema_notation(before.response_contract.schema_dict()) + '\n'
        assert after.messages[1].content == before.messages[1].content[len(header):]
        assert after.messages[2:] == before.messages[2:]
        assert after.messages[0].content.replace(current.TOOL_DELIVERY, current.TEXT_DELIVERY) == before.messages[0].content
        assert replace(after, messages=before.messages, tools=before.tools,
                       response_contract=before.response_contract) == before


@pytest.mark.parametrize('reply', [
    response(content='There is another actual error.'),
    response(content='No error.', tool_calls=(), finish_reason='stop'),
    response(tool_calls=(ToolCall('a', 'unknown', opinion(None)),)),
    response(tool_calls=(ToolCall('a', current.SUBMIT_TOOL, opinion(None)),
                         ToolCall('b', current.SUBMIT_TOOL, opinion(None)))),
    response(finish_reason='length'), response(finish_reason='stop'),
])
def test_bad_channel_stops_before_any_reassessment_and_preserves_response(reply):
    _, req = prepare_claim_scope(1)
    provider, records = Responses([reply]), []
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000),
        record=lambda phase, exchange: records.append(exchange.response))
    with pytest.raises(ValueError, match='native_review_tool_channel_invalid'):
        flow.evaluate(req)
    assert flow.stopped and flow.calls == len(provider.requests) == 1
    assert records == [reply]


@pytest.mark.parametrize('mutation', ['receipt', 'input', 'tool', 'choice'])
def test_tampered_input_or_receipt_never_admitted(mutation):
    _, req = prepare_claim_scope(1)
    prepared = current.request(current.native.build_inputs(req))
    provider = Responses([response()])
    provider.chat(prepared)
    original = provider.last_exchange
    if mutation == 'receipt':
        changed = replace(original, receipt_request_sha256='0' * 64)
    else:
        delta = {'input': {'messages': (ChatMessage(MessageRole.USER, 'changed'),)},
                 'tool': {'tools': ()}, 'choice': {'tool_choice': ToolChoiceMode.NONE}}[mutation]
        changed = replace(original, issued_request=replace(prepared, **delta))
    with pytest.raises(ValueError, match='integrated_(issued_input|receipt)_mismatch'):
        current.tool_result(prepared, changed)


def test_arguments_use_strict_schema_and_explicit_old_finding_resolution():
    _, req = prepare_claim_scope(3)
    malformed = dict(opinion(None, block=6), score='70')
    provider = Responses([response(malformed), response()])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    with pytest.raises(ValueError, match='native_issue_resolution_inventory'):
        flow.evaluate(req)
    assert flow.stopped and flow.calls == 2
    assert 'previous_issues' in provider.requests[1].messages[1].content


def test_valid_submission_edit_and_recheck_keep_original_channel_evidence():
    _, req = prepare_claim_scope(3)
    revised = req.report + '\n\n合成修订见证。[K1]'
    replies = [response(opinion(None, block=6)), revised, response()]
    provider, recorded = Responses(replies), []
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000),
        record=lambda phase, exchange: recorded.append(exchange.response))
    first = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, first))
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == 'pass' and flow.calls == 3 and flow.revisions == 1
    assert flow.last_journal['raw_representation'] == 'tool_arguments_projection'
    assert recorded[0] is replies[0] and recorded[2] is replies[2]
    assert recorded[0].content is None and not provider.requests[1].tools


def test_actual_prior_prose_tail_is_rejected_without_truncating_or_new_judgment():
    saved = json.loads(Path('data/evaluation/results/golden_native_business_result_d41c0bd.json').read_text(encoding='utf-8'))
    tail = saved['cases'][1]['calls'][2]['content']
    _, req = prepare_claim_scope(4)
    provider = Responses([response(content=tail, tool_calls=(), finish_reason='stop')])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000))
    with pytest.raises(ValueError, match='native_review_tool_channel_invalid'):
        flow.evaluate(req)
    assert provider.last_exchange.response.content == tail and flow.calls == 1


def test_actual_sdk_stream_payload_uses_auto_function_and_high_without_json_mode(tmp_path):
    from tests.test_zhipu_stream_adapter import chunk, tool_fragment, usage
    from app.runtime.coach_contract import CAPACITY_COACH_CONTRACT
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream
    from app.evaluation import golden_stream_bridge as bridge

    _, req = prepare_claim_scope(1)
    prepared = current.request(current.native.build_inputs(req))
    raw = ClosableStream([chunk(tool_calls=[tool_fragment(call_id='submission',
        name=current.SUBMIT_TOOL, arguments=compact(opinion(None)))], finish_reason='tool_calls'), chunk(raw_usage=usage())])
    client = FakeClient(raw)
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3-flash',
        profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    result = bridge.collect(prepared, lambda r, hook: provider.stream_adapter(tool_stream=True,
        evaluation_request_policy=CAPACITY_COACH_CONTRACT.request_policy).stream_session(r, include_usage_tail=True),
        directory=tmp_path, started=0, deadline=300, clock=lambda: 1, allow_tool_content=True,
        transport_id=CAPACITY_TRANSPORT_ID)
    payload = client.completions.calls[0]
    assert payload['tools'][0]['function']['parameters'] == prepared.tools[0].input_schema
    assert payload['tool_choice'] == 'auto' and 'response_format' not in payload
    assert payload['extra_body']['reasoning_effort'] == 'high' and payload['extra_body']['tool_stream'] is True
    assert payload['max_tokens'] == 32768 and result.finish_reason == 'tool_calls'


@pytest.mark.parametrize('recover', [False, True])
def test_real_runtime_factory_shares_all_five_calls_including_generation(recover):
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
    from app.runtime.observed_provider import ObservedLLMProvider
    from app.runtime.review_sender import SharedBudgetReviewSender
    from tests.test_runtime_execution_factory_combined import _factory, _NoopObserver

    _, req = prepare_claim_scope(3)
    first = opinion(None, block=6)
    corrected = dict(first, issue_resolutions=[dict(previous_id=1, disposition='replaced',
        final_issue=1, source_ids=[1], explanation='修正类型，保留原问题。')])
    replies = ['generation', 'generation']
    replies += [response(dict(first, score='70')), response(corrected)] if recover else [response(first)]
    replies += [req.report + '\n\n合成修改。[K1]', response()]
    delegate, captured = Responses(replies), []

    def factory(runtime, provider):
        flow = current.NativeBusinessReviewWorkflow(SharedBudgetReviewSender(provider))
        captured.append((flow, provider))
        return flow

    bundle = _factory(coach_contract=CONTEXT_COACH_CONTRACT, review_workflow_factory=factory).build(
        provider=ObservedLLMProvider(delegate=delegate, observer=_NoopObserver()), observer=_NoopObserver())
    flow, budget = captured[0]
    for index in (1, 2):
        budget.chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, 'generation fixture'),),
            max_tokens=32768, metadata={'agent_loop_iteration': index}))
    first = bundle.evaluator.evaluate(req)
    revised = bundle.reviser.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, first))
    if recover:
        with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
            bundle.evaluator.evaluate(replace(req, report=revised.report))
        assert flow.stopped
    else:
        assert bundle.evaluator.evaluate(replace(req, report=revised.report)).verdict.value == 'pass'
    assert len(delegate.requests) == budget.calls == 5
    assert flow.send.provider is bundle.draft_preparer._agent_loop.provider
