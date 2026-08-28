"""Render the source-derived layer proof locally.

This renderer intentionally makes no external model calls. The mother image is
the immutable base. Only source-derived bright material pixels are shifted in
feathered masks; opaque architecture never moves.
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
# Contract labels kept in the implementation for auditability: locked-base
# never moves; central_event is a local crystal-only alpha envelope.


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Portal source-derived material layers")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--duration", type=float, default=DURATION)
    parser.add_argument("--motion-scale", type=float, default=1.0)
    parser.add_argument("--mode", choices=("lightfield", "shifted", "replace-shifted"), default="lightfield")
    return parser.parse_args()


def mask_from_polygon(size: tuple[int, int], points: list[tuple[int, int]], blur: float = 12.0) -> np.ndarray:
    image = Image.new("L", size, 0)
    ImageDraw.Draw(image).polygon(points, fill=255)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(image, dtype=np.float32) / 255.0


def shift_array(array: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Periodic-safe shift with zeroed wrap edges, not a camera transform."""
    shifted = np.roll(array, shift=(dy, dx), axis=(0, 1))
    if dy > 0:
        shifted[:dy, ...] = 0
    elif dy < 0:
        shifted[dy:, ...] = 0
    if dx > 0:
        shifted[:, :dx, ...] = 0
    elif dx < 0:
        shifted[:, dx:, ...] = 0
    return shifted


def phase_shift(t: float, phase: float, amplitude: tuple[float, float], speed: float = 1.0) -> tuple[int, int]:
    theta = 2.0 * math.pi * (t / DURATION) * speed + phase
    return round(amplitude[0] * math.sin(theta)), round(amplitude[1] * math.cos(theta * 1.13))


def lightfield_coordinate(name: str, width: int, height: int) -> tuple[np.ndarray, int, float]:
    y, x = np.mgrid[0:height, 0:width]
    xn = x / max(width - 1, 1)
    yn = y / max(height - 1, 1)
    if name == "rift-energy":
        angle = (np.arctan2(y - height * 0.40, x - width * 0.15) + math.pi) / (2.0 * math.pi)
        radius = np.sqrt(((x - width * 0.15) / width) ** 2 + ((y - height * 0.40) / height) ** 2)
        return (angle + radius * 0.65) % 1.0, 3, 1.0
    if name == "road-reflection":
        return (xn * 0.72 + yn * 0.28) % 1.0, 3, 1.0
    if name == "crystal-refraction":
        return yn % 1.0, 2, 0.92
    if name == "right-constellation-terrain":
        return (xn * 0.78 + yn * 0.22) % 1.0, 2, 1.0
    if name.startswith("air-"):
        return yn % 1.0, 2, 0.68
    return xn % 1.0, 2, 0.86


def write_preview(path: Path, alpha: np.ndarray) -> None:
    preview = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(path)


