from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.check_cinematic_media import (
    MAX_CSS_GZIP_BYTES,
    MAX_JS_GZIP_BYTES,
    CinematicMediaAuditError,
    audit_manifest,
    main,
    validate_manifest_contract,
)


PORTAL_SOURCE_PATH = "docs/assets/8e-portal/portal-mother-image-source-v2.png"
PORTAL_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def _write(root: Path, relative: str, marker: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = f"fixture:{marker}".encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _fixture_manifest(tmp_path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, dict[str, Any]]]:
    digest_by_path: dict[str, str] = {}
    probe_by_path: dict[str, dict[str, Any]] = {}

    portal_source = "fixtures/source-portal.png"
    account_source = "fixtures/source-account.png"
    _, portal_bytes = _write(tmp_path, portal_source, "portal-source")
    _, account_bytes = _write(tmp_path, account_source, "account-source")
    digest_by_path[portal_source] = PORTAL_SOURCE_SHA
    digest_by_path[account_source] = "b" * 64

    renditions: list[dict[str, Any]] = []
    total_media_bytes = 0
    for scene in ("portal", "account"):
        for viewport in ("desktop", "mobile"):
            width, height = ((1672, 941) if viewport == "desktop" else (900, 1600))
            posters: list[dict[str, Any]] = []
            for poster_format in ("avif", "webp"):
                relative = f"fixtures/{scene}-{viewport}-poster.{poster_format}"
                digest, byte_count = _write(tmp_path, relative, relative)
                digest_by_path[relative] = digest
                probe_by_path[relative] = {"width": width, "height": height, "codec_type": "video"}
                posters.append({
                    "format": poster_format,
                    "path": relative,
                    "sha256": digest,
                    "bytes": byte_count,
                    "width": width,
                    "height": height,
                    "source_ssim": 0.99,
                })
                total_media_bytes += byte_count

            videos: list[dict[str, Any]] = []
            for video_format in ("webm", "mp4"):
                relative = f"fixtures/{scene}-{viewport}-loop.{video_format}"
                digest, byte_count = _write(tmp_path, relative, relative)
                digest_by_path[relative] = digest
                probe_by_path[relative] = {
                    "format_name": video_format,
                    "codec_name": "vp9" if video_format == "webm" else "h264",
                    "width": width,
                    "height": height,
                    "fps": 24,
                    "pix_fmt": "yuv420p",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "has_audio": False,
                    "faststart": True,
                    "metadata_removed": True,
                }
                videos.append({
                    "format": video_format,
                    "path": relative,
                    "sha256": digest,
                    "bytes": byte_count,
                    "width": width,
                    "height": height,
                    "duration_s": 8.0,
                    "fps": 24,
                    "pix_fmt": "yuv420p",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "has_audio": False,
                    "faststart": True,
                    "metadata_removed": True,
                    "max_keyframe_interval_s": 1.5,
                    "source_to_first_frame_ssim": 0.98,
                    "poster_to_first_frame_ssim": 0.99,
                    "adjacent_dssim_p95": 0.01,
                    "seam_dssim": 0.015,
                    "dropped_frame_ratio": 0.0,
                })
                total_media_bytes += byte_count

            renditions.append({
                "scene": scene,
                "viewport": viewport,
                "source_sha256": PORTAL_SOURCE_SHA if scene == "portal" else "b" * 64,
                "posters": posters,
                "videos": videos,
                "browser": {"dropped_frame_ratio": 0.0, "transferred_bytes": total_media_bytes},
            })

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "fixture",
        "policy": _fixture_policy(),
        "toolchain": {"status": "verified", "ffmpeg_version": "8.1.2", "ffprobe_version": "8.1.2"},
        "source": {
            "portal": {
                "status": "adopted-source",
                "path": portal_source,
                "sha256": PORTAL_SOURCE_SHA,
                "bytes": portal_bytes,
                "width": 1672,
                "height": 941,
            },
            "account": {
                "status": "adopted-source",
                "path": account_source,
                "sha256": "b" * 64,
                "bytes": account_bytes,
                "width": 1672,
                "height": 941,
            },
        },
        "renditions": renditions,
        "budgets": {
            "js_gzip_bytes": 144_070,
            "css_gzip_bytes": 18_500,
            "non_media_cold_start_bytes": 100,
            "total_media_bytes": total_media_bytes,
        },
    }
    return manifest, digest_by_path, probe_by_path


