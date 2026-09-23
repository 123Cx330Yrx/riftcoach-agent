"""Opt-in native Coach composition using the existing product publication path."""
from pathlib import Path

from app.agent.memory_context import MemoryAwareContextBuilder
from app.evaluation.golden_native_issues_review import NativeBusinessReviewWorkflow
from app.lol.report_renderer import render_deterministic_report
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.rag.provider import KnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT
from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import AgentRuntimeV1, RuntimeExecutionFactory
from .recent_review import RecentReviewRuntimeRequestCompiler
from .recent_review_service import RecentReviewApplicationService
from .run_receipts import FileRunReceiptStore


ASSETS = Path(__file__).resolve().parents[2] / 'examples/runtime_profiles/flash_v2_native'
ROLE_ASSETS = Path(__file__).resolve().parents[2] / 'examples/runtime_profiles/flash_glm_review_v1'


def render_native_publication_context(report, summary, projection):
    """Use the very projection that will be saved, including expired-source gaps.

    The same deterministic document reaches generation, review and revision.
    No second projection, fetch, inferred training goal or timestamp is created.
    """
    import hashlib
    import json
    from app.evaluation.golden_source_context import render_source_context
    from .coach_positions import position_context
    encoded = json.dumps(summary, sort_keys=True, ensure_ascii=True,
                         separators=(',', ':'), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != projection.summary_digest:
        raise ValueError('native_publication_summary_mismatch')
    roles = position_context(summary)
    return (report + '\n\nEvidence snapshot digest: ' + projection.summary_digest
        + '\nEvidence bundle digest: ' + projection.bundle.digest
        + '\nPosition context (sample facts, not a training goal): ' + roles.model_dump_json()
        + render_source_context(projection.bundle, roles))


def _build_coach_application(*, contract, assets, workflow_type, summary_builder, provider_factory, knowledge_provider,
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
    root = RuntimeCompositionRoot.from_directories(skills_root=assets/'skills',
        prompt_programs_root=assets/'prompt_programs', coach_contract=contract)
    context = CoachContextBuilder(coach_contract=contract, compact_json=True)
    if memory_repository is not None:
        context = MemoryAwareContextBuilder(delegate=context, repository=memory_repository,
            manifest_store=memory_manifest_store)
    factory = RuntimeExecutionFactory(knowledge_provider=CoachingQueryKnowledgeProvider(knowledge_provider),
        coach_contract=contract, review_workflow_factory=lambda runtime, provider:
            workflow_type(SharedBudgetReviewSender(provider)))
    runtime = AgentRuntimeV1(runs_root=runs_root, catalog=root.skill_catalog,
        provider=provider_factory.descriptor, provider_factory=provider_factory, execution_factory=factory,
        context_builder=context, prompt_program_resolver=root.prompt_program_resolver)
    return RecentReviewApplicationService(summary_builder=summary_builder,
        compiler=RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=contract),
        runtime=runtime, receipt_writer=FileRunReceiptStore(runs_root),
        publication_sources=publication_sources, publication_writer=publication_writer,
        publication_report_renderer=render_native_publication_context,
        report_renderer=report_renderer or render_deterministic_report)


def build_native_coach_application(**kwargs):
    """Original single-model opt-in composition; default behavior is unchanged."""
    return _build_coach_application(contract=NATIVE_COACH_CONTRACT, assets=ASSETS,
        workflow_type=NativeBusinessReviewWorkflow, **kwargs)


def build_role_coach_application(**kwargs):
    """Explicit adopted role candidate; this construction does not grant admission."""
    return _build_coach_application(contract=ROLE_COACH_CONTRACT, assets=ROLE_ASSETS,
        workflow_type=RoleNoteReviewWorkflow, **kwargs)
