"""Compile the five-game offline acceptance case; emit only metrics and digests."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from app.agent.compiler import AgentRunCompiler
from app.agent.loop import _to_tool_spec
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as ceiling
from app.evidence.fusion import EvidenceBundle
from app.memory.context_models import MemoryContextBinding
from app.product import player_wording_contract as wording, player_wording_worker, sol_chat_contract as chat, sol_contract as responses
from app.product.player_language import render_product_report
from app.product.recent_review import ConversationRecentReviewRequest, RecentReviewRuntimeRequestCompiler
from app.product.review_purpose import ProductContextBuilder
from app.product.source_scope import render_product_publication_context
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.sol_session_receipts import request_from_raw
from app.skills.execution import SkillExecutionBoundary
from app.tools.adapters.knowledge import build_knowledge_tools
from app.tools.registry import ToolRegistry


def verify(root):
    def read(path):
        return json.loads(path.read_bytes())

    transport = root / '.continuation/transport' / root.name
    summary = read(root / 'inputs/player_summary.json')
    projection = SimpleNamespace(summary_digest=read(root / 'evidence_publication_manifest.json')['summary_digest'],
        bundle=EvidenceBundle.model_validate_json((root / 'evidence_bundle.json').read_bytes()))
    report = render_product_publication_context(render_product_report(summary), summary, projection)
    memory = read(root / 'memory_context_manifest.json')
    assert memory['candidate_count'] == memory['selected_count'] == memory['omitted_count'] == 0
    binding = MemoryContextBinding.model_validate_json(json.dumps(memory['binding']))
    assert binding.run_id == root.name and binding.relationship_role == 'observed'
    runtime = RuntimeCompositionRoot.from_directories(skills_root=chat.ASSETS/'skills',
        prompt_programs_root=chat.ASSETS/'prompt_programs', coach_contract=chat.CONTRACT)
    job = RecentReviewRuntimeRequestCompiler(runtime.skill_catalog, coach_contract=chat.CONTRACT).compile(
        ConversationRecentReviewRequest(count=5, queue=420, focus='overall'), player_summary=summary,
        deterministic_report=report, run_id=root.name, memory_context_binding=binding)
    execution = SkillExecutionBoundary(runtime.skill_catalog).validate(job.execution_request)
    class NoLookup:
        provider_name = 'offline'
        def search(self, query):
            raise AssertionError('offline compiler cannot retrieve knowledge')
    registry = ToolRegistry()
    for tool in build_knowledge_tools(NoLookup(), include_retrieval_time=True):
        registry.register(tool)
    compiler = AgentRunCompiler(registry, request_policy=chat.CONTRACT.request_policy)
    def compile_with(builder):
        ctx = builder.build(execution, max_context_tokens=job.policy.max_context_tokens)
        assert not ctx.omitted_section_ids
        return compiler.compile(execution, ctx)
    old = compile_with(ProductContextBuilder(coach_contract=chat.CONTRACT, compact_json=True, purpose='observed'))
    new = compile_with(wording.PlayerWordingContextBuilder(purpose='observed'))
    # The selectable Worker must compile the same complete input as the offline
    # proposal, through its own manifest, policy and Runtime context guard.
    from app.runtime.coach_contract import require_coach_context
    worker_root = RuntimeCompositionRoot.from_directories(
        skills_root=player_wording_worker.ASSETS/'skills',
        prompt_programs_root=player_wording_worker.ASSETS/'prompt_programs',
        coach_contract=player_wording_worker.CONTRACT)
    worker_job = RecentReviewRuntimeRequestCompiler(worker_root.skill_catalog,
        coach_contract=player_wording_worker.CONTRACT).compile(
        ConversationRecentReviewRequest(count=5, queue=420, focus='overall'), player_summary=summary,
        deterministic_report=report, run_id=root.name, memory_context_binding=binding)
    worker_execution = SkillExecutionBoundary(worker_root.skill_catalog).validate(worker_job.execution_request)
    worker_context = ProductContextBuilder(coach_contract=player_wording_worker.CONTRACT,
        compact_json=True, purpose='observed').build(worker_execution,
            max_context_tokens=worker_job.policy.max_context_tokens)
    require_coach_context(worker_context, player_wording_worker.CONTRACT)
    worker_compiled = AgentRunCompiler(registry, request_policy=player_wording_worker.CONTRACT.request_policy).compile(
        worker_execution, worker_context)
    assert worker_compiled == new
    assert old.messages[1:] == new.messages[1:] and old.allowed_tools == new.allowed_tools
    assert all(new.metadata[k] == v for k,v in old.metadata.items() if k != 'context_estimated_tokens')
    rows = []
    for ordinal in (1, 2, 3):
        req = request_from_raw((transport/f'generation/request-{ordinal:03}.json').read_bytes())
        assert req.messages[:len(old.messages)] == old.messages
        assert all(req.metadata[k] == v for k,v in json.loads(json.dumps(dict(old.metadata))).items())
        assert req.tools == tuple(_to_tool_spec(registry.get(t)) for t in old.allowed_tools)
        assert sha256(chat.request_bytes(req)).hexdigest() == read(transport/f'call-{ordinal:03}.json')['request_sha256']
        trial = replace(req, messages=(*new.messages, *req.messages[len(old.messages):]),
                        metadata={**req.metadata, **new.metadata})
        wire = chat.request_bytes(trial)
        rows.append(dict(ordinal=ordinal, before=ceiling(req), after=ceiling(trial), wire_bytes=len(wire),
                         sha256=sha256(wire).hexdigest(), output_limit=req.max_tokens))
    checks = []
    for n in range(4,8):
        p = transport/f'review/call-{n:03}'
        saved = read(p/'validation-context.json')
        for contract in (chat, responses):
            restored = contract.restore_context(dict(saved, version=contract.VERSION))
            req = contract.make_request(restored, saved['duty'], saved['stage'])
            req = replace(req, metadata={**req.metadata, 'coach_budget_contract':'coach-bounded-review-v2'})
            digest = sha256(contract.request_bytes(req)).hexdigest()
            if contract is chat:
                assert digest == read(transport/f'call-{n:03}.json')['request_sha256']
            checks.append(dict(ordinal=n, route=contract.VERSION, input_ceiling=ceiling(req), sha256=digest))
    total = 18467 + rows[-1]['after'] + rows[-1]['output_limit'] + 321536
    assert total <= 401920 and rows[-1]['output_limit'] == 15135
    return dict(version=wording.VERSION, run=root.name, rows=rows, reviews=checks, historical_third_total=total,
                historical_third_margin=401920-total, model_calls=0, worker_enabled=False,
                explicit_worker_contract=player_wording_worker.CONTRACT.snapshot().model_dump(mode='json'),
                explicit_worker_input_matches_offline=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_root', type=Path)
    print(json.dumps(verify(parser.parse_args().run_root), ensure_ascii=True, indent=2))
