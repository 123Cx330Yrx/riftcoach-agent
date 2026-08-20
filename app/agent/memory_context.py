from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

from app.agent.context import ContextBuilderV1, ContextSection, ContextTrust
from app.memory.context_models import (
    MemoryContextBinding,
    MemoryContextManifest,
    MemoryContextManifestDisposition,
    MemoryContextManifestRef,
    MemoryContextRecord,
    MemoryContextSnapshot,
)
from app.skills.execution import ValidatedSkillExecution


class MemoryContextRepository(Protocol):
    def load(self, binding: MemoryContextBinding) -> MemoryContextSnapshot: ...


class MemoryContextManifestWriter(Protocol):
    def write(self, manifest: MemoryContextManifest) -> str: ...


Clock = Callable[[], datetime]


class MemoryAwareContextBuilder:
    """Decorate the existing Builder with bounded, data-only Memory records."""

    def __init__(
        self,
        *,
        delegate: ContextBuilderV1,
        repository: MemoryContextRepository,
        manifest_store: MemoryContextManifestWriter,
        clock: Clock | None = None,
    ) -> None:
        if not isinstance(delegate, ContextBuilderV1):
            raise TypeError("delegate must be a ContextBuilderV1")
        if not callable(getattr(repository, "load", None)):
            raise TypeError("repository must expose load()")
        if not callable(getattr(manifest_store, "write", None)):
            raise TypeError("manifest_store must expose write()")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._delegate = delegate
        self._repository = repository
        self._manifest_store = manifest_store
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def build(
        self,
        execution: ValidatedSkillExecution,
        *,
        knowledge=None,
        max_context_tokens: int | None = None,
        memory_context_binding: MemoryContextBinding | None = None,
    ):
        if memory_context_binding is None:
            return self._delegate.build(
                execution,
                knowledge=knowledge,
                max_context_tokens=max_context_tokens,
            )
        if not isinstance(memory_context_binding, MemoryContextBinding):
            raise TypeError(
                "memory_context_binding must be a MemoryContextBinding or None"
            )
        if memory_context_binding.run_id != execution.run_id:
            raise ValueError("Memory Context run_id must match execution")

        snapshot = self._repository.load(memory_context_binding)
        if not isinstance(snapshot, MemoryContextSnapshot):
            raise TypeError("Memory Context repository returned an invalid snapshot")
        if snapshot.binding != memory_context_binding:
            raise ValueError("Memory Context snapshot binding drifted")

        sections = tuple(_record_section(row) for row in snapshot.records)
        bundle = self._delegate.build(
            execution,
            knowledge=knowledge,
            max_context_tokens=max_context_tokens,
            additional_data_sections=sections,
        )
        selected_ids = {section.section_id for section in bundle.sections}
        refs = tuple(
            MemoryContextManifestRef(
                kind=row.kind,
                record_id=row.record_id,
                version=row.version,
                content_sha256=row.content_sha256,
                disposition=(
                    MemoryContextManifestDisposition.SELECTED
                    if _record_section_id(row) in selected_ids
                    else MemoryContextManifestDisposition.OMITTED
                ),
                omission_reason=(
                    None
                    if _record_section_id(row) in selected_ids
                    else "context_budget"
                ),
            )
            for row in snapshot.records
        )
        selected_count = sum(
            row.disposition is MemoryContextManifestDisposition.SELECTED
            for row in refs
        )
        manifest = MemoryContextManifest(
            binding=memory_context_binding,
            selector_policy_version="memory-context-v1",
            effective_context_ceiling=bundle.max_context_tokens,
            estimated_context_units=bundle.estimated_tokens,
            candidate_count=len(refs),
            selected_count=selected_count,
            omitted_count=len(refs) - selected_count,
            records=refs,
            created_at=self._clock(),
        )
        digest = self._manifest_store.write(manifest)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("Memory Context manifest store returned a bad digest")
        return bundle


def _record_section(record: MemoryContextRecord) -> ContextSection:
    return ContextSection(
        section_id=_record_section_id(record),
        trust=ContextTrust.DETERMINISTIC_FACTS,
        source=f"memory:{record.kind.value}:{record.record_id}",
        content=json.dumps(
            {
                "schema_version": "1.0",
                "record_kind": record.kind.value,
                "relationship_role": (
                    None
                    if record.relationship_role is None
                    else record.relationship_role.value
                ),
                "value": record.content,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        required=False,
        priority=record.priority,
    )


def _record_section_id(record: MemoryContextRecord) -> str:
    return f"memory:{record.kind.value}:{record.record_id}"


__all__ = ["MemoryAwareContextBuilder"]
