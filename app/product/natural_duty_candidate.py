"""Explicit dependency-injected natural workflows on the product Runtime.

Construction loads no keys and changes no default. Diagnostic contracts retain
their unpublished outcomes; the separate product contract uses ProductWorkflow.
"""
from pathlib import Path
from copy import deepcopy

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
        publication_sources=None, publication_writer=None, candidate=None, execution_session=None,
        patch_coordination=None):
    if patch_coordination is not None and execution_session is None:
        raise ValueError('natural_patch_coordination_requires_session')
    patch_coordination = deepcopy(patch_coordination)
    if candidate is None:
        from app.evaluation import natural_duty_contract as candidate
        provider_type, assets = NaturalDutyProvider, ASSETS
    else:
        from app.evaluation import sol_natural_contract, sol_necessity_contract, sol_review_contract
        from app.product import sol_contract
        from app.runtime.sol_natural_provider import SolNaturalProvider
        if candidate not in (sol_natural_contract, sol_necessity_contract, sol_review_contract, sol_contract):
            raise ValueError("unsupported_natural_candidate")
        provider_type, assets = SolNaturalProvider, ROOT/"examples/runtime_profiles/sol_natural_v1"
        if candidate is sol_necessity_contract:
            assets = ROOT/'examples/runtime_profiles/sol_necessity_v1'
        elif candidate in (sol_review_contract, sol_contract):
            assets = candidate.ASSETS
        if candidate is sol_contract and execution_session is None:
            raise ValueError("product_requires_durable_session")
    contract = candidate.CONTRACT
    if getattr(provider_factory.descriptor, 'contract_module', candidate) is not candidate:
        raise ValueError('natural_candidate_provider_contract')
    if execution_session is not None:
        from app.evaluation import sol_natural_contract, sol_necessity_contract, sol_review_contract
        from app.product import sol_contract
        from app.evaluation.sol_natural_session import CandidateSession
        if (candidate not in (sol_natural_contract, sol_necessity_contract, sol_review_contract, sol_contract)
                or type(execution_session) is not CandidateSession
                or execution_session.contract_module is not candidate):
            raise ValueError('session_requires_sol_candidate')
    if (memory_repository is None) != (memory_manifest_store is None):
        raise ValueError('Memory repository and manifest store must be supplied together')
    contract.require_provider(provider_factory.descriptor)
    root = RuntimeCompositionRoot.from_directories(skills_root=assets/'skills',
        prompt_programs_root=assets/'prompt_programs', coach_contract=contract)
    context = CoachContextBuilder(coach_contract=contract, compact_json=True)
    if memory_repository is not None:
        context = MemoryAwareContextBuilder(delegate=context, repository=memory_repository,
            manifest_store=memory_manifest_store)

    def bound_provider(run_id):
        provider = provider_factory(run_id)
        if type(provider) is not provider_type:
            raise TypeError('natural duty requires its exact routed provider')
        contract.require_provider(provider)
        provider.candidate_run_id = run_id
        return provider

    def workflow(_runtime, budget):
        routed = budget.provider._delegate
        routed.candidate_budget = budget
        run_id = routed.candidate_run_id
        workflow_type = NaturalDutyWorkflow
        if execution_session is not None:
            from app.runtime.sol_session_runtime import SessionWorkflow
            from app.product import sol_contract
            from app.product.sol_workflow import ProductWorkflow
            selected_workflow = ProductWorkflow if candidate is sol_contract else SessionWorkflow
            return selected_workflow(SharedBudgetReviewSender(budget), session=execution_session,
                journal_root=execution_session.journal_root, contract_module=candidate,
                patch_coordination=patch_coordination)
        return workflow_type(SharedBudgetReviewSender(budget),
            journal_root=Path(runs_root)/run_id/'natural-duty-journal', contract_module=candidate)

    session_factories = {}
    if execution_session is not None:
        from app.runtime.sol_session_runtime import SessionBudget, SessionTools
        from app.product import sol_contract
        from app.product.sol_workflow import ProductBudget
        selected_budget = ProductBudget if candidate is sol_contract else SessionBudget
        session_factories = dict(
            budget_factory=lambda provider, **kwargs: selected_budget(provider, session=execution_session, **kwargs),
            knowledge_runtime_factory=lambda registry: SessionTools(registry, session=execution_session))
    factory = RuntimeExecutionFactory(knowledge_provider=CoachingQueryKnowledgeProvider(knowledge_provider),
        coach_contract=contract, review_workflow_factory=workflow, **session_factories)
    runtime = DispatchAwareRuntime(runs_root=runs_root, catalog=root.skill_catalog,
        provider=provider_factory.descriptor, provider_factory=bound_provider,
        execution_factory=factory, context_builder=context, prompt_program_resolver=root.prompt_program_resolver)
    return RecentReviewApplicationService(summary_builder=summary_builder,
        compiler=RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=contract),
        runtime=runtime, receipt_writer=FileRunReceiptStore(runs_root),
        publication_sources=publication_sources, publication_writer=publication_writer,
        publication_report_renderer=render_native_publication_context, report_renderer=render_deterministic_report)