def _run_fixture(manifest: dict[str, Any], root: Path, digests: dict[str, str], probes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return audit_manifest(
        manifest,
        root=root,
        digest=lambda path: digests[path.relative_to(root).as_posix()],
        probe=lambda path: probes[path.relative_to(root).as_posix()],
    )


def test_planned_manifest_is_contract_only_and_performs_no_media_io() -> None:
    manifest = {
        "schema_version": "1.0",
        "status": "planned",
        "policy": _fixture_policy(),
        "toolchain": {"status": "pending", "ffmpeg_version": None, "ffprobe_version": None},
        "source": {
            "portal": {"status": "adopted-source", "path": PORTAL_SOURCE_PATH, "sha256": PORTAL_SOURCE_SHA, "bytes": 2_268_033, "width": 1672, "height": 941},
            "account": {"status": "pending"},
        },
        "renditions": [],
        "budgets": {
            "js_gzip_bytes": None,
            "css_gzip_bytes": None,
            "non_media_cold_start_bytes": None,
            "total_media_bytes": None,
        },
    }

    assert validate_manifest_contract(manifest) == "planned"
    assert audit_manifest(manifest, root=Path("C:/does-not-exist")) == {
        "schema_version": "1.0",
        "status": "planned",
        "checked_renditions": 0,
    }


def _fixture_policy() -> dict[str, Any]:
    return {
        "source_first_frame_ssim_min": 0.95,
        "poster_first_frame_ssim_min": 0.98,
        "seam_dssim_floor_max": 0.03,
        "seam_adjacent_multiplier": 1.5,
        "dropped_frame_ratio_max": 0.01,
        "keyframe_interval_s_max": 2.0,
        "js_gzip_bytes_max": 150_000,
        "css_gzip_bytes_max": 22_000,
        "non_media_cold_start_bytes_max": 220_000,
        "total_media_bytes_max": 25_000_000,
        "anti_references": [
            {"path": path, "sha256": sha}
            for path, sha in {
                "web/public/assets/awakening/rift-aperture-plate.webp": "ba3d9ab530f9456cc29e12f6ac05715ff222820d71c82eae5a3d45dd3ed8206b",
                "web/public/assets/awakening/rift-portal-background-v2.webp": "d782898f9d2757e4f60c94cf66d52ec2a507ea81e726eb3611eca0eeb802bb67",
                "docs/assets/8e-portal/portal-motion-keyframe-v2.webp": "636051a579e1b715f9adb4cb31fb807d8645a43a6801e7533524d49101aba48f",
                "docs/assets/8e-portal/retired-instrumentarium-v2.webp": "0f9362ad38c2a1c1abb83376624863c1fda9ac7282ee205ba40bc310454ce364",
            }.items()
        ],
    }

def test_fixture_manifest_passes_all_read_only_contracts(tmp_path: Path) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)

    result = _run_fixture(manifest, tmp_path, digests, probes)

    assert result["status"] == "fixture"
    assert result["checked_renditions"] == 4
    assert result["total_media_bytes"] == manifest["budgets"]["total_media_bytes"]


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value["renditions"].pop(), "rendition_matrix_incomplete"),
        (lambda value: value["renditions"].append(copy.deepcopy(value["renditions"][0])), "rendition_matrix_incomplete"),
        (lambda value: value["renditions"][0].update({"scene": "unknown"}), "rendition_identity_invalid"),
        (lambda value: value["renditions"][0]["videos"][0].update({"format": "avi"}), "video_matrix_invalid"),
    ],
)
def test_manifest_shape_and_identity_fail_closed(tmp_path: Path, mutation, code: str) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    mutation(manifest)

    with pytest.raises(CinematicMediaAuditError, match=code):
        _run_fixture(manifest, tmp_path, digests, probes)


def test_remote_traversal_and_anti_reference_paths_are_rejected(tmp_path: Path) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["renditions"][0]["posters"][0]["path"] = "https://cdn.example/portal.avif"
    with pytest.raises(CinematicMediaAuditError, match="media_path_invalid"):
        validate_manifest_contract(manifest)

    manifest, _, _ = _fixture_manifest(tmp_path)
    manifest["renditions"][0]["posters"][0]["path"] = "web/public/assets/awakening/retired-instrumentarium-v2.webp"
    with pytest.raises(CinematicMediaAuditError, match="anti_reference_reintroduced"):
        validate_manifest_contract(manifest)


