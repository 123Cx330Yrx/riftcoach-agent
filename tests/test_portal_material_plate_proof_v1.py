from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_material_plate_proof_v1"
CONTRACT = EXPERIMENT / "plate-contract.json"
RENDERER = EXPERIMENT / "generate_material_plates.py"
EXPECTED_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_plate_contract_locks_source_timeline_and_research_boundary() -> None:
    contract = _contract()
    assert contract["status"] == "material-plate-proof-v1"
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


def test_plate_contract_has_independent_roles_and_no_ghost_policy() -> None:
    contract = _contract()
    assert contract["plate_roles"] == [
        "rift-fluid",
        "road-caustic",
        "crystal-refraction",
        "right-field",
        "air-far",
        "air-mid",
        "air-near",
        "foreground-reflection",
    ]
    assert contract["plate_policy"] == {
        "format": "RGBA PNG",
        "source_pixels_copied": False,
        "opaque_geometry": False,
        "base_moves": False,
        "full_frame_veil": False,
        "max_alpha": 0.34,
    }
    assert contract["central_event"] == {
        "scope": ["crystal-refraction"],
        "window_s": [3.5, 5.5],
        "max_multiplier": 1.35,
    }


def test_renderer_is_local_seeded_and_does_not_duplicate_source_image() -> None:
    text = RENDERER.read_text(encoding="utf-8")
    for marker in (
        "RGBA PNG",
        "np.random.default_rng",
        "locked-base",
        "crystal-refraction",
        "alpha-only",
        "no external model calls",
    ):
        assert marker in text
    assert "portal-mother-image-source-v2.png" not in text
    assert "requests." not in text
    assert "http://" not in text
    assert "https://" not in text
