"""Explicit dependency-injected candidate on the actual product Runtime.

No key loading, paid CLI or Worker/API registration. Model-pass outcomes are
retained for evaluation but never published by this unqualified adapter.
"""
from pathlib import Path

from app.evaluation.natural_duty_contract import CONTRACT, NaturalDutyProvider, ROOT
from app.evaluation.natural_duty_workflow import NaturalDutyWorkflow
from app.product.native_coach_composition import render_native_publication_context
from app.product.recent_review import RecentReviewRuntimeRequestCompiler
from app.product.recent_review_service import RecentReviewApplicationService
from app.product.run_receipts import FileRunReceiptStore
from app.lol.report_renderer import render_deterministic_report
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.agent.memory_context import MemoryAwareContextBuilder
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.runtime import RuntimeExecutionFactory
from app.runtime.dispatch_runtime import DispatchAwareRuntime
from app.runtime.review_sender import SharedBudgetReviewSender

ASSETS = ROOT/'examples/runtime_profiles/natural_duty_v1'


def build_natural_duty_candidate(*, summary_builder, provider_factory, knowledge_provider,
        runs_root, memory_repository=None, memory_manifest_store=None,
        publication_sources=None, publication_writer=None):
    if (memory_repository is None) != (memory_manifest_store is None):
        raise ValueError('Memory repository and manifest store must be supplied together')
    CONTRACT.require_provider(provider_factory.descriptor)
    root = RuntimeCompositionRoot.from_directories(skills_root=ASSETS/'skills',
        prompt_programs_root=ASSETS/'prompt_programs', coach_contract=CONTRACT)
    context = CoachContextBuilder(coach_contract=CONTRACT, compact_json=True)
    if memory_repository is not None:
        context = MemoryAwareContextBuilder(delegate=context, repository=memory_repository,
            manifest_store=memory_manifest_store)

    def bound_provider(run_id):
        provider = provider_factory(run_id)
        if type(provider) is not NaturalDutyProvider:
            raise TypeError('natural duty requires its exact routed provider')
        provider.candidate_run_id = run_id
        return provider

    def workflow(_runtime, budget):
        routed = budget.provider._delegate
        routed.candidate_budget = budget
        run_id = routed.candidate_run_id
        return NaturalDutyWorkflow(SharedBudgetReviewSender(budget),
            journal_root=Path(runs_root)/run_id/'natural-duty-journal')

    factory = RuntimeExecutionFactory(knowledge_provider=CoachingQueryKnowledgeProvider(knowledge_provider),
        coach_contract=CONTRACT, review_workflow_factory=workflow)
    runtime = DispatchAwareRuntime(runs_root=runs_root, catalog=root.skill_catalog,
        provider=provider_factory.descriptor, provider_factory=bound_provider,
        execution_factory=factory, context_builder=context, prompt_program_resolver=root.prompt_program_resolver)
    return RecentReviewApplicationService(summary_builder=summary_builder,
        compiler=RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=CONTRACT),
        runtime=runtime, receipt_writer=FileRunReceiptStore(runs_root),
        publication_sources=publication_sources, publication_writer=publication_writer,
        publication_report_renderer=render_native_publication_context, report_renderer=render_deterministic_report)
