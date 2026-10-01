"""Write-once sidecars, verified against the existing Runtime query chain."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from app.harness.run_ids import normalize_run_id
from app.product.run_query import RunQueryService
from app.product.run_receipts import FileRunReceiptStore
from app.runtime.models import RuntimeStatus
from .publication import (
    EvidenceBundleReference, EvidencePublicationContext,
    EvidencePublicationIntegrityError, EvidencePublicationManifest,
    canonical_bytes, sha256_bytes,
)
from .storage import (
    PendingEvidenceBundleSnapshot,
    bundle_from_storage_projection,
    bundle_to_storage_projection,
)
from .summary_bridge import SummaryEvidenceProjection, summary_to_evidence


class FileEvidencePublicationStore:
    filename = "evidence_publication_manifest.json"

    def __init__(self, runs_root: str | Path):
        self.runs_root = Path(runs_root).resolve()

    def _path(self, run_id: str, relative_path: str) -> Path:
        if normalize_run_id(run_id) != run_id:
            raise ValueError("invalid run")
        parts = PurePosixPath(relative_path).parts
        if (not parts or "\\" in relative_path or ":" in relative_path
                or relative_path != "/".join(parts)
                or any(p in (".", "..", "/") for p in parts)):
            raise ValueError("invalid path")
        current = self.runs_root
        if current.is_symlink() or current.resolve() != current:
            raise ValueError("root changed")
        # Reject aliases even when their target happens to remain inside root.
        for part in (run_id, *parts):
            current = current / part
            if current.is_symlink() or current.resolve() != current:
                raise ValueError("linked path")
        if not current.is_relative_to(self.runs_root):
            raise ValueError("escaped path")
        return current

    def _verified(self, context: EvidencePublicationContext):
        run_id = context.run_id
        # Preflight dependencies before the legacy verifier opens them. Reuse
        # its receipt/trace/publication/input checks, including rejected runs.
        for name in ("api_run_receipt.json", "runtime_trace.json", "manifest.json"):
            self._path(run_id, name)
        harness = json.loads(self._path(run_id, "manifest.json").read_bytes())
        for record in harness["artifacts"]:
            self._path(run_id, record["path"])
        query = RunQueryService(self.runs_root)
        verified = query._load_safely(run_id)
        if verified.receipt.runtime_status is not RuntimeStatus.COMPLETED or verified.trace is None:
            raise ValueError("incomplete runtime")
        summary = dict(query._read_verified_player_summary(verified))
        receipt, reference = FileRunReceiptStore(self.runs_root).read_receipt_with_reference(run_id)
        if receipt != verified.receipt:
            raise ValueError("receipt changed")
        summaries = [a for a in verified.trace.artifacts if a.kind == "player_summary"]
        reports = [a for a in verified.trace.artifacts if a.kind == "final_report"]
        return verified, summary, reference, summaries[0], reports[0] if verified.report is not None else None

    @staticmethod
    def _project_again(summary, bundle, observation_basis):
        if not bundle.riot_matches:
            raise ValueError("missing match evidence")
        first = bundle.riot_matches[0]
        return summary_to_evidence(
            summary, routing_region=first.routing_region, now=bundle.created_at,
            observed_at=first.observed_at if observation_basis == "caller_observed_at" else None,
            data_dragon=bundle.data_dragon, official_patch=bundle.official_patch,
            meta_evidence=bundle.meta_evidence,
        )

    def _manifest(self, context, projection):
        verified, summary, receipt, summary_ref, report_ref = self._verified(context)
        rebuilt = self._project_again(summary, projection.bundle, projection.observation_basis)
        if rebuilt != projection:
            raise ValueError("summary or evidence changed")
        bundle_bytes = canonical_bytes(bundle_to_storage_projection(projection.bundle))
        return EvidencePublicationManifest(
            context=context, summary_digest=projection.summary_digest,
            observation_basis=projection.observation_basis,
            bundle=EvidenceBundleReference(sha256=sha256_bytes(bundle_bytes),
                                           bundle_digest=projection.bundle.digest),
            summary=summary_ref, receipt=receipt,
            trace=verified.receipt.trace_reference, report=report_ref,
        ), bundle_bytes

    def write(self, context: EvidencePublicationContext,
              projection: SummaryEvidenceProjection) -> EvidencePublicationManifest:
        try:
            context = EvidencePublicationContext.model_validate(context)
            manifest, bundle_bytes = self._manifest(context, projection)
            self._write_once(self._path(context.run_id, manifest.bundle.relative_path), bundle_bytes)
            # An interrupted bundle is not a publication. The complete index
            # is last; recheck dependencies before creating it.
            checked, _ = self._manifest(context, projection)
            if (checked != manifest
                    or self._path(context.run_id, manifest.bundle.relative_path).read_bytes() != bundle_bytes):
                raise ValueError("dependencies changed")
            self._write_once(self._path(context.run_id, self.filename), manifest.canonical_bytes())
            return self.read(context)
        except Exception:
            pass
        # Outside the handler: no raw error context retained on public errors.
        raise EvidencePublicationIntegrityError()

    def read(self, context: EvidencePublicationContext) -> EvidencePublicationManifest:
        try:
            context = EvidencePublicationContext.model_validate(context)
            payload = self._path(context.run_id, self.filename).read_bytes()
            manifest = EvidencePublicationManifest.model_validate_json(payload)
            if manifest.context != context or payload != manifest.canonical_bytes():
                raise ValueError("identity changed")
            raw = self._path(context.run_id, manifest.bundle.relative_path).read_bytes()
            if sha256_bytes(raw) != manifest.bundle.sha256:
                raise ValueError("bundle bytes changed")
            bundle = bundle_from_storage_projection(json.loads(raw))
            _, summary, _, _, _ = self._verified(context)
            projection = self._project_again(summary, bundle, manifest.observation_basis)
            expected, expected_bytes = self._manifest(context, projection)
            if expected != manifest or expected_bytes != raw:
                raise ValueError("dependency mismatch")
            return manifest
        except Exception:
            pass
        raise EvidencePublicationIntegrityError()

    def read_pending_snapshot(
        self, context: EvidencePublicationContext
    ) -> PendingEvidenceBundleSnapshot:
        """Rebuild the atomic-task input from a verified publication sidecar.

        This is deliberately read-only: it validates the manifest and bundle
        through ``read`` first, then reconstructs the in-memory pending value
        consumed by the PostgreSQL transaction.  No model/provider call is
        repeated during recovery.
        """
        context = EvidencePublicationContext.model_validate(context)
        manifest = self.read(context)
        raw = self._path(context.run_id, manifest.bundle.relative_path).read_bytes()
        bundle = bundle_from_storage_projection(json.loads(raw))
        return PendingEvidenceBundleSnapshot(
            task_id=context.task_id,
            run_id=context.run_id,
            owner_id=context.owner_id,
            refresh_id="publication-1",
            bundle=bundle,
            stored_at=bundle.created_at,
        )

    @staticmethod
    def _write_once(target: Path, content: bytes) -> None:
        # Parent is an existing verified Runtime directory; never create runs.
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent,
                                             prefix=".publication.", delete=False) as stream:
                temp = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temp, target)
            except FileExistsError:
                if target.is_symlink() or target.resolve() != target or target.read_bytes() != content:
                    raise ValueError("immutable conflict")
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
