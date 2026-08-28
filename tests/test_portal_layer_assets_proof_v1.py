from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_layer_assets_proof_v1"
CONTRACT = EXPERIMENT / "layer-contract.json"
RENDERER = EXPERIMENT / "render_material_layers.py"
EXPECTED_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_layer_contract_locks_source_and_research_only_boundary() -> None:
    contract = _contract()
    assert contract["status"] == "layer-assets-proof-v1"
    assert contract["source"]["sha256"] == EXPECTED_SOURCE_SHA
    assert contract["timeline"] == {
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "frames": 192,
        "duration_s": 8.0,
    }
    assert contract["output_policy"] == {
        "external_model_calls": 0,
        "repository_media": False,
        "runtime_adoption": False,
    }


def test_layer_contract_names_source_derived_carriers_and_occlusion_rules() -> None:
    contract = _contract()
    assert contract["layer_names"] == [
        "locked-base",
        "rift-energy",
        "road-reflection",
        "crystal-refraction",
        "right-constellation-terrain",
        "air-far-mid-near",
        "foreground-surface-light",
    ]
    assert contract["alpha_policy"] == "source-derived-high-energy-only"
    assert contract["central_event"] == {
        "scope": ["crystal-refraction"],
        "window_s": [3.5, 5.5],
        "max_alpha_multiplier": 1.35,
    }
    assert contract["occlusion_rules"] == {
        "base_geometry_moves": False,
        "opaque_structure_moves": False,
        "layer_shift_px_max": 12,
        "full_frame_overlay": False,
    }


def test_renderer_is_local_deterministic_and_preserves_base() -> None:
    text = RENDERER.read_text(encoding="utf-8")
    for marker in (
        "source-derived-high-energy-only",
        "Image.Resampling.LANCZOS",
        "np.roll",
        "locked-base",
        "central_event",
        "no external model calls",
    ):
        assert marker in text
    assert "requests." not in text
    assert "http://" not in text
    assert "https://" not in text
    assert "global_tint" not in text
