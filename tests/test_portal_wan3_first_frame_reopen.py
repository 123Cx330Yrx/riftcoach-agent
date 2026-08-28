from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "docs/assets/8e-portal/portal-motion-preflight-wan3-first-frame-reopen-v1.json"
PROMPT = ROOT / "docs/assets/8e-portal/portal-motion-brief-wan3-first-frame-reopen-v1.txt"
SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def test_wan_reopen_preflight_uses_first_frame_only_and_no_runtime() -> None:
    contract = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    assert contract["transport"]["model"] == "wan3.0-video"
    assert contract["source"]["sha256"] == SOURCE_SHA
    assert contract["parameters"] == {
        "resolution": "1080P",
        "ratio": "adaptive",
        "duration_s": 12,
        "audio": False,
        "prompt_extend": False,
        "watermark": False,
        "seed": 127,
    }
    assert contract["guardrails"]["max_post"] == 1
    assert contract["guardrails"]["max_recovery_post"] == 0
    assert contract["paid_call_authorized"] is True
    assert contract["preflight_observed"]["post_attempts_observed"] == 0


def test_prompt_digest_and_motion_only_brief_are_bound() -> None:
    contract = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    assert hashlib.sha256(PROMPT.read_bytes()).hexdigest() == contract["prompt"]["sha256"]
    brief = PROMPT.read_text(encoding="utf-8")
    assert "first frame" in brief.lower()
    assert "No separate burst event" in brief
    assert "No camera movement" in brief
