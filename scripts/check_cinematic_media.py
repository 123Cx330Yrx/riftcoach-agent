"""Read-only contract and budget checks for RQ-108 cinematic media.

This module deliberately does not generate, transcode, upload, or mutate media.
It validates an explicit JSON audit manifest and, for adopted/fixture entries,
reads local bytes plus ffprobe metadata.  Tests inject a probe and digest
function so the policy can be exercised without shipping media or requiring a
particular workstation codec installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
SCENES = ("portal", "account")
VIEWPORTS = ("desktop", "mobile")
POSTER_FORMATS = ("avif", "webp")
VIDEO_FORMATS = ("webm", "mp4")
PORTAL_SOURCE_SHA256 = "552a87453daae53762f56f0cb5f7c7c2fee18256ef6d193c00575283e9b7aada"

MAX_JS_GZIP_BYTES = 150_000
MAX_CSS_GZIP_BYTES = 22_000
MAX_NON_MEDIA_COLD_START_BYTES = 220_000
MAX_TOTAL_MEDIA_BYTES = 25_000_000
MAX_DROPPED_FRAME_RATIO = 0.01
MIN_SOURCE_FIRST_FRAME_SSIM = 0.95
MIN_POSTER_FIRST_FRAME_SSIM = 0.98
MAX_KEYFRAME_INTERVAL_S = 2.0
SEAM_DSSIM_FLOOR = 0.03

VIDEO_BUDGETS: Mapping[tuple[str, str, str], int] = {
    ("portal", "desktop", "webm"): 4_500_000,
    ("portal", "desktop", "mp4"): 5_500_000,
    ("portal", "mobile", "webm"): 2_400_000,
    ("portal", "mobile", "mp4"): 3_000_000,
    ("account", "desktop", "webm"): 4_000_000,
    ("account", "desktop", "mp4"): 5_000_000,
    ("account", "mobile", "webm"): 2_200_000,
    ("account", "mobile", "mp4"): 2_800_000,
}
POSTER_BUDGETS: Mapping[tuple[str, str], int] = {
    ("portal", "desktop"): 500_000,
    ("portal", "mobile"): 350_000,
    ("account", "desktop"): 450_000,
    ("account", "mobile"): 320_000,
}

ANTI_REFERENCE_TOKENS = (
    "rift-portal-background-v2",
    "rift-aperture-plate",
    "portal-motion-keyframe-v2",
    "retired-instrumentarium",
    "hero-loop",
)
ANTI_REFERENCES: Mapping[str, str] = {
    "web/public/assets/awakening/rift-aperture-plate.webp": "ba3d9ab530f9456cc29e12f6ac05715ff222820d71c82eae5a3d45dd3ed8206b",
    "web/public/assets/awakening/rift-portal-background-v2.webp": "d782898f9d2757e4f60c94cf66d52ec2a507ea81e726eb3611eca0eeb802bb67",
    "docs/assets/8e-portal/portal-motion-keyframe-v2.webp": "636051a579e1b715f9adb4cb31fb807d8645a43a6801e7533524d49101aba48f",
    "docs/assets/8e-portal/retired-instrumentarium-v2.webp": "0f9362ad38c2a1c1abb83376624863c1fda9ac7282ee205ba40bc310454ce364",
}

Probe = Callable[[Path], Mapping[str, Any]]
Digest = Callable[[Path], str]


class CinematicMediaAuditError(ValueError):
    """A fail-closed manifest or media evidence violation."""

    def __init__(self, code: str, path: str, detail: str) -> None:
        self.code = code
        self.path = path
        self.detail = detail
        super().__init__(f"{code} at {path}: {detail}")


def _fail(code: str, path: str, detail: str) -> None:
    raise CinematicMediaAuditError(code, path, detail)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("manifest_shape_invalid", path, "expected an object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    required: Sequence[str],
    optional: Sequence[str],
    path: str,
) -> None:
    allowed = set(required) | set(optional)
    unknown = sorted(set(value) - allowed)
    missing = [key for key in required if key not in value]
    if unknown:
        _fail("manifest_unknown_key", path, ", ".join(unknown))
    if missing:
        _fail("manifest_missing_key", path, ", ".join(missing))


def _string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        _fail("manifest_value_invalid", path, "expected a non-empty string")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail("manifest_value_invalid", path, f"expected integer >= {minimum}")
    return value


def _number(value: Any, path: str, *, minimum: float = 0.0, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _fail("manifest_value_invalid", path, "expected a finite number")
    number = float(value)
    if number < minimum or (maximum is not None and number > maximum):
        _fail("manifest_value_invalid", path, "number is outside the allowed range")
    return number


def _sha(value: Any, path: str) -> str:
    result = _string(value, path).lower()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        _fail("manifest_sha_invalid", path, "expected a lowercase/uppercase SHA-256 hex digest")
    return result


def _validate_relative_path(value: Any, path: str) -> str:
    result = _string(value, path)
    if (
        result.startswith(("/", "\\"))
        or "://" in result
        or result.startswith(("data:", "blob:"))
        or "\\" in result
        or "\x00" in result
    ):
        _fail("media_path_invalid", path, "must be a relative local path")
    parts = Path(result).parts
    if any(part in {".", ".."} for part in parts):
        _fail("media_path_invalid", path, "directory traversal is not allowed")
    lowered = result.casefold()
    if any(token in lowered for token in ANTI_REFERENCE_TOKENS):
        _fail("anti_reference_reintroduced", path, "path is a rejected/retired visual asset")
    return result


def _validate_relative_path_allowing_anti_reference(value: Any, path: str) -> str:
    result = _string(value, path)
    if (
        result.startswith(("/", "\\"))
        or "://" in result
        or result.startswith(("data:", "blob:"))
        or "\\" in result
        or "\x00" in result
        or any(part in {".", ".."} for part in Path(result).parts)
    ):
        _fail("media_path_invalid", path, "must be a relative local path")
    return result


def _validate_ssim(value: Any, path: str, minimum: float) -> float:
    result = _number(value, path, minimum=0.0, maximum=1.0)
    if result < minimum:
        _fail("ssim_below_threshold", path, f"{result:.6f} < {minimum:.2f}")
    return result


def _validate_poster(value: Any, path: str, *, planned: bool) -> None:
    row = _mapping(value, path)
    _exact_keys(
        row,
        ("format", "path", "sha256", "bytes", "width", "height", "source_ssim"),
        (),
        path,
    )
    fmt = _string(row["format"], f"{path}.format")
    if fmt not in POSTER_FORMATS:
        _fail("poster_format_invalid", f"{path}.format", fmt)
    _validate_relative_path(row["path"], f"{path}.path")
    _sha(row["sha256"], f"{path}.sha256")
    _integer(row["bytes"], f"{path}.bytes", minimum=1)
    _integer(row["width"], f"{path}.width", minimum=1)
    _integer(row["height"], f"{path}.height", minimum=1)
    _validate_ssim(row["source_ssim"], f"{path}.source_ssim", MIN_SOURCE_FIRST_FRAME_SSIM)
    del planned


def _validate_video(value: Any, path: str, *, planned: bool) -> None:
    row = _mapping(value, path)
    required = (
        "format",
        "path",
        "sha256",
        "bytes",
        "width",
        "height",
        "duration_s",
        "fps",
        "pix_fmt",
        "color_space",
        "color_transfer",
        "color_primaries",
        "has_audio",
        "faststart",
        "metadata_removed",
        "max_keyframe_interval_s",
        "source_to_first_frame_ssim",
        "poster_to_first_frame_ssim",
        "adjacent_dssim_p95",
        "seam_dssim",
        "dropped_frame_ratio",
    )
    _exact_keys(row, required, (), path)
    fmt = _string(row["format"], f"{path}.format")
    if fmt not in VIDEO_FORMATS:
        _fail("video_format_invalid", f"{path}.format", fmt)
    _validate_relative_path(row["path"], f"{path}.path")
    _sha(row["sha256"], f"{path}.sha256")
    _integer(row["bytes"], f"{path}.bytes", minimum=1)
    _integer(row["width"], f"{path}.width", minimum=1)
    _integer(row["height"], f"{path}.height", minimum=1)
    _number(row["duration_s"], f"{path}.duration_s", minimum=0.1)
    fps = _number(row["fps"], f"{path}.fps", minimum=1.0)
    if abs(fps - 24.0) > 0.01:
        _fail("video_fps_invalid", f"{path}.fps", f"expected 24fps, got {fps}")
    if _string(row["pix_fmt"], f"{path}.pix_fmt") != "yuv420p":
        _fail("video_pixel_format_invalid", f"{path}.pix_fmt", "expected yuv420p")
    for key in ("color_space", "color_transfer", "color_primaries"):
        if _string(row[key], f"{path}.{key}").casefold() != "bt709":
            _fail("video_color_invalid", f"{path}.{key}", "expected bt709")
    if row["has_audio"] is not False:
        _fail("video_audio_present", f"{path}.has_audio", "cinematic media must have no audio stream")
    if row["faststart"] is not True:
        _fail("video_faststart_missing", f"{path}.faststart", "MP4/WebM must be seekable from the start")
    if row["metadata_removed"] is not True:
        _fail("video_metadata_present", f"{path}.metadata_removed", "metadata removal was not proven")
    keyframe_interval = _number(row["max_keyframe_interval_s"], f"{path}.max_keyframe_interval_s", minimum=0.0)
    if keyframe_interval > MAX_KEYFRAME_INTERVAL_S:
        _fail("video_keyframe_interval_too_large", f"{path}.max_keyframe_interval_s", str(keyframe_interval))
    _validate_ssim(row["source_to_first_frame_ssim"], f"{path}.source_to_first_frame_ssim", MIN_SOURCE_FIRST_FRAME_SSIM)
    _validate_ssim(row["poster_to_first_frame_ssim"], f"{path}.poster_to_first_frame_ssim", MIN_POSTER_FIRST_FRAME_SSIM)
    adjacent = _number(row["adjacent_dssim_p95"], f"{path}.adjacent_dssim_p95", minimum=0.0, maximum=1.0)
    seam = _number(row["seam_dssim"], f"{path}.seam_dssim", minimum=0.0, maximum=1.0)
    if seam > max(1.5 * adjacent, SEAM_DSSIM_FLOOR):
        _fail("loop_seam_invalid", f"{path}.seam_dssim", f"{seam:.6f} exceeds allowed seam")
    dropped = _number(row["dropped_frame_ratio"], f"{path}.dropped_frame_ratio", minimum=0.0, maximum=1.0)
    if dropped > MAX_DROPPED_FRAME_RATIO:
        _fail("dropped_frame_ratio_too_large", f"{path}.dropped_frame_ratio", str(dropped))
    del planned


def validate_manifest_contract(manifest: Mapping[str, Any]) -> str:
    """Validate JSON shape and return its status without touching media files."""

    root = _mapping(manifest, "manifest")
    _exact_keys(
        root,
        ("schema_version", "status", "policy", "toolchain", "source", "renditions", "budgets"),
        ("notes",),
        "manifest",
    )
    if root["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version_unsupported", "manifest.schema_version", str(root["schema_version"]))
    status = _string(root["status"], "manifest.status")
    if status not in {"planned", "fixture", "adopted", "runtime-complete"}:
        _fail("manifest_status_invalid", "manifest.status", status)
    planned = status == "planned"

    policy = _mapping(root["policy"], "manifest.policy")
    _exact_keys(
        policy,
        (
            "source_first_frame_ssim_min",
            "poster_first_frame_ssim_min",
            "seam_dssim_floor_max",
            "seam_adjacent_multiplier",
            "dropped_frame_ratio_max",
            "keyframe_interval_s_max",
            "js_gzip_bytes_max",
            "css_gzip_bytes_max",
            "non_media_cold_start_bytes_max",
            "total_media_bytes_max",
            "anti_references",
        ),
        (),
        "manifest.policy",
    )
    expected_policy = {
        "source_first_frame_ssim_min": MIN_SOURCE_FIRST_FRAME_SSIM,
        "poster_first_frame_ssim_min": MIN_POSTER_FIRST_FRAME_SSIM,
        "seam_dssim_floor_max": SEAM_DSSIM_FLOOR,
        "seam_adjacent_multiplier": 1.5,
        "dropped_frame_ratio_max": MAX_DROPPED_FRAME_RATIO,
        "keyframe_interval_s_max": MAX_KEYFRAME_INTERVAL_S,
        "js_gzip_bytes_max": MAX_JS_GZIP_BYTES,
        "css_gzip_bytes_max": MAX_CSS_GZIP_BYTES,
        "non_media_cold_start_bytes_max": MAX_NON_MEDIA_COLD_START_BYTES,
        "total_media_bytes_max": MAX_TOTAL_MEDIA_BYTES,
    }
    for key, expected in expected_policy.items():
        if policy[key] != expected:
            _fail("policy_drift", f"manifest.policy.{key}", f"expected {expected!r}")
    anti_references = policy["anti_references"]
    if not isinstance(anti_references, list):
        _fail("policy_drift", "manifest.policy.anti_references", "expected an array")
    decoded_anti_references: dict[str, str] = {}
    for index, value in enumerate(anti_references):
        row = _mapping(value, f"manifest.policy.anti_references[{index}]")
        _exact_keys(row, ("path", "sha256"), (), f"manifest.policy.anti_references[{index}]")
        relative_path = _validate_relative_path_allowing_anti_reference(
            row["path"], f"manifest.policy.anti_references[{index}].path"
        )
        decoded_anti_references[relative_path] = _sha(
            row["sha256"], f"manifest.policy.anti_references[{index}].sha256"
        )
    if decoded_anti_references != dict(ANTI_REFERENCES):
        _fail("policy_drift", "manifest.policy.anti_references", "anti-reference paths/SHA values changed")

    toolchain = _mapping(root["toolchain"], "manifest.toolchain")
    _exact_keys(toolchain, ("status", "ffmpeg_version", "ffprobe_version"), (), "manifest.toolchain")
    toolchain_status = _string(toolchain["status"], "manifest.toolchain.status")
    if toolchain_status not in {"pending", "verified"}:
        _fail("toolchain_status_invalid", "manifest.toolchain.status", toolchain_status)
    if toolchain_status == "pending":
        if toolchain["ffmpeg_version"] is not None or toolchain["ffprobe_version"] is not None:
            _fail("toolchain_status_invalid", "manifest.toolchain", "pending toolchain cannot claim versions")
    else:
        _string(toolchain["ffmpeg_version"], "manifest.toolchain.ffmpeg_version")
        _string(toolchain["ffprobe_version"], "manifest.toolchain.ffprobe_version")

    source = _mapping(root["source"], "manifest.source")
    _exact_keys(source, SCENES, (), "manifest.source")
    for scene in SCENES:
        source_row = _mapping(source[scene], f"manifest.source.{scene}")
        source_path = f"manifest.source.{scene}"
        _exact_keys(source_row, ("status",), ("path", "sha256", "bytes", "width", "height"), source_path)
        source_status = _string(source_row["status"], f"{source_path}.status")
        if source_status == "pending":
            if len(source_row) != 1:
                _fail("source_status_invalid", source_path, "pending source cannot claim identity fields")
            if not planned:
                _fail("source_status_invalid", source_path, "non-planned manifest requires adopted sources")
            continue
        if source_status != "adopted-source":
            _fail("source_status_invalid", f"{source_path}.status", source_status)
        _exact_keys(source_row, ("status", "path", "sha256", "bytes", "width", "height"), (), source_path)
        _validate_relative_path(source_row["path"], f"{source_path}.path")
        source_sha = _sha(source_row["sha256"], f"{source_path}.sha256")
        _integer(source_row["bytes"], f"{source_path}.bytes", minimum=1)
        _integer(source_row["width"], f"{source_path}.width", minimum=1)
        _integer(source_row["height"], f"{source_path}.height", minimum=1)
        if scene == "portal" and source_sha != PORTAL_SOURCE_SHA256:
            _fail("portal_source_identity_invalid", f"{source_path}.sha256", "does not match confirmed mother image")

    renditions = root["renditions"]
    if not isinstance(renditions, list):
        _fail("manifest_shape_invalid", "manifest.renditions", "expected an array")
    if planned:
        if renditions:
            _fail("planned_manifest_has_assets", "manifest.renditions", "planned manifest must not adopt assets")
    else:
        if len(renditions) != len(SCENES) * len(VIEWPORTS):
            _fail("rendition_matrix_incomplete", "manifest.renditions", "expected exact Portal/Account × desktop/mobile matrix")
        seen: set[tuple[str, str]] = set()
        for index, value in enumerate(renditions):
            path = f"manifest.renditions[{index}]"
            row = _mapping(value, path)
            _exact_keys(row, ("scene", "viewport", "source_sha256", "posters", "videos", "browser"), (), path)
            scene = _string(row["scene"], f"{path}.scene")
            viewport = _string(row["viewport"], f"{path}.viewport")
            if scene not in SCENES or viewport not in VIEWPORTS:
                _fail("rendition_identity_invalid", path, f"unsupported {scene}/{viewport}")
            identity = (scene, viewport)
            if identity in seen:
                _fail("rendition_identity_duplicate", path, f"duplicate {scene}/{viewport}")
            seen.add(identity)
            source_row = _mapping(source[scene], f"manifest.source.{scene}")
            source_sha = _sha(source_row["sha256"], f"manifest.source.{scene}.sha256")
            if _sha(row["source_sha256"], f"{path}.source_sha256") != source_sha:
                _fail("source_identity_mismatch", f"{path}.source_sha256", f"does not match {scene} source")
            posters = row["posters"]
            videos = row["videos"]
            if not isinstance(posters, list) or {item.get("format") for item in posters if isinstance(item, Mapping)} != set(POSTER_FORMATS):
                _fail("poster_matrix_invalid", f"{path}.posters", "expected exactly avif and webp")
            if not isinstance(videos, list) or {item.get("format") for item in videos if isinstance(item, Mapping)} != set(VIDEO_FORMATS):
                _fail("video_matrix_invalid", f"{path}.videos", "expected exactly webm and mp4")
            for poster_index, poster in enumerate(posters):
                _validate_poster(poster, f"{path}.posters[{poster_index}]", planned=False)
            for video_index, video in enumerate(videos):
                _validate_video(video, f"{path}.videos[{video_index}]", planned=False)
            browser = _mapping(row["browser"], f"{path}.browser")
            _exact_keys(browser, ("dropped_frame_ratio", "transferred_bytes"), (), f"{path}.browser")
            dropped = _number(browser["dropped_frame_ratio"], f"{path}.browser.dropped_frame_ratio", minimum=0.0, maximum=1.0)
            if dropped > MAX_DROPPED_FRAME_RATIO:
                _fail("dropped_frame_ratio_too_large", f"{path}.browser.dropped_frame_ratio", str(dropped))
            _integer(browser["transferred_bytes"], f"{path}.browser.transferred_bytes", minimum=0)
        if seen != {(scene, viewport) for scene in SCENES for viewport in VIEWPORTS}:
            _fail("rendition_matrix_incomplete", "manifest.renditions", "missing scene/viewport identity")

    budgets = _mapping(root["budgets"], "manifest.budgets")
    _exact_keys(
        budgets,
        ("js_gzip_bytes", "css_gzip_bytes", "non_media_cold_start_bytes", "total_media_bytes"),
        (),
        "manifest.budgets",
    )
    if not planned:
        for key in ("js_gzip_bytes", "css_gzip_bytes", "non_media_cold_start_bytes", "total_media_bytes"):
            _integer(budgets[key], f"manifest.budgets.{key}", minimum=0)
    return status


def _resolve_local(root: Path, value: str, path: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        _fail("media_path_outside_root", path, value)
    if not candidate.is_file():
        _fail("media_file_missing", path, value)
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_ffprobe(path: Path) -> Mapping[str, Any]:
    binary = shutil.which("ffprobe")
    if not binary:
        _fail("ffprobe_unavailable", str(path), "ffprobe is required for adopted media")
    command = [
        binary,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-show_packets",
        "-print_format",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except OSError as error:
        _fail("ffprobe_failed", str(path), type(error).__name__)
    except subprocess.TimeoutExpired:
        _fail("ffprobe_timeout", str(path), "ffprobe exceeded 20 seconds")
    if completed.returncode != 0:
        _fail("ffprobe_failed", str(path), "ffprobe returned a non-zero exit code")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        _fail("ffprobe_invalid_json", str(path), "ffprobe output was not JSON")
    return _mapping(payload, "ffprobe")


def _probe_stream(probe: Mapping[str, Any], *, path: str, kind: str) -> Mapping[str, Any]:
    streams = probe.get("streams")
    if isinstance(streams, list):
        if kind == "poster":
            stream = next((item for item in streams if isinstance(item, Mapping) and item.get("codec_type") == "video"), None)
        else:
            stream = next((item for item in streams if isinstance(item, Mapping) and item.get("codec_type") == "video"), None)
        if stream is None:
            _fail("media_stream_missing", path, "video stream is missing")
        return stream
    # Tests may inject an already-normalized probe record.
    return probe


def _probe_value(probe: Mapping[str, Any], stream: Mapping[str, Any], key: str, path: str) -> Any:
    if key in probe:
        return probe[key]
    if key in stream:
        return stream[key]
    _fail("media_probe_field_missing", path, key)


def _fps_value(value: Any, path: str) -> float:
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            return float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            _fail("video_fps_invalid", path, value)
    return _number(value, path, minimum=0.0)


def _check_file_and_probe(
    row: Mapping[str, Any],
    path: str,
    root: Path,
    probe: Probe,
    digest: Digest,
    *,
    kind: str,
) -> Mapping[str, Any]:
    local = _resolve_local(root, _string(row["path"], f"{path}.path"), f"{path}.path")
    actual_digest = digest(local).lower()
    if actual_digest != _sha(row["sha256"], f"{path}.sha256"):
        _fail("media_digest_mismatch", f"{path}.sha256", str(local.relative_to(root)))
    actual_bytes = local.stat().st_size
    if actual_bytes != _integer(row["bytes"], f"{path}.bytes", minimum=1):
        _fail("media_bytes_mismatch", f"{path}.bytes", str(local.relative_to(root)))
    return probe(local)


def audit_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path = PROJECT_ROOT,
    probe: Probe | None = None,
    digest: Digest = _sha256_file,
) -> dict[str, Any]:
    status = validate_manifest_contract(manifest)
    if status == "planned":
        return {"schema_version": SCHEMA_VERSION, "status": status, "checked_renditions": 0}

    root = root.resolve()
    source_rows = _mapping(manifest["source"], "manifest.source")
    source_sha_by_scene: dict[str, str] = {}
    for scene in SCENES:
        source_row = _mapping(source_rows[scene], f"manifest.source.{scene}")
        source_path = _resolve_local(root, _string(source_row["path"], f"manifest.source.{scene}.path"), f"manifest.source.{scene}.path")
        source_sha = _sha(source_row["sha256"], f"manifest.source.{scene}.sha256")
        if digest(source_path).lower() != source_sha:
            _fail("source_digest_mismatch", f"manifest.source.{scene}.sha256", str(source_path.relative_to(root)))
        if source_path.stat().st_size != _integer(source_row["bytes"], f"manifest.source.{scene}.bytes", minimum=1):
            _fail("source_bytes_mismatch", f"manifest.source.{scene}.bytes", str(source_path.relative_to(root)))
        source_sha_by_scene[scene] = source_sha
    if source_sha_by_scene["portal"] != PORTAL_SOURCE_SHA256:
        _fail("portal_source_identity_invalid", "manifest.source.portal.sha256", "does not match the confirmed Portal mother image")
    probe_fn = probe or (lambda path: _default_ffprobe(path))
    total_media_bytes = 0
    for index, value in enumerate(manifest["renditions"]):
        row = _mapping(value, f"manifest.renditions[{index}]")
        scene = _string(row["scene"], f"manifest.renditions[{index}].scene")
        viewport = _string(row["viewport"], f"manifest.renditions[{index}].viewport")
        poster_rows = row["posters"]
        for poster_index, poster_value in enumerate(poster_rows):
            poster = _mapping(poster_value, f"manifest.renditions[{index}].posters[{poster_index}]")
            poster_path = f"manifest.renditions[{index}].posters[{poster_index}]"
            poster_probe = _check_file_and_probe(poster, poster_path, root, probe_fn, digest, kind="poster")
            stream = _probe_stream(poster_probe, path=poster_path, kind="poster")
            if int(_probe_value(poster_probe, stream, "width", f"{poster_path}.width")) != _integer(poster["width"], f"{poster_path}.width", minimum=1):
                _fail("poster_dimensions_mismatch", f"{poster_path}.width", str(poster["path"]))
            if int(_probe_value(poster_probe, stream, "height", f"{poster_path}.height")) != _integer(poster["height"], f"{poster_path}.height", minimum=1):
                _fail("poster_dimensions_mismatch", f"{poster_path}.height", str(poster["path"]))
            if int(poster["bytes"]) > POSTER_BUDGETS[(scene, viewport)]:
                _fail("poster_budget_exceeded", poster_path, str(poster["bytes"]))
            total_media_bytes += int(poster["bytes"])

        for video_index, video_value in enumerate(row["videos"]):
            video = _mapping(video_value, f"manifest.renditions[{index}].videos[{video_index}]")
            video_path = f"manifest.renditions[{index}].videos[{video_index}]"
            video_probe = _check_file_and_probe(video, video_path, root, probe_fn, digest, kind="video")
            stream = _probe_stream(video_probe, path=video_path, kind="video")
            format_probe = _mapping(video_probe.get("format", {}), f"{video_path}.format_probe")
            format_name = str(video_probe.get("format_name", format_probe.get("format_name", ""))).casefold()
            codec = str(video_probe.get("codec_name", stream.get("codec_name", ""))).casefold()
            expected_format = str(video["format"])
            if expected_format == "webm" and ("webm" not in format_name or codec != "vp9"):
                _fail("video_codec_invalid", video_path, "webm rendition must be VP9")
            if expected_format == "mp4" and ("mp4" not in format_name and "mov" not in format_name or codec != "h264"):
                _fail("video_codec_invalid", video_path, "mp4 rendition must be H.264")
            for key in ("width", "height"):
                actual = int(_probe_value(video_probe, stream, key, f"{video_path}.{key}"))
                declared = _integer(video[key], f"{video_path}.{key}", minimum=1)
                if actual != declared:
                    _fail("video_dimensions_mismatch", f"{video_path}.{key}", str(video["path"]))
            fps = _fps_value(video_probe.get("fps", stream.get("avg_frame_rate", stream.get("r_frame_rate"))), f"{video_path}.fps")
            if abs(fps - 24.0) > 0.01:
                _fail("video_fps_invalid", f"{video_path}.fps", str(fps))
            for key in ("pix_fmt", "color_space", "color_transfer", "color_primaries"):
                actual = str(video_probe.get(key, stream.get(key, ""))).casefold()
                if actual != str(video[key]).casefold():
                    _fail("video_probe_contract_invalid", f"{video_path}.{key}", actual)
            if bool(video_probe.get("has_audio", any(item.get("codec_type") == "audio" for item in video_probe.get("streams", []) if isinstance(item, Mapping)))):
                _fail("video_audio_present", video_path, "audio stream detected")
            for boolean_key in ("faststart", "metadata_removed"):
                if video_probe.get(boolean_key) is not None and video_probe.get(boolean_key) is not video[boolean_key]:
                    _fail("video_probe_contract_invalid", f"{video_path}.{boolean_key}", str(video_probe.get(boolean_key)))
            if int(video["bytes"]) > VIDEO_BUDGETS[(scene, viewport, expected_format)]:
                _fail("video_budget_exceeded", video_path, str(video["bytes"]))
            total_media_bytes += int(video["bytes"])

    budgets = _mapping(manifest["budgets"], "manifest.budgets")
    js_bytes = _integer(budgets["js_gzip_bytes"], "manifest.budgets.js_gzip_bytes", minimum=0)
    css_bytes = _integer(budgets["css_gzip_bytes"], "manifest.budgets.css_gzip_bytes", minimum=0)
    cold_bytes = _integer(budgets["non_media_cold_start_bytes"], "manifest.budgets.non_media_cold_start_bytes", minimum=0)
    declared_total = _integer(budgets["total_media_bytes"], "manifest.budgets.total_media_bytes", minimum=0)
    if js_bytes > MAX_JS_GZIP_BYTES:
        _fail("js_budget_exceeded", "manifest.budgets.js_gzip_bytes", str(js_bytes))
    if css_bytes > MAX_CSS_GZIP_BYTES:
        _fail("css_budget_exceeded", "manifest.budgets.css_gzip_bytes", str(css_bytes))
    if cold_bytes > MAX_NON_MEDIA_COLD_START_BYTES:
        _fail("cold_start_budget_exceeded", "manifest.budgets.non_media_cold_start_bytes", str(cold_bytes))
    if declared_total != total_media_bytes:
        _fail("total_media_bytes_mismatch", "manifest.budgets.total_media_bytes", f"declared={declared_total}, actual={total_media_bytes}")
    if total_media_bytes > MAX_TOTAL_MEDIA_BYTES:
        _fail("total_media_budget_exceeded", "manifest.budgets.total_media_bytes", str(total_media_bytes))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "checked_renditions": len(manifest["renditions"]),
        "total_media_bytes": total_media_bytes,
        "js_gzip_bytes": js_bytes,
        "css_gzip_bytes": css_bytes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only RQ-108 cinematic media contract and budget audit.")
    parser.add_argument("--manifest", type=Path, required=True, help="JSON audit manifest")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Root for relative media paths")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print a JSON result")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = audit_manifest(
            _mapping(payload, "manifest"),
            root=args.root,
            probe=None,
        )
    except (OSError, json.JSONDecodeError) as error:
        print(f"cinematic_media_audit_failed manifest_read_error: {type(error).__name__}", file=sys.stderr)
        return 1
    except CinematicMediaAuditError as error:
        print(f"cinematic_media_audit_failed {error.code} {error.path}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True) if args.as_json else f"cinematic_media_audit {result['status']} checked={result['checked_renditions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
