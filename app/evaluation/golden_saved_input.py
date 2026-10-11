"""Read verified prior golden facts; old source snapshots are not re-admitted."""
from datetime import datetime
import hashlib
import json
import re

from app.evidence.publication import EvidencePublicationManifest
from app.evidence.publication_store import FileEvidencePublicationStore


def load_saved_summary(runs_root, *, run_id, expected_digest, riot_id, routing_region, count, queue):
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,95}", run_id):
        raise ValueError("saved_golden_run_invalid")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise ValueError("saved_golden_digest_invalid")
    store = FileEvidencePublicationStore(runs_root)
    path = store._path(run_id, store.filename)
    summary_path = store._path(run_id, "inputs/player_summary.json")
    if path.stat().st_size > 65536 or summary_path.stat().st_size > 2_000_000:
        raise ValueError("saved_golden_input_too_large")
    manifest = EvidencePublicationManifest.model_validate_json(path.read_bytes())
    if manifest.context.run_id != run_id:
        raise ValueError("saved_golden_run_mismatch")
    verified = store.read(manifest.context)
    raw = summary_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != verified.summary.sha256:
        raise ValueError("saved_golden_summary_changed")
    summary = json.loads(raw)
    digest = hashlib.sha256(json.dumps(summary, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if digest != expected_digest or digest != verified.summary_digest:
        raise ValueError("saved_golden_digest_mismatch")
    from app.evidence.storage import bundle_from_storage_projection
    bundle_raw = store._path(run_id, verified.bundle.relative_path).read_bytes()
    if hashlib.sha256(bundle_raw).hexdigest() != verified.bundle.sha256:
        raise ValueError("saved_golden_bundle_changed")
    bundle = bundle_from_storage_projection(json.loads(bundle_raw))
    if not bundle.riot_matches or any(row.routing_region != routing_region for row in bundle.riot_matches):
        raise ValueError("saved_golden_region_mismatch")
    request = summary["request"]
    if (summary["player"]["riot_id"] != riot_id or request["count"] != count
            or request["queue"] != queue or request.get("queue_fallback_used")):
        raise ValueError("saved_golden_request_mismatch")
    observed_at = datetime.fromisoformat(summary["metadata"]["generated_at_utc"].replace("Z", "+00:00"))
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("saved_golden_observation_invalid")
    return summary, observed_at


def refresh_saved_static(summary, service):
    # The loader returned a detached JSON value; preserve the old files and all
    # match/timeline measurements while replacing only static descriptions.
    for row in summary["matches"]:
        service.enrich_match_row(row)
        if row.get("timeline_available"):
            service.enrich_item_purchases(row.get("item_purchases", []))
    summary["request"]["data_dragon_version"] = service.version
    summary["request"]["data_dragon_language"] = service.language
    return summary
