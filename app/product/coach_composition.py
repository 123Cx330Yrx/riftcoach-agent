"""Explicit, unadmitted Coach application; production Worker defaults stay put."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.evidence.publication import EvidencePublicationSources, EvidencePublicationWriter

from app.agent.memory_context import (
    MemoryAwareContextBuilder,
    MemoryContextManifestWriter,
    MemoryContextRepository,
)
from app.providers.protocol import LLMProvider
from app.rag.provider import KnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.lol.report_renderer import render_deterministic_report

from .recent_review import RecentReviewRuntimeRequestCompiler
from .recent_review_service import RecentReviewApplicationService, RecentReviewSummaryBuilder
from .run_receipts import FileRunReceiptStore


_COACH_ASSETS = Path(__file__).resolve().parents[2] / "examples/runtime_profiles/flash_v2_batch"


def build_coach_application(
    *,
    summary_builder: RecentReviewSummaryBuilder,
    provider: LLMProvider,
    knowledge_provider: KnowledgeProvider,
    runs_root: str | Path,
    memory_repository: MemoryContextRepository | None = None,
    memory_manifest_store: MemoryContextManifestWriter | None = None,
    publication_sources: EvidencePublicationSources | None = None,
    publication_writer: EvidencePublicationWriter | None = None,
    report_renderer=None,
    compact_context_json: bool = False,
    coach_contract=BATCH_COACH_CONTRACT,
) -> RecentReviewApplicationService:
    """Assemble explicit verified assets; default remains the frozen 1.2.0 bundle.

    Construction reads only repository-local assets, not environment or secrets,
    and performs no outbound calls or run writes. Calls can occur later through
    the injected dependencies when review() / review_by_puuid() is invoked.
    This is not registration, activation, or a production Worker entry point.

    Memory dependencies are an explicit pair so the wrapper cannot silently
    replace the trusted Coach policy. A request carrying a Memory binding when
    Memory is unconfigured fails through the existing Runtime boundary.
    """

    if not all(
        callable(getattr(summary_builder, name, None))
        for name in ("build", "build_by_puuid")
    ):
        raise TypeError("summary_builder must expose build() and build_by_puuid()")
    if not isinstance(knowledge_provider, KnowledgeProvider):
        raise TypeError("knowledge_provider must satisfy KnowledgeProvider")
    if (memory_repository is None) != (memory_manifest_store is None):
        raise ValueError("Memory repository and manifest store must be supplied together")

    if coach_contract is not BATCH_COACH_CONTRACT and coach_contract is not GOLDEN_COACH_CONTRACT:
        raise ValueError("application requires an explicit supported Coach contract")
    assets = (_COACH_ASSETS.parent / "flash_v2_golden"
              if coach_contract is GOLDEN_COACH_CONTRACT else _COACH_ASSETS)
    context_builder: CoachContextBuilder | MemoryAwareContextBuilder
    context_builder = CoachContextBuilder(coach_contract=coach_contract,
                                         compact_json=compact_context_json)
    if memory_repository is not None and memory_manifest_store is not None:
        context_builder = MemoryAwareContextBuilder(
            delegate=context_builder,
            repository=memory_repository,
            manifest_store=memory_manifest_store,
        )

    root = RuntimeCompositionRoot.from_directories(
        skills_root=assets / "skills",
        prompt_programs_root=assets / "prompt_programs",
        coach_contract=coach_contract,
    )
    runtime = root.build_offline_coach_runtime(
        runs_root=runs_root,
        provider=provider,
        knowledge_provider=knowledge_provider,
        context_builder=context_builder,
    )
    return RecentReviewApplicationService(
        summary_builder=summary_builder,
        compiler=RecentReviewRuntimeRequestCompiler(
            root.skill_catalog, coach_contract=coach_contract,
        ),
        runtime=runtime,
        receipt_writer=FileRunReceiptStore(runs_root),
        publication_sources=publication_sources,
        publication_writer=publication_writer,
        report_renderer=report_renderer or render_deterministic_report,
    )


__all__ = ["build_coach_application"]
