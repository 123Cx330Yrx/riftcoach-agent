"""Opt-in native Coach composition using the existing product publication path."""
from pathlib import Path

from app.agent.memory_context import MemoryAwareContextBuilder
from app.evaluation.golden_native_issues_review import NativeBusinessReviewWorkflow
from app.lol.report_renderer import render_deterministic_report
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.rag.provider import KnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import AgentRuntimeV1, RuntimeExecutionFactory
from .recent_review import RecentReviewRuntimeRequestCompiler
from .recent_review_service import RecentReviewApplicationService
from .run_receipts import FileRunReceiptStore


ASSETS = Path(__file__).resolve().parents[2] / 'examples/runtime_profiles/flash_v2_native'


def build_native_coach_application(*, summary_builder, provider_factory, knowledge_provider,
        runs_root, memory_repository=None, memory_manifest_store=None,
        publication_sources=None, publication_writer=None, report_renderer=None):
    """Explicit server-side construction only; no environment reads or outbound IO.

    provider_factory creates one fresh receipted transport per trusted run and
    exposes its identity-only descriptor. Worker defaults remain unchanged.
    """
    if not all(callable(getattr(summary_builder, name, None)) for name in ('build', 'build_by_puuid')):
        raise TypeError('summary_builder must expose both typed entrypoints')
    if not isinstance(knowledge_provider, KnowledgeProvider):
        raise TypeError('knowledge_provider must satisfy KnowledgeProvider')
    if not callable(provider_factory):
        raise TypeError('provider_factory must be callable')
    if (memory_repository is None) != (memory_manifest_store is None):
        raise ValueError('Memory repository and manifest store must be supplied together')
    contract = NATIVE_COACH_CONTRACT
    root = RuntimeCompositionRoot.from_directories(skills_root=ASSETS/'skills',
        prompt_programs_root=ASSETS/'prompt_programs', coach_contract=contract)
    context = CoachContextBuilder(coach_contract=contract, compact_json=True)
    if memory_repository is not None:
        context = MemoryAwareContextBuilder(delegate=context, repository=memory_repository,
            manifest_store=memory_manifest_store)
    factory = RuntimeExecutionFactory(knowledge_provider=CoachingQueryKnowledgeProvider(knowledge_provider),
        coach_contract=contract, review_workflow_factory=lambda runtime, provider:
            NativeBusinessReviewWorkflow(SharedBudgetReviewSender(provider)))
    runtime = AgentRuntimeV1(runs_root=runs_root, catalog=root.skill_catalog,
        provider=provider_factory.descriptor, provider_factory=provider_factory, execution_factory=factory,
        context_builder=context, prompt_program_resolver=root.prompt_program_resolver)
    return RecentReviewApplicationService(summary_builder=summary_builder,
        compiler=RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=contract),
        runtime=runtime, receipt_writer=FileRunReceiptStore(runs_root),
        publication_sources=publication_sources, publication_writer=publication_writer,
        report_renderer=report_renderer or render_deterministic_report)
