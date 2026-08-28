from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_masked_inpaint_plate_proof_v1"
CONTRACT = EXPERIMENT / "plate-contract.json"
RENDERER = EXPERIMENT / "render_masked_inpaint_proof.py"
SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"


def test_contract_locks_bounded_mask_and_research_boundary() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "masked-inpaint-plate-proof-v1"
    assert contract["source"]["sha256"] == SOURCE_SHA
    assert contract["mask"]["name"] == "rift-interior-only"
    assert contract["mask"]["outside_pixels_locked"] is True
    assert contract["output_policy"] == {
        "external_model_calls": 0,
        "repository_media": False,
        "runtime_adoption": False,
        "research_only": True,
    }


def test_contract_requires_independent_rgba_plate_and_bounded_backplate() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["backplate"]["role"].startswith("bounded Rift interior")
    assert contract["plate"]["role"].startswith("independent transparent")
    assert contract["motion"]["base_moves"] is False
    assert contract["motion"]["global_tint"] is False
    assert contract["motion"]["full_frame_veil"] is False


def test_renderer_has_no_network_or_source_duplicate_shortcuts() -> None:
    text = RENDERER.read_text(encoding="utf-8")
    for marker in ("outside this feathered mask", "RGBA", "periodic", "base_moves", "runtime_adoption"):
        assert marker in text
    assert "http://" not in text
    assert "https://" not in text
    assert "requests." not in text
    assert "np.roll(source" not in text
