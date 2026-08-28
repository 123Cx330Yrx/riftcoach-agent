from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets" / "8e-portal"
MANIFEST = ASSETS / "portal-motion-preflight-kling-v3-omni-video-image-b2.json"
PROMPT = ASSETS / "portal-motion-brief-kling-v3-omni-video-image-b2.txt"


def test_kling_b2_preflight_binds_video_and_image_roles() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "prepared"
    assert manifest["candidate"] == "kling-v3-omni-video-image-b2"
    assert manifest["references"]["video1"]["source_task_id"] == "task_w6ggXo15mMMw5Y3KMu9CfLK1QLevULvW"
    assert manifest["references"]["video1"]["refer_type"] == "base"
    assert manifest["references"]["video1"]["keep_original_sound"] == "no"
    assert manifest["references"]["video1"]["result_url_policy"].endswith("in memory only")
    assert manifest["references"]["image1"]["sha256"] == "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
    assert manifest["request"]["prompt_placeholders"] == ["<<<video_1>>>", "<<<image_1>>>"]
    assert manifest["request"]["audio_field"] == "omitted because video_list is present"


def test_kling_b2_prompt_digest_and_failed_mode_anti_patterns_are_bound() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw = PROMPT.read_bytes()
    text = raw.decode("utf-8")
    assert len(text) == 1856
    assert hashlib.sha256(raw).hexdigest() == "6669494364216c8ac366ac4c9ee2f354632b438e253625dbdadee1299eb86b56"
    assert "<<<video_1>>>" in text and "<<<image_1>>>" in text
    assert "solid torus" in text and "isolated gold stars" in text
    assert "platform geometry unchanged" in text


def test_kling_b2_preflight_remains_unsubmitted_and_one_post() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gates = manifest["preflight_gates"]
    assert gates["source_task_get_only_required"] is True
    assert gates["source_result_url_persisted"] is False
    assert gates["runner_parse_verified"] is True
    assert gates["source_get_path_verified"] is True
    assert gates["single_post_path_verified"] is True
    assert gates["paid_call_authorized"] is False
    assert gates["source_get_attempts_observed"] == 0
    assert gates["post_attempts_observed"] == 0
    assert manifest["pricing_readback"]["quoted_total_cny"] == 3.696
