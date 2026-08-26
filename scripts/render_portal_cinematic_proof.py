"""Render the RQ-125 Portal hybrid motion proof in an isolated research directory.

The wrapper never installs HyperFrames, signs in, enables telemetry, calls a media
provider, or writes generated media inside the repository.  It accepts only an
already-vetted local HyperFrames 0.8.14 installation and the pinned Portal source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Sequence


EXPECTED_HYPERFRAMES_VERSION = "0.8.14"
EXPECTED_SOURCE_SHA256 = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
EXPERIMENT_RELATIVE = Path("experiments/portal_cinematic_proof")
SOURCE_RELATIVE = Path("docs/assets/8e-portal/portal-mother-image-source-v2.png")


class RenderPlan(NamedTuple):
    project_root: Path
    hyperframes_root: Path
    hyperframes_version: str
    source_path: Path
    source_sha256: str
    browser_path: Path
    output_dir: Path
    work_dir: Path
    frames_dir: Path
    preview_path: Path
    commands: tuple[tuple[str, ...], ...]
    external_model_calls: int
    network_assets: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _hyperframes_executable(hyperframes_root: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    executable = hyperframes_root / "node_modules" / ".bin" / f"hyperframes{suffix}"
    if not executable.is_file():
        raise ValueError("hyperframes_executable_missing")
    return executable.resolve()


def build_plan(
    *,
    project_root: Path,
    hyperframes_root: Path,
    output_dir: Path,
    ffmpeg_path: Path,
    ffprobe_path: Path,
    browser_path: Path,
) -> RenderPlan:
    project_root = project_root.resolve()
    hyperframes_root = hyperframes_root.resolve()
    output_dir = output_dir.resolve()
    if _inside(output_dir, project_root):
        raise ValueError("output_inside_repository")

    source_path = (project_root / SOURCE_RELATIVE).resolve()
    if not source_path.is_file():
        raise ValueError("portal_source_missing")
    source_sha256 = _sha256_file(source_path)
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("portal_source_digest_mismatch")

    package_path = hyperframes_root / "node_modules" / "hyperframes" / "package.json"
    if not package_path.is_file():
        raise ValueError("hyperframes_package_missing")
    try:
        hyperframes_version = str(json.loads(package_path.read_text(encoding="utf-8"))["version"])
    except (KeyError, json.JSONDecodeError, OSError) as error:
        raise ValueError("hyperframes_package_invalid") from error
    if hyperframes_version != EXPECTED_HYPERFRAMES_VERSION:
        raise ValueError("hyperframes_version_mismatch")
    hyperframes = _hyperframes_executable(hyperframes_root)
    browser_path = browser_path.resolve()
    if not browser_path.is_file() or browser_path.name.casefold() != "chrome-headless-shell.exe":
        raise ValueError("browser_path_invalid")

    work_dir = output_dir / "work"
    frames_dir = output_dir / "frames"
    preview_path = output_dir / "portal-c-line-proof-preview.mp4"
    frame_pattern = frames_dir / "frame_%06d.png"

    check_command = (
        str(hyperframes),
        "check",
        str(work_dir),
        "--json",
        "--samples=9",
        "--no-browser-gpu",
    )
    render_command = (
        str(hyperframes),
        "render",
        "--format",
        "png-sequence",
        "--fps",
        "24",
        "--workers",
        "1",
        "--no-browser-gpu",
        "--strict",
        "--no-best-effort",
        "-o",
        str(frames_dir),
        str(work_dir),
    )
    encode_command = (
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        "24",
        "-start_number",
        "1",
        "-i",
        str(frame_pattern),
        "-frames:v",
        "192",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-g",
        "48",
        "-keyint_min",
        "48",
        "-sc_threshold",
        "0",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-movflags",
        "+faststart",
        "-map_metadata",
        "-1",
        str(preview_path),
    )
    probe_command = (
        str(ffprobe_path),
        "-v",
        "error",
        "-show_entries",
        "stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,color_space,color_transfer,color_primaries:format=duration,size",
        "-of",
        "json",
        str(preview_path),
    )
    return RenderPlan(
        project_root=project_root,
        hyperframes_root=hyperframes_root,
        hyperframes_version=hyperframes_version,
        source_path=source_path,
        source_sha256=source_sha256,
        browser_path=browser_path,
        output_dir=output_dir,
        work_dir=work_dir,
        frames_dir=frames_dir,
        preview_path=preview_path,
        commands=(check_command, render_command, encode_command, probe_command),
        external_model_calls=0,
        network_assets=False,
    )


def _safe_environment(plan: RenderPlan) -> dict[str, str]:
    environment = dict(os.environ)
    home = plan.output_dir / "home"
    home.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "HYPERFRAMES_NO_TELEMETRY": "1",
            "DO_NOT_TRACK": "1",
            "NO_UPDATE_NOTIFIER": "1",
            "npm_config_update_notifier": "false",
            "HYPERFRAMES_EXTRACT_CACHE_DIR": "off",
            "HYPERFRAMES_BROWSER_PATH": str(plan.browser_path),
            "PRODUCER_HEADLESS_SHELL_PATH": str(plan.browser_path),
        }
    )
    return environment


def _prepare_work_dir(plan: RenderPlan) -> None:
    if plan.preview_path.exists() or plan.frames_dir.exists() or plan.work_dir.exists():
        raise ValueError("output_already_exists")
    assets = plan.work_dir / "assets"
    assets.mkdir(parents=True)
    source_experiment = plan.project_root / EXPERIMENT_RELATIVE
    shutil.copy2(source_experiment / "index.html", plan.work_dir / "index.html")
    shutil.copy2(source_experiment / "motion-contract.json", plan.work_dir / "motion-contract.json")
    shutil.copy2(plan.source_path, assets / "portal-mother-image-source-v2.png")


def _run(command: tuple[str, ...], *, environment: dict[str, str], timeout_s: int) -> subprocess.CompletedProcess[str]:
    actual: Sequence[str]
    if os.name == "nt" and command[0].casefold().endswith(".cmd"):
        actual = ("cmd.exe", "/d", "/s", "/c", *command)
    else:
        actual = command
    completed = subprocess.run(
        actual,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command_failed:{Path(command[0]).name}:{command[1]}:{completed.returncode}")
    return completed


def execute(plan: RenderPlan) -> dict[str, object]:
    _prepare_work_dir(plan)
    environment = _safe_environment(plan)
    _run(plan.commands[0], environment=environment, timeout_s=120)
    _run(plan.commands[1], environment=environment, timeout_s=1800)
    _run(plan.commands[2], environment=environment, timeout_s=600)
    probe = _run(plan.commands[3], environment=environment, timeout_s=30)
    try:
        probe_payload = json.loads(probe.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("ffprobe_invalid_json") from error
    return {
        "schema_version": "1.0",
        "status": "rendered",
        "source_sha256": plan.source_sha256,
        "hyperframes_version": plan.hyperframes_version,
        "external_model_calls": 0,
        "network_assets": False,
        "preview_path": str(plan.preview_path),
        "preview_sha256": _sha256_file(plan.preview_path),
        "frames": len(list(plan.frames_dir.glob("*.png"))),
        "probe": probe_payload,
    }


def _resolve_tool(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_file():
        return candidate.resolve()
    resolved = shutil.which(value)
    if not resolved:
        raise ValueError(f"tool_missing:{value}")
    return Path(resolved).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the isolated RQ-125 Portal C-line proof.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hyperframes-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--browser-path", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = build_plan(
            project_root=args.project_root,
            hyperframes_root=args.hyperframes_root,
            output_dir=args.output_dir,
            ffmpeg_path=_resolve_tool(args.ffmpeg),
            ffprobe_path=_resolve_tool(args.ffprobe),
            browser_path=args.browser_path,
        )
        result = execute(plan) if args.execute else {
            "schema_version": "1.0",
            "status": "dry-run",
            "source_sha256": plan.source_sha256,
            "hyperframes_version": plan.hyperframes_version,
            "output_dir": str(plan.output_dir),
            "browser_path": str(plan.browser_path),
            "external_model_calls": 0,
            "network_assets": False,
            "commands": [Path(command[0]).name + ":" + command[1] for command in plan.commands],
        }
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"portal_c_line_proof_failed:{type(error).__name__}:{error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
