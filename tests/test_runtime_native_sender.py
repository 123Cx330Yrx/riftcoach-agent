from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import golden_native_issues_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, GoldenProcessStreamProvider, validate_request
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage
from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from tests.test_golden_native_reassessment import recorded_failure
from tests.test_runtime_execution_factory_combined import _factory, _NoopObserver, _Provider


def test_actual_native_workflow_shares_generation_budget_and_issued_receipts():
    controls = json.loads(Path('data/evaluation/datasets/golden_observed_review_controls_v1.json').read_text(encoding='utf-8'))
    _, request = recorded_failure()
    bad, good = controls['cases'][1]['report'], controls['cases'][0]['report']
    request = replace(request, report=bad, user_utterance=controls['user_utterance'])
    inputs = candidate.build_inputs(request)
    issue_block = next(i for i, (_, text) in enumerate(inputs.source.blocks, 1) if controls['cases'][1]['target'] in text)
    initial = dict(score=70, verdict='needs_revision', issues=[dict(block=issue_block,
        severity='medium', category='fact_error', source_ids=[7,9,10,11],
        explanation='分析者脚本问题，仅验证产品接线。', suggested_correction='去掉无依据未来外推。')], issue_resolutions=[])
    candidate.validate(compact(initial), inputs)
    replies = [compact(initial), good, compact(dict(score=95, verdict='pass', issues=[], issue_resolutions=[]))]

    class Receipted(_Provider):
        def chat(self, req):
            self.transport_calls += 1
            response = ChatResponse(content='ok' if 'agent_loop_iteration' in req.metadata else replies.pop(0),
                model=self.model_name, provider=self.provider_name, finish_reason='stop',
                usage=TokenUsage(input_tokens=1, output_tokens=1))
            self.last_exchange = Exchange(req, response,
                hashlib.sha256(validate_request(req, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
            return response
    delegate = Receipted(provider_name='zhipu', model_name='glm-5.3-flash', capabilities=GoldenProcessStreamProvider.capabilities)
    delegate.thinking_profile_id='glm-5.3-flash-candidate-enabled-high-replay'
    delegate.sdk_max_retries=0
    delegate.runtime_profile=None
    captured=[]
    def factory(runtime, provider):
        flow = candidate.NativeBusinessReviewWorkflow(SharedBudgetReviewSender(provider))
        captured.append((flow, provider))
        return flow
    bundle = _factory(coach_contract=CONTEXT_COACH_CONTRACT, review_workflow_factory=factory).build(
        provider=ObservedLLMProvider(delegate=delegate, observer=_NoopObserver()), observer=_NoopObserver())
    flow, provider = captured[0]
    for i in (1,2):
        provider.chat(ChatRequest(messages=(ChatMessage(role=MessageRole.USER, content='generation placeholder'),),
            max_tokens=1, metadata={'agent_loop_iteration':i}))
    first = bundle.evaluator.evaluate(request)
    revised = bundle.reviser.revise(RevisionRequest(request.player_summary, request.deterministic_report,
        request.knowledge, request.report, first))
    final = bundle.evaluator.evaluate(replace(request, report=revised.report))
    assert final.verdict.value == 'pass'
    assert flow.calls == 3 and provider.calls == delegate.transport_calls == 5
    assert flow.send.provider is bundle.draft_preparer._agent_loop.provider
    with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
        flow.send(candidate.request(candidate.build_inputs(replace(request, report=good))))
    assert delegate.transport_calls == 5
