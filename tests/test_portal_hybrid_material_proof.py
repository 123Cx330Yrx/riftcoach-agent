from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_hybrid_material_proof"
CONTRACT = EXPERIMENT / "motion-contract.json"
COMPOSITION = EXPERIMENT / "index.html"
EXPECTED_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_hybrid_contract_locks_source_and_stays_research_only() -> None:
    contract = _contract()
    assert contract["status"] == "research-proof"
    assert contract["source"] == {
        "path": "docs/assets/8e-portal/portal-mother-image-source-v2.png",
        "sha256": EXPECTED_SOURCE_SHA,
        "runtime_name": "assets/portal-mother-image-source-v2.png",
    }
    assert contract["timeline"] == {
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "frames": 192,
        "nominal_duration_s": 8.0,
        "closed_animation_duration_s": 7.958333,
    }
    assert contract["motion_model"] == "masked source-texture displacement and low-frequency local light only"
    assert contract["output_policy"] == {
        "repository_media": False,
        "runtime_adoption": False,
        "external_model_calls": 0,
        "output_must_be_outside_repository": True,
    }


def test_hybrid_composition_has_material_masks_without_visible_line_overlay() -> None:
    html = COMPOSITION.read_text(encoding="utf-8")
    assert "portal-mother-image-source-v2.png" in html
    assert "feDisplacementMap" in html
    assert "feTurbulence" in html
    assert "animateTransform" in html
    assert "clipPath" in html
    assert "stroke=" not in html
    assert "<line " not in html
    assert "<circle " not in html
    assert "http://" not in html
    assert "https://" not in html


def test_hybrid_composition_mentions_all_required_material_carriers() -> None:
    html = COMPOSITION.read_text(encoding="utf-8")
    for marker in ("clip-rift", "clip-road", "clip-crystal", "clip-column", "clip-right", "clip-far", "clip-mid", "clip-near", "clip-reflection"):
        assert marker in html
    for marker in ("rift-texture", "road-texture", "crystal-texture", "right-texture", "air-texture", "reflection-texture"):
        assert marker in html
