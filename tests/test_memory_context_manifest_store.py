from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import json
import pytest

from app.memory.context_manifest_store import (
    FileMemoryContextManifestStore,
    MemoryContextManifestStoreError,
)
from app.memory.context_models import (
    MemoryContextBinding,
    MemoryContextManifest,
)
from app.players.models import RelationshipRole


def manifest(run_id: str = "review_manifest_001") -> MemoryContextManifest:
    return MemoryContextManifest(
        binding=MemoryContextBinding(
            run_id=run_id,
            owner_id="owner-manifest",
            conversation_id=UUID("30000000-0000-0000-0000-000000000001"),
            relationship_id=UUID("30000000-0000-0000-0000-000000000002"),
            player_subject_id=UUID("30000000-0000-0000-0000-000000000003"),
            relationship_role=RelationshipRole.SELF,
        ),
        selector_policy_version="memory-context-v1",
        effective_context_ceiling=16000,
        estimated_context_units=8000,
        candidate_count=0,
        selected_count=0,
        omitted_count=0,
        records=(),
        created_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )


def test_manifest_store_writes_canonical_body_free_file_and_replays(tmp_path) -> None:
    store = FileMemoryContextManifestStore(tmp_path)

    first = store.write(manifest())
    second = store.write(manifest())

    assert first == second
    path = tmp_path / "review_manifest_001" / "memory_context_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert "content" not in path.read_text(encoding="utf-8")
    assert not tuple(path.parent.glob("*.tmp"))


def test_manifest_store_rejects_existing_different_bytes(tmp_path) -> None:
    store = FileMemoryContextManifestStore(tmp_path)
    store.write(manifest())
    path = tmp_path / "review_manifest_001" / "memory_context_manifest.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(MemoryContextManifestStoreError, match="integrity"):
        store.write(manifest())


def test_manifest_store_rejects_symlink_run_directory(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    run_path = tmp_path / "review_manifest_001"
    try:
        run_path.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(MemoryContextManifestStoreError, match="unsafe"):
        FileMemoryContextManifestStore(tmp_path).write(manifest())
