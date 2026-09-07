"""Explicit, unadmitted Coach application; production Worker defaults stay put."""

from __future__ import annotations

from pathlib import Path

from app.agent.memory_context import (
    MemoryAwareContextBuilder,
    MemoryContextManifestWriter,
    MemoryContextRepository,
)
from app.providers.protocol import LLMProvider
from app.rag.provider import KnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import BATCH_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot

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
) -> RecentReviewApplicationService:
    """Assemble the verified 1.2.0 bundle from already constructed dependencies.

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

    context_builder: CoachContextBuilder | MemoryAwareContextBuilder
    context_builder = CoachContextBuilder(coach_contract=BATCH_COACH_CONTRACT)
    if memory_repository is not None and memory_manifest_store is not None:
        context_builder = MemoryAwareContextBuilder(
            delegate=context_builder,
            repository=memory_repository,
            manifest_store=memory_manifest_store,
        )

    root = RuntimeCompositionRoot.from_directories(
        skills_root=_COACH_ASSETS / "skills",
        prompt_programs_root=_COACH_ASSETS / "prompt_programs",
        coach_contract=BATCH_COACH_CONTRACT,
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
            root.skill_catalog, coach_contract=BATCH_COACH_CONTRACT,
        ),
        runtime=runtime,
        receipt_writer=FileRunReceiptStore(runs_root),
    )


__all__ = ["build_coach_application"]
