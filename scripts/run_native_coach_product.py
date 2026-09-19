"""One bounded native product run using frozen ShowMaker facts and real local RAG.

Preview compiles the first request without credentials, network or run writes.
Execution requires exact-SHA public CI and the reviewed five-control result.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from app.agent.loop import _to_tool_spec
from app.evidence.publication import EvidencePublicationContext, EvidencePublicationSources
from app.evidence.publication_store import FileEvidencePublicationStore
from app.evidence.storage import bundle_from_storage_projection
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.memory.context_models import MemoryContextBinding, MemoryContextSnapshot
from app.players.models import RelationshipRole
from app.product.native_coach_composition import build_native_coach_application
from app.product.recent_review import ConversationRecentReviewRequest
from app.providers.models import ChatRequest, ToolChoiceMode
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT
from app.runtime.receipted_provider_factory import RunScopedReceiptedProviderFactory
from app.skills.execution import SkillExecutionBoundary
from scripts.run_golden_native_review import prepare, DATASET, ROOT
from scripts.run_golden_inference_development import verify_public_ci

PRODUCT_LIVE_STATUS = 'offline_source_binding_and_attribution_review'


class EmptyObservedMemory:
    def load(self, binding):
        return MemoryContextSnapshot(binding=binding, records=())


class NoopObserver:
    def observe(self, signal):
        pass


def run(args):
    if args.execute and PRODUCT_LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError('native_product_semantic_qualification_required')
    _, original = prepare(1)  # Hash-check every frozen source; no old report is generated.
    source_run = ROOT/json.loads(DATASET.read_text(encoding='utf-8'))['source_bindings']['source_run']
    bundle = bundle_from_storage_projection(json.loads((source_run/'evidence_bundle.json').read_text(encoding='utf-8')))
    run_id = args.run_id or 'native-product-preview'
    context = EvidencePublicationContext(owner_id='native-coach-development',
        task_id=uuid5(NAMESPACE_URL, 'riftcoach-native:'+run_id), run_id=run_id,
        request_fingerprint=digest(compact(dict(count=5, queue=420, role='observed'))))
    memory = MemoryContextBinding(run_id=run_id, owner_id=context.owner_id,
        conversation_id=uuid5(NAMESPACE_URL, run_id+':conversation'),
        relationship_id=uuid5(NAMESPACE_URL, run_id+':relationship'),
        player_subject_id=uuid5(NAMESPACE_URL, 'riftcoach:ShowMaker'), relationship_role=RelationshipRole.OBSERVED)
    settings = SimpleNamespace(model='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4')
    head = None
    if args.execute:
        if not args.run_id.startswith('native-product-'):
            raise ValueError('native_product_run_id_required')
        controls = json.loads((ROOT/'data/evaluation/results/golden_native_review_result_a71eb94.json').read_text(encoding='utf-8'))
        if controls['controls_accepted'] != 5 or not all(c['manual_semantic_acceptance'] for c in controls['cases']):
            raise ValueError('native_controls_not_qualified')
        head = verify_public_ci(args.ci_run)
        from dotenv import dotenv_values
        from app.providers.config import load_zhipu_settings
        settings = load_zhipu_settings(dotenv_values(args.env_file))
    factory = RunScopedReceiptedProviderFactory(settings=settings, transport_root=args.output_root/'transport')
    class Summary:
        def build(self, **kwargs): return deepcopy(original.player_summary)
        def build_by_puuid(self, **kwargs): return deepcopy(original.player_summary)
    publication = FileEvidencePublicationStore(args.output_root/'reports')
    app = build_native_coach_application(summary_builder=Summary(), provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT/'data/rag_docs'),
        runs_root=args.output_root/'reports', memory_repository=EmptyObservedMemory(),
        memory_manifest_store=FileMemoryContextManifestStore(args.output_root/'reports'),
        publication_sources=EvidencePublicationSources(now=datetime.now(timezone.utc), data_dragon=bundle.data_dragon,
            official_patch=bundle.official_patch, meta_evidence=bundle.meta_evidence), publication_writer=publication)
    request = ConversationRecentReviewRequest(count=5,queue=420)
    # Use the actual compiler and Agent request compiler. Empty Memory adds no
    # prompt records; the frozen observed identity is already in user_utterance.
    projection = app._publication_sources.project(deepcopy(original.player_summary), routing_region='asia')
    compiled = app._compiler.compile(request, player_summary=deepcopy(original.player_summary),
        deterministic_report=app._render_report(original.player_summary, projection=projection),
        run_id=run_id, memory_context_binding=memory)
    execution = SkillExecutionBoundary(app._runtime._catalog).validate(compiled.execution_request)
    ctx = CoachContextBuilder(coach_contract=NATIVE_COACH_CONTRACT, compact_json=True).build(
        execution, max_context_tokens=compiled.policy.max_context_tokens)
    parts = app._runtime._execution_factory.build(provider=factory.descriptor, observer=NoopObserver())
    agent = parts.draft_preparer._compiler.compile(execution, ctx)
    registry = parts.draft_preparer._agent_loop.tool_registry
    first = ChatRequest(messages=agent.messages,
        tools=tuple(_to_tool_spec(registry.get(name)) for name in agent.allowed_tools), tool_choice=ToolChoiceMode.AUTO,
        max_tokens=agent.max_tokens, temperature=agent.temperature, top_p=agent.top_p,
        timeout_s=min(agent.timeout_s,300), metadata={**agent.metadata,'agent_loop_iteration':1})
    ceiling = estimate_runtime_request_input_ceiling(first)
    if ceiling > NATIVE_COACH_CONTRACT.descriptor()['max_input_tokens']:
        raise ValueError('native_product_initial_input_budget_exceeded')
    plan = dict(run_id=run_id, head_sha=head, ci_run=args.ci_run, source_scope='frozen_ShowMaker_development_not_current_meta',
        contract=NATIVE_COACH_CONTRACT.snapshot().model_dump(), first_input_ceiling=ceiling,
        total_calls=5, total_tokens=401920, max_seconds=900, max_revisions=1,
        production_admitted=False, real_generation_included=args.execute, semantic_approval=False)
    plan['live_status'] = PRODUCT_LIVE_STATUS
    if not args.execute:
        print(compact(plan))
        return plan
    directory = args.output_root/'observations'/run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory/'plan.json',plan)
    outcome = dict(status='failed', semantic_approval=False, production_admitted=False)
    try:
        result = app.review_by_puuid(request, puuid='frozen-observation', routing_region='asia',
            game_name='DK ShowMaker',tag_line='KR1',run_id=run_id,memory_context_binding=memory,publication_context=context)
        manifest = publication.read(context)
        pending = publication.read_pending_snapshot(context)
        outcome.update(status=result.publication_status.value, report_available=result.output.report is not None,
            report_sha256=manifest.report.sha256 if manifest.report else None,
            evidence_bundle_digest=manifest.bundle.bundle_digest, pending_snapshot_run_id=pending.run_id,
            result=result.model_dump(mode='json'))
    except Exception as exc:
        outcome['error_type'] = type(exc).__name__  # No arbitrary private error body.
    finally:
        responses = list((args.output_root/'transport'/run_id).glob('response-*.json'))
        responses_data=[json.loads(p.read_text(encoding='utf-8')) for p in responses]
        reservations=list((args.output_root/'transport'/run_id).glob('stream-*/reservation.json'))
        outcome.update(reserved_calls=len(reservations),completed_calls=len(responses),
            input_tokens=sum(r['usage']['input_tokens'] for r in responses_data),
            output_tokens=sum(r['usage']['output_tokens'] for r in responses_data),
            unknown_usage_calls=len(reservations)-len(responses))
        write_new_json(directory/'result.json',outcome)
    print(compact({k:v for k,v in outcome.items() if k != 'result'}))
    return outcome


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--run-id',default='')
    parser.add_argument('--ci-run',default='')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--output-root',type=Path,default=ROOT/'data/runs/native_product')
    run(parser.parse_args())
