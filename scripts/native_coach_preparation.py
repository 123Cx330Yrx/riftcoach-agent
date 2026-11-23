"""Shared frozen ShowMaker application preparation; never reads credentials or sends provider IO."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.agent.loop import _to_tool_spec
from app.evidence.publication import EvidencePublicationContext, EvidencePublicationSources
from app.evidence.publication_store import FileEvidencePublicationStore
from app.evidence.storage import bundle_from_storage_projection
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.memory.context_models import MemoryContextBinding, MemoryContextSnapshot
from app.players.models import RelationshipRole
from app.product.recent_review import ConversationRecentReviewRequest
from app.providers.models import ChatRequest, ToolChoiceMode
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.skills.execution import SkillExecutionBoundary
from scripts.run_golden_native_review import DATASET, ROOT, prepare


class EmptyObservedMemory:
    def load(self, binding):
        return MemoryContextSnapshot(binding=binding, records=())


class NoopObserver:
    def observe(self, signal):
        pass


def load_frozen_sources():
    """Use the same original, hash-checked sources as the native preview."""
    _, original = prepare(1)
    source_run = ROOT / json.loads(DATASET.read_text(encoding='utf-8'))['source_bindings']['source_run']
    bundle = bundle_from_storage_projection(json.loads((source_run / 'evidence_bundle.json').read_text(encoding='utf-8')))
    return deepcopy(original.player_summary), bundle


@dataclass(frozen=True)
class PreparedCoachApplication:
    app: object
    request: ConversationRecentReviewRequest
    memory: MemoryContextBinding
    context: EvidencePublicationContext
    publication: FileEvidencePublicationStore
    first_request: ChatRequest
    first_input_ceiling: int
    source_now: datetime


def prepare_frozen_application(*, builder, contract, provider_factory, output_root, run_id, now=None):
    """Compile once against one projection timestamp and the actual application.

    The runtime later loads the same empty observed Memory and uses this same
    source object. No fixture report or expected review is supplied to the model.
    """
    summary, bundle = load_frozen_sources()
    source_now = now if now is not None else datetime.now(timezone.utc)
    output_root = Path(output_root)
    context = EvidencePublicationContext(owner_id='native-coach-development',
        task_id=uuid5(NAMESPACE_URL, 'riftcoach-native:' + run_id), run_id=run_id,
        request_fingerprint=digest(compact(dict(count=5, queue=420, role='observed'))))
    memory = MemoryContextBinding(run_id=run_id, owner_id=context.owner_id,
        conversation_id=uuid5(NAMESPACE_URL, run_id + ':conversation'),
        relationship_id=uuid5(NAMESPACE_URL, run_id + ':relationship'),
        player_subject_id=uuid5(NAMESPACE_URL, 'riftcoach:ShowMaker'), relationship_role=RelationshipRole.OBSERVED)

    class Summary:
        def build(self, **kwargs):
            return deepcopy(summary)

        def build_by_puuid(self, **kwargs):
            return deepcopy(summary)

    publication = FileEvidencePublicationStore(output_root / 'reports')
    app = builder(summary_builder=Summary(), provider_factory=provider_factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT / 'data/rag_docs'),
        runs_root=output_root / 'reports', memory_repository=EmptyObservedMemory(),
        memory_manifest_store=FileMemoryContextManifestStore(output_root / 'reports'),
        publication_sources=EvidencePublicationSources(now=source_now, data_dragon=bundle.data_dragon,
            official_patch=bundle.official_patch, meta_evidence=bundle.meta_evidence), publication_writer=publication)
    request = ConversationRecentReviewRequest(count=5, queue=420)
    projection = app._publication_sources.project(deepcopy(summary), routing_region='asia')
    compiled = app._compiler.compile(request, player_summary=deepcopy(summary),
        deterministic_report=app._render_report(summary, projection=projection),
        run_id=run_id, memory_context_binding=memory)
    execution = SkillExecutionBoundary(app._runtime._catalog).validate(compiled.execution_request)
    ctx = CoachContextBuilder(coach_contract=contract, compact_json=True).build(
        execution, max_context_tokens=compiled.policy.max_context_tokens)
    parts = app._runtime._execution_factory.build(provider=provider_factory.descriptor, observer=NoopObserver())
    agent = parts.draft_preparer._compiler.compile(execution, ctx)
    registry = parts.draft_preparer._agent_loop.tool_registry
    first = ChatRequest(messages=agent.messages,
        tools=tuple(_to_tool_spec(registry.get(name)) for name in agent.allowed_tools),
        tool_choice=ToolChoiceMode.AUTO if agent.allowed_tools else ToolChoiceMode.NONE,
        max_tokens=agent.max_tokens, temperature=agent.temperature, top_p=agent.top_p,
        timeout_s=min(agent.timeout_s, contract.descriptor()['request_timeout_s']),
        metadata={**agent.metadata, 'agent_loop_iteration': 1})
    ceiling = estimate_runtime_request_input_ceiling(first)
    if ceiling > contract.descriptor()['max_input_tokens']:
        raise ValueError('native_product_initial_input_budget_exceeded')
    return PreparedCoachApplication(app, request, memory, context, publication, first, ceiling, source_now)
