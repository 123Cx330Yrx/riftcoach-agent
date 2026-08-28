from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_layered_material_proof_v2"
CONTRACT = EXPERIMENT / "motion-contract.json"
COMPOSITION = EXPERIMENT / "index.html"
EXPECTED_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_v2_contract_locks_source_and_research_only_boundary() -> None:
    contract = _contract()
    assert contract["status"] == "research-proof-v2"
    assert contract["source"]["sha256"] == EXPECTED_SOURCE_SHA
    assert contract["timeline"] == {
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "frames": 192,
        "nominal_duration_s": 8.0,
        "closed_animation_duration_s": 7.958333,
    }
    assert contract["output_policy"] == {
        "repository_media": False,
        "runtime_adoption": False,
        "external_model_calls": 0,
        "output_must_be_outside_repository": True,
    }


def test_v2_contract_names_material_carriers_and_hard_gates() -> None:
    contract = _contract()
    assert contract["motion_model"] == "feathered source-texture displacement with deterministic phase clock"
    assert contract["motion_layers"] == [
        "locked-base",
        "rift-interior",
        "road-and-reflection",
        "crystal-refraction",
        "right-constellation-terrain",
        "depth-air-near-mid-far",
        "foreground-surface-light",
    ]
    assert contract["central_event"]["scope"] == ["crystal-refraction"]
    assert contract["central_event"]["window_s"] == [3.5, 5.5]
    assert "solid-rift-ring" in contract["prohibitions"]
    assert "solid-central-beam" in contract["prohibitions"]
    assert "full-frame-fog-sheet" in contract["prohibitions"]
    assert "visible-hud-lines" in contract["prohibitions"]
    assert contract["quality_gates"]["manual_full_scene_motion_required"] is True
    assert contract["quality_gates"]["manual_no_sticker_or_hud_required"] is True


def test_v2_composition_has_all_masks_without_remote_or_visible_line_overlay() -> None:
    html = COMPOSITION.read_text(encoding="utf-8")
    assert "portal-mother-image-source-v2.png" in html
    for marker in (
        "mask-rift",
        "mask-road",
        "mask-crystal",
        "mask-right",
        "mask-far",
        "mask-mid",
        "mask-near",
        "mask-foreground",
    ):
        assert marker in html
    for marker in (
        "layer-rift",
        "layer-road",
        "layer-crystal",
        "layer-right",
        "layer-far",
        "layer-mid",
        "layer-near",
        "layer-foreground",
    ):
        assert marker in html
    assert "feTurbulence" in html
    assert "feDisplacementMap" in html
    assert "data-phase" in html
    assert "stroke=" not in html
    assert "<line " not in html
    assert "<circle " not in html
    assert "http://" not in html
    assert "https://" not in html
