from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow() -> dict:
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
    )


def _web_scoped_commands(job: dict) -> str:
    commands: list[str] = []
    for step in job["steps"]:
        run = str(step.get("run", ""))
        working_directory = str(step.get("working-directory", "")).replace(
            "\\", "/"
        )
        if working_directory.rstrip("/") == "web":
            commands.append(run)
            continue

        if re.search(r"(?m)^\s*cd\s+web(?:/)?(?:\s+&&|\s*$)", run):
            commands.append(run)
            continue

        for line in run.splitlines():
            if re.search(
                r"\b(?:npm|npx)\b[^\n]*--prefix(?:=|\s+)web(?:/)?(?:\s|$)",
                line,
            ):
                commands.append(line)
    return "\n".join(commands)


def _docker_copy_sources(dockerfile: str) -> tuple[str, ...]:
    logical_lines = re.sub(r"\\\r?\n\s*", " ", dockerfile).splitlines()
    sources: list[str] = []
    for line in logical_lines:
        match = re.match(r"^\s*(?:COPY|ADD)\s+(.*)$", line, re.IGNORECASE)
        if match is None:
            continue

        arguments = re.sub(r"^(?:--\S+\s+)+", "", match.group(1)).strip()
        if arguments.startswith("["):
            values = json.loads(arguments)
        else:
            values = shlex.split(arguments, posix=True)
        sources.extend(str(value) for value in values[:-1])
    return tuple(sources)


def test_pytest_job_blocks_on_all_frontend_quality_gates() -> None:
    job = _workflow()["jobs"]["pytest"]
    setup_node = next(
        step
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    )
    cache_paths = {
        line.strip()
        for line in str(setup_node["with"]["cache-dependency-path"]).splitlines()
        if line.strip()
    }

    assert "web/package-lock.json" in cache_paths

    commands = _web_scoped_commands(job)
    assert re.search(r"\bnpm\s+ci\s+--ignore-scripts\b", commands)
    assert re.search(r"\bnpm\s+run\s+typecheck\b", commands)
    assert re.search(r"\bnpm\s+run\s+test:unit\b", commands)
    assert re.search(r"\bnpm\s+run\s+build\b", commands)
    assert re.search(r"\bplaywright\s+install\b[^\n]*\bchromium\b", commands)
    assert re.search(
        r"\bnpm\s+run\s+test:e2e\b|\bplaywright\s+test\b",
        commands,
    )


def test_batch_d_runtime_image_does_not_copy_frontend_sources() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_sources = _docker_copy_sources(dockerfile)
    frontend_sources = tuple(
        source
        for source in copy_sources
        if source.replace("\\", "/").lstrip("./").split("/", 1)[0] == "web"
        or source.replace("\\", "/") in {".", "./"}
    )

    assert frontend_sources == (), (
        "Batch D is fixture-backed UI verification only; Dockerfile must not "
        f"copy web sources into the Python runtime image: {frontend_sources}"
    )
