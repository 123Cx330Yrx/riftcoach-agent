from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.memory.context_models import (
    MemoryContextBinding,
    MemoryContextManifest,
    MemoryContextManifestDisposition,
    MemoryContextManifestRef,
    MemoryContextRecord,
    MemoryContextRecordKind,
    MemoryContextSnapshot,
    canonical_memory_context_manifest_bytes,
    compute_memory_context_manifest_sha256,
)
from app.players.models import RelationshipRole


OWNER = "owner-context"
CONVERSATION_ID = UUID("10000000-0000-0000-0000-000000000001")
RELATIONSHIP_ID = UUID("10000000-0000-0000-0000-000000000002")
SUBJECT_ID = UUID("10000000-0000-0000-0000-000000000003")
RECORD_ID = UUID("10000000-0000-0000-0000-000000000004")
DIGEST = "a" * 64


def binding(**overrides: object) -> MemoryContextBinding:
    values: dict[str, object] = {
        "run_id": "review_context_001",
        "owner_id": OWNER,
        "conversation_id": CONVERSATION_ID,
        "relationship_id": RELATIONSHIP_ID,
        "player_subject_id": SUBJECT_ID,
        "relationship_role": RelationshipRole.SELF,
    }
    values.update(overrides)
    return MemoryContextBinding(**values)


def record(**overrides: object) -> MemoryContextRecord:
    values: dict[str, object] = {
        "kind": MemoryContextRecordKind.PLAYER_PROFILE,
        "record_id": RECORD_ID,
        "version": 2,
        "content_sha256": DIGEST,
        "content": '{"memory_key":"main_role","value":"mid"}',
        "priority": 700,
        "stable_order": "profile:main_role:0000000002",
        "relationship_role": RelationshipRole.SELF,
    }
    values.update(overrides)
    return MemoryContextRecord(**values)


def test_binding_is_strict_and_normalizes_only_valid_utc_independent_identity() -> None:
    value = binding()

    assert value.run_id == "review_context_001"
    assert value.relationship_role is RelationshipRole.SELF
    with pytest.raises(ValidationError):
        binding(owner_id="../escape")
    with pytest.raises(ValidationError):
        binding(run_id="../escape")


def test_context_record_rejects_bad_digest_blank_content_and_instructional_kind() -> None:
    assert record().content_sha256 == DIGEST
    with pytest.raises(ValidationError):
        record(content_sha256="A" * 64)
    with pytest.raises(ValidationError):
        record(content="  ")
    with pytest.raises(ValidationError):
        record(priority=True)


def test_snapshot_rejects_duplicate_refs_and_observed_self_only_records() -> None:
    item = record()
    snapshot = MemoryContextSnapshot(binding=binding(), records=(item,))
    assert snapshot.records == (item,)

    with pytest.raises(ValidationError, match="duplicate"):
        MemoryContextSnapshot(binding=binding(), records=(item, item))
    with pytest.raises(ValidationError, match="observed"):
        MemoryContextSnapshot(
            binding=binding(relationship_role=RelationshipRole.OBSERVED),
            records=(item,),
        )
    with pytest.raises(ValidationError, match="self snapshot"):
        MemoryContextSnapshot(
            binding=binding(),
            records=(
                record(
                    kind=MemoryContextRecordKind.REVIEW_MEMORY,
                    relationship_role=RelationshipRole.OBSERVED,
                ),
            ),
        )


def test_observed_snapshot_allows_messages_preferences_and_observed_review_only() -> None:
    observed = binding(relationship_role=RelationshipRole.OBSERVED)
    records = (
        record(
            kind=MemoryContextRecordKind.MESSAGE,
            relationship_role=RelationshipRole.OBSERVED,
            stable_order="message:0000000001",
        ),
        record(
            kind=MemoryContextRecordKind.OWNER_PREFERENCE,
            relationship_role=None,
            stable_order="preference:report_language",
        ),
        record(
            kind=MemoryContextRecordKind.REVIEW_MEMORY,
            relationship_role=RelationshipRole.OBSERVED,
            stable_order="review:public_trend",
        ),
    )

    assert MemoryContextSnapshot(binding=observed, records=records).records == records


def test_manifest_is_body_free_stable_and_digest_bound() -> None:
    selected = MemoryContextManifestRef(
        kind=MemoryContextRecordKind.PLAYER_PROFILE,
        record_id=RECORD_ID,
        version=2,
        content_sha256=DIGEST,
        disposition=MemoryContextManifestDisposition.SELECTED,
        omission_reason=None,
    )
    omitted = MemoryContextManifestRef(
        kind=MemoryContextRecordKind.MESSAGE,
        record_id=UUID("10000000-0000-0000-0000-000000000005"),
        version=1,
        content_sha256="b" * 64,
        disposition=MemoryContextManifestDisposition.OMITTED,
        omission_reason="context_budget",
    )
    manifest = MemoryContextManifest(
        binding=binding(),
        selector_policy_version="memory-context-v1",
        effective_context_ceiling=16000,
        estimated_context_units=9000,
        candidate_count=2,
        selected_count=1,
        omitted_count=1,
        records=(selected, omitted),
        created_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )

    encoded = canonical_memory_context_manifest_bytes(manifest)
    assert b"main_role" not in encoded
    assert b'"content"' not in encoded
    assert compute_memory_context_manifest_sha256(manifest) == (
        compute_memory_context_manifest_sha256(manifest)
    )
    assert len(compute_memory_context_manifest_sha256(manifest)) == 64

    with pytest.raises(ValidationError, match="counts"):
        MemoryContextManifest.model_validate(
            {**manifest.model_dump(mode="python"), "selected_count": 2}
        )
