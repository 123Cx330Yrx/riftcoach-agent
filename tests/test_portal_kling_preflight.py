from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets" / "8e-portal"
MANIFEST = ASSETS / "portal-motion-preflight-kling-v3-omni-b1.json"
PROMPT = ASSETS / "portal-motion-brief-kling-v3-omni-b1.txt"
SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def test_kling_preflight_is_image_only_and_not_paid() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "prepared"
    assert manifest["candidate"] == "kling-v3-omni-image-reference-b1"
    assert manifest["request"] == {
        "model": "kling-v3-omni",
        "mode": "std",
        "input_mode": "single_image_reference",
        "duration_s": 8,
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "audio": False,
        "prompt_path": "docs/assets/8e-portal/portal-motion-brief-kling-v3-omni-b1.txt",
        "prompt_chars": 1833,
        "prompt_sha256": "eeae44fdf85b5dbf8092d818ea4b5981543bece7f3f249d71432e37feff4df05",
        "prompt_placeholders": ["<<<image_1>>>"]
    }
    assert manifest["references"]["image1"]["sha256"] == SOURCE_SHA
    assert manifest["preflight_gates"]["video_reference_used"] is False
    assert manifest["preflight_gates"]["price_readback_verified"] is True
    assert manifest["preflight_gates"]["paid_call_authorized"] is False
    assert manifest["preflight_gates"]["post_attempts_observed"] == 0


def test_kling_prompt_digest_and_placeholder_are_bound() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prompt = PROMPT.read_bytes()
    assert len(prompt.decode("utf-8")) == manifest["request"]["prompt_chars"]
    assert hashlib.sha256(prompt).hexdigest() == manifest["request"]["prompt_sha256"]
    text = prompt.decode("utf-8")
    assert "<<<image_1>>>" in text
    assert "<<<video_1>>>" not in text
    assert "platform into a dome/pool" in text