def build_layers(source: np.ndarray, motion_scale: float = 1.0) -> dict[str, tuple[np.ndarray, tuple[float, float], float, float]]:
    height, width = source.shape[:2]
    r, g, b = source[..., 0], source[..., 1], source[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    blue = np.clip((b - 0.78 * r - 0.10 * g - 0.018) / 0.22, 0.0, 1.0)
    # Keep only source highlights and high-frequency energy. The high-pass term
    # is the anti-veil boundary: dark/opaque architecture is never copied into
    # a moving layer, while existing filaments/facets remain visibly mobile.
    blurred = np.asarray(
        Image.fromarray(np.clip(source * 255.0, 0, 255).astype(np.uint8), mode="RGB")
        .filter(ImageFilter.GaussianBlur(10)),
        dtype=np.float32,
    ) / 255.0
    blurred_luma = 0.2126 * blurred[..., 0] + 0.7152 * blurred[..., 1] + 0.0722 * blurred[..., 2]
    detail = np.clip((luma - blurred_luma - 0.001) / 0.022, 0.0, 1.0)
    broad_highlight = np.clip((luma - 0.05) / 0.28, 0.0, 1.0) ** 0.95
    energy = (0.42 * broad_highlight + 0.58 * detail) * (0.24 + 0.76 * blue)

    def polygon(points: list[tuple[int, int]], strength: float, phase: float) -> tuple[np.ndarray, tuple[float, float], float, float]:
        mask = mask_from_polygon((width, height), points, blur=12.0)
        return source, (strength, 0.0), phase, mask

    masks = {
        "rift-energy": mask_from_polygon((width, height), [(92, 150), (174, 104), (350, 122), (444, 222), (460, 394), (420, 510), (288, 626), (144, 584), (82, 438)], blur=12),
        "road-reflection": mask_from_polygon((width, height), [(38, 785), (255, 690), (500, 560), (835, 475), (880, 570), (630, 665), (410, 780), (48, 920)], blur=10),
        "crystal-refraction": mask_from_polygon((width, height), [(946, 170), (1000, 130), (1054, 170), (1054, 394), (1000, 438), (946, 394), (970, 438), (1030, 438), (1040, 690), (960, 690)], blur=7),
        "right-constellation-terrain": mask_from_polygon((width, height), [(1128, 78), (1920, 20), (1920, 825), (1530, 836), (1280, 760), (1112, 625)], blur=14),
        "air-far": mask_from_polygon((width, height), [(0, 0), (1920, 0), (1920, 305), (1360, 282), (760, 300), (0, 325)], blur=20),
        "air-mid": mask_from_polygon((width, height), [(0, 220), (1920, 200), (1920, 620), (1300, 600), (650, 610), (0, 630)], blur=20),
        "air-near": mask_from_polygon((width, height), [(0, 560), (1920, 575), (1920, 1080), (0, 1080)], blur=18),
        "foreground-surface-light": mask_from_polygon((width, height), [(0, 748), (420, 710), (1035, 720), (1500, 735), (1920, 760), (1920, 1080), (0, 1080)], blur=12),
    }
    specs = {
        "rift-energy": ((5.0, 3.0), 0.40, 0.10),
        "road-reflection": ((7.0, 2.0), 0.38, 0.40),
        "crystal-refraction": ((2.0, 4.0), 0.34, 0.80),
        "right-constellation-terrain": ((5.0, 2.0), 0.36, 1.30),
        "air-far": ((3.0, 1.0), 0.08, 0.20),
        "air-mid": ((4.0, 1.0), 0.09, 2.00),
        "air-near": ((4.0, 1.0), 0.08, 3.10),
        "foreground-surface-light": ((4.0, 2.0), 0.18, 4.20),
    }
    layers: dict[str, tuple[np.ndarray, tuple[float, float], float, float]] = {}
    for name, mask in masks.items():
        amp, strength, phase = specs[name]
        layers[name] = (energy * mask * strength * motion_scale, tuple(value * motion_scale for value in amp), phase, 1.0)
    return layers


def render(args: argparse.Namespace) -> dict[str, object]:
    if args.fps != FPS or args.duration != DURATION:
        raise SystemExit("This proof is frozen at 192 frames / 24fps / 8 seconds.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    layer_dir = args.output_dir / "layers"
    layer_dir.mkdir(exist_ok=True)

    source_path = args.source.resolve()
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_sha != SOURCE_SHA256:
        raise SystemExit(f"source SHA mismatch: {source_sha}")
    source_image = Image.open(source_path).convert("RGB").resize((args.width, args.height), Image.Resampling.LANCZOS)
    source = np.asarray(source_image, dtype=np.float32) / 255.0
    if not 0.5 <= args.motion_scale <= 3.0:
        raise SystemExit("motion-scale must stay between 0.5 and 3.0")
    layers = build_layers(source, args.motion_scale)
    if args.mode == "replace-shifted":
        blurred = np.asarray(source_image.filter(ImageFilter.GaussianBlur(8)), dtype=np.float32) / 255.0
        moving_alpha = np.maximum.reduce([values[0] for values in layers.values()])
        removal = np.clip(moving_alpha * 0.55, 0.0, 0.16)[..., None]
        # Approximate a backplate only where moving source highlights will be
        # replaced. The rest of the mother image remains pixel-identical.
        clean_base = source * (1.0 - removal) + blurred * removal
    else:
        clean_base = source
    for name, (alpha, _amp, _phase, _event) in layers.items():
        write_preview(layer_dir / f"{name}-alpha.png", alpha)

    output_path = args.output_dir / "layer-assets-proof-v1.mp4"
    ffmpeg = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}",
        "-r", str(args.fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        str(output_path),
    ], stdin=subprocess.PIPE)
    assert ffmpeg.stdin is not None
    for frame_index in range(args.fps * int(args.duration)):
        t = frame_index / args.fps
        frame = clean_base.copy()
        for name, (alpha, amplitude, phase, _event) in layers.items():
            if args.mode == "lightfield":
                coord, cycles, speed = lightfield_coordinate(name, args.width, args.height)
                phase_wave = (2.0 * math.pi * (coord * cycles - (t / DURATION) * speed) + phase)
                wave = np.sin(phase_wave)
                modulation = 1.0 + np.clip(0.18 * args.motion_scale, 0.0, 0.48) * wave
                if name == "crystal-refraction":
                    event = math.exp(-0.5 * ((t - 4.5) / 0.85) ** 2)
                    modulation *= 1.0 + 0.35 * event
                a = np.clip(alpha * modulation, 0.0, min(0.30, 0.18 * args.motion_scale))[..., None]
                frame = frame * (1.0 - a) + source * a
                continue
            dx, dy = phase_shift(t, phase, amplitude, speed=0.82 if name.startswith("air-") else 1.0)
            # Two source-derived samples create parallax-like material flow
            # inside a layer. Neither sample carries opaque architecture.
            samples = ((dx, dy, 1.0), (round(-dx * 0.55), round(-dy * 0.55), 0.34))
            for sample_dx, sample_dy, sample_weight in samples:
                shifted_rgb = shift_array(source, sample_dx, sample_dy)
                shifted_alpha = shift_array(alpha, sample_dx, sample_dy) * sample_weight
                central_event = None
                if name == "crystal-refraction":
                    central_event = "crystal-only"
                    event = math.exp(-0.5 * ((t - 4.5) / 0.85) ** 2)
                    shifted_alpha = shifted_alpha * (1.0 + 0.35 * event)
                local_phase = 2.0 * math.pi * (t / DURATION) + phase + sample_weight
                shifted_alpha *= 0.88 + 0.12 * (0.5 + 0.5 * math.sin(local_phase))
                a = np.clip(shifted_alpha, 0.0, min(0.36, 0.18 * args.motion_scale))[..., None]
                frame = frame * (1.0 - a) + shifted_rgb * a
        ffmpeg.stdin.write(np.clip(frame * 255.0, 0, 255).astype(np.uint8).tobytes())
    ffmpeg.stdin.close()
    return_code = ffmpeg.wait()
    if return_code != 0:
        raise SystemExit(f"ffmpeg exited with {return_code}")

    manifest = {
        "schema_version": "1.0",
        "status": "research-proof",
        "source_sha256": source_sha,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "frames": args.fps * int(args.duration),
        "duration_s": args.duration,
        "alpha_policy": "source-derived-high-energy-only",
        "motion_scale": args.motion_scale,
        "mode": args.mode,
        "base_geometry_moves": False,
        "external_model_calls": 0,
        "output": str(output_path),
    }
    (args.output_dir / "proof-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    render(parse_args())