def test_digest_and_size_are_checked_against_local_bytes(tmp_path: Path) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["renditions"][0]["posters"][0]["sha256"] = "c" * 64

    with pytest.raises(CinematicMediaAuditError, match="media_digest_mismatch"):
        _run_fixture(manifest, tmp_path, digests, probes)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("source_to_first_frame_ssim", 0.94, "ssim_below_threshold"),
        ("poster_to_first_frame_ssim", 0.97, "ssim_below_threshold"),
        ("seam_dssim", 0.2, "loop_seam_invalid"),
        ("dropped_frame_ratio", 0.02, "dropped_frame_ratio_too_large"),
        ("max_keyframe_interval_s", 2.1, "video_keyframe_interval_too_large"),
    ],
)
def test_motion_quality_metrics_are_blocking(tmp_path: Path, field: str, value: Any, code: str) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["renditions"][0]["videos"][0][field] = value

    with pytest.raises(CinematicMediaAuditError, match=code):
        _run_fixture(manifest, tmp_path, digests, probes)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("fps", 30, "video_fps_invalid"),
        ("pix_fmt", "yuv444p", "video_pixel_format_invalid"),
        ("color_space", "bt2020", "video_color_invalid"),
        ("has_audio", True, "video_audio_present"),
        ("faststart", False, "video_faststart_missing"),
        ("metadata_removed", False, "video_metadata_present"),
    ],
)
def test_codec_and_probe_contracts_are_blocking(tmp_path: Path, field: str, value: Any, code: str) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["renditions"][0]["videos"][0][field] = value

    with pytest.raises(CinematicMediaAuditError, match=code):
        _run_fixture(manifest, tmp_path, digests, probes)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("js_gzip_bytes", MAX_JS_GZIP_BYTES + 1, "js_budget_exceeded"),
        ("css_gzip_bytes", MAX_CSS_GZIP_BYTES + 1, "css_budget_exceeded"),
        ("non_media_cold_start_bytes", 220_001, "cold_start_budget_exceeded"),
    ],
)
def test_runtime_budgets_are_blocking(tmp_path: Path, field: str, value: int, code: str) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["budgets"][field] = value

    with pytest.raises(CinematicMediaAuditError, match=code):
        _run_fixture(manifest, tmp_path, digests, probes)


def test_portal_source_must_match_the_confirmed_mother_image(tmp_path: Path) -> None:
    manifest, digests, probes = _fixture_manifest(tmp_path)
    manifest["source"]["portal"]["sha256"] = "d" * 64
    manifest["renditions"][0]["source_sha256"] = "d" * 64

    with pytest.raises(CinematicMediaAuditError, match="portal_source_identity_invalid"):
        validate_manifest_contract(manifest)


def test_planned_portal_source_path_cannot_fall_back_to_archival_v1() -> None:
    manifest = {
        "schema_version": "1.0",
        "status": "planned",
        "policy": _fixture_policy(),
        "toolchain": {"status": "pending", "ffmpeg_version": None, "ffprobe_version": None},
        "source": {
            "portal": {
                "status": "adopted-source",
                "path": "docs/assets/8e-portal/portal-mother-image-source-v1.png",
                "sha256": PORTAL_SOURCE_SHA,
                "bytes": 2_268_033,
                "width": 1672,
                "height": 941,
            },
            "account": {"status": "pending"},
        },
        "renditions": [],
        "budgets": {
            "js_gzip_bytes": None,
            "css_gzip_bytes": None,
            "non_media_cold_start_bytes": None,
            "total_media_bytes": None,
        },
    }

    with pytest.raises(CinematicMediaAuditError, match="portal_source_identity_invalid"):
        validate_manifest_contract(manifest)


def test_policy_and_toolchain_drift_are_rejected(tmp_path: Path) -> None:
    manifest, _, _ = _fixture_manifest(tmp_path)
    manifest["policy"]["seam_adjacent_multiplier"] = 2.0
    with pytest.raises(CinematicMediaAuditError, match="policy_drift"):
        validate_manifest_contract(manifest)

    manifest, _, _ = _fixture_manifest(tmp_path)
    manifest["toolchain"]["status"] = "pending"
    manifest["toolchain"]["ffprobe_version"] = "8.1.2"
    with pytest.raises(CinematicMediaAuditError, match="toolchain_status_invalid"):
        validate_manifest_contract(manifest)


def test_cli_accepts_the_planned_repo_ledger_without_media_io(capsys) -> None:
    from scripts.check_cinematic_media import PROJECT_ROOT

    result = main([
        "--manifest",
        str(PROJECT_ROOT / "docs/assets/8e-portal/cinematic-media-audit-v1.json"),
        "--root",
        str(PROJECT_ROOT),
        "--json",
    ])

    assert result == 0
    assert json.loads(capsys.readouterr().out)["status"] == "planned"
