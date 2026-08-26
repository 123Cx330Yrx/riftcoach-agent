from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "portal_cinematic_proof"
CONTRACT_PATH = EXPERIMENT / "motion-contract.json"
COMPOSITION_PATH = EXPERIMENT / "index.html"
RENDERER_PATH = ROOT / "scripts" / "render_portal_cinematic_proof.py"

EXPECTED_SOURCE_SHA = "8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e"
EXPECTED_SYSTEMS = {
    "base-structure",
    "left-atmosphere",
    "rift-interior",
    "route-energy",
    "crystal-tower",
    "star-map",
    "foreground",
    "global-light",
}


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _load_renderer():
    spec = importlib.util.spec_from_file_location("portal_cinematic_proof_renderer", RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_motion_contract_freezes_source_timeline_and_systems() -> None:
    contract = _contract()

    assert set(contract) == {
        "schema_version",
        "status",
        "source",
        "timeline",
        "renderer",
        "motion_systems",
        "output_policy",
        "quality_gates",
        "fallback",
    }
    assert contract["schema_version"] == "1.0"
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
    assert contract["renderer"] == {
        "name": "hyperframes",
        "version": "0.8.14",
        "telemetry": False,
        "auth": False,
        "network_assets": False,
    }
    systems = contract["motion_systems"]
    assert isinstance(systems, list)
    assert {row["id"] for row in systems} == EXPECTED_SYSTEMS
    assert all(row["periodic"] is True for row in systems)


def test_contract_keeps_outputs_research_only_and_a_line_reversible() -> None:
    contract = _contract()

    assert contract["output_policy"] == {
        "repository_media": False,
        "runtime_adoption": False,
        "audio": False,
        "randomness": False,
        "external_model_calls": 0,
        "output_must_be_outside_repository": True,
    }
    assert contract["fallback"] == {
        "on_hybrid_failure": "proof_fail_reopen_corrected_a",
        "a_prompt_style": "short-motion-only",
        "a_input_mode": "first-frame-plus-deterministic-seam",
        "same_source_first_last_retry": False,
    }


def test_composition_declares_every_system_without_remote_runtime() -> None:
    html = COMPOSITION_PATH.read_text(encoding="utf-8")

    for system in EXPECTED_SYSTEMS:
        assert f'id="{system}"' in html
    assert 'src="assets/portal-mother-image-source-v2.png"' in html
    assert 'data-duration="8"' in html
    assert 'data-width="1920"' in html
    assert 'data-height="1080"' in html
    assert "7.958333s" in html
    lowered = html.casefold()
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert "<audio" not in lowered
    assert "<video" not in lowered
    assert "<canvas" not in lowered
    assert "math.random" not in lowered
    assert "transform:" not in _extract_rule(html, "#base-structure")


def _extract_rule(html: str, selector: str) -> str:
    start = html.index(f"{selector} {{")
    end = html.index("}", start)
    return html[start:end]


def test_renderer_dry_run_verifies_identities_and_safe_commands(tmp_path: Path) -> None:
    renderer = _load_renderer()
    hyperframes_root = tmp_path / "hyperframes"
    package = hyperframes_root / "node_modules" / "hyperframes" / "package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"version": "0.8.14"}), encoding="utf-8")
    executable = hyperframes_root / "node_modules" / ".bin" / "hyperframes.cmd"
    executable.parent.mkdir(parents=True)
    executable.write_text("@echo off\r\n", encoding="utf-8")
    browser = tmp_path / "chrome-headless-shell.exe"
    browser.write_bytes(b"browser")
    output = tmp_path / "out"

    result = renderer.build_plan(
        project_root=ROOT,
        hyperframes_root=hyperframes_root,
        output_dir=output,
        ffmpeg_path=Path("C:/tools/ffmpeg.exe"),
        ffprobe_path=Path("C:/tools/ffprobe.exe"),
        browser_path=browser,
    )

    assert result.source_sha256 == EXPECTED_SOURCE_SHA
    assert result.hyperframes_version == "0.8.14"
    assert result.output_dir == output.resolve()
    assert result.external_model_calls == 0
    assert result.network_assets is False
    assert result.browser_path == browser.resolve()
    commands = [list(command) for command in result.commands]
    assert commands[0][1:3] == ["check", str(result.work_dir)]
    assert "png-sequence" in commands[1]
    assert "--start_number" not in commands[2]
    assert commands[2][commands[2].index("-start_number") + 1] == "1"
    assert "-pix_fmt" in commands[2] and "yuv420p" in commands[2]
    flat = " ".join(part for command in commands for part in command).casefold()
    for forbidden in (" npx ", " auth ", " cloud ", " publish ", " telemetry "):
        assert forbidden not in f" {flat} "


def test_renderer_rejects_repository_output_and_version_drift(tmp_path: Path) -> None:
    renderer = _load_renderer()
    hyperframes_root = tmp_path / "hyperframes"
    package = hyperframes_root / "node_modules" / "hyperframes" / "package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"version": "0.8.15"}), encoding="utf-8")
    executable = hyperframes_root / "node_modules" / ".bin" / "hyperframes.cmd"
    executable.parent.mkdir(parents=True)
    executable.write_text("@echo off\r\n", encoding="utf-8")
    browser = tmp_path / "chrome-headless-shell.exe"
    browser.write_bytes(b"browser")

    with pytest.raises(ValueError, match="hyperframes_version_mismatch"):
        renderer.build_plan(
            project_root=ROOT,
            hyperframes_root=hyperframes_root,
            output_dir=tmp_path / "out",
            ffmpeg_path=Path("C:/tools/ffmpeg.exe"),
            ffprobe_path=Path("C:/tools/ffprobe.exe"),
            browser_path=browser,
        )

    package.write_text(json.dumps({"version": "0.8.14"}), encoding="utf-8")
    with pytest.raises(ValueError, match="output_inside_repository"):
        renderer.build_plan(
            project_root=ROOT,
            hyperframes_root=hyperframes_root,
            output_dir=ROOT / "tmp" / "proof",
            ffmpeg_path=Path("C:/tools/ffmpeg.exe"),
            ffprobe_path=Path("C:/tools/ffprobe.exe"),
            browser_path=browser,
        )


def test_renderer_environment_pins_existing_browser_and_disables_updates(tmp_path: Path) -> None:
    renderer = _load_renderer()
    browser = tmp_path / "chrome-headless-shell.exe"
    browser.write_bytes(b"browser")
    plan = renderer.RenderPlan(
        project_root=ROOT,
        hyperframes_root=tmp_path,
        hyperframes_version="0.8.14",
        source_path=ROOT / "docs/assets/8e-portal/portal-mother-image-source-v2.png",
        source_sha256=EXPECTED_SOURCE_SHA,
        browser_path=browser,
        output_dir=tmp_path / "out",
        work_dir=tmp_path / "out/work",
        frames_dir=tmp_path / "out/frames",
        preview_path=tmp_path / "out/preview.mp4",
        commands=(),
        external_model_calls=0,
        network_assets=False,
    )

    environment = renderer._safe_environment(plan)

    assert environment["HYPERFRAMES_BROWSER_PATH"] == str(browser)
    assert environment["PRODUCER_HEADLESS_SHELL_PATH"] == str(browser)
    assert environment["HYPERFRAMES_NO_TELEMETRY"] == "1"
    assert environment["NO_UPDATE_NOTIFIER"] == "1"
