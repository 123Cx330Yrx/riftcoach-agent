"""Create-only, owner-free archive of a verified observation run."""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.golden_saved_input import load_saved_summary
from app.evidence.publication import EvidencePublicationManifest
from app.evidence.publication_store import FileEvidencePublicationStore

SCHEMA_VERSION = "showmaker-observation-v1"
SCOPE = "public_observed_archive"
RUN_ID = "golden_20260910_compact_1cd694d"
SUMMARY_DIGEST = "755b788254909b9dcfd18ac5ee9aa2db8580089e2e98d31f750a7173027b87c9"
RIOT_ID = "DK ShowMaker#KR1"
REGION = "asia"
ORIGINAL_REPORT_SHA256 = "aade1720b7b2633cfb7842c175609d102b3504a71207a7ed8f70e86b3ff5fcae"
TRACE_SHA256 = "5dd2e2899175939fd3a6a131c8882f0c055e1ee55b7ff5de44f2c51310cb0808"
MANUAL_REVIEW_SHA256 = "8485a643fcc2578034e30ac7b74a3c98bebfb2706ef32152ad1402fe59f3d5ef"
MAX_BYTES = 250_000
_ROLE_MAP = {"MIDDLE": "mid", "UTILITY": "support", "BOTTOM": "bot", "JUNGLE": "jungle", "TOP": "top"}


def _manual_binding(root: Path) -> dict[str, Any]:
    record = _regular(root.parent / "golden_manual_reviews" / f"{RUN_ID}.json", max_bytes=65536)
    try:
        value = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("observation_archive_manual_binding_invalid") from exc
    if (not isinstance(value, dict) or value.get("run_id") != RUN_ID or value.get("manual_copy_automatically_evaluated") is not False
            or value.get("reviewed_copy_sha256") != MANUAL_REVIEW_SHA256
            or value.get("original_report_sha256") != ORIGINAL_REPORT_SHA256
            or value.get("trace_sha256") != TRACE_SHA256
            or value.get("manual_original_accepted") is not False
            or value.get("manual_copy_corrected") is not True
            or value.get("automated_score") != 95):
        raise ValueError("observation_archive_manual_binding_invalid")
    return value


def _regular(path: Path, *, max_bytes: int) -> Path:
    path = path.expanduser().absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError("observation_archive_path_invalid")
    resolved = path.resolve()
    if resolved != path:
        raise ValueError("observation_archive_linked_path")
    if path.stat().st_size > max_bytes:
        raise ValueError("observation_archive_too_large")
    return path



