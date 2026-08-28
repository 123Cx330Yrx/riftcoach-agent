"""Bounded Rift inpaint/backplate + transparent plate research proof.

The mother image remains the immutable base.  The generated backplate is used
only inside a hand-bounded Rift aperture mask; one independent RGBA plate is
clipped to that same mask and moved on a periodic local clock.  This is a
no-network, research-only proof and never writes runtime media.
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


SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
BACKPLATE_SHA = "04a8302f050dd54934e7af8ac297caf5a6e91d622aab51305a2a2c7f1c0434d0"
PLATE_SHA = "fb3a4bd991fbf69ac2cd2a4d96eb496dfeefc589987cb16ca244f087bad998c3"
FPS = 24
FRAMES = 192
DURATION = 8.0

MASK_POINTS = [
    (132, 234), (170, 184), (252, 166), (350, 184), (430, 246),
    (468, 338), (463, 440), (418, 514), (350, 562), (270, 579),
    (184, 548), (126, 492), (106, 394), (112, 300),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render bounded Rift inpaint/plate proof")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--backplate", type=Path, required=True)
    parser.add_argument("--plate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--motion-scale", type=float, default=1.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rift_mask(width: int, height: int) -> np.ndarray:
    scale_x = width / 1672.0
    scale_y = height / 941.0
    points = [(round(x * scale_x), round(y * scale_y)) for x, y in MASK_POINTS]
    image = Image.new("L", (width, height), 0)
    ImageDraw.Draw(image).polygon(points, fill=255)
    image = image.filter(ImageFilter.GaussianBlur(max(2.0, 9.0 * scale_x)))
    return np.asarray(image, dtype=np.float32) / 255.0


def prepare_plate(path: Path, width: int, height: int) -> np.ndarray:
    image = Image.open(path).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
    rgba = np.asarray(image, dtype=np.float32) / 255.0
    return rgba


def shift_rgba(rgba: np.ndarray, dx: int, dy: int) -> np.ndarray:
    moved = np.roll(rgba, shift=(dy, dx), axis=(0, 1))
    if dy > 0:
        moved[:dy] = 0
    elif dy < 0:
        moved[dy:] = 0
    if dx > 0:
        moved[:, :dx] = 0
    elif dx < 0:
        moved[:, dx:] = 0
    return moved


def render(args: argparse.Namespace) -> dict[str, object]:
    if (args.width, args.height) != (960, 540):
        raise SystemExit("This bounded proof is frozen at 960x540.")
    if not 0.5 <= args.motion_scale <= 1.5:
        raise SystemExit("motion-scale must stay between 0.5 and 1.5")
    if sha256(args.source) != SOURCE_SHA:
        raise SystemExit("source SHA mismatch")
    if sha256(args.backplate) != BACKPLATE_SHA:
        raise SystemExit("backplate SHA mismatch")
    if sha256(args.plate) != PLATE_SHA:
        raise SystemExit("plate SHA mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(args.source).convert("RGB").resize((args.width, args.height), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    backplate = np.asarray(Image.open(args.backplate).convert("RGB").resize((args.width, args.height), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    plate = prepare_plate(args.plate, args.width, args.height)
    mask = rift_mask(args.width, args.height)
    # The clean backplate replaces only the inner Rift aperture.  Every pixel
    # outside this feathered mask remains the original source pixel.
    locked_base = source * (1.0 - mask[..., None]) + backplate * mask[..., None]
    # Use a deliberately visible low-resolution gate.  The cap still keeps
    # the plate translucent; this is not a production opacity recommendation.
    clipped_alpha = np.clip(plate[..., 3] * mask * 0.72, 0.0, 0.34)
    plate_rgb = np.clip(plate[..., :3], 0.0, 1.0)
    output = args.output_dir / "masked-inpaint-plate-proof-v1.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{args.width}x{args.height}", "-r", str(FPS),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-colorspace", "bt709", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    for index in range(FRAMES):
        t = index / FPS
        theta = 2.0 * math.pi * t / DURATION
        dx = round(7.0 * args.motion_scale * math.sin(theta))
        dy = round(3.0 * args.motion_scale * math.cos(theta * 1.11))
        moved = shift_rgba(np.dstack((plate_rgb, clipped_alpha)), dx, dy)
        alpha = np.clip(moved[..., 3:4], 0.0, 0.34)
        # Re-clip after translation so no plate escapes the inpainted aperture.
        alpha *= mask[..., None]
        frame = locked_base * (1.0 - alpha) + moved[..., :3] * alpha
        process.stdin.write(np.clip(frame * 255.0, 0, 255).astype(np.uint8).tobytes())
    process.stdin.close()
    if process.wait() != 0:
        raise SystemExit("ffmpeg failed")
    manifest = {
        "schema_version": "1.0",
        "status": "research-proof",
        "source_sha256": SOURCE_SHA,
        "backplate_sha256": BACKPLATE_SHA,
        "plate_sha256": PLATE_SHA,
        "timeline": {"width": args.width, "height": args.height, "fps": FPS, "frames": FRAMES, "duration_s": DURATION},
        "mask": {"name": "rift-interior-only", "feather_px_at_source": 9, "outside_pixels_locked": True},
        "motion": {"carrier": "rift-fluid-wisps", "motion_scale": args.motion_scale, "max_translation_px_at_output": 9, "base_moves": False},
        "external_model_calls": 0,
        "runtime_adoption": False,
        "output": str(output),
    }
    (args.output_dir / "proof-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    render(parse_args())
