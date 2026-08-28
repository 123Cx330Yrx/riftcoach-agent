"""Generate and render independent transparent material plates locally.

This renderer makes no external model calls. The locked-base image is never
shifted or blurred; every moving plate is newly generated RGBA texture. The
compositor changes alpha-only plate layers and never duplicates source pixels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SOURCE_SHA256 = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
FPS = 24
DURATION = 8.0
FRAMES = 192


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Portal material plates")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--duration", type=float, default=DURATION)
    parser.add_argument("--motion-scale", type=float, default=1.0)
    return parser.parse_args()


def smooth_noise(width: int, height: int, grid_x: int, grid_y: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    small = Image.fromarray((rng.random((grid_y, grid_x)) * 255).astype(np.uint8), mode="L")
    large = small.resize((width, height), Image.Resampling.BICUBIC)
    return np.asarray(large, dtype=np.float32) / 255.0


def mask_from_polygon(width: int, height: int, points: list[tuple[int, int]], blur: float) -> np.ndarray:
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return np.asarray(mask.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32) / 255.0


def shift_rgba(rgba: np.ndarray, dx: int, dy: int) -> np.ndarray:
    shifted = np.roll(rgba, shift=(dy, dx), axis=(0, 1))
    if dy > 0:
        shifted[:dy, ...] = 0
    elif dy < 0:
        shifted[dy:, ...] = 0
    if dx > 0:
        shifted[:, :dx, ...] = 0
    elif dx < 0:
        shifted[:, dx:, ...] = 0
    return shifted


def make_plate(mask: np.ndarray, color: tuple[int, int, int], seed: int, strength: float) -> np.ndarray:
    height, width = mask.shape
    coarse = smooth_noise(width, height, 24, 14, seed)
    fine = smooth_noise(width, height, 72, 44, seed + 19)
    field = np.clip(0.68 * coarse + 0.32 * fine, 0.0, 1.0)
    ridge = np.clip(np.abs(field * 2.0 - 1.0) * 1.7 - 0.35, 0.0, 1.0)
    luminance = np.clip(0.22 + 0.55 * field + 0.23 * ridge, 0.0, 1.0)
    alpha = np.clip(mask * strength * (0.18 + 0.82 * luminance), 0.0, 0.34)
    rgb = np.empty((height, width, 3), dtype=np.float32)
    for index, channel in enumerate(color):
        rgb[..., index] = channel / 255.0 * (0.68 + 0.32 * luminance)
    rgba = np.concatenate([np.clip(rgb * 255.0, 0, 255), alpha[..., None] * 255.0], axis=2)
    return np.clip(rgba, 0, 255).astype(np.uint8)


def plate_specs(width: int, height: int) -> dict[str, tuple[np.ndarray, tuple[int, int, int], tuple[float, float], float, float]]:
    masks = {
        "rift-fluid": mask_from_polygon(width, height, [(92, 150), (174, 104), (350, 122), (444, 222), (460, 394), (420, 510), (288, 626), (144, 584), (82, 438)], 14),
        "road-caustic": mask_from_polygon(width, height, [(38, 785), (255, 690), (500, 560), (835, 475), (880, 570), (630, 665), (410, 780), (48, 920)], 11),
        "crystal-refraction": mask_from_polygon(width, height, [(946, 170), (1000, 130), (1054, 170), (1054, 394), (1000, 438), (946, 394), (970, 438), (1030, 438), (1040, 690), (960, 690)], 8),
        "right-field": mask_from_polygon(width, height, [(1130, 80), (1920, 20), (1920, 820), (1530, 835), (1280, 760), (1112, 625)], 16),
        "air-far": mask_from_polygon(width, height, [(0, 0), (1920, 0), (1920, 304), (1360, 282), (760, 300), (0, 325)], 22),
        "air-mid": mask_from_polygon(width, height, [(0, 220), (1920, 200), (1920, 620), (1300, 600), (650, 610), (0, 630)], 22),
        "air-near": mask_from_polygon(width, height, [(0, 560), (1920, 575), (1920, 1080), (0, 1080)], 20),
        "foreground-reflection": mask_from_polygon(width, height, [(0, 748), (420, 710), (1035, 720), (1500, 735), (1920, 760), (1920, 1080), (0, 1080)], 14),
    }
    specs = {
        "rift-fluid": ((20.0, 10.0), 0.82, 0.14, (42, 188, 255)),
        "road-caustic": ((24.0, 8.0), 0.76, 0.52, (44, 196, 255)),
        "crystal-refraction": ((6.0, 18.0), 0.72, 0.90, (128, 232, 255)),
        "right-field": ((18.0, 8.0), 0.70, 1.35, (42, 176, 255)),
        "air-far": ((8.0, 3.0), 0.38, 0.22, (48, 144, 215)),
        "air-mid": ((10.0, 3.0), 0.34, 2.10, (54, 170, 235)),
        "air-near": ((12.0, 4.0), 0.30, 3.20, (42, 156, 224)),
        "foreground-reflection": ((14.0, 6.0), 0.48, 4.35, (36, 169, 230)),
    }
    return {
        name: (masks[name], color, amplitude, phase, strength)
        for name, (amplitude, strength, phase, color) in specs.items()
    }


def render(args: argparse.Namespace) -> dict[str, object]:
    if args.fps != FPS or args.duration != DURATION:
        raise SystemExit("This proof is frozen at 192 frames / 24fps / 8 seconds.")
    if not 0.5 <= args.motion_scale <= 3.0:
        raise SystemExit("motion-scale must stay between 0.5 and 3.0")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    layer_dir = args.output_dir / "plates"
    layer_dir.mkdir(exist_ok=True)
    source_path = args.source.resolve()
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_sha != SOURCE_SHA256:
        raise SystemExit(f"source SHA mismatch: {source_sha}")
    source_image = Image.open(source_path).convert("RGB").resize((args.width, args.height), Image.Resampling.LANCZOS)
    base = np.asarray(source_image, dtype=np.float32) / 255.0
    specs = plate_specs(args.width, args.height)
    plates: dict[str, tuple[np.ndarray, tuple[float, float], float, float]] = {}
    for index, (name, (mask, color, amplitude, phase, strength)) in enumerate(specs.items()):
        plate = make_plate(mask, color, 100 + index * 17, strength)
        Image.fromarray(plate, mode="RGBA").save(layer_dir / f"{name}.png")
        plates[name] = (plate, amplitude, phase, strength)

    output_path = args.output_dir / "material-plate-proof-v1.mp4"
    ffmpeg = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(output_path)
    ], stdin=subprocess.PIPE)
    assert ffmpeg.stdin is not None
    for frame_index in range(FRAMES):
        t = frame_index / args.fps
        frame = base.copy()  # locked-base: never shifted, blurred, or globally tinted
        for name, (plate, amplitude, phase, _strength) in plates.items():
            theta = 2.0 * math.pi * (t / DURATION) + phase
            dx = round(amplitude[0] * args.motion_scale * math.sin(theta))
            dy = round(amplitude[1] * args.motion_scale * math.cos(theta * 1.17))
            moved = shift_rgba(plate, dx, dy)
            alpha = moved[..., 3].astype(np.float32) / 255.0
            if name == "crystal-refraction":
                event = math.exp(-0.5 * ((t - 4.5) / 0.85) ** 2)
                alpha *= 1.0 + 0.35 * event
            alpha = np.clip(alpha, 0.0, 0.34)[..., None]
            rgb = moved[..., :3].astype(np.float32) / 255.0
            frame = frame * (1.0 - alpha) + rgb * alpha
        ffmpeg.stdin.write(np.clip(frame * 255.0, 0, 255).astype(np.uint8).tobytes())
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise SystemExit("ffmpeg failed")

    manifest = {
        "schema_version": "1.0",
        "status": "research-proof",
        "source_sha256": source_sha,
        "timeline": {"width": args.width, "height": args.height, "fps": args.fps, "frames": FRAMES, "duration_s": args.duration},
        "plate_roles": list(plates),
        "plate_policy": {"format": "RGBA PNG", "source_pixels_copied": False, "base_moves": False, "full_frame_veil": False, "max_alpha": 0.34},
        "motion_scale": args.motion_scale,
        "external_model_calls": 0,
        "output": str(output_path),
    }
    (args.output_dir / "plate-proof-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    render(parse_args())
