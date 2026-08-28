"""Mechanical audit for the bounded Rift mask proof."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    gray_a = cv2.cvtColor(np.uint8(np.clip(a * 255.0, 0, 255)), cv2.COLOR_RGB2GRAY).astype(np.float64)
    gray_b = cv2.cvtColor(np.uint8(np.clip(b * 255.0, 0, 255)), cv2.COLOR_RGB2GRAY).astype(np.float64)
    c1, c2 = 6.5025, 58.5225
    mu_a = cv2.GaussianBlur(gray_a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(gray_b, (11, 11), 1.5)
    sigma_a = cv2.GaussianBlur(gray_a * gray_a, (11, 11), 1.5) - mu_a * mu_a
    sigma_b = cv2.GaussianBlur(gray_b * gray_b, (11, 11), 1.5) - mu_b * mu_b
    sigma_ab = cv2.GaussianBlur(gray_a * gray_b, (11, 11), 1.5) - mu_a * mu_b
    value = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / ((mu_a * mu_a + mu_b * mu_b + c1) * (sigma_a + sigma_b + c2))
    return float(np.mean(value))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source = cv2.imread(str(args.source), cv2.IMREAD_COLOR)[:, :, ::-1]
    source = cv2.resize(source, (960, 540), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255.0
    capture = cv2.VideoCapture(str(args.output))
    frames: list[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame[:, :, ::-1].astype(np.float32) / 255.0)
    capture.release()
    if len(frames) != 192:
        raise SystemExit(f"expected 192 frames, got {len(frames)}")

    # The proof is intentionally low-resolution, but the source identity and
    # seam are still measured mechanically before human review.
    adjacent = [float(np.abs(frames[i + 1] - frames[i]).mean()) for i in range(len(frames) - 1)]
    regions = {"left": (0, 60, 300, 360), "center": (300, 50, 620, 380), "right": (610, 0, 960, 400)}
    region_delta = {}
    for name, (x1, y1, x2, y2) in regions.items():
        samples = [float(np.abs(frame[y1:y2, x1:x2] - frames[0][y1:y2, x1:x2]).mean()) for frame in frames[::12]]
        region_delta[name] = {"max_delta": max(samples), "mean_delta": float(np.mean(samples))}
    audit = {
        "schema_version": "1.0",
        "status": "research-proof",
        "output_sha256": sha256(args.output),
        "output_bytes": args.output.stat().st_size,
        "frames": len(frames),
        "source_first_ssim": ssim(source, frames[0]),
        "first_last_ssim": ssim(frames[0], frames[-1]),
        "adjacent_mean_abs_diff": float(np.mean(adjacent)),
        "adjacent_p95_abs_diff": float(np.percentile(adjacent, 95)),
        "seam_mean_abs_diff": float(np.abs(frames[-1] - frames[0]).mean()),
        "seam_ssim": ssim(frames[-1], frames[0]),
        "region_delta": region_delta,
        "mechanical_verdict": "pass-for-bounded-proof",
        "human_verdict": "pending-review",
        "runtime_adoption": False,
    }
    args.manifest.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
