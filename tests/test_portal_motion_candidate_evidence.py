"""Regression checks for the repo-tracked Portal candidate evidence ledger."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/assets/8e-portal/portal-motion-candidate-tx-v1.json"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_evidence_is_explicitly_research_only() -> None:
    evidence = _load()
    assert evidence["schema_version"] == "1.0"
    assert evidence["status"] == "research-candidate"
    assert evidence["source"]["sha256"] == "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
    assert evidence["interpretation"]["adoption_status"] == "not-adopted"


def test_both_codecs_meet_the_frozen_portal_mechanical_candidate_gates() -> None:
    evidence = _load()
    assert {item["format"] for item in evidence["candidates"]} == {"mp4", "webm"}
    for item in evidence["candidates"]:
        assert item["width"] == 1280
        assert item["height"] == 720
        assert item["duration_s"] == 8.0
        assert item["fps"] == 24.0
        assert item["pix_fmt"] == "yuv420p"
        assert item["color"] == "bt709/tv"
        assert item["has_audio"] is False
        assert item["source_to_first_frame_ssim"] >= 0.95
        assert item["poster_to_first_frame_ssim"] >= 0.98
        assert item["seam_dssim"] <= max(1.5 * item["adjacent_dssim_p95"], 0.03)


def test_identity_split_keeps_geometry_and_motion_as_separate_signals() -> None:
    evidence = _load()
    assert evidence["interpretation"]["baseline_source_encode_ssim"] >= 0.995
    for item in evidence["candidates"]:
        split = item["identity_fault_split"]
        assert split["edge_correlation"] >= 0.995
        assert split["temporal_luma_mean_abs_8bit"] > 0
        assert split["left_mean_abs"] > 0
        assert split["center_mean_abs"] > 0
        assert split["right_mean_abs"] > 0
        assert split["near_mean_abs"] > 0
        assert split["mid_mean_abs"] > 0
        assert split["far_mean_abs"] > 0
