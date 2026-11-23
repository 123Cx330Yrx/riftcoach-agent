"""Offline control-flow witnesses, not candidate integration or model quality.

Exercise the real AgentLoop/local knowledge adapter and unchanged Coach budget.
The budget-only probe uses synthetic Flash requests; it deliberately does not
route the unadmitted direct-patch candidate through a production identity.
No run artifacts, model receipts, credentials or historical evidence are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

from app.agent.draft import _knowledge_from_actual_tool_executions
from app.agent.loop import AgentLoop, AgentRunRequest
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage, ToolCall
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT
from app.tools.adapters import build_knowledge_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

ROOT = Path(__file__).resolve().parents[1]


class Scripted:
    provider_name, model_name = 'zhipu', 'glm-5.3-flash'
    thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
    sdk_max_retries = 0
    runtime_profile = None
    capabilities = ProviderCapabilities(tool_calling=True, parallel_tool_calls=True)

    def __init__(self, rounds=()):
        self.rounds, self.requests = rounds, []

    def chat(self, request):
        self.requests.append(request)
        index = len(self.requests) - 1
        calls = tuple(ToolCall(id=f'offline-{index}-{n}', name='knowledge.search',
            arguments={'query': query, 'top_k': 1})
            for n, query in enumerate(self.rounds[index])) if index < len(self.rounds) else ()
        return ChatResponse(content=None if calls else 'Offline control-flow witness only.',
            tool_calls=calls, provider=self.provider_name, model=self.model_name,
            finish_reason='tool_calls' if calls else 'stop',
            usage=TokenUsage(input_tokens=10, output_tokens=10))


def loop_probe(rounds):
    provider = Scripted(rounds)
    registry = ToolRegistry()
    local = CoachingQueryKnowledgeProvider(LocalHybridKnowledgeProvider.from_directory(ROOT/'data/rag_docs'))
    for definition in build_knowledge_tools(local, include_retrieval_time=True):
        registry.register(definition)
    result = AgentLoop(provider=provider, tool_registry=registry,
        tool_runtime=ToolRuntime(registry)).run(AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content='Offline recent-form control.'),),
            allowed_tools=('knowledge.search',), max_iterations=4, max_tool_calls=8))
    knowledge = _knowledge_from_actual_tool_executions(result)
    assert result.status.value == 'completed'
    assert len(provider.requests) == len(rounds) + 1
    assert len(result.tool_executions) == sum(map(len, rounds))
    if rounds:
        assert knowledge.source_ids
        assert any(m.role is MessageRole.TOOL for m in provider.requests[-1].messages)
    else:
        assert not knowledge.source_ids
    return dict(model_calls=len(provider.requests), tool_executions=len(result.tool_executions),
        source_count=len(knowledge.source_ids),
        meets_existing_minimum_evidence=bool(knowledge.source_ids),
        candidate_initial_pass_calls=len(provider.requests)+2,
        candidate_repair_and_two_fresh_calls=len(provider.requests)+4)


def budget_probe():
    native, roles = NATIVE_COACH_CONTRACT.descriptor(), ROLE_COACH_CONTRACT.descriptor()
    keys = ('max_calls', 'total_tokens', 'execution_timeout_s', 'max_input_tokens', 'max_output_tokens')
    assert {k: native[k] for k in keys} == {k: roles[k] for k in keys}
    now = [0.0]
    provider = Scripted()
    budget = CoachBudgetedProvider(provider, clock=lambda: now[0], coach_contract=NATIVE_COACH_CONTRACT)
    request = ChatRequest(messages=(ChatMessage(role=MessageRole.USER, content='Offline admission probe.'),),
        max_tokens=32768, timeout_s=600)
    for _ in range(5):
        budget.chat(request)
    try:
        budget.chat(request)
    except ProviderResponseError as error:
        assert error.code == 'external_call_budget_exhausted'
        sixth = error.code
    else:
        raise AssertionError('sixth call was admitted')
    assert budget.calls == len(provider.requests) == 5 and budget.stopped

    provider = Scripted()
    timed = CoachBudgetedProvider(provider, clock=lambda: now[0], coach_contract=NATIVE_COACH_CONTRACT)
    now[0] = 850
    timed.chat(request)
    assert provider.requests[-1].timeout_s == 50
    now[0] = 900
    try:
        timed.chat(request)
    except ProviderResponseError as error:
        assert error.code == 'timeout' and len(provider.requests) == 1
    else:
        raise AssertionError('expired task was admitted')

    provider = Scripted()
    limited = CoachBudgetedProvider(provider, clock=lambda: now[0], coach_contract=NATIVE_COACH_CONTRACT)
    limited.tokens = native['total_tokens'] - 1
    try:
        limited.chat(request)
    except ProviderResponseError as error:
        assert error.code == 'token_budget_exhausted' and not provider.requests
    else:
        raise AssertionError('insufficient token reservation was admitted')
    return dict(limits={k: native[k] for k in keys}, sixth_call_error=sixth,
        delegate_calls_before_stop=5, remaining_50s_issued_timeout=50,
        expired_task_stops_before_send=True, insufficient_tokens_stop_before_send=True,
        probe_scope='synthetic requests under actual shared gate; no candidate routing or quality proof')


def audit():
    def denied(*args, **kwargs):
        raise AssertionError('offline audit attempted network access')
    with patch.object(socket.socket, 'connect', denied), patch.object(socket, 'create_connection', denied):
        loops = {
            'no_tool': loop_probe(()),
            'batched_tools': loop_probe((('早期死亡', '补刀与经济'),)),
            'sequential_tools': loop_probe((('早期死亡',), ('补刀与经济',))),
        }
        budget = budget_probe()
    paths = (
        'scripts/audit_natural_review_duty_budget.py', 'app/agent/loop.py', 'app/agent/draft.py',
        'app/runtime/runtime.py', 'app/runtime/coach_budget.py', 'app/runtime/coach_contract.py',
        'app/harness/runtime.py', 'app/harness/adapters.py', 'app/product/native_coach_composition.py',
        'app/product/recent_review.py', 'app/product/recent_review_service.py', 'app/rag/coaching_query.py',
        'scripts/review_duty_patch_execution.py', 'app/runtime/reviewer_roles.py',
    )
    return dict(kind='offline-natural-review-duty-budget-audit-v1', external_calls=0,
        scripted_model_responses=True, production_admitted=False,
        loop_probes=loops, budget_probe=budget,
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, ensure_ascii=True, indent=2)
        handle.write('\n')
    print(json.dumps({k: result[k] for k in ('external_calls', 'loop_probes', 'budget_probe')}, ensure_ascii=True))
