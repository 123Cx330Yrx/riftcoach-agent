"""Safe projection of persisted Harness artifacts into Runtime references."""

from __future__ import annotations

from app.harness.models import RunManifest
from app.harness.store import FileRunStore

from .models import RuntimeArtifactReference


def project_artifact_references(
    *,
    manifest: RunManifest,
    store: FileRunStore,
) -> tuple[RuntimeArtifactReference, ...]:
    """Revalidate every persisted artifact before exposing a body-free reference.

    The Runtime trace stores identity and integrity metadata only.  The actual
    bytes remain in the Harness run store and are read once here so a tampered
    file cannot be projected as if its manifest digest were trustworthy.
    """

    if not isinstance(manifest, RunManifest):
        raise TypeError("manifest must be a RunManifest")
    if not isinstance(store, FileRunStore):
        raise TypeError("store must be a FileRunStore")
    if manifest.run_id != store.run_id:
        raise ValueError("manifest and artifact store run IDs must match")

    references: list[RuntimeArtifactReference] = []
    seen_paths: set[str] = set()
    for record in manifest.artifacts:
        if not isinstance(record, dict):
            raise TypeError("artifact records must be mappings")
        if record.get("run_id") != manifest.run_id:
            raise ValueError("artifact record run ID does not match manifest")

        # read_artifact verifies the actual file bytes against the registered
        # SHA-256 before a reference is constructed.
        store.read_artifact(record)
        relative_path = record.get("path")
        if not isinstance(relative_path, str):
            raise ValueError("artifact record path must be a string")
        if relative_path in seen_paths:
            raise ValueError("artifact relative paths must be unique")
        seen_paths.add(relative_path)

        references.append(
            RuntimeArtifactReference(
                kind=record["kind"],
                schema_version=record["schema_version"],
                relative_path=relative_path,
                sha256=record["sha256"],
                producer=record["producer"],
            )
        )

    return tuple(references)
