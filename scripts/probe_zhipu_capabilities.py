"""Run explicitly authorized, bounded Zhipu capability/admission probes."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI

from app.evaluation.provider_capability_gate import (
    CapabilityProbeReport,
    ProbeScope,
)
from app.model_runtime import resolve_model_runtime_profile
from app.evaluation.provider_adapter_protocol import (
    AdapterProtocolSliceReport,
    AdapterProtocolSliceRunner,
)
from app.providers.config import load_zhipu_settings
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_probe import ZhipuCapabilityProbe


ProbeCliScope = Literal["p1_p5", "p1_diagnostic", "adapter_protocol"]
ProbeCliReport = CapabilityProbeReport | AdapterProtocolSliceReport


_DEFAULT_OUTPUTS = {
    "p1_p5": Path(
        "data/evaluation/results/provider_capabilities/zhipu_glm52_p1_p5.json"
    ),
    "p1_diagnostic": Path(
        "data/evaluation/results/provider_capabilities/"
        "zhipu_glm52_p1_diagnostic.json"
    ),
    "adapter_protocol": Path(
        "data/evaluation/results/provider_capabilities/zhipu_adapter_slice.json"
    ),
}

_MODEL_OUTPUT_PREFIXES = {
    "glm-5.2": "zhipu_glm52",
    "glm-5.3": "zhipu_glm53",
    "glm-5.3-flash": "zhipu_glm53_flash",
}


@dataclass(frozen=True)
class ProbeCliOptions:
    confirm_real_call: bool
    scope: ProbeCliScope
    max_calls: int
    output: Path | None


def run_cli(
    options: ProbeCliOptions,
    *,
    environ: Mapping[str, str] | None = None,
    repository_root: Path | None = None,
    client_factory: Callable[..., Any] = OpenAI,
    code_sha_reader: Callable[[Path], str] | None = None,
) -> ProbeCliReport:
    """Validate safety gates, run the selected bounded scope, and persist evidence."""

    if not options.confirm_real_call:
        raise RuntimeError("Real provider calls require explicit confirmation.")
    if options.scope not in _DEFAULT_OUTPUTS:
        raise ValueError("Unsupported capability probe scope.")
    expected_calls = {
        "p1_diagnostic": 1,
        "p1_p5": 5,
        "adapter_protocol": 3,
    }[options.scope]
    if options.max_calls != expected_calls:
        raise ValueError(
            f"{options.scope} requires an exact {expected_calls}-call budget."
        )

    root = (
        repository_root
        if repository_root is not None
        else Path(__file__).resolve().parents[1]
    ).resolve()
    allowed_root = (
        root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    settings = load_zhipu_settings(environ)
    output = options.output or _default_output_for_model(
        options.scope,
        settings.model,
    )
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError(
            "Output must remain inside the provider capability result directory."
        )

    code_sha = (code_sha_reader or _read_code_sha)(root)
    runtime_profile = resolve_model_runtime_profile(
        "zhipu",
        settings.model,
    )
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=(
            runtime_profile.transport_timeout_s
            if runtime_profile is not None
            else settings.default_timeout_s
        ),
        max_retries=0,
    )
    if options.scope == "adapter_protocol":
        report = AdapterProtocolSliceRunner(
            provider=ZhipuProvider(
                client=client,
                model=settings.model,
                profile=settings.thinking_profile,
                runtime_profile=runtime_profile,
            ),
            code_sha=code_sha,
            max_calls=options.max_calls,
            runtime_profile=runtime_profile,
        ).run()
    else:
        probe_scope: ProbeScope = options.scope
        report = ZhipuCapabilityProbe(
            client=client,
            model=settings.model,
            code_sha=code_sha,
            scope=probe_scope,
            max_calls=options.max_calls,
            profile=settings.thinking_profile,
        ).run()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def _default_output_for_model(scope: ProbeCliScope, model: str) -> Path:
    """Keep historical outputs stable while isolating known model families."""

    prefix = _MODEL_OUTPUT_PREFIXES.get(model.strip().lower())
    if prefix is None:
        return _DEFAULT_OUTPUTS[scope]
    suffix = {
        "p1_diagnostic": "p1_diagnostic.json",
        "p1_p5": "p1_p5.json",
        "adapter_protocol": "adapter_protocol.json",
    }[scope]
    return Path(
        "data/evaluation/results/provider_capabilities"
    ) / f"{prefix}_{suffix}"


def _read_code_sha(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str] | None = None) -> ProbeCliOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded Zhipu GLM capability experiment.",
    )
    parser.add_argument(
        "--confirm-real-call",
        action="store_true",
        help="Acknowledge that this command performs billable external calls.",
    )
    parser.add_argument(
        "--scope",
        choices=("p1_p5", "p1_diagnostic", "adapter_protocol"),
        default="p1_p5",
    )
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    max_calls = args.max_calls
    if max_calls is None:
        max_calls = {
            "p1_diagnostic": 1,
            "p1_p5": 5,
            "adapter_protocol": 3,
        }[args.scope]
    return ProbeCliOptions(
        confirm_real_call=args.confirm_real_call,
        scope=args.scope,
        max_calls=max_calls,
        output=args.output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    report = run_cli(_parse_args(argv), environ=os.environ)
    statuses = ", ".join(
        f"{case.case_id}={case.status}" for case in report.cases
    )
    print(
        f"provider={report.provider_id} model={report.requested_model} "
        f"calls={report.calls_used}/{report.max_calls} admitted={report.admitted}"
    )
    print(statuses)
    return 0 if report.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