def _iso(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("observation_archive_time_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observation_archive_time_invalid")
    return parsed.isoformat()


def _position(role: Any) -> str:
    if not isinstance(role, str) or role not in _ROLE_MAP:
        raise ValueError("observation_archive_position_invalid")
    return _ROLE_MAP[role]


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("observation_archive_metric_invalid")
    return float(value)


def _build_exercises(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_position: dict[str, list[dict[str, Any]]] = {}
    for row in matches:
        by_position.setdefault(row["position"], []).append(row)
    exercises: list[dict[str, Any]] = []
    mids = by_position.get("mid", [])
    if mids:
        exercises.append({
            "id": "observe-mid-win-loss",
            "title": "中路同位置胜负录像对比",
            "position": "mid",
            "prompt": "仅对照这些中路对局的补刀、伤害和参团时机，记录可在录像中验证的差异；不要把结果直接当成原因。",
            "match_ids": [row["match_id"] for row in mids],
            "evidence_note": "来自已校验的中路归档样本；这是观摩练习，不是本人的训练计划。",
        })
    supports = by_position.get("support", [])
    if supports:
        exercises.append({
            "id": "observe-support-death-times",
            "title": "辅助单局死亡时间观察",
            "position": "support",
            "prompt": "回看该辅助单局的死亡时间，标记每次死亡前的站位、资源和队友信息；统计结果不代表长期辅助能力。",
            "match_ids": [row["match_id"] for row in supports],
            "evidence_note": "仅基于一局辅助样本；这是观摩练习，不是本人的训练计划。",
        })
    return exercises


def export_observation(
    *,
    runs_root: str | Path,
    manual_review: str | Path,
    output: str | Path,
    exported_at: str | None = None,
) -> dict[str, Any]:
    root = Path(runs_root).resolve()
    manual = _regular(Path(manual_review), max_bytes=MAX_BYTES)
    binding = _manual_binding(root)
    report_raw = manual.read_bytes()
    report_digest = hashlib.sha256(report_raw).hexdigest()
    if report_digest != MANUAL_REVIEW_SHA256:
        raise ValueError("observation_archive_manual_changed")
    report_text = report_raw.decode("utf-8")
    store = FileEvidencePublicationStore(root)
    manifest_path = _regular(store._path(RUN_ID, store.filename), max_bytes=65536)
    publication = EvidencePublicationManifest.model_validate_json(manifest_path.read_bytes())
    if publication.context.run_id != RUN_ID:
        raise ValueError("observation_archive_run_mismatch")
    verified = store.read(publication.context)
    if verified.summary_digest != SUMMARY_DIGEST:
        raise ValueError("observation_archive_summary_digest_mismatch")
    if verified.trace.sha256 != TRACE_SHA256:
        raise ValueError("observation_archive_trace_mismatch")
    if verified.report is None or verified.report.sha256 != ORIGINAL_REPORT_SHA256:
        raise ValueError("observation_archive_report_mismatch")
    summary, observed = load_saved_summary(
        root, run_id=RUN_ID, expected_digest=SUMMARY_DIGEST,
        riot_id=RIOT_ID, routing_region=REGION, count=5, queue=420,
    )
    matches: list[dict[str, Any]] = []
    for row in summary["matches"]:
        matches.append({
            "match_id": row["match_id"],
            "champion": row["champion_name"],
            "position": _position(row["role"]),
            "win": bool(row["win"]),
            "cs_per_min": _number(row, "cs_per_min"),
            "damage_per_min": _number(row, "damage_per_min"),
            "deaths_before_15": _number(row, "deaths_before_15"),
        })
    positions: list[dict[str, Any]] = []
    for position in sorted({row["position"] for row in matches}):
        rows = [row for row in matches if row["position"] == position]
        positions.append({
            "position": position, "games": len(rows),
            "champions": [row["champion"] for row in rows],
            "cs_per_min": (round(sum(row["cs_per_min"] for row in rows if row["cs_per_min"] is not None) /
                                    len([row for row in rows if row["cs_per_min"] is not None]), 2)
                           if any(row["cs_per_min"] is not None for row in rows) else None),
        })
    bundle_raw = store._path(RUN_ID, verified.bundle.relative_path).read_bytes()
    if hashlib.sha256(bundle_raw).hexdigest() != verified.bundle.sha256:
        raise ValueError("observation_archive_bundle_changed")
    bundle = json.loads(bundle_raw)
    sources = [
        {"label": "Riot API", "detail": "5局赛后统计与 timeline", "observed_at": _iso(observed.isoformat())},
        {"label": "Data Dragon", "detail": f"英雄与静态名称映射 {bundle['data_dragon']['version']}", "observed_at": _iso(bundle["data_dragon"]["retrieved_at"])},
        {"label": "官方版本", "detail": f"版本身份 {bundle['official_patch']['patch_version']}（{bundle['official_patch'].get('update_id', '')}），仅核对版本元数据，未消费平衡改动正文", "observed_at": _iso(bundle["official_patch"]["retrieved_at"])},
    ]
    for item in bundle["meta_evidence"]:
        if item.get("source") != "opgg":
            continue
        sources.append({"label": "OP.GG", "detail": f"{item.get('position', 'unknown')}位置快照，仅作归档观摩对照，不代表本人胜率", "observed_at": _iso(item["retrieved_at"])})
    archive = {
        "schema_version": SCHEMA_VERSION, "scope": SCOPE, "riot_id": RIOT_ID, "region": REGION,
        "source_run_id": RUN_ID, "observed_at": _iso(observed.isoformat()),
        "exported_at": _iso(exported_at or datetime.now(timezone.utc).isoformat()),
        "report": {"text": report_text, "kind": "human_reviewed", "sha256": report_digest,
                   "original_sha256": ORIGINAL_REPORT_SHA256, "automated_score": binding["automated_score"],
                   "original_manual_accepted": False},
        "summary": {"games": len(matches), "wins": sum(row["win"] for row in matches),
                    "losses": sum(not row["win"] for row in matches), "positions": positions, "matches": matches},
        "evidence": {"bundle_digest": verified.bundle.bundle_digest, "sources": sources},
        "exercises": _build_exercises(matches),
    }
    raw = json.dumps(archive, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("observation_archive_too_large")
    target = Path(output).expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError("observation_archive_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(target, flags)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd != -1:
            os.close(fd)
    return archive


__all__ = ["export_observation"]
