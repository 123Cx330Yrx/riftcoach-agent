"""Run the explicitly confirmed, bounded DeepSeek V4 Pro protocol gate."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.provider_adoption import ExperimentPreparationReport
from app.evaluation.provider_protocol_experiment import (
    ProviderAdapterProtocolExperimentRecord,
    run_deepseek_adapter_protocol_experiment,
)
from app.providers.config import (
    DeepSeekSettings,
    create_deepseek_provider,
    load_deepseek_settings,
)
from app.providers.protocol import LLMProvider
from scripts.prepare_second_provider_experiment import (
    NoIoExperimentOptions,
    run_cli as run_no_io_preflight,
)


_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)


@dataclass(frozen=True)
class DeepSeekProtocolCliOptions:
    confirm_real_call: bool
    confirm_public_ci_success: bool
    public_ci_sha: str
    max_calls: int = 3
    output: Path = _DEFAULT_OUTPUT


PreflightRunner = Callable[..., ExperimentPreparationReport]
ProviderFactory = Callable[[DeepSeekSettings], LLMProvider]
EnvironmentLoader = Callable[[Path], Mapping[str, str]]


def run_cli(
    options: DeepSeekProtocolCliOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    preflight_runner: PreflightRunner | None = None,
    environment_loader: EnvironmentLoader | None = None,
    provider_factory: ProviderFactory = create_deepseek_provider,
) -> ProviderAdapterProtocolExperimentRecord:
    """Preflight before Key loading, then run and persist one immutable record."""

    if not options.confirm_real_call:
        raise RuntimeError("Real provider calls require explicit confirmation.")
    if options.max_calls != 3:
        raise ValueError("DeepSeek adapter protocol requires exactly 3 calls.")

    root = repository_root.resolve()
    output = _resolve_new_output(root, options.output)
    preflight = preflight_runner or _run_preflight
    preparation = preflight(
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        repository_root=root,
    )

    load_environment = environment_loader or _load_environment
    settings = load_deepseek_settings(load_environment(root))
    provider = provider_factory(settings)
    record = run_deepseek_adapter_protocol_experiment(
        preparation=preparation,
        provider=provider,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(record.model_dump_json(indent=2))
        stream.write("\n")
    return record


def _run_preflight(
    *,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    repository_root: Path,
) -> ExperimentPreparationReport:
    return run_no_io_preflight(
        NoIoExperimentOptions(
            public_ci_sha=public_ci_sha,
            confirm_public_ci_success=confirm_public_ci_success,
        ),
        repository_root=repository_root,
    )


def _load_environment(repository_root: Path) -> Mapping[str, str]:
    load_dotenv(repository_root / ".env")
    return os.environ


def _resolve_new_output(repository_root: Path, value: Path) -> Path:
    allowed_root = (
        repository_root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    output = value if value.is_absolute() else repository_root / value
    output = output.resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError(
            "Output must remain inside the provider capability result directory."
        )
    if output.suffix.lower() != ".json":
        raise ValueError("Output must be a JSON result file.")
    if output.exists():
        raise FileExistsError(
            "Provider protocol evidence is immutable and cannot be overwritten."
        )
    return output


def _parse_args(argv: Sequence[str] | None = None) -> DeepSeekProtocolCliOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded DeepSeek V4 Pro adapter protocol gate.",
    )
    parser.add_argument(
        "--confirm-real-call",
        action="store_true",
        help="Acknowledge up to three billable external Provider calls.",
    )
    parser.add_argument(
        "--confirm-public-ci-success",
        action="store_true",
        help="Confirm the exact public CI SHA completed successfully.",
    )
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--max-calls", type=int, default=3)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    values = parser.parse_args(argv)
    return DeepSeekProtocolCliOptions(
        confirm_real_call=values.confirm_real_call,
        confirm_public_ci_success=values.confirm_public_ci_success,
        public_ci_sha=values.public_ci_sha,
        max_calls=values.max_calls,
        output=values.output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    record = run_cli(_parse_args(argv))
    protocol = record.protocol
    statuses = ", ".join(
        f"{case.case_id}={case.status}" for case in protocol.cases
    )
    print(
        f"provider={protocol.provider_id} model={protocol.requested_model} "
        f"calls={protocol.calls_used}/{protocol.max_calls} "
        f"admitted={str(protocol.admitted).lower()}"
    )
    print(statuses)
    return 0 if protocol.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
